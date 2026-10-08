"""Admit only explicitly reviewed exact excerpts, never promote their entire parent."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Literal
from pydantic import Field
from backend.app.rag.ingestion.models import Record, Passage, SourceRange
from backend.app.rag.ingestion.pipeline import file_sha256
from backend.app.rag.ingestion.normalization import search_normalize
from .core import Chunk


class ExcerptDecision(Record):
    passage_id: str
    source_sha256: str
    parent_text_sha256: str
    char_start: int = Field(ge=0)
    char_end: int = Field(gt=0)
    quote: str = Field(min_length=20)
    checked_pdf_pages: list[int]
    reviewer: str
    method: Literal['assisted_pdf_comparison', 'human_pdf_comparison']
    reviewed_at: datetime
    scope: Literal['exact_excerpt_and_context']
    evidence: str = Field(min_length=30)


def reviewed_excerpts(root, passages, rows, tokenizer, handoff, max_tokens, policy):
    reference = handoff.get('excerpt_reviews')
    if not reference:
        return []
    path = Path(root) / reference
    if file_sha256(path) != handoff['excerpt_reviews_sha256']:
        raise ValueError('Excerpt review ledger checksum mismatch')
    document = json.loads(path.read_text())
    lookup = {p.id: p for p in passages}
    chunks, seen = [], set()
    for raw in document['decisions']:
        decision = ExcerptDecision.model_validate(raw)
        p: Passage = lookup[decision.passage_id]
        if p.book_id == 'ibn-sirin' or p.source_sha256 != decision.source_sha256 or p.text_sha256 != decision.parent_text_sha256:
            raise ValueError('Stale or ineligible excerpt parent')
        if p.text[decision.char_start:decision.char_end] != decision.quote:
            raise ValueError('Excerpt differs from parent text')
        if decision.char_end > len(p.text) or decision.char_start >= decision.char_end:
            raise ValueError('Invalid excerpt offsets')
        cursor, touched, full = 0, [], []
        for source_range in p.source_ranges:
            for n in range(source_range.line_start, source_range.line_end + 1):
                row = rows[(p.book_id, source_range.pdf_page, n)]
                full.append(row.candidate_text)
                if cursor < decision.char_end and cursor + len(row.candidate_text) > decision.char_start:
                    touched.append((source_range.pdf_page, n, row))
                cursor += len(row.candidate_text) + 1
        if '\n'.join(full) != p.text or set(decision.checked_pdf_pages) != {r[0] for r in touched}:
            raise ValueError('Excerpt source rows/pages do not match review')
        count = len(tokenizer(decision.quote, add_special_tokens=False, verbose=False)['input_ids'])
        if not 0 < count <= max_tokens:
            raise ValueError('Reviewed excerpt exceeds token budget; review smaller spans explicitly')
        identity = f'{p.id}:{p.text_sha256}:{decision.char_start}:{decision.char_end}:reviewed-excerpt'
        chunk_id = 'chunk_' + hashlib.sha256(identity.encode()).hexdigest()[:24]
        if chunk_id in seen:
            raise ValueError('Duplicate excerpt review')
        seen.add(chunk_id)
        chunks.append(Chunk(id=chunk_id, parent_entry_id=p.id, chunk_index=len(chunks),
            book_id=p.book_id, book_title=p.book_title, author=p.author, chapter=p.chapter,
            section=p.section, symbol=p.symbol, source_file=p.source_file, source_sha256=p.source_sha256,
            page_start=touched[0][0], page_end=touched[-1][0],
            source_ranges=[SourceRange(pdf_page=page, line_start=n, line_end=n) for page,n,_ in touched],
            char_start=decision.char_start, char_end=decision.char_end, text=decision.quote,
            normalized_text=search_normalize(decision.quote), raw_source_text='\n'.join(r.raw_text for _,_,r in touched),
            token_count=count, validation_status='verified',
            review_flags=['excerpt_source_review', 'parent_' + p.validation_status], corpus_policy=policy))
    return chunks
