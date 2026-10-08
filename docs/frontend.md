# Phase 5 frontend

The Arabic RTL application uses Next.js App Router, TypeScript, Tailwind CSS,
a locally adapted shadcn/ui Button with Radix Slot, and Lucide icons. Typography is
bundled locally through Fontsource (Noto Sans Arabic and Noto Naskh Arabic).

From the repository root, in separate terminals:

```bash
# Backend: checked Phase 2/3 artifacts must already exist.
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log

# Frontend: Node 22 was used for validation.
npm --prefix frontend ci
npm --prefix frontend run dev
```

Open http://127.0.0.1:3000. The browser calls FastAPI directly at
`http://127.0.0.1:8000`. A different API origin can be configured in
`frontend/.env.local` using `NEXT_PUBLIC_API_URL`; this value is public and is
inlined at build time. Update the backend's `RUYA_CORS_ORIGINS` for a different
frontend origin. Never put a provider key in a `NEXT_PUBLIC_*` variable.

```bash
# Production compilation and local serving
npm --prefix frontend run build
npm --prefix frontend run start
# Compile-time checks
npm --prefix frontend run typecheck
# Browser checks: stop any servers on ports 3000/8000 first.
npx --prefix frontend playwright install chromium
npm --prefix frontend run test:e2e
```

Browser tests start both local servers themselves and stop them afterward. They
force generation and experimental search off. Tests use retained real corpus
artifacts and exercise no paid provider calls. The production build must exist
before browser tests. Screenshots and traces go to ignored `frontend/test-results/`.

| Page | Backend data and behavior |
| --- | --- |
| `/` | Health, stats and interpretation; reviewed quotes, generated synthesis, citation links, expandable retrieval inspection |
| `/search` | Search, books and stats; book/chapter/mode filters, optional experimental corpus when server permits it |
| `/library` | Actual three-book statuses and counts; links to original PDFs |
| `/dashboard` | Real stats, review counts, quality flags, embedding metadata, retrieval timings, Recall@k and MRR@k |
| `/about` | Corpus attribution, RAG pipeline, privacy, limitations and future work |

Generation is unchecked by default, and disabled when the backend has not enabled
it. Enabling it explicitly discloses that query and selected excerpts go to DeepSeek.
There are no fabricated result fallbacks. Failed API reads show retry actions;
empty search results and insufficient interpretation evidence have separate states.
No dreams, queries or outputs are saved by the frontend. Only theme preference is
stored in localStorage. Rendering uses React text nodes, never model-authored HTML.
PDF links accept only the three catalog routes, and use physical PDF page numbers.

The chapter filter requires the complete chapter title (matching backend semantics).
A title can be copied from a search hit. Arabic morphology is not normalized beyond
the backend's existing rules; use the exact symbol or hybrid search. An empty or
filtered-out corpus produces honest empty results. Dashboard counters belong to
one backend process, and retrieval timing excludes model loading and generation.

The frontend remains a local research application. It does not add authentication,
expand corpus review, validate live-model faithfulness, or make the project ready
for public deployment. Manual screen-reader evaluation and cross-browser testing
are separate from the automated checks. Docker packaging remains Phase 6.

Implementation references:
[Next.js installation](https://nextjs.org/docs/app/getting-started/installation),
[Tailwind with Next.js](https://tailwindcss.com/docs/installation/framework-guides/nextjs),
[shadcn/ui manual setup](https://ui.shadcn.com/docs/installation/manual).
