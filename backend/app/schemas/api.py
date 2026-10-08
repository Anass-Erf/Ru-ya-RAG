from typing import Literal
from pydantic import Field, field_validator
from backend.app.rag.ingestion.models import Record
from backend.app.rag.ingestion.normalization import unicode_normalize, ARABIC
from backend.app.rag.chunking.core import Chunk

DISCLAIMER = 'هذه شواهد من كتب تاريخية وليست حقائق أو تنبؤات أو أحكاما دينية قطعية، ولا تقدم إرشادات طبية أو قانونية.'


class SearchRequest(Record):
    query: str = Field(min_length=2, max_length=2000)
    mode: Literal['bm25', 'dense', 'hybrid'] = 'hybrid'
    policy: Literal['reviewed', 'experimental'] = 'reviewed'
    top_k: int = Field(default=5, ge=1, le=20)
    book_id: Literal['nabulsi', 'ibn-Shahin', 'ibn-sirin'] | None = None
    chapter: str | None = Field(default=None, max_length=500)

    @field_validator('query')
    @classmethod
    def arabic_query(cls, value):
        value = unicode_normalize(value).strip()
        if len(value) < 2 or not ARABIC.search(value):
            raise ValueError('An Arabic dream description or symbol is required')
        return value


class InterpretRequest(SearchRequest):
    top_k: int = Field(default=8, ge=1, le=20)
    generate: bool = True


class Hit(Record):
    chunk: Chunk
    score: float
    bm25_score: float | None
    dense_cosine: float | None
    lexical_rank: int | None
    dense_rank: int | None
    pdf_url: str


class SearchResponse(Record):
    query: str
    requested_mode: str
    mode: str
    policy: str
    hits: list[Hit]
    latency_ms: float
    score_notice: str
    warnings: list[str] = Field(default_factory=list)


class Source(Record):
    id: str
    passage_id: str
    book_id: str
    book_title: str
    author: str
    symbol: str | None
    page_start: int
    page_end: int
    pdf_url: str
    quote: str
    validation_status: str
    review_scope: Literal['full_passage', 'excerpt'] = 'full_passage'


class Citation(Record):
    source_id: str
    quote: str
    book_title: str
    author: str
    page_start: int
    page_end: int
    pdf_url: str


class InterpretationClaim(Record):
    text: str
    citations: list[Citation]


class GenerationIssue(Record):
    code: str
    message: str
    retryable: bool = False


class InterpretResponse(Record):
    status: Literal['retrieval_only', 'insufficient_sources', 'generated', 'generation_failed']
    message: str
    disclaimer: str = DISCLAIMER
    evidence_sufficient: bool
    matched_symbols: list[str] = Field(default_factory=list)
    generation_requested: bool = False
    generation_available: bool = False
    coverage_notice: str = 'هذه شواهد مرتبطة برموز منفردة؛ لا تثبت تفسيرا مركبا للرؤيا كاملة.'
    evidence_rule: str = 'verified passage + explicit symbol/curated Arabic form match; heuristic, not confidence'
    retrieval: SearchResponse
    sources: list[Source]
    # Every model-authored substantive statement must carry checked citations.
    synthesis: list[InterpretationClaim] = Field(default_factory=list)
    differences: list[InterpretationClaim] = Field(default_factory=list)
    generation_issue: GenerationIssue | None = None
    provider_model: str | None = None


class BookResponse(Record):
    id: str
    title: str
    author: str
    status: Literal['partially_available', 'processing', 'OCR_PENDING', 'not_ingested']
    source_available: bool
    pages_extracted: int
    candidate_passages: int
    verified_passages: int
    verified_excerpts: int = 0
    reviewed_index_chunks: int
    experimental_index_chunks: int
    source_url: str


class HealthResponse(Record):
    status: Literal['ok', 'degraded']
    ready: bool
    search_available: bool
    dense_model: Literal['not_loaded', 'loaded', 'unavailable']
    generation_configured: bool


class StatsResponse(Record):
    books: list[BookResponse]
    model_details: dict
    searches_completed: int
    mean_search_latency_ms: float | None
    last_search_latency_ms: float | None
    generation_enabled: bool
    experimental_search_enabled: bool
    warning: str


class ErrorDetail(Record):
    code: str
    message: str
    request_id: str
    fields: list[dict[str, str]] = Field(default_factory=list)


class ErrorResponse(Record):
    error: ErrorDetail
