import hashlib
from pydantic import Field
from backend.app.rag.ingestion.models import Record, Passage, SourceRange
from backend.app.rag.ingestion.normalization import search_normalize, ARABIC

BLOCKERS = {'replacement_character', 'presentation_forms_remain', 'known_font_encoding_artifact',
            'nonmonotonic_arabic_glyph_order', 'overlapping_text_spans', 'ambiguous_span_order',
            'very_little_arabic', 'low_text_page_in_span', 'unnamed_section'}


class Chunk(Record):
    id: str
    parent_entry_id: str
    chunk_index: int
    book_id: str
    book_title: str
    author: str
    chapter: str | None
    section: str | None
    symbol: str | None
    source_file: str
    source_sha256: str
    page_start: int
    page_end: int
    source_ranges: list[SourceRange]
    char_start: int
    char_end: int
    text: str
    normalized_text: str
    # Raw source rows may extend beyond a partial-row chunk; never pretend raw
    # Unicode offsets align one-to-one with transformed candidate characters.
    raw_source_text: str
    token_count: int = Field(gt=0)
    validation_status: str
    review_flags: list[str]
    corpus_policy: str


def exclusion_reason(passage: Passage, policy: str) -> str | None:
    if policy not in {'reviewed', 'experimental'}:
        raise ValueError('Unknown corpus policy')
    if passage.book_id == 'ibn-sirin':
        return 'OCR_PENDING'
    allowed_flags = {'short_text_review', 'long_text_review', 'long_page_span_review', 'chapter_preamble_review'}
    blocked = set(passage.review_flags) - allowed_flags
    if blocked:
        return 'quality:' + ','.join(sorted(blocked))
    if len(ARABIC.findall(passage.text)) < 10:
        return 'insufficient_arabic'
    if policy == 'reviewed' and passage.validation_status != 'verified':
        return 'not_verified'
    if policy == 'experimental' and passage.validation_status == 'needs_review':
        return 'needs_review'
    return None


def chunk_passage(passage: Passage, tokenizer, source_rows: dict, *, max_tokens=120, overlap_tokens=16, policy='reviewed') -> list[Chunk]:
    """Use exact tokenizer counts, preferring line/word ends; never merge parents."""
    if max_tokens < 8 or not 0 <= overlap_tokens < max_tokens // 2:
        raise ValueError('Invalid chunk size/overlap')
    reason = exclusion_reason(passage, policy)
    if reason:
        return []
    text = passage.text
    line_map, cursor = [], 0
    for source_range in passage.source_ranges:
        for number in range(source_range.line_start, source_range.line_end + 1):
            key = (passage.book_id, source_range.pdf_page, number)
            line = source_rows[key]
            line_map.append((cursor, cursor + len(line.candidate_text), source_range.pdf_page, number, line))
            cursor += len(line.candidate_text) + 1
    if '\n'.join(row[4].candidate_text for row in line_map) != text:
        raise ValueError('Passage does not match source rows')
    if hashlib.sha256(text.encode()).hexdigest() != passage.text_sha256:
        raise ValueError('Passage checksum mismatch')
    chunks, start = [], 0
    while start < len(text):
        remaining = text[start:]
        encoded = tokenizer(remaining, add_special_tokens=False, return_offsets_mapping=True, truncation=False, verbose=False)
        offsets = encoded['offset_mapping']
        if not offsets:
            break
        end = len(text) if len(offsets) <= max_tokens else start + offsets[max_tokens - 1][1]
        if end < len(text):
            # Prefer a complete layout line when it uses at least half the budget.
            floor = start + offsets[max_tokens // 2 - 1][1]
            split = text.rfind('\n', floor, end)
            if split < 0:
                split = text.rfind(' ', floor, end)
            if split > start:
                end = split + 1
        value = text[start:end]
        count = len(tokenizer(value, add_special_tokens=False, verbose=False)['input_ids'])
        while count > max_tokens:
            end -= 1
            value = text[start:end]
            count = len(tokenizer(value, add_special_tokens=False, verbose=False)['input_ids'])
        touched = [r for r in line_map if r[0] < end and r[1] > start]
        ranges = []
        for _, _, page, number, _ in touched:
            if ranges and ranges[-1].pdf_page == page and ranges[-1].line_end + 1 == number:
                ranges[-1].line_end = number
            else:
                ranges.append(SourceRange(pdf_page=page, line_start=number, line_end=number))
        if not ranges or count == 0:
            raise ValueError('Chunk has no source text')
        identity = f'{passage.id}:{passage.text_sha256}:{start}:{end}'
        chunks.append(Chunk(id='chunk_' + hashlib.sha256(identity.encode()).hexdigest()[:24],
                            parent_entry_id=passage.id, chunk_index=len(chunks),
                            book_id=passage.book_id, book_title=passage.book_title, author=passage.author,
                            chapter=passage.chapter, section=passage.section, symbol=passage.symbol,
                            source_file=passage.source_file, source_sha256=passage.source_sha256,
                            page_start=ranges[0].pdf_page, page_end=ranges[-1].pdf_page,
                            source_ranges=ranges, char_start=start, char_end=end, text=value,
                            normalized_text=search_normalize(value), raw_source_text='\n'.join(r[4].raw_text for r in touched),
                            token_count=count, validation_status=passage.validation_status,
                            review_flags=passage.review_flags, corpus_policy=policy))
        if end == len(text):
            break
        used_offsets = tokenizer(value, add_special_tokens=False, return_offsets_mapping=True, verbose=False)['offset_mapping']
        next_start = start + used_offsets[-overlap_tokens][0] if overlap_tokens and len(used_offsets) > overlap_tokens else end
        start = max(start + 1, next_start)
    return chunks
