from collections import Counter
import json
from pathlib import Path
import threading
from backend.app.core.config import Settings
from backend.app.core.errors import APIError
from backend.app.schemas.api import SearchRequest, SearchResponse, BookResponse
from backend.app.rag.ingestion.catalog import BOOKS
from backend.app.rag.ingestion.models import Passage
from backend.app.rag.ingestion.pipeline import file_sha256, verify_run
from backend.app.rag.retrieval.index import SearchIndex, read_records


class Library:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.indexes = {}
        self.passages = {}
        self.ingestion_report = {}
        self.evaluations = {}
        self.embedder = None
        self.dense_unavailable = False
        self.ready = False
        self._model_lock = threading.Lock()
        self._stats_lock = threading.Lock()
        self._search_slots = threading.BoundedSemaphore(2)
        self.searches = 0
        self.total_latency = 0.0
        self.last_latency = None

    def load(self):
        root = self.settings.project_root
        handoff = json.loads((root / 'storage/manifests/phase3-handoff.json').read_text())
        for policy in ['reviewed', 'experimental']:
            if policy == 'experimental' and not self.settings.allow_experimental_search:
                continue
            directory = root / handoff[f'{policy}_index']
            if file_sha256(directory / 'manifest.json') != handoff[f'{policy}_manifest_sha256']:
                raise ValueError('Index handoff checksum differs')
            self.indexes[policy] = SearchIndex(directory)
        source_handoff = json.loads((root / 'storage/manifests/phase2-handoff.json').read_text())
        if any(index.config['source_manifest_checksum'] != source_handoff['reviewed_manifest_sha256']
               for index in self.indexes.values()):
            raise ValueError('Reviewed source ledger/index mismatch')
        if source_handoff.get('excerpt_reviews'):
            checksum = file_sha256(root / source_handoff['excerpt_reviews'])
            if checksum != source_handoff['excerpt_reviews_sha256'] or any(index.config.get('excerpt_reviews_sha256') != checksum for index in self.indexes.values()):
                raise ValueError('Excerpt review ledger/index mismatch')
        reviewed = root / source_handoff['reviewed_run']
        candidate = root / source_handoff['candidate_run']
        for path, key in [(reviewed, 'reviewed_manifest_sha256'), (candidate, 'candidate_manifest_sha256')]:
            if file_sha256(path / 'manifest.json') != source_handoff[key]:
                raise ValueError('Source handoff checksum differs')
            verify_run(path)
        self.passages = {p.id: p for p in read_records(reviewed / 'passages.jsonl', Passage)}
        self.ingestion_report = json.loads((candidate / 'report.json').read_text())
        for policy in self.indexes:
            path = root / handoff[f'{policy}_evaluation']
            if path.exists():
                report = json.loads(path.read_text())
                if report.get('corpus_checksum') == self.indexes[policy].config['corpus_checksum']:
                    self.evaluations[policy] = report
        self.ready = True

    def require_ready(self):
        if not self.ready:
            raise APIError(503, 'corpus_unavailable', 'The checked corpus is unavailable; run ingestion and index setup first.')

    def get_embedder(self):
        with self._model_lock:
            if self.dense_unavailable:
                return None
            if self.embedder is None:
                try:
                    from backend.app.rag.embeddings.minilm import MiniLM
                    model = MiniLM(local_only=True)
                    if any(model.identity != index.config['model'] for index in self.indexes.values()):
                        raise ValueError('Model metadata mismatch')
                    self.embedder = model
                except (OSError, ValueError, ImportError):
                    # Lexical search remains available without a model download.
                    self.dense_unavailable = True
                    return None
            return self.embedder

    def search(self, request: SearchRequest) -> SearchResponse:
        self.require_ready()
        if request.policy == 'experimental' and not self.settings.allow_experimental_search:
            raise APIError(403, 'experimental_disabled', 'Experimental search must be enabled explicitly by the server operator.')
        if not self._search_slots.acquire(blocking=False):
            raise APIError(503, 'search_busy', 'Search capacity is busy. Try again shortly.')
        try:
            index = self.indexes[request.policy]
            mode, warnings = request.mode, []
            if mode != 'bm25':
                model = self.get_embedder()
                if model is None:
                    mode = 'bm25'
                    warnings.append('Dense model unavailable; used BM25 without downloading a model.')
                else:
                    index.embedder = model
                    if len(model.tokenizer(request.query, add_special_tokens=False, verbose=False)['input_ids']) > model.max_tokens:
                        raise APIError(422, 'query_token_limit', 'Shorten the query for dense/hybrid search, or select BM25. No text was truncated.')
            result = index.search(request.query, mode=mode, top_k=request.top_k,
                                  book_id=request.book_id, chapter=request.chapter)
            for hit in result['hits']:
                c = hit['chunk']
                hit['pdf_url'] = f"/api/books/{c['book_id']}/source#page={c['page_start']}"
            with self._stats_lock:
                self.searches += 1
                self.total_latency += result['latency_ms']
                self.last_latency = result['latency_ms']
            if request.policy == 'experimental':
                warnings.append('Experimental corpus includes unreviewed candidates; do not treat them as verified sources.')
            return SearchResponse(**result, requested_mode=request.mode, warnings=warnings)
        finally:
            self._search_slots.release()

    def books(self):
        counts = Counter(p.book_id for p in self.passages.values() if p.validation_status == 'verified')
        indexed = {policy: Counter(c.book_id for c in index.chunks) for policy, index in self.indexes.items()}
        records = []
        for book in BOOKS.values():
            report = self.ingestion_report.get('books', {}).get(book.id, {})
            reviewed_count = indexed.get('reviewed', {}).get(book.id, 0)
            status = 'OCR_PENDING' if book.ocr_pending else 'partially_available' if reviewed_count else 'processing' if report else 'not_ingested'
            records.append(BookResponse(id=book.id, title=book.title, author=book.author, status=status,
                                        source_available=(self.settings.project_root/'data/raw'/book.filename).exists(),
                                        pages_extracted=report.get('pages_extracted', 0),
                                        candidate_passages=report.get('candidate_passages', 0),
                                        verified_passages=counts[book.id],
                                        verified_excerpts=sum(c.book_id == book.id and 'excerpt_source_review' in c.review_flags for c in self.indexes.get('reviewed', []).chunks) if 'reviewed' in self.indexes else 0,
                                        reviewed_index_chunks=reviewed_count,
                                        experimental_index_chunks=indexed.get('experimental', {}).get(book.id, 0),
                                        source_url=f'/api/books/{book.id}/source'))
        return records

    def statistics(self):
        self.require_ready()
        with self._stats_lock:
            return dict(books=self.books(), model_details=self.indexes['reviewed'].config['model'],
                        searches_completed=self.searches, mean_search_latency_ms=self.total_latency/self.searches if self.searches else None,
                        last_search_latency_ms=self.last_latency,
                        generation_enabled=self.settings.enable_generation and bool(self.settings.deepseek_api_key.get_secret_value()),
                        experimental_search_enabled=self.settings.allow_experimental_search,
                        warning='Small AI-assisted reviewed corpus, including scoped excerpts from unreviewed parents. Not a representative benchmark.')
