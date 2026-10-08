# Previous educational lessons

`v1` preserves all five original scripts, artificial example documents and the
five-vector MiniLM index. It is not the historical book retrieval system.
Search and indexing paths now resolve relative to the lesson directory.

From the repository root:

```bash
.venv/bin/python archive/previous_lessons/v1/lesson01.py
.venv/bin/python archive/previous_lessons/v1/lesson02.py
.venv/bin/python archive/previous_lessons/v1/compare.py
.venv/bin/python archive/previous_lessons/v1/search.py
# Explicitly rebuilds the archived educational index:
.venv/bin/python archive/previous_lessons/v1/storage/index_documents.py
```

Semantic commands require sentence-transformers and model weights; a first run
may download weights. Phase 1 did not download a model or rebuild this index.

## Frozen Phase 1 ingestion

`phase1_pipeline/` preserves the six old ingestion stages, path helper and old CLI.
The active pipeline is now `backend/app/rag/ingestion/`, run by `scripts/ingest.py`.
For historical replay only, use `phase1_pipeline/run.py`; default paths still point
to the repository's original data, so prefer a separate `--data-dir`. Phase 1 tests
exercise the frozen code in temporary directories. Its parsing defects remain known.
