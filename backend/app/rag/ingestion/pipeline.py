"""Immutable, checksum-addressed ingestion runs; publication happens only on success."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import tempfile

from .catalog import BOOKS
from .extraction import extract_book
from .normalization import ARABIC
from .parsers import detect_boundaries
from .reconstruction import reconstruct

PIPELINE_VERSION = '2.0.0'


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def json_text(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n'


def write_jsonl(path: Path, rows):
    with path.open('w', encoding='utf-8') as stream:
        for row in rows:
            value = row.model_dump(mode='json') if hasattr(row, 'model_dump') else row
            stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + '\n')


def verify_run(path: Path) -> dict:
    manifest = json.loads((path / 'manifest.json').read_text(encoding='utf-8'))
    for filename, checksum in manifest['outputs'].items():
        if Path(filename).name != filename or file_sha256(path / filename) != checksum:
            raise ValueError(f'Ingestion artifact checksum mismatch: {filename}')
    return manifest


def run_ingestion(data_dir: Path, output_root: Path, book_ids: list[str]) -> tuple[Path, bool]:
    selected = sorted(set(book_ids))
    if not selected or any(book_id not in BOOKS for book_id in selected):
        raise ValueError('Select known book IDs')
    sources = {book_id: file_sha256(data_dir / 'raw' / BOOKS[book_id].filename) for book_id in selected}
    code = {p.name: file_sha256(p) for p in sorted(Path(__file__).parent.glob('*.py'))}
    identity = {'pipeline_version': PIPELINE_VERSION, 'schema_version': 2, 'sources': sources,
                'implementation': code, 'normalization': 'NFKC; search strips harakat/tatweel and folds alef/maqsura',
                'extraction': 'native-span-order; baseline tolerance 1.5pt; single-column edition profiles',
                'dependencies': {name: importlib.metadata.version(name) for name in ['PyMuPDF', 'pydantic']}}
    run_id = hashlib.sha256(json_text(identity).encode()).hexdigest()[:24]
    destination = output_root / run_id
    if destination.exists():
        existing = verify_run(destination)
        if existing['identity'] != identity:
            raise ValueError('Run identity mismatch')
        return destination, True
    output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.ingest-', dir=output_root) as temporary:
        stage = Path(temporary) / 'run'
        stage.mkdir()
        all_passages, all_boundaries, all_rejected, all_excluded = [], [], [], []
        report = {'pipeline_version': PIPELINE_VERSION, 'run_id': run_id, 'books': {},
                  'approved_for_indexing': 0,
                  'warning': 'Historical texts; extraction and segmentation candidates are not verified interpretations.'}
        # Stream page records to disk between books rather than retaining the full corpus.
        with (stage / 'pages.jsonl').open('w', encoding='utf-8') as stream:
            for book_id in selected:
                book = BOOKS[book_id]
                pages = extract_book(data_dir / 'raw' / book.filename, book, sources[book_id])
                for page in pages:
                    stream.write(page.model_dump_json() + '\n')
                text_pages = sum(bool(p.original_text.strip()) for p in pages)
                arabic_pages = sum(len(ARABIC.findall(p.corrected_candidate_text)) >= 25 for p in pages)
                matched = sources[book_id] == book.sha256
                status = 'OCR_PENDING' if book.ocr_pending or not arabic_pages else ('REVIEW_REQUIRED' if matched else 'SOURCE_PROFILE_MISMATCH')
                boundaries, rejected, passages, excluded = [], [], [], []
                if status == 'REVIEW_REQUIRED':
                    boundaries, rejected = detect_boundaries(pages)
                    passages, excluded = reconstruct(pages, boundaries, book)
                else:
                    excluded = [{'book_id': book_id, 'pdf_page': p.pdf_page, 'line_number': l.line_number,
                                 'text': l.candidate_text, 'reason': status}
                                for p in pages for l in p.lines if l.candidate_text.strip()]
                all_passages.extend(passages)
                all_boundaries.extend(boundaries)
                all_rejected.extend(rejected)
                all_excluded.extend(excluded)
                coverage = sum(r.line_end - r.line_start + 1 for passage in passages for r in passage.source_ranges)
                total_lines = sum(bool(l.candidate_text.strip()) for p in pages for l in p.lines)
                if coverage + len(excluded) != total_lines:
                    raise ValueError('Line accounting failed; refusing to publish')
                report['books'][book_id] = {
                    'title': book.title, 'author': book.author, 'source_file': book.filename,
                    'source_sha256': sources[book_id], 'edition_profile_matched': matched,
                    'status': status, 'pages_extracted': len(pages), 'pages_with_text': text_pages,
                    'pages_with_substantial_arabic': arabic_pages,
                    'pages_without_text': [p.pdf_page for p in pages if not p.original_text.strip()],
                    'page_flag_counts': dict(Counter(f for p in pages for f in p.review_flags)),
                    'boundary_counts': dict(Counter(b.kind for b in boundaries)),
                    'chapter_labels': [b.label for b in boundaries if b.kind == 'chapter'],
                    'candidate_passages': len(passages), 'verified_passages': 0,
                    'validation_counts': dict(Counter(p.validation_status for p in passages)),
                    'passage_flag_counts': dict(Counter(f for p in passages for f in p.review_flags)),
                    'rejected_candidate_counts': dict(Counter(r['reason'] for r in rejected)),
                    'nonempty_layout_rows': total_lines, 'rows_in_passages': coverage,
                    'excluded_rows': len(excluded), 'line_accounting_complete': True,
                    'largest_passages': [{'id': p.id, 'characters': len(p.text), 'page_start': p.page_start,
                                          'page_end': p.page_end, 'label': p.symbol or p.section or p.chapter}
                                         for p in sorted(passages, key=lambda p: len(p.text), reverse=True)[:10]],
                }
                # Color/format drift must be visible, not automatically corrected to target counts.
                chapters = sum(b.kind == 'chapter' for b in boundaries)
                report['books'][book_id]['structural_warnings'] = (
                    ['chapter_count_differs_from_source_outline']
                    if status == 'REVIEW_REQUIRED' and chapters != {'nabulsi': 28, 'ibn-Shahin': 80}[book_id] else [])
        ids = [p.id for p in all_passages]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate passage IDs')
        write_jsonl(stage / 'passages.jsonl', all_passages)
        write_jsonl(stage / 'boundaries.jsonl', all_boundaries)
        write_jsonl(stage / 'rejected_candidates.jsonl', all_rejected)
        write_jsonl(stage / 'excluded_lines.jsonl', all_excluded)
        write_jsonl(stage / 'review_queue.jsonl', [
            {'passage_id': p.id, 'text_sha256': p.text_sha256, 'book_id': p.book_id,
             'page_start': p.page_start, 'page_end': p.page_end, 'label': p.symbol or p.section or p.chapter,
             'validation_status': p.validation_status, 'review_flags': p.review_flags,
             'preview': p.text[:300]} for p in all_passages])
        (stage / 'report.json').write_text(json_text(report), encoding='utf-8')
        # Detect source changes during processing before publishing a manifest.
        if any(file_sha256(data_dir / 'raw' / BOOKS[k].filename) != v for k, v in sources.items()):
            raise ValueError('Source PDF changed during ingestion')
        manifest = {'run_id': run_id, 'created_at': datetime.now(timezone.utc).isoformat(), 'identity': identity,
                    'outputs': {p.name: file_sha256(p) for p in sorted(stage.iterdir())}}
        (stage / 'manifest.json').write_text(json_text(manifest), encoding='utf-8')
        stage.rename(destination)
    return destination, False
