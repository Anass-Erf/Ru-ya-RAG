# Ru'ya RAG

Arabic retrieval over traditional dream interpretations in historical texts.
These texts are not facts, predictions, or definitive religious rulings.

**Current state: Phase 4 FastAPI backend implemented.** BM25, dense and hybrid
retrieval feed an optional DeepSeek adapter with checked citations and bounded calls.
Retrieval works without an API key. The default reviewed corpus still contains only
two AI-assisted source-checked passages; broad interpretation quality is not established.
Next.js and Docker remain for later phases.

Run `.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log`
and open http://127.0.0.1:8000/docs. See [backend setup and endpoints](docs/backend.md),
[generation limits](docs/generation.md), and [Phase 4 results](docs/phase4-report.md).

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
.venv/bin/python scripts/search.py --index storage/indexes/97578da88bda54f4322ffe55 \
  --query 'يعسوب' --mode hybrid
.venv/bin/python scripts/evaluate.py --index storage/indexes/97578da88bda54f4322ffe55 \
  --output data/evaluation/retrieval-smoke-report.json
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

Phase 4 is implemented; Phase 5 (Next.js frontend) awaits confirmation. There are no mock
interpretations, and retrieval results alone are not dream predictions.
Keep independent PDF backups: Git ignores source data, and checksums cannot restore it.
