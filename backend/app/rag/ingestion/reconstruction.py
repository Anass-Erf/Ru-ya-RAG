"""Reconstruct disjoint candidates from checked boundaries, preserving every row."""
import hashlib
from .catalog import Book
from .models import Page, Passage, Boundary, SourceRange
from .normalization import unicode_normalize, search_normalize, ARABIC
from .parsers import is_shahin_heading


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def reconstruct(pages: list[Page], boundaries: list[Boundary], book: Book) -> tuple[list[Passage], list[dict]]:
    if not pages or any(p.book_id != book.id or p.source_sha256 != pages[0].source_sha256 for p in pages):
        raise ValueError('Pages must belong to one book and source edition')
    numbers = [p.pdf_page for p in pages]
    if numbers != list(range(numbers[0], numbers[-1] + 1)):
        raise ValueError('Missing or unordered pages in reconstruction input')
    coords = [(p.pdf_page, l.line_number) for p in pages for l in p.lines]
    if coords != sorted(set(coords)):
        raise ValueError('Duplicate or unordered source coordinates')
    rows = [(p, l) for p in pages for l in p.lines]
    positions = {key: index for index, key in enumerate(coords)}
    starts = []
    for boundary in boundaries:
        key = (boundary.pdf_page, boundary.line_number)
        if boundary.book_id != book.id or key not in positions:
            raise ValueError('Boundary book/position mismatch')
        index = positions[key]
        if rows[index][1].candidate_text != boundary.source_text or rows[index][1].excluded_reason:
            raise ValueError('Boundary source text does not match current page')
        starts.append((index, boundary))
    if [i for i, _ in starts] != sorted({i for i, _ in starts}):
        raise ValueError('Duplicate or unordered boundaries')
    passages, excluded = [], []
    covered = set()
    exclusion_reasons = {}
    for n, (start, boundary) in enumerate(starts):
        end = starts[n + 1][0] if n + 1 < len(starts) else len(rows)
        if boundary.kind == 'end_matter' or (book.id == 'nabulsi' and boundary.kind == 'chapter'):
            continue
        block = [(i, p, l) for i, (p, l) in enumerate(rows[start:end], start)
                 if not l.excluded_reason and l.candidate_text.strip()]
        if not block:
            continue
        if boundary.kind == 'chapter' and all(is_shahin_heading(l) for _, _, l in block):
            exclusion_reasons.update({i: 'chapter_heading_without_body' for i, _, _ in block})
            continue
        ranges = []
        for _, p, l in block:
            if ranges and ranges[-1].pdf_page == p.pdf_page and ranges[-1].line_end + 1 == l.line_number:
                ranges[-1].line_end = l.line_number
            else:
                ranges.append(SourceRange(pdf_page=p.pdf_page, line_start=l.line_number, line_end=l.line_number))
        text = '\n'.join(l.candidate_text for _, _, l in block)
        raw = '\n'.join(l.raw_text for _, _, l in block)
        flags = sorted({flag for _, _, l in block for flag in l.review_flags} | set(boundary.review_flags))
        if len(text) < 80:
            flags.append('short_text_review')
        if len(text) > 9000:
            flags.append('long_text_review')
        if ranges[-1].pdf_page - ranges[0].pdf_page > 2:
            flags.append('long_page_span_review')
        if len(ARABIC.findall(text)) < 20:
            flags.append('very_little_arabic')
        if any('very_little_arabic' in p.review_flags or 'no_text_layer_on_page' in p.review_flags
               for p in pages if ranges[0].pdf_page <= p.pdf_page <= ranges[-1].pdf_page):
            flags.append('low_text_page_in_span')
        if boundary.kind == 'chapter':
            flags.append('chapter_preamble_review')
        if boundary.section == 'فصل':
            flags.append('unnamed_section')
        # A stable source anchor survives added/removed boundaries elsewhere.
        anchor = f'{book.id}:{pages[0].source_sha256}:{boundary.pdf_page}:{boundary.line_number}:{boundary.kind}'
        passage = Passage(id=f'{book.id}_{sha256_text(anchor)[:24]}', book_id=book.id,
                          book_title=book.title, author=book.author, chapter=boundary.chapter,
                          section=boundary.section, symbol=boundary.symbol,
                          passage_kind={'entry': 'symbol_entry', 'section': 'section', 'chapter': 'chapter_preamble'}[boundary.kind],
                          page_start=ranges[0].pdf_page, page_end=ranges[-1].pdf_page,
                          source_ranges=ranges, source_file=book.filename,
                          source_sha256=pages[0].source_sha256, raw_text=raw,
                          unicode_normalized_text=unicode_normalize(raw), text=text,
                          normalized_text=search_normalize(text), text_sha256=sha256_text(text),
                          validation_status='needs_review' if flags else 'unreviewed',
                          review_flags=sorted(set(flags)), boundary_id=boundary.id)
        passages.append(passage)
        covered.update(i for i, _, _ in block)
    for i, (p, line) in enumerate(rows):
        if i not in covered and line.candidate_text.strip():
            excluded.append({'book_id': book.id, 'pdf_page': p.pdf_page, 'line_number': line.line_number,
                             'text': line.candidate_text,
                             'reason': line.excluded_reason or exclusion_reasons.get(i, 'outside_candidate_passages')})
    return passages, excluded
