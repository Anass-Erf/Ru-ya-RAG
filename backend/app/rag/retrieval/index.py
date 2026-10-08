"""Immutable FAISS indexes with source and model compatibility checks."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import tempfile
import time
import sys

import faiss
import numpy as np
from backend.app.rag.ingestion.models import Page, Passage
from backend.app.rag.ingestion.pipeline import verify_run, file_sha256, json_text, write_jsonl
from backend.app.rag.chunking.core import Chunk, chunk_passage, exclusion_reason
from .lexical import BM25, rrf
from backend.app.rag.chunking.excerpts import reviewed_excerpts

INDEX_VERSION = 1


def read_records(path, model):
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            if line.strip():
                yield model.model_validate_json(line)


def read_corpus(root: Path):
    handoff = json.loads((root / 'storage/manifests/phase2-handoff.json').read_text())
    candidate, reviewed = root / handoff['candidate_run'], root / handoff['reviewed_run']
    for path, key in [(candidate, 'candidate_manifest_sha256'), (reviewed, 'reviewed_manifest_sha256')]:
        if file_sha256(path / 'manifest.json') != handoff[key]:
            raise ValueError('Handoff manifest checksum mismatch')
        verify_run(path)
    originals = {p.id: p for p in read_records(candidate / 'passages.jsonl', Passage)}
    passages = list(read_records(reviewed / 'passages.jsonl', Passage))
    if len(passages) != len(originals) or {p.id for p in passages} != set(originals):
        raise ValueError('Reviewed corpus IDs differ from source corpus')
    for p in passages:
        fields = {'validation_status', 'validated_text'}
        if p.model_dump(exclude=fields) != originals[p.id].model_dump(exclude=fields):
            raise ValueError('Reviewed passage content differs from candidate source')
    rows = {}
    for page in read_records(candidate / 'pages.jsonl', Page):
        for line in page.lines:
            rows[(page.book_id, page.pdf_page, line.line_number)] = line
    return passages, rows, handoff


def build_index(root: Path, output_root: Path, embedder, policy='reviewed', max_tokens=120, overlap=16):
    if max_tokens > embedder.max_tokens:
        raise ValueError('Chunk token budget exceeds model capacity')
    passages, rows, handoff = read_corpus(root)
    chunks, rejected = [], []
    for p in passages:
        reason = exclusion_reason(p, policy)
        if reason:
            rejected.append({'passage_id': p.id, 'reason': reason})
        else:
            chunks.extend(chunk_passage(p, embedder.tokenizer, rows, max_tokens=max_tokens,
                                        overlap_tokens=overlap, policy=policy))
    # Explicit excerpt reviews can admit clean spans from an otherwise held-out parent.
    chunks.extend(reviewed_excerpts(root, passages, rows, embedder.tokenizer, handoff, max_tokens, policy))
    if not chunks:
        raise ValueError('No eligible chunks; refusing empty index')
    if len({c.id for c in chunks}) != len(chunks):
        raise ValueError('Duplicate chunk IDs')
    corpus_hash = hashlib.sha256(''.join(c.model_dump_json() + '\n' for c in chunks).encode()).hexdigest()
    rag = Path(__file__).resolve().parents[1]
    code = {str(p.relative_to(rag)): file_sha256(p) for folder in ['chunking', 'embeddings', 'retrieval']
            for p in sorted((rag / folder).glob('*.py'))}
    config = {'index_version': INDEX_VERSION, 'model': embedder.identity, 'corpus_checksum': corpus_hash,
              'policy': policy, 'max_tokens': max_tokens, 'overlap_tokens': overlap,
              'source_manifest_checksum': handoff['reviewed_manifest_sha256'],
              'excerpt_reviews_sha256': handoff.get('excerpt_reviews_sha256'),
              'implementation': code, 'lexical': {'normalization': 'arabic-NFKC-clitics-explicit-aliases-v2',
              'k1': 1.5, 'b': .75, 'symbol_bonus': 2.0}, 'rrf_constant': 60,
              'dependencies': {name: importlib.metadata.version(name) for name in ['numpy', 'faiss-cpu', 'sentence-transformers']}}
    version = hashlib.sha256(json_text(config).encode()).hexdigest()[:24]
    destination = output_root / version
    if destination.exists():
        verify_run(destination)
        if json.loads((destination/'manifest.json').read_text())['config'] != config:
            raise ValueError('Index configuration mismatch')
        return destination, True
    output_root.mkdir(parents=True, exist_ok=True)
    # Reuse only checksum-verified vectors for the exact corpus/model pair.
    # Changes to lexical code or file handling need not re-embed identical text.
    faiss.omp_set_num_threads(2)
    index = None
    for existing_path in sorted(output_root.iterdir()):
        if not (existing_path / 'manifest.json').is_file():
            continue
        existing_manifest = json.loads((existing_path / 'manifest.json').read_text())
        old = existing_manifest.get('config', {})
        if old.get('corpus_checksum') == corpus_hash and old.get('model') == embedder.identity:
            verify_run(existing_path)
            index = faiss.read_index(str(existing_path / 'vectors.faiss'))
            break
    print(f"{policy}: {len(chunks)} chunks; {'reusing matching vectors' if index is not None else 'encoding on CPU'}", file=sys.stderr)
    if index is None:
        vectors = embedder.encode([c.text for c in chunks])
        if vectors.shape != (len(chunks), embedder.identity['dimension']) or not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-4):
            raise ValueError('Embedding dimensions or normalization invalid')
        index = faiss.IndexFlatIP(vectors.shape[1]); index.add(vectors)
    if index.ntotal != len(chunks) or index.d != embedder.identity['dimension'] or index.metric_type != faiss.METRIC_INNER_PRODUCT:
        raise ValueError('Cached vector index is incompatible')
    with tempfile.TemporaryDirectory(prefix='.index-', dir=output_root) as temporary:
        stage = Path(temporary) / 'run'; stage.mkdir()
        write_jsonl(stage / 'chunks.jsonl', chunks)
        write_jsonl(stage / 'excluded_passages.jsonl', rejected)
        faiss.write_index(index, str(stage / 'vectors.faiss'))
        report = {'policy': policy, 'passages_input': len(passages), 'passages_admitted': len({c.parent_entry_id for c in chunks}),
                  'chunks': len(chunks), 'excluded_by_reason': dict(Counter(r['reason'] for r in rejected)),
                  'book_counts': dict(Counter(c.book_id for c in chunks)),
                  'validation_counts': dict(Counter(c.validation_status for c in chunks)),
                  'warning': 'Experimental candidates are not source-verified.' if policy == 'experimental' else 'Source review was AI-assisted, not scholarly approval.'}
        (stage / 'report.json').write_text(json_text(report))
        manifest = {'run_id': version, 'created_at': datetime.now(timezone.utc).isoformat(), 'config': config,
                    'outputs': {p.name: file_sha256(p) for p in sorted(stage.iterdir())}}
        (stage / 'manifest.json').write_text(json_text(manifest))
        stage.rename(destination)
    return destination, False


class SearchIndex:
    def __init__(self, directory: Path, embedder=None):
        manifest = verify_run(directory)
        self.config = manifest['config']
        if self.config['index_version'] != INDEX_VERSION:
            raise ValueError('Unsupported index version')
        self.chunks = list(read_records(directory / 'chunks.jsonl', Chunk))
        corpus_hash = hashlib.sha256(''.join(c.model_dump_json() + '\n' for c in self.chunks).encode()).hexdigest()
        if corpus_hash != self.config['corpus_checksum']:
            raise ValueError('Corpus checksum mismatch')
        self.index = faiss.read_index(str(directory / 'vectors.faiss'))
        if self.index.ntotal != len(self.chunks) or self.index.d != self.config['model']['dimension']:
            raise ValueError('Vector/corpus dimensions differ')
        self.lexical = BM25(self.chunks)
        self.embedder = embedder
        if embedder and embedder.identity != self.config['model']:
            raise ValueError('Embedding model metadata mismatch; rebuild or load the recorded model')
        faiss.omp_set_num_threads(2)

    def search(self, query, *, mode='hybrid', top_k=5, book_id=None, chapter=None, candidate_k=50):
        start = time.perf_counter()
        if not isinstance(query, str) or not query.strip() or len(query) > 4000:
            raise ValueError('Query must contain 1–4000 characters')
        if mode not in {'bm25', 'dense', 'hybrid'} or not 1 <= top_k <= 50 or not top_k <= candidate_k <= 1000:
            raise ValueError('Invalid retrieval mode or result limits')
        allowed = {i for i,c in enumerate(self.chunks) if (not book_id or c.book_id == book_id) and (not chapter or c.chapter == chapter)}
        lexical = self.lexical.search(query, allowed)[:candidate_k] if mode != 'dense' else []
        dense = []
        if mode != 'bm25' and allowed:
            if not self.embedder:
                raise ValueError('Dense search requires the recorded embedding model')
            q = self.embedder.encode([query])
            scores, ids = self.index.search(q, self.index.ntotal)
            dense = sorted([(int(i), float(s)) for i,s in zip(ids[0], scores[0]) if i in allowed], key=lambda x: (-x[1], self.chunks[x[0]].id))[:candidate_k]
        ranking = lexical if mode == 'bm25' else dense if mode == 'dense' else rrf([lexical, dense], self.config['rrf_constant'])
        lexical_map, dense_map = dict(lexical), dict(dense)
        hits = [{'chunk': self.chunks[i].model_dump(mode='json'), 'score': float(score),
                 'bm25_score': lexical_map.get(i), 'dense_cosine': dense_map.get(i),
                 'lexical_rank': next((n for n,(j,_) in enumerate(lexical,1) if i==j),None),
                 'dense_rank': next((n for n,(j,_) in enumerate(dense,1) if i==j),None)} for i,score in ranking[:top_k]]
        return {'query': query, 'mode': mode, 'policy': self.config['policy'], 'hits': hits,
                'latency_ms': (time.perf_counter() - start) * 1000,
                'score_notice': 'Ranking scores are not calibrated confidence or truth probabilities.'}
