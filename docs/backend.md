# Phase 4 backend

Run from the repository root after installing `requirements.txt` and preparing the
Phase 2/3 handoffs and their referenced artifacts (see `retrieval.md`):

```bash
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log
.venv/bin/python -m unittest discover -s backend/tests -v
```

Open http://127.0.0.1:8000/docs for interactive OpenAPI documentation, or
`/openapi.json` for the schema. The API validates artifact checksums at startup.
Missing/corrupt artifacts yield a degraded `/health` and 503 corpus endpoints.
Health is a liveness response; inspect its `ready` field for readiness.

| Endpoint | Result |
| --- | --- |
| `GET /health` | Readiness, dense-model state, generation configuration |
| `GET /api/books` | Actual extraction/review/index counts and OCR status |
| `GET /api/books/{book_id}` | One catalog book |
| `GET /api/books/{book_id}/source` | Checksum-checked original PDF, supports byte ranges |
| `POST /api/search` | BM25/dense/hybrid hits, scores, provenance, PDF links |
| `POST /api/interpret` | Retrieval plus optional checked synthesis |
| `GET /api/passages/{passage_id}` | Full parent passage, including validation status |
| `GET /api/stats` | Corpus/model metadata and process-local search timings |
| `GET /api/ingestion/report` | Selected immutable run's actual report |
| `GET /api/evaluation/report` | Corpus-matching smoke report; optional `policy` query |

```bash
curl -s http://127.0.0.1:8000/api/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"يعسوب","mode":"bm25","top_k":5}'
curl -s http://127.0.0.1:8000/api/interpret \
  -H 'Content-Type: application/json' \
  -d '{"query":"رأيت اليعسوب","mode":"hybrid","generate":false}'
```

Requests accept Arabic `query`, `mode` (default hybrid), `policy` (default reviewed),
`top_k` (1–20), optional `book_id` and `chapter`. Interpret defaults to eight hits and also accepts `generate`
(default true). Unknown fields and invalid values return 422. Query text is limited
to 2,000 characters; dense/hybrid additionally rejects queries beyond the actual
model token budget, without silent truncation. A missing cached model falls back
to BM25 with an explicit warning; serving never downloads it automatically.
BM25 handles definite articles and a small explicit form map (for example
`أسافر` → `سفر`, `الأمواج` → `موج`). This is not a general Arabic stemmer. Scores are ranking signals, never confidence percentages.

Interpret response separates `sources` (verbatim excerpts) from `synthesis` and
`differences` (model statements, each with checked citations). PDF pages are 1-based
physical PDF pages, not printed page labels. `sources[].passage_id` opens the parent
passage; `sources[].id` identifies the retrieved chunk. Outcomes use HTTP 200:
`retrieval_only`, `insufficient_sources`, `generated`, or `generation_failed`.
A generation failure retains retrieval and exposes a sanitized `generation_issue`.
HTTP request/server errors use `{ "error": { "code", "message", "request_id", "fields" } }`.
Request validation errors omit submitted values. A 32 KiB body cap applies even to
chunked bodies. Every request receives `X-Request-ID`.

Configuration is loaded from the root `.env`, then overridden by environment
variables. Copy the example without overwriting an existing `.env`. Generation
requires BOTH `RUYA_ENABLE_GENERATION=true` and `DEEPSEEK_API_KEY`. It sends the dream
query and eligible source excerpts to DeepSeek. Keep keys server-side. Experimental
search requires `RUYA_ALLOW_EXPERIMENTAL_SEARCH=true`; experimental results never
enter generation. CORS defaults to the two local frontend origins in `.env.example`.

This is a local development backend with no authentication. Bind to loopback.
Generation limits are per process: five calls/minute, two concurrent calls, 30-second
wall timeout, 900 output tokens, 16,000 prompt bytes, 6,000 source characters by
default. There are no automatic paid retries. Restart resets counters; multiple
workers multiply limits. Public deployment needs authentication and shared budgets.
Search also limits concurrent work to two calls. Request logs contain only generated
request IDs, method, status, and elapsed time; disable Uvicorn's separate access log
as above to avoid logging arbitrary URL/query text. No dream content is persisted.

The current source repair adds `review_scope` to interpretation sources, separate
`verified_excerpts` counts, matched symbols and generation state. Only explicitly
reviewed substrings are admitted; full parent status remains visible and unchanged.
