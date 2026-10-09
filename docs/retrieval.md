# Chunking and retrieval

## Corpus admission

The default `reviewed` policy admits only verified passages with adequate Arabic and
no blocking extraction flags. Current verification is AI-assisted, as recorded in
Phase 2 and subsequent review batches. It is not human scholarly approval. There are
31 completely reviewed passages (24 Nabulsi, 7 Ibn Shahin) plus six reviewed exact excerpts
from four additional parents. The excerpt ledger records offsets, checksums and
PDF review scope; it never promotes the full parent. Coverage remains very limited.

Ibn Shahin's explicit `فصل في رؤيا ...` section headings also supply topics for
lexical ranking and interpretation evidence selection. An explicit `وهو` gloss
can name the same topic, such as `الطل وهو الندى`. Body text never supplies an
inferred symbol, and compound headings are not split into unrelated topics.
Source passage metadata and quoted text remain unchanged.

`experimental` is an explicit opt-in for unreviewed candidates that meet the same
text-quality checks. It does not change validation status. Neither policy admits Ibn Sirin or automatically admits font-corrupt/replacement
text, suspect reading order or unnamed sections. A clean, explicitly reviewed excerpt
can be admitted separately even when another part of its parent contains defects.
Rejected passage IDs and reasons are saved. Quality heuristics can miss errors;
experimental results must be checked against PDFs before publication or generation.

## Chunks and citations

Each chunk belongs to exactly one parent passage. Complete short passages remain
whole. Long passages use the model's actual fast tokenizer: default maximum 120
content tokens, with 16 tokens of overlap, below MiniLM's 128-token limit including
special tokens. The splitter prefers layout-line ends, then whitespace boundaries.
Sentence structure may still be imperfect because the PDFs do not consistently
encode sentence punctuation. This is source-entry-aware chunking, not semantic
sentence classification.

Character offsets are into the parent's candidate text. Source rows that intersect
those offsets determine the chunk's actual PDF page range. `raw_source_text` contains
those original rows, which can extend beyond a partial-row chunk; Unicode correction
is not assumed to preserve character offsets. Parent IDs, symbol, chapter, section,
book, author, source checksum and review status survive. The loader retains the full
parent corpus in the ingestion run; chunking never deletes or replaces it.

## Retrieval algorithms

- Dense: CPU Sentence Transformers MiniLM, 384 dimensions, unit-normalized vectors,
  persisted in a FAISS `IndexFlatIP`. Query-only embedding at search time. No silent
  truncation: over-budget query inputs fail explicitly.
- Lexical: readable Python BM25 with `k1=1.5`, `b=0.75`, Arabic search normalization,
  symbol/section terms, definite-article handling, a small explicit Arabic form map,
  and an explicit 2-point symbol-match bonus. This is not general stemming.
- Hybrid: reciprocal rank fusion, `sum(1 / (60 + rank))`, over up to 50 candidates
  from each retriever. It combines positions rather than incomparable raw scores.

Book and exact chapter filters apply before candidate truncation. Scores, component
ranks, latency, source coordinates and review status are exposed. Cosine and RRF
scores are ranking signals, not confidence probabilities or truth judgments.
FAISS currently scans all vectors for deterministic filtering; this is appropriate
for the local corpus, not an ANN scalability claim.

## Commands

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/build_index.py
.venv/bin/python scripts/build_index.py --policy experimental
# Use the index directory printed by the chosen build:
.venv/bin/python scripts/search.py --index storage/indexes/INDEX_ID \
  --query 'رأيت يعسوب في المنام' --mode hybrid --top-k 5 \
  --html storage/inspection/search.html
.venv/bin/python scripts/search.py --index storage/indexes/INDEX_ID \
  --query 'يعسوب' --mode bm25 --book nabulsi
```

Open the generated HTML locally to inspect quotes, raw source rows, metadata and
clickable PDF pages. It is a static real-result inspection report, not the Phase 5
Next.js application. Generate another query through the CLI; the FastAPI and Next.js interfaces use the same retrieval implementation. HTML escapes all source/query content and makes no external requests.

Model loading defaults to the pinned local cache. For a fresh machine, use
`build_index.py --download-model` to explicitly allow downloading the pinned model.
No API key is required. BM25 search of an existing index needs no loaded model.

## Index compatibility

Each immutable index saves model name and pinned revision, dimension, normalization,
model capacity, chunk settings, source manifest hash, corpus hash, dependency
versions, implementation checksums, index version, creation time and output hashes.
The loader checks artifact/corpus hashes, vector count/dimension, and the embedder's
full identity before dense retrieval. A changed model/revision cannot silently query
the old vectors. FAISS is a generated local artifact; only load your own indexes.

Repeated identical builds reuse the verified index. No published index is overwritten.
Use the explicit Phase 3 handoff to select the intended corpus; never concatenate
historical index directories or candidate run versions.
