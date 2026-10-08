# Phase 1 cleanup report — 2026-10-08

All 39 pre-existing project files were retained. No file contents were deleted.
The now-empty `src/` directory was removed after relocating its six scripts.

## Moved and modified

- `src/build_nabulsi_entries.py` → `backend/app/rag/ingestion/build_nabulsi_entries.py`; paths and usage instructions updated, parsing logic preserved.
- `src/clean_validate.py` → `backend/app/rag/ingestion/clean_validate.py`; paths and usage instructions updated, parsing logic preserved.
- `src/detect_nabulsi_entries.py` → `backend/app/rag/ingestion/detect_nabulsi_entries.py`; paths and usage instructions updated, parsing logic preserved.
- `src/detect_structure.py` → `backend/app/rag/ingestion/detect_structure.py`; paths and usage instructions updated, parsing logic preserved.
- `src/pdf_extractor.py` → `backend/app/rag/ingestion/pdf_extractor.py`; paths and usage instructions updated, parsing logic preserved.
- `src/validate_headings.py` → `backend/app/rag/ingestion/validate_headings.py`; paths and usage instructions updated, parsing logic preserved.

## Archived

- `v1/compare.py` → `archive/previous_lessons/v1/compare.py`; contents unchanged.
- `v1/data/documents.json` → `archive/previous_lessons/v1/data/documents.json`; contents unchanged.
- `v1/lesson01.py` → `archive/previous_lessons/v1/lesson01.py`; contents unchanged.
- `v1/lesson02.py` → `archive/previous_lessons/v1/lesson02.py`; contents unchanged.
- `v1/search.py` → `archive/previous_lessons/v1/search.py`; working-directory dependency fixed.
- `v1/storage/documents.json` → `archive/previous_lessons/v1/storage/documents.json`; contents unchanged.
- `v1/storage/index_documents.py` → `archive/previous_lessons/v1/storage/index_documents.py`; working-directory dependency fixed.
- `v1/storage/model.txt` → `archive/previous_lessons/v1/storage/model.txt`; contents unchanged.
- `v1/storage/vectors.npy` → `archive/previous_lessons/v1/storage/vectors.npy`; contents unchanged.

## Quarantined, unchanged

- `data/processed/nabulsi_entry_candidates.jsonl` → `data/quarantine/nabulsi_entry_candidates.jsonl`
- `data/processed/nabulsi_entry_candidates_filtered.jsonl` → `data/quarantine/nabulsi_entry_candidates_filtered.jsonl`
- `data/processed/nabulsi_entry_candidates_strict.jsonl` → `data/quarantine/nabulsi_entry_candidates_strict.jsonl`
- `data/processed/nabulsi_entry_report.json` → `data/quarantine/nabulsi_entry_report.json`
- `data/processed/nabulsi_entry_report_filtered.json` → `data/quarantine/nabulsi_entry_report_filtered.json`
- `data/processed/nabulsi_entry_report_strict.json` → `data/quarantine/nabulsi_entry_report_strict.json`

## Kept unchanged

- `data/extracted/ibn-Shahin_candidate.txt`
- `data/extracted/ibn-Shahin_raw.txt`
- `data/extracted/nabulsi_candidate.txt`
- `data/extracted/nabulsi_raw.txt`
- `data/processed/nabulsi_entries_report.json`
- `data/processed/nabulsi_entries_review.jsonl`
- `data/processed/nabulsi_entries_samples.txt`
- `data/processed/nabulsi_entry_candidates_v3.jsonl`
- `data/processed/nabulsi_entry_report_v3.json`
- `data/processed/normalized_headings.jsonl`
- `data/processed/pages.jsonl`
- `data/processed/quality_report.json`
- `data/processed/review_samples.txt`
- `data/processed/structure_candidates.jsonl`
- `data/processed/structure_report.json`
- `data/raw/ibn-Shahin.pdf`
- `data/raw/ibn-sirine.pdf`
- `data/raw/nabulsi.pdf`

## Created

- `README.md`
- `.gitignore`
- `.env.example`
- `pyproject.toml`
- `scripts/ingest.py`
- `backend/__init__.py`
- `backend/app/__init__.py`
- `backend/app/rag/__init__.py`
- `backend/app/rag/ingestion/__init__.py`
- `backend/app/rag/ingestion/paths.py`
- `backend/tests/test_phase1.py`
- `storage/manifests/phase1-baseline.json`
- `archive/previous_lessons/README.md`
- `data/raw/README.md`
- `data/quarantine/README.md`
- `docs/architecture.md`
- `docs/evaluation.md`
- `docs/ingestion.md`
- `docs/learning-guide.md`
- `docs/repository-audit.md`
- `docs/cleanup-report.md`

Reserved empty directories: `storage/indexes/`, `data/evaluation/`.

## Untouched and unavailable

- `.venv/` retained; no packages installed or model weights downloaded.
- `.git/`, `.agents/`, `.codex/`, `.aws/` untouched; no unknown user files removed.
- Git status/history cannot be checked because the supplied `.git` directory is empty.
- No existing data or vectors were regenerated in place; checks ran in temporary directories.

## Actual verification

- ` .venv/bin/python -m unittest discover -s backend/tests -v`: **3 tests passed**.
  Tests verify original data/artifact SHA-256 checksums, all five post-extraction
  stages reproducing their existing outputs byte-for-byte from another working
  directory, and overwrite refusal before any stage writes.
- Full two-book PDF extraction in a separate temporary directory: exit 0;
  all four TXT outputs byte-identical; 1,410 and 416 pages processed.
- `.venv/bin/python archive/previous_lessons/v1/lesson01.py`: exit 0;
  all query scores zero for the existing synonym example.
- `.venv/bin/python -m pip check`: no broken requirements.
- All relocated ingestion modules compile.
- No failing checks. Semantic inference, fresh dependency installation, human PDF
  fidelity review and segmentation regression evaluation were **not run**.
- No API/frontend/Docker checks exist because those phases have not started.

## Running and limitations

See [README](../README.md) for setup and tests and [ingestion](ingestion.md) for
safe isolated runs. Tests require preserved local datasets. No parser accuracy
claim follows from byte equality. Existing v3 entries remain unvalidated; no
approved searchable corpus exists. The CLI guard is not a transactional writer.
Pinned observed top-level dependencies are not a complete environment lock.

Phase 2 awaits user confirmation, as explicitly requested in the task.
