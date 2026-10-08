# Sea-and-ship retrieval repair — 2026-10-09

Phase 6 was paused at the user's request. This repair addresses the reported dream:

> رأيت في المنام أنني أسافر في سفينة وسط البحر، وكانت الأمواج عالية، لكنني وصلت إلى الشاطئ بسلام.

## Cause

The default index contained only two fully reviewed Nabulsi entries (`ذل`, `يعسوب`).
Sea and ship entries existed in the candidate corpus but had whole-entry extraction
flags and were excluded, even from experimental indexing. Exact symbol matching
also missed forms such as `أسافر` and `الأمواج`. Independently, generation was
configured off, and the UI requests retrieval-only unless explicitly selected.
A key alone does not activate generation.

## Changes

- Added six narrowly source-reviewed excerpts after visual PDF comparison. Parent
  passage status and text remain unchanged. Exact offsets/checksums and reviewed
  pages are enforced at build time. The API checks the ledger/index association.
- Added a small explicit Arabic query-form map and definite-article handling shared
  between lexical ranking and generation eligibility. This is not general stemming;
  `سفرجل` and `سفرة` do not become `سفر`.
- Expanded the interpretation default to eight retrieval hits and up to six source
  excerpts, with at most two per parent. Other search filters and limits remain.
- Added matched symbols, generation-request/configuration state, a partial-coverage
  notice and review scope to the response. UI badges distinguish reviewed excerpts
  from fully reviewed entries; parent inspection retains its original status.
- Rebuilt versioned reviewed/experimental indexes and updated the active handoff.
  Old indexes and evaluations remain available as historical artifacts.
- Added the exact reported dream and Arabic form cases to the clearly labeled,
  assistant-judged regression smoke dataset. It is not an independent benchmark.

## Use

Restart the backend to load the updated handoff/index; refresh/restart the frontend:

```bash
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log
npm --prefix frontend run dev
```

The reported dream should now show six exact source excerpts, including PDF pages
84, 87, 619, 620, 637 and 1171. They support individual source topics; they do not
prove an interpretation of the entire dream, or of every detail such as the shore.
No live provider call was made for this repair. The existing local key is configured and `RUYA_ENABLE_GENERATION=true` was set in
the ignored local `.env`. Restart the backend and explicitly check the UI's
synthesis option to request a generated summary. Keep the key only on the backend. That
sends the query and selected excerpts to DeepSeek and may incur provider charges.

## Limits

Coverage remains small: two fully reviewed passages plus six reviewed excerpts.
Other dreams may still lack reviewed evidence. More source review is needed for
broad usefulness. Exact citation validation does not establish semantic entailment,
and no live-model behavior or human scholarly approval is claimed. Optional backend generation was enabled; the UI still requires an explicit opt-in. Phase 6 packaging remains deferred.

## Validation results

- **56 backend tests passed in 57.779 seconds**, including all prior regressions,
  exact excerpt/offset/page integrity, unchanged parent statuses, false-match checks
  (`سفرجل`/`سفرة`), and the exact user dream's six source excerpts.
- **9 Chromium browser tests passed (1.1 minutes)**, including that dream through
  the default hybrid mode on mobile, review-scope labeling and no horizontal overflow.
- Production frontend build, TypeScript, formatting and `git diff --check` passed.
- On the eight-query reviewed regression smoke set, Recall@4/MRR@4 were 1.0/1.0 for
  BM25 and hybrid, and 0.5/0.5 for dense. For the reported dream alone, all three
  methods retrieved the four labeled parent topics at k=4. These limited,
  assistant-authored labels do not establish general retrieval quality.
- The experimental evaluation was regenerated against its new corpus checksum;
  original Phase 3 evaluation artifacts were preserved.
- No live generation call was made. Backend generation availability was checked via
  configuration without printing credentials. The frontend still requires opt-in.

New data/code: scoped review ledger, expanded smoke dataset and reports,
`backend/app/rag/chunking/excerpts.py`, `backend/app/rag/retrieval/query.py`,
`backend/tests/test_excerpt_coverage.py`. Existing retrieval, API schemas/services,
source components, browser tests and active handoffs were updated. Current OpenAPI
is exported to `storage/manifests/current-openapi.json`; the Phase 4 export remains
historical. No original PDF, candidate text, full-parent review status or old index
was deleted or modified.
