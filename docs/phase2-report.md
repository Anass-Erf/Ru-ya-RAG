# Phase 2 report — 2026-10-08

Ingestion repair, candidate reconstruction and source-review tooling are implemented.
The bulk corpus is **not** fully verified or ready for automatic inclusion in a live
index. Phase 3 has not started.

## Actual corpus results

| Source | PDF pages assessed | Chapters | Sections/symbols | Candidate passages |
|---|---:|---:|---:|---:|
| nabulsi | 1410 | 28 | 2455 | 2455 |
| ibn-Shahin | 416 | 80 | 281 | 319 |
| ibn-sirin | 385 | 0 | 0 | 0 |

Nabulsi's 2,455 symbols replace the old 2,712 heuristic starts for the new run; old
outputs remain untouched. The new count includes repaired detection and rejected
continuations, not a claim of ground-truth completeness. Ibn Shahin has 281 section
boundaries plus 38 substantive chapter preambles; 42 heading-only chapter blocks
are retained outside passages. Counts agreeing with chapter outlines do not prove accuracy.
All 385 Ibn Sirin pages have no extracted text; status remains OCR_PENDING.

Before review, 1,135 passages need review and 1,639 are unreviewed. Four explicit
AI-assisted source checks produce a derivative with **2 verified**, **1,135 needs_review**
and **1,637 unreviewed** passages. This is a limited fidelity check, not human or
scholarly approval. See [source review](source-review.md) for exact scope and evidence.

## Changes and evidence

- Replaced unconditional word reversal with native positioned spans; original and
  normalized extraction remain available. Geometry spaces fix split headings;
  nonmonotonic Arabic glyph positions flag unresolved internal reading-order problems.
- Recovered Nabulsi الكاف/الواو chapters, reject conditional continuations, and stop
  the final entry before the author's closing prose on PDF page 1405.
- Added Ibn Shahin chapter/section reconstruction using the edition's heading color,
  wrapped titles and cross-page context; prose cross-references are not headings.
- Added Pydantic provenance schemas, source-anchored IDs, exact boundary validation,
  source ranges, explicit exclusions and checksummed immutable publication.
- Added a separate review command that binds decisions to the exact source and text.
- Archived the Phase 1 implementation; its frozen replay still reproduces old data.

Nabulsi accounts for 20,498 nonempty layout rows: 18,731 in passages and 1,767 excluded.
Ibn Shahin accounts for 13,106 rows: 12,894 in passages and 212 excluded. No original
text was deleted. All 2,774 passages were checked against their recorded source rows;
raw and candidate text reconstruct exactly, with no overlapping passage ranges.
The longest candidate contains 45,507 characters and is retained, not truncated.

## Run artifacts

Candidate run: `data/processed/ingestion/b0217c73dfa8a89464281d47/`.
Reviewed derivative: `data/processed/reviewed/576bd911d9e8cb2946d9cd1b/`.
[Handoff manifest](../storage/manifests/phase2-handoff.json) records selected versions
and checksums. [Report snapshot](../storage/manifests/phase2-ingestion-report.json)
retains actual quality counts in a small trackable file.

Earlier exploratory immutable runs are retained as development history. They must
not be concatenated as separate corpus partitions. The handoff selects the intended
run explicitly. Repeating the final ingestion command returned `reused: true` after
checking output hashes. Both candidate and reviewed manifests were verified.

## Files created, modified and archived

Created active implementation:
- `backend/app/rag/ingestion/{catalog,models,normalization,extraction,parsers,reconstruction,pipeline,review}.py`
- `scripts/review.py`
- `backend/tests/test_ingestion.py`, `backend/tests/fixtures/{source_pages.jsonl,README.md}`
- `data/evaluation/phase2-review-decisions.json`
- `storage/manifests/{phase2-handoff,phase2-ingestion-report}.json`
- `docs/{phase2-report,source-review}.md`
- Versioned candidate/reviewed run directories described above.

Modified:
- `scripts/ingest.py` (current versioned pipeline CLI).
- `backend/tests/test_phase1.py` (replay the archive).
- `pyproject.toml`, `requirements.txt` (Pydantic 2.14.0 added to both).
- `README.md`, `.env.example`, `docs/{ingestion,architecture,evaluation,learning-guide}.md`.
- `archive/previous_lessons/README.md` (historical replay instructions).

Archived under `archive/previous_lessons/phase1_pipeline/`:
- `pdf_extractor.py`, `clean_validate.py`, `detect_structure.py`, `validate_headings.py`,
  `detect_nabulsi_entries.py`, `build_nabulsi_entries.py`, `paths.py` from the old backend package.
- The former ingestion CLI is `run.py`; an archive package initializer was added.
  Paths and usage instructions were adjusted for the archive; parsing remains frozen.

Deleted: no original files, datasets, PDFs or artifacts. Existing source PDFs,
extracted TXT, processed JSON/JSONL, and educational vectors still match Phase 1
baseline checksums. Git metadata remains unavailable in this workspace; no commit
or tracked-file status is claimed. The existing environment gained Pydantic and
its dependencies; no model weights or embeddings were generated.

## Validation and commands

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s backend/tests -v
.venv/bin/python scripts/ingest.py all
.venv/bin/python scripts/review.py \
  --run data/processed/ingestion/b0217c73dfa8a89464281d47 \
  --decisions data/evaluation/phase2-review-decisions.json \
  --output-root data/processed/reviewed
```

- Final automated suite: **22 tests passed** (19 Phase 2, three Phase 1).
- Full three-PDF ingestion: succeeded; repeated run reused checksum-verified artifacts.
- All 2,774 passages passed whole-corpus source-row/overlap checks.
- Original-data checksum preservation: passed.
- Review command: published the explicit reviewed derivative successfully.
- Dependency declarations agree; `pip check` reports no broken requirements.
- During development, a short-entry test initially used an inaccurate expected
  label/word; corrected it against the actual fixture. No failures remain.
- Not performed: exhaustive human transcription review, corpus-wide segmentation
  precision/recall measurement, fresh-environment installation or any Phase 3+ tests.

## Remaining limits and next phase

Most candidates still need source review. In particular, 273 Ibn Shahin passages
have nonmonotonic glyph-order warnings and 228 have known font artifacts; categories
overlap. Nabulsi has 543 font-artifact warnings, 268 short passages, 70 long page spans,
five oversized texts, and 32 passages spanning a low-text page. Diagnostic heuristics
can themselves produce false positives or miss defects. Edition-specific geometry
and colors are not a universal Arabic PDF parser.

Very long sections remain intact; token-aware chunking and an explicit quality gate
belong to Phase 3. There are zero approved indexed chunks, no embeddings for this
corpus, and no retrieval scores. Proceeding with retrieval should use an explicit
review/quality policy, not treat all candidates as validated.

Phase 2 stops here for the requested confirmation before Phase 3.
