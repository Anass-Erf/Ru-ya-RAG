"""Apply explicit, source-bound review decisions without modifying ingestion runs."""
from datetime import datetime
from typing import Literal
from pydantic import Field
from .models import Record, Passage


class Decision(Record):
    passage_id: str
    source_sha256: str
    text_sha256: str
    status: Literal['verified', 'needs_review']
    reviewer: str = Field(min_length=1)
    method: Literal['human_pdf_comparison', 'assisted_pdf_comparison']
    reviewed_at: datetime
    scope: Literal['full_passage_and_boundaries']
    checked_pdf_pages: list[int]
    evidence: str = Field(min_length=20)


def apply_decisions(passages: list[Passage], decisions: list[Decision]) -> list[Passage]:
    by_id = {p.id: p for p in passages}
    seen = set()
    for decision in decisions:
        if decision.passage_id in seen or decision.passage_id not in by_id:
            raise ValueError('Duplicate or unknown review passage ID')
        seen.add(decision.passage_id)
        passage = by_id[decision.passage_id]
        if decision.text_sha256 != passage.text_sha256 or decision.source_sha256 != passage.source_sha256:
            raise ValueError('Stale review: source or text checksum differs')
        if decision.status == 'verified' and set(decision.checked_pdf_pages) != set(range(passage.page_start, passage.page_end + 1)):
            raise ValueError('Verification must cover every PDF page in the passage span')
        data = passage.model_dump()
        data['validation_status'] = decision.status
        data['validated_text'] = passage.text if decision.status == 'verified' else None
        # Keep all diagnostic flags, even after review. A later index policy must consider them.
        by_id[passage.id] = Passage.model_validate(data)
    return [by_id[p.id] for p in passages]
