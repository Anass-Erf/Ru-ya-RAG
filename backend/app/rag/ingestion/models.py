"""Versioned records; candidates and source-verified text are explicitly distinct."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Status = Literal['unreviewed', 'needs_review', 'verified']
BBox = tuple[float, float, float, float]


class Record(BaseModel):
    model_config = ConfigDict(extra='forbid')


class SourceSpan(Record):
    block: int
    line: int
    span: int
    bbox: BBox
    baseline: float
    color: int
    glyph_order_suspect: bool = False
    text: str


class SourceLine(Record):
    line_number: int = Field(ge=1)
    bbox: BBox
    raw_text: str
    normalized_text: str
    candidate_text: str
    spans: list[SourceSpan]
    transformations: list[str] = Field(default_factory=list)
    excluded_reason: str | None = None
    review_flags: list[str] = Field(default_factory=list)


class Page(Record):
    schema_version: int = 2
    book_id: str
    source_file: str
    source_sha256: str
    pdf_page: int = Field(ge=1)
    width: float
    height: float
    extraction_method: str = 'pymupdf_native_spans'
    original_text: str
    normalized_text: str
    corrected_candidate_text: str
    validated_text: str | None = None
    validation_status: Status = 'unreviewed'
    lines: list[SourceLine]
    review_flags: list[str] = Field(default_factory=list)


class Boundary(Record):
    id: str
    book_id: str
    pdf_page: int = Field(ge=1)
    line_number: int = Field(ge=1)
    kind: Literal['chapter', 'section', 'entry', 'end_matter']
    label: str
    source_text: str
    chapter: str | None = None
    section: str | None = None
    symbol: str | None = None
    rule: str
    review_flags: list[str] = Field(default_factory=list)


class SourceRange(Record):
    pdf_page: int = Field(ge=1)
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    # These are layout row coordinates in pages.jsonl, not legacy TXT line numbers.
    @model_validator(mode='after')
    def ordered(self):
        if self.line_end < self.line_start:
            raise ValueError('Reversed source range')
        return self


class Passage(Record):
    schema_version: int = 2
    id: str
    book_id: str
    book_title: str
    author: str
    chapter: str | None
    section: str | None
    symbol: str | None
    passage_kind: Literal['symbol_entry', 'section', 'chapter_preamble']
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    source_ranges: list[SourceRange] = Field(min_length=1)
    source_file: str
    source_sha256: str
    extraction_method: str = 'pymupdf_native_spans'
    raw_text: str
    unicode_normalized_text: str
    text: str
    normalized_text: str
    text_sha256: str
    validation_status: Status = 'unreviewed'
    validated_text: str | None = None
    review_flags: list[str] = Field(default_factory=list)
    boundary_id: str

    @model_validator(mode='after')
    def validate_provenance(self):
        if self.page_start != self.source_ranges[0].pdf_page or self.page_end != self.source_ranges[-1].pdf_page:
            raise ValueError('Page range must match source ranges')
        if self.page_end < self.page_start or not self.text.strip():
            raise ValueError('Empty text or reversed page range')
        coords = [(r.pdf_page, r.line_start) for r in self.source_ranges]
        if coords != sorted(set(coords)):
            raise ValueError('Duplicate or unordered source ranges')
        if self.validation_status == 'verified' and self.validated_text != self.text:
            raise ValueError('Verified passages require source-checked text')
        if self.validation_status != 'verified' and self.validated_text is not None:
            raise ValueError('Unverified records cannot carry validated_text')
        return self
