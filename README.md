# Ru'ya RAG

Arabic retrieval over traditional dream interpretations in historical texts.
These texts are not facts, predictions, or definitive religious rulings.

**Current state: Phase 5 Arabic RTL frontend implemented.** Five Next.js pages
connect to the FastAPI backend: interpretation, source search, digital library,
engineering dashboard and project methodology. Light/dark modes, PDF citations,
source inspection and actual quality metrics are available. The reviewed corpus
contains two fully reviewed passages plus six source-reviewed excerpts; broad
interpretation quality is not established. The [sea-and-ship retrieval repair](docs/source-coverage-fix.md)
explains the current coverage and how to enable optional generation. Docker packaging remains for Phase 6.

Start the backend and frontend in separate terminals:

```bash
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log
npm --prefix frontend ci
npm --prefix frontend run dev
```

Open http://127.0.0.1:3000. API docs: http://127.0.0.1:8000/docs.
See [frontend setup](docs/frontend.md), [backend setup](docs/backend.md),
[generation limits](docs/generation.md), and [Phase 5 results](docs/phase5-report.md).

Sources: *تعطير الأنام في تعبير المنام* by عبد الغني النابلسي;
*الإشارات في علم العبارات* by ابن شاهين الظاهري; and
*منتخب الكلام في تفسير الأحلام*, traditionally attributed to Ibn Sirin with
uncertain authorship. Ibn Sirin remains **OCR_PENDING**, outside passage generation.

## Setup and checks

From the repository root, using Python 3.12+:

```bash
# If you do not already have an environment:
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
# Alternatively, install the project:
.venv/bin/python -m pip install -e .

.venv/bin/python -m unittest discover -s backend/tests -v
.venv/bin/python scripts/ingest.py all
# Process one supported book:
.venv/bin/python scripts/ingest.py --books nabulsi
```

The original PDFs must be in `data/raw/` with their existing filenames. Tests use
local PDFs and retained Phase 1 data; nothing downloads books or calls an LLM.
Core dependencies include PyMuPDF, Pydantic, NumPy, Sentence Transformers and CPU
FAISS. Retrieval tests require the pinned model in the local cache. A fresh machine
can download it with `scripts/build_index.py --download-model`. The existing
environment was tested; a full fresh-environment installation has not been tested.

## Ingestion outputs

The CLI prints a versioned run directory under `data/processed/ingestion/` containing:

- `pages.jsonl`: original extraction, normalized and candidate text, span coordinates.
- `boundaries.jsonl`: book-specific chapter, section, symbol and conclusion boundaries.
- `passages.jsonl`: candidate passages with stable source anchors and page ranges.
- `report.json`: actual counts, quality flags, coverage and OCR status.
- `review_queue.jsonl`, `rejected_candidates.jsonl`, `excluded_lines.jsonl`: review evidence.
- `manifest.json`: source, implementation, dependency and output checksums.

Identical inputs and implementation reuse a checked run; changed inputs produce a
new version. Existing artifacts are never overwritten by this runner. A modified PDF
is extracted but held out of segmentation until its edition profile is reviewed.

Explicit review decisions create a separate reviewed derivative. Only full passage
and boundary checks can produce `verified` text. An AI-assisted visual check is
recorded as such; it is not represented as human or scholarly validation. See
[ingestion and review commands](docs/ingestion.md).

## Retrieval

```bash
.venv/bin/python scripts/build_index.py
# Optional, explicitly unreviewed-candidate corpus:
.venv/bin/python scripts/build_index.py --policy experimental
.venv/bin/python scripts/search.py --index storage/indexes/c497c4f81508fcb20bd75b01 \
  --query 'يعسوب' --mode hybrid
.venv/bin/python scripts/evaluate.py --index storage/indexes/c497c4f81508fcb20bd75b01 \
  --dataset data/evaluation/retrieval-expanded-smoke.json \
  --output data/evaluation/retrieval-expanded-report.json --k 1 4
```

The exact index IDs above refer to this workspace's recorded build. On a fresh or
modified setup, use the directory printed by `build_index.py`. The
[Phase 3 handoff](storage/manifests/phase3-handoff.json) identifies both selected
indexes. See [retrieval instructions](docs/retrieval.md) for filters and HTML reports.
Evaluation scores are limited smoke tests, not a corpus-wide quality claim.

## Layout and progress

- `backend/app/rag/ingestion/`: extraction, schemas, parsers, reconstruction, manifests, review.
- `backend/app/rag/{chunking,embeddings,retrieval,evaluation}/`: local retrieval subsystems.
- `scripts/`: ingestion, review, index, search and evaluation commands.
- `backend/tests/fixtures/`: excerpts from actual PDFs with page references.
- `data/raw`, `extracted`, `processed`: original sources and preserved outputs.
- `data/quarantine`: known-invalid or superseded early experiments.
- `archive/previous_lessons/v1`: educational lexical/semantic examples.
- `archive/previous_lessons/phase1_pipeline`: frozen old pipeline for regression comparison.
- `storage/manifests`: baseline and phase handoff records.

[Phase 3 report](docs/phase3-report.md) · [Phase 2 report](docs/phase2-report.md) · [Source review](docs/source-review.md)
· [Architecture](docs/architecture.md) · [Learning guide](docs/learning-guide.md)
· [Phase 1 audit](docs/repository-audit.md) · [Phase 1 cleanup](docs/cleanup-report.md)

Phase 5 is implemented; Phase 6 (testing and packaging) awaits confirmation. Product
results come from the API; simulated provider responses exist only in clearly labeled
automated tests. Retrieval results alone are not dream predictions.
Keep independent PDF backups: Git ignores source data, and checksums cannot restore it.
