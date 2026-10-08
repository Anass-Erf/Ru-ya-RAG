# Phase 4 — FastAPI and grounded generation

Completed 2026-10-08. Phase 5 has not started.

The API exposes real corpus search, passage inspection, book status, original PDF
links, statistics and ingestion/evaluation reports. Generation is optional and
requires reviewed matching evidence, bounded provider calls and checked citations.
Retrieval-only behavior works without credentials. The API does not expand the
reviewed corpus or conceal Phase 3's weak experimental retrieval results.

## Files

Created:

- `backend/app/main.py`: application factory, lifespan and ten documented API paths.
- `backend/app/core/{__init__,config,errors}.py`: environment settings and sanitized errors.
- `backend/app/api/{__init__,middleware}.py`: request size cap, IDs and structured logs.
- `backend/app/schemas/{__init__,api}.py`: request, response, source and citation schemas.
- `backend/app/services/{__init__,library,interpretation}.py`: checked corpus access and orchestration.
- `backend/app/rag/generation/{__init__,provider,grounding}.py`: provider interface, DeepSeek adapter and citation validation.
- `backend/tests/test_api.py`, `backend/tests/test_provider.py`: 17 new tests.
- `docs/backend.md`, `docs/generation.md`, `docs/phase4-report.md`.
- `storage/manifests/phase4-openapi.json`, `storage/manifests/phase4-handoff.json`.

Modified: `.env.example`, `pyproject.toml`, `requirements.txt`, `README.md`,
`docs/architecture.md`, `docs/learning-guide.md`.

Archived/deleted: none. Original PDFs, source derivatives and Phase 3 indexes remain
unchanged. API dependencies were installed in the existing virtual environment.

## Run and test

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log
# In another terminal:
.venv/bin/python -m unittest discover -s backend/tests -v
```

See `docs/backend.md` for prerequisites, request examples and environment settings.

Actual validation:

- Full suite before the final logging assertion: **51 passed in 27.627 seconds**,
  including all 35 existing ingestion/retrieval/preservation regressions.
- After enabling structured logs, checking privacy and correcting error request-ID
  headers: final API
  and provider suite **17 passed in 2.281 seconds**. Together these cover **52 unique
  passing tests**. The unaffected 35 older tests were not repeated after that change.
- Real localhost Uvicorn HTTP smoke: health ready; cached-model hybrid search returned
  two hits; interpretation with generation disabled returned a source on PDF page
  1405; `/docs` and `/openapi.json` returned 200. Temporary server shut down afterward.
- `pip check`: no broken requirements.
- OpenAPI export generated successfully with ten paths.
- No live DeepSeek request, paid generation, representative quality benchmark,
  production load test, or fresh-environment install was run.

Sandbox restrictions blocked async worker wakeups in the first test-client probes.
The same tests completed outside the sandbox. Starlette emits a deprecation warning
for its HTTPX test-client adapter; it still passes with the installed pinned version.

## Remaining limits and next phase

Only two Nabulsi passages have AI-assisted source review; Ibn Shahin is not yet in
the reviewed index and Ibn Sirin remains OCR_PENDING. Generation's explicit-symbol
rule is deliberately conservative and cannot establish full dream answerability.
Exact citation checks prevent fabricated quotes/pages from being accepted, but do
not establish semantic entailment or complete prompt-injection resistance. Live
provider authentication and model output quality remain untested. The default
provider model follows current official documentation linked in `docs/generation.md`.

This local service has no authentication. Budgets are process-local and reset on
restart. A public deployment requires further work. The frontend must display corpus
limits, generation state, original quotes and synthesized text distinctly.

Awaiting confirmation for Phase 5, as required by the original phased execution plan.
