# Repository audit — 2026-10-08

Scope: Phase 1 only. All 11 original Python scripts were read, along with the
existing reports, JSON/JSONL schemas and record counts, extracted-text samples,
PDF page counts and sampled text layers, saved vector metadata and environment
configuration. No AGENTS.md was found. No existing README, dependency declaration,
backend, frontend, tests, or Docker configuration was present.

## Inventory and findings

- PDFs: Nabulsi 1,410 pages; Ibn Shahin 416; Ibn Sirin 385. First, middle and last
  sampled pages in Ibn Sirin have no extracted text. Its status remains OCR_PENDING;
  this sample is not a comprehensive OCR assessment. All three originals are retained.
- `pages.jsonl`: 1,826 records, all `validated: false`. Reports flag 605 Nabulsi
  pages and 311 Ibn Shahin pages. Counts are diagnostics, not fidelity measures.
- Structure: 26 Nabulsi chapter candidates, 80 Ibn Shahin chapter candidates and
  283 section candidates. Normalizing headings does not validate them.
- Nabulsi v3: 2,712 starts and 2,712 reconstructed entries, all unvalidated.
  Reports flag 369 short entries, 64 long page spans, six long texts (categories overlap).
  الكاف and الواو are absent from its chapter distribution; investigate against PDFs.
- Earlier outputs: 1,003 original candidates, 987 strict candidates, and 18,325
  filtered candidates. The filtered report includes prose as chapters, including
  `باب السلطان فإنه يشهد شه`. These outputs have no consumers in current scripts.
  Their producing script versions are absent, so they cannot safely be reproduced.
- `v1` contains five educational search scripts, five artificial documents, and
  a normalized float32 (5, 384) NumPy index. Model identity is saved as
  `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`; no revision,
  corpus checksum or compatibility manifest exists. This is not a book index.
- Python 3.12.3 is available as `python3` and `.venv/bin/python`; bare `python`
  is unavailable outside activation. The existing environment is about 5.8 GB.
  Installed versions: PyMuPDF 1.28.2, NumPy 2.5.3, scikit-learn 1.9.1,
  sentence-transformers 6.1.0, torch 2.14.1. Pydantic and pytest are absent.
  Phase 1 tests use the standard library. Dependency declarations record observed
  versions; this is not a complete lockfile or a claim of fresh-install verification.
- `.git` is an empty, read-only directory in this workspace. `git status` and
  `git ls-files` both fail. Tracked/generated-file history cannot be inspected;
  no Git metadata was modified or initialized. Ignore rules do not untrack files.
- The IDE-listed `data/inspection/nabulsi_pages.json` does not exist on disk.

## Actual dependency graph

```text
data/raw/{nabulsi,ibn-Shahin}.pdf
  -> pdf_extractor -> data/extracted/{book}_{raw,candidate}.txt + report.json
  -> clean_validate (candidate TXT only) -> pages.jsonl + quality_report + samples
  -> detect_structure -> structure_candidates.jsonl + structure_report
     -> validate_headings -> normalized_headings.jsonl
  -> detect_nabulsi_entries (pages.jsonl directly) -> candidates_v3 + report_v3
  -> build_nabulsi_entries (pages + candidates_v3) -> entries_review + report + samples
```

Normalized headings are a review side branch, not an input to entry building.
The extraction report was absent at baseline even though TXT outputs existed.
The educational indexer consumes only its own `data/documents.json`; search uses
its saved documents, vectors and model name. Lessons 01/02 and compare are standalone.

## Capability and risk assessment

The six current ingestion scripts execute and preserve review labels. The extractor
uses NFKC followed by unconditional word reversal for every line; it does not detect
reading order or OCR needs. Original raw text is retained, but normalized-only text
is not persisted separately. Cleanup is edition-specific and flags only selected
artifacts. General chapter regexes are broader than the later Nabulsi whitelist.
Chapter normalization is duplicated between detector and builder and differs from
heading normalization. The builder checks coordinate existence, not source-line
identity or book identity in candidate inputs; IDs shift when earlier boundaries
change. No passage schema, validated corpus, chunker, FAISS/BM25, evaluation,
generation, API, or frontend exists yet.

`validate_headings`, educational search and indexer used working-directory-relative
paths; Phase 1 fixes those paths. Import-time model loading in educational lessons
remains archived. Existing semantic examples require model availability and have
not been represented as production retrieval. The known false starts, quoted prose,
post-page-460 detection and cross-page reconstruction still require Phase 2
source-grounded fixtures and review. Counts alone cannot establish correctness.

## Implementation sequence

1. Phase 1: preserve/checksum originals; archive lessons; quarantine obsolete
   outputs; relocate one ingestion implementation; add safe runner, dependencies,
   documentation and relocation checks. Completed; stop for confirmation.
2. Phase 2: verify source pages, fix reading order and book-specific boundaries,
   unify provenance and schemas, stable IDs, quality reports and review workflow.
3. Phase 3: quality-gated chunks, model-compatible dense/BM25/hybrid index and
   human-reviewed relevance judgments with measured evaluation.
4. Phase 4: FastAPI and grounded, bounded DeepSeek generation with retrieval-only mode.
5. Phase 5: Arabic RTL Next.js application connected to actual APIs.
6. Phase 6: full regression suite, Docker and deployment/portfolio documentation.

Each later phase requires the user's confirmation at the previous phase boundary.
