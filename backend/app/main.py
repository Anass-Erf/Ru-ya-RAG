"""Run from the project root: uvicorn backend.app.main:app."""
from contextlib import asynccontextmanager
import logging
from typing import Literal
import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse, FileResponse
from backend.app.core.config import Settings
from backend.app.core.errors import APIError
from backend.app.api.middleware import RequestBoundary
from backend.app.schemas.api import (SearchRequest, SearchResponse, InterpretRequest, InterpretResponse,
    HealthResponse, BookResponse, StatsResponse, ErrorResponse)
from backend.app.rag.ingestion.models import Passage
from backend.app.rag.ingestion.catalog import BOOKS
from backend.app.rag.ingestion.pipeline import file_sha256
from backend.app.rag.generation.provider import DeepSeek
from backend.app.services.library import Library
from backend.app.services.interpretation import Interpreter


def create_app(settings: Settings | None = None, library: Library | None = None, provider=None) -> FastAPI:
    settings = settings or Settings.from_env()
    library = library or Library(settings)

    @asynccontextmanager
    async def lifespan(app):
        request_logger = logging.getLogger('ruya.requests')
        if not request_logger.handlers:
            request_logger.addHandler(logging.StreamHandler())
        request_logger.setLevel(logging.INFO)
        request_logger.propagate = False
        try:
            library.load()
        except (OSError, ValueError, KeyError, RuntimeError):
            library.ready = False
            logging.getLogger('ruya').error('Corpus startup validation failed; API is degraded.')
        async with httpx.AsyncClient(trust_env=False) as client:
            app.state.interpreter = Interpreter(settings, library, provider or DeepSeek(settings, client))
            yield

    app = FastAPI(title="Ru'ya historical text API", version='0.4.0', lifespan=lifespan,
        description='Arabic historical source retrieval. Generated summaries require reviewed citations.',
        responses={code: {'model': ErrorResponse} for code in [400, 403, 404, 413, 422, 500, 503]})
    app.state.library = library
    app.add_middleware(RequestBoundary, max_bytes=settings.max_request_bytes)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=['GET', 'POST'],
                       allow_headers=['Content-Type'], expose_headers=['X-Request-ID'])

    def error(request, status, code, message, fields=None):
        rid = getattr(request.state, 'request_id', '')
        return JSONResponse({'error': {'code': code, 'message': message, 'request_id': rid, 'fields': fields or []}},
                            status_code=status, headers={'X-Request-ID': rid})

    @app.exception_handler(APIError)
    async def api_error(request: Request, exc: APIError):
        return error(request, exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc):
        return error(request, 422, 'invalid_request', 'Request validation failed.',
            [{'field': '.'.join(map(str, e['loc'])), 'type': e['type']} for e in exc.errors()])

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc):
        return error(request, exc.status_code, 'http_error', 'The requested resource or method is unavailable.')

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc):
        logging.getLogger('ruya').error('Unhandled request failure; request_id=%s', getattr(request.state, 'request_id', ''))
        return error(request, 500, 'internal_error', 'An internal error occurred.')

    @app.get('/health', response_model=HealthResponse)
    def health():
        return dict(status='ok' if library.ready else 'degraded', ready=library.ready, search_available=library.ready,
            dense_model='loaded' if library.embedder else 'unavailable' if library.dense_unavailable else 'not_loaded',
            generation_configured=settings.enable_generation and bool(settings.deepseek_api_key.get_secret_value()))

    @app.get('/api/books', response_model=list[BookResponse])
    def books():
        library.require_ready()
        return library.books()

    @app.get('/api/books/{book_id}', response_model=BookResponse)
    def book(book_id: str):
        library.require_ready()
        for item in library.books():
            if item.id == book_id:
                return item
        raise APIError(404, 'book_not_found', 'Book not found.')

    @app.get('/api/books/{book_id}/source', response_class=FileResponse)
    def source(book_id: str):
        catalog = BOOKS.get(book_id)
        if catalog is None:
            raise APIError(404, 'book_not_found', 'Book not found.')
        path = settings.project_root / 'data/raw' / catalog.filename
        if not path.is_file():
            raise APIError(404, 'source_not_found', 'Source PDF unavailable.')
        if file_sha256(path) != catalog.sha256:
            raise APIError(503, 'source_checksum_mismatch', 'Source PDF differs from the indexed edition.')
        return FileResponse(path, media_type='application/pdf', filename=catalog.filename, content_disposition_type='inline')

    @app.post('/api/search', response_model=SearchResponse)
    def search(body: SearchRequest):
        return library.search(body)

    @app.post('/api/interpret', response_model=InterpretResponse)
    async def interpret(body: InterpretRequest, request: Request):
        return await request.app.state.interpreter.interpret(body)

    @app.get('/api/passages/{passage_id}', response_model=Passage)
    def passage(passage_id: str):
        library.require_ready()
        if passage_id not in library.passages:
            raise APIError(404, 'passage_not_found', 'Passage not found.')
        return library.passages[passage_id]

    @app.get('/api/stats', response_model=StatsResponse)
    def stats():
        return library.statistics()

    @app.get('/api/ingestion/report')
    def ingestion_report() -> dict:
        library.require_ready()
        return library.ingestion_report

    @app.get('/api/evaluation/report')
    def evaluation_report(policy: Literal['reviewed', 'experimental'] = 'reviewed') -> dict:
        library.require_ready()
        if policy == 'experimental' and not settings.allow_experimental_search:
            raise APIError(403, 'experimental_disabled', 'Experimental search is disabled.')
        if policy not in library.evaluations:
            raise APIError(404, 'report_not_found', 'No evaluation matching this corpus is available.')
        return library.evaluations[policy]
    return app


app = create_app()
