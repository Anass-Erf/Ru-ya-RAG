# Phase 3 report

Local chunking, persisted dense retrieval, BM25, hybrid search, inspection and
retrieval evaluation are implemented. This is a working engineering foundation;
measured retrieval quality is limited and the bulk corpus remains unverified.
No Phase 4 API or generation work has started.

## Corpus and artifacts

| Policy | Admitted parents | Indexed chunks | Status |
|---|---:|---:|---|
| Reviewed, default | 2 | 2 | AI-assisted source-verified; not human scholarly approval |
| Experimental, explicit opt-in | 1,639 | 2,651 | 2 verified chunks and 2,649 unreviewed chunks |

Experimental chunks comprise 2,624 Nabulsi and 27 Ibn Shahin chunks. Quality/status
checks exclude the other 1,135 parent passages; many important symbols, including
بحر and مطر, remain excluded because their source text needs review. Ibn Sirin is
excluded entirely. No admission decision changes a passage's validation status.

- Reviewed index: `storage/indexes/97578da88bda54f4322ffe55/`
- Experimental index: `storage/indexes/eb1ce35559f7087a3b4c3fe4/`
- [Selected versions and checksums](../storage/manifests/phase3-handoff.json)
- [Reviewed admission report](../storage/manifests/phase3-reviewed-report.json)
- [Experimental admission report](../storage/manifests/phase3-experimental-report.json)
- [Exact-symbol inspection](../storage/inspection/experimental-symbol.html)
- [Paraphrase inspection](../storage/inspection/experimental-paraphrase.html)

Earlier development index versions remain intact. They are not additional corpus
partitions. Identical builds reuse their checked immutable index. Implementation
changes can also reuse checksum-verified vectors when the full corpus and model
identity are identical, while publishing new metadata separately.

## Implementation

The chunker preserves complete short parents, splits only long ones using actual
MiniLM token counts, and retains overlapping candidate-character ranges plus the
intersecting PDF rows/pages. Defaults are 120 content tokens and 16 overlap tokens;
the model limit is 128 including special tokens. Source/raw text and metadata stay
separate. Full source parents are preserved, including oversized excluded passages.

The CPU encoder pins MiniLM revision `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`,
produces 384-dimensional normalized vectors, and refuses silent truncation. FAISS
IndexFlatIP persists those vectors. Arabic BM25 is implemented directly with an
explicit exact-symbol bonus. Equal-weight reciprocal rank fusion combines candidate
rankings. Query-only embeddings, source filters, component scores/ranks and latency
are exposed. Model/revision/dimension/normalization incompatibility fails on load.

The CLI and static RTL HTML inspector show actual results, review status, quotes,
raw source rows, scores and links to original PDF pages. This is not the later Next.js
application. Generated HTML escapes source/query content and uses no external assets.

## Actual evaluation

Four assistant-authored Arabic queries refer to two AI-assisted source-checked
passages. They are human-reviewable but not independently human-judged ground truth.
Both reports are deliberately labeled smoke tests. A seven-query broader draft is
preserved for human review and is rejected by the evaluator until its status changes
through an actual review process.

On the two-chunk reviewed corpus:

| Mode | Recall@1 | MRR@2 | Precision@2 | Mean warm query latency |
|---|---:|---:|---:|---:|
| BM25 | 0.75 | 0.875 | 0.50 | 0.08 ms |
| Dense | 0.50 | 0.750 | 0.50 | 44.37 ms |
| Hybrid | 0.50 | 0.750 | 0.50 | 46.13 ms |

On the 2,651-chunk experimental corpus, using the same four source-linked queries:

| Mode | Recall@5 | MRR@5 | Precision@5 | Mean warm query latency |
|---|---:|---:|---:|---:|
| BM25 | 0.50 | 0.500 | 0.10 | 23.90 ms |
| Dense | 0.00 | 0.000 | 0.00 | 49.33 ms |
| Hybrid | 0.50 | 0.175 | 0.10 | 82.24 ms |

Raw per-query rankings and timings are saved in
[reviewed evaluation](../data/evaluation/retrieval-smoke-report.json) and
[experimental evaluation](../data/evaluation/experimental-smoke-report.json).
Precision uses a fixed k denominator; duplicate chunk parents count once. MRR@k
is mean reciprocal rank within k. Times are single-run warm CPU query timings,
excluding model/index loading, not throughput claims.

These results show that hybrid search is not automatically better than BM25. The
exact-symbol query سفر finds that entry, while the paraphrase رأيت أنني أسافر في المنام
did not retrieve it in the top five. Both inspection reports are retained. The small
set is unsuitable for general quality estimates or tuning claims. Arabic morphology,
query formulation, source errors, exclusions and a general-purpose model all warrant
further investigation using an independently reviewed, larger benchmark.

## Validation

- **35 automated tests passed:** the existing 22 plus 13 retrieval/chunking tests.
- Real cached MiniLM inference, normalized vector dimensions and FAISS search passed.
- Both indexes built successfully on CPU; selected-index manifests/checksums verified.
- Every one of the 2,651 experimental chunks was checked against its parent text;
  all admitted parents have complete overlapping coverage with no gaps or cross-book
  metadata mixing. A separate long-source test covers a 45,507-character passage.
- Tests cover stable IDs, short entries, source pages, quality gates, overlong inputs,
  filters, lexical-only search, RRF arithmetic, metrics and model-revision mismatch.
- Index tampering, unreviewed evaluation drafts and absent relevance labels were rejected.
- HTML containing a script-like query remained escaped and parsed successfully.
- Dependency declarations match, and `pip check` reported no broken requirements.
- A development provenance test initially used non-Arabic text that the quality gate
  correctly excluded before provenance checking; it was corrected to exercise the
  intended failure. File-handle warnings were fixed. No failures remain.
- Not run: fresh-machine installation, exhaustive browser testing, independent human
  relevance review, large-scale throughput/load tests, or any Phase 4+ service tests.

## Files

Created:
- `backend/app/rag/chunking/{__init__,core}.py`
- `backend/app/rag/embeddings/{__init__,minilm}.py`
- `backend/app/rag/retrieval/{__init__,lexical,index}.py`
- `backend/app/rag/evaluation/{__init__,metrics}.py`
- `scripts/{build_index,search,evaluate}.py`, `backend/tests/test_retrieval.py`
- `data/evaluation/{retrieval-smoke,retrieval-review-draft,retrieval-smoke-report,experimental-smoke-report}.json`
- `storage/manifests/phase3-{handoff,reviewed-report,experimental-report}.json`
- Versioned index artifacts and `storage/inspection/` HTML reports.
- `docs/{retrieval,phase3-report}.md`

Modified: `pyproject.toml`, `requirements.txt`, `.gitignore`, `README.md`,
`docs/{architecture,evaluation,learning-guide}.md`.
Archived/deleted: none in this phase. Original PDFs, ingestion artifacts and previous
lesson code remain intact; the existing preservation tests still pass. FAISS was
installed; existing cached model weights were used. No API keys or provider calls
were needed. Git status/history remains unavailable in this workspace.

## Run and next steps

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s backend/tests -v
.venv/bin/python scripts/build_index.py
.venv/bin/python scripts/build_index.py --policy experimental
.venv/bin/python scripts/search.py --index storage/indexes/eb1ce35559f7087a3b4c3fe4 \
  --query 'سفر' --mode bm25 --html storage/inspection/experimental-symbol.html
.venv/bin/python scripts/evaluate.py --index storage/indexes/eb1ce35559f7087a3b4c3fe4 \
  --output data/evaluation/experimental-smoke-report.json --k 1 3 5
```

See [retrieval documentation](retrieval.md) for model-download options, filters,
policy details and citation semantics. The default reviewed index is intentionally
small. The experimental corpus must not be presented as fully validated, and the
measured ranking failures must not be hidden by plausible generated answers.

Phase 4 awaits confirmation. Before a credible public interpretation service, expand
source/relevance review, investigate morphology and query processing, and evaluate
retrieval improvements independently. The API can expose these limitations honestly.
