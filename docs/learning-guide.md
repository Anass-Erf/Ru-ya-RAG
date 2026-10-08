# Learning guide

## Provenance schemas

**What/why:** keep source evidence separate from transformed or reviewed text.
**How:** Pydantic models validate pages, positioned spans, boundaries, source ranges,
and passages; extra fields are rejected. Source and text hashes bind identities and reviews.
**Choices:** book IDs and original filenames remain stable; PDF pages are 1-based;
layout rows and bboxes locate evidence, while candidate display and search text differ.
**Failure modes:** confusing printed page numbers with PDF positions; labeling cleanup
as verification; stale boundaries; sequential IDs changing after an earlier correction.
**Test:** schema/status tests, stale-boundary rejection and round-trip source reconstruction.
**Interview:** “Every passage carries the PDF checksum and exact extraction coordinates.”

## Native PDF extraction

**What/why:** obtain readable candidates without destroying the original extraction.
**How:** preserve native text, collect positioned spans, group baselines, retain span
order and sort rows vertically. Normalize Unicode separately and record geometry-derived spaces.
**Choices:** no global word reversal and no LLM reconstruction. Known edition checksums
limit parser assumptions. All pages are assessed for text; scanned Ibn Sirin is withheld.
**Failure modes:** wrong native glyph order, embedded-font substitutions, broken words,
column layouts and nearly blank pages. Glyph-order flags expose remaining defects.
**Test:** direct PDF extraction comparisons, geometry/fragment fixtures, source-page images.
**Interview:** “I found that reversing a whole line fixed one symptom while corrupting
other words, so I retained layout evidence and flagged unresolved font problems.”

## Book-specific segmentation

**What/why:** build coherent source passages instead of arbitrary page slices.
**How:** Nabulsi uses exact alphabetic chapter labels plus quoted/dashed symbols;
conditional phrases stay inside entries. Ibn Shahin uses blue headings plus anchored
patterns and keeps chapter/section context across pages.
**Choices:** chapter-only titles and editorial conclusions are preserved as excluded
evidence; substantive chapter preambles remain candidates. Section internals are not
split into invented symbols. Rules remain specific to the supplied editions.
**Failure modes:** quotations split entries, prose becomes a chapter, missed starts
merge symbols, or authorial closing prose contaminates the final entry.
**Test:** actual PDF fixtures around pages 195, 460, 1057, 1357 and 1405; colored
Ibn Shahin headings and body cross-references. Matching counts is not enough.
**Interview:** “I test boundaries against source examples, including negative cases.”

## Reconstruction and quality accounting

**What/why:** preserve cross-page interpretations and explain anything left out.
**How:** validate boundary book/position/text, then collect disjoint source ranges.
Keep raw, NFKC and candidate text, normalize a separate search version, attach flags.
Every nonempty row belongs to a passage or an explicit exclusion record.
**Choices:** keep short entries; retain and flag very long sections for Phase 3
chunking. Stable IDs use source anchors; changing content invalidates prior reviews.
**Failure modes:** missing pages, changed extraction coordinates, merged symbols and
unresolved font/order defects. Complete row accounting cannot detect absent PDF text.
**Test:** cross-page reconstruction, no overlap, stable IDs, missing-page/mixed-book
rejection, and corpus-wide equality between passage text and its recorded source rows.
**Interview:** “Coverage proves traceability, not semantic correctness.”

## Immutable runs and explicit review

**What/why:** make reruns reproducible and stop candidates becoming trusted silently.
**How:** checksum-addressed run directories, atomic publication, output verification on
reuse; review decisions create a separate derivative with source/text hashes and evidence.
**Choices:** no overwrite flag on the current runner; a reviewer must cover the whole
passage and boundaries. Record human versus AI-assisted review honestly.
**Failure modes:** editing a run breaks checksums; claimed reviews may still be poor;
hashes are not backups or signatures. Review assertions require judgment.
**Test:** repeat runs reuse artifacts, tampering fails, stale/unknown/duplicate decisions
fail, incomplete verified page coverage fails. Original-data preservation tests remain.
**Interview:** “The system records why a passage was verified and exactly which version.”

## Educational retrieval (archived)

**What/why:** compare word overlap with multilingual semantic similarity.
**How:** TF-IDF/cosine versus normalized 384-dimensional MiniLM embeddings; persist
vectors and example metadata, then embed only the query during search.
**Choices:** five artificial examples are isolated from the historical corpus.
**Failure modes:** synonyms defeat lexical matches; cosine similarity is not truth or
confidence. Saving model name alone does not guarantee index compatibility.
**Test:** lexical lesson and saved vector inspection; semantic inference needs model weights.
**Interview:** “A persistent index avoids re-embedding the documents per query.”

## Chunking and corpus admission

**What/why:** keep interpretable source units while meeting the encoder's real input limit.
**How:** gate passages by review status/flags, then split only long parents using exact
fast-tokenizer counts, line/word boundaries and a small token overlap. Map character
spans back to source rows for precise PDF ranges.
**Choices:** reviewed and experimental corpora are separate; originals and full parent
passages remain intact. Raw source rows may extend beyond a partial-row chunk.
**Failures:** truncation loses text; arbitrary page splitting mixes symbols; broad
quality gates admit damaged text or exclude useful passages. Unknown flags fail closed.
**Test:** full coverage and stable IDs for real long/cross-page fixtures, short entries,
metadata from both books, token limits and policy rejection.
**Interview:** “The encoder limit determines my chunk budget; I test for text loss.”

## Persistent dense, lexical and hybrid retrieval

**What/why:** compare semantic matching with Arabic keyword/symbol matching.
**How:** unit-normalized MiniLM vectors in FAISS inner-product search; readable BM25;
reciprocal rank fusion combines candidate positions with a constant of 60.
**Choices:** CPU execution, pinned model revision, exact index compatibility checks,
query-only embeddings, explicit lexical symbol bonus and source filters.
**Failures:** Arabic inflections defeat exact tokens, dense neighbors can be irrelevant,
and equal-weight fusion can reduce quality. Scores are not calibrated probabilities.
**Test:** vector norms/dimensions, real symbol lookup, known RRF arithmetic, model
mismatch and checksum rejection, lexical-only operation and corpus filtering.
**Interview:** “Hybrid search is a hypothesis to evaluate, not an automatic improvement.”

## Evaluation and inspection

**What/why:** show actual evidence for ranking behavior and make failures inspectable.
**How:** Arabic queries map to explicit passage IDs; chunk rankings are deduplicated;
compute recall, fixed-k precision and reciprocal rank, plus warm-query latency.
HTML reports display actual scores, candidate/raw text, source pages and status.
**Choices:** the four-query/two-passage set is explicitly a smoke test. Seven broader
query judgments remain drafts for human review and cannot be scored as approved labels.
**Failures:** tiny or self-authored datasets overstate quality; duplicated chunks inflate
metrics; model-loading time confounds query latency; filters can hide relevant labels.
**Test:** known metric examples, absent-label rejection, actual report runs and HTML
escaping. Inspect the recorded travel paraphrase failure rather than hiding it.
**Interview:** “I distinguish measured smoke-test results from an independent benchmark.”

## Later work

FastAPI and grounded DeepSeek generation are Phase 4. The Next.js application and
Docker packaging remain later phases. More human source/relevance review is needed
before the candidate corpus can support a credible public interpretation application.

## FastAPI service and provider boundary (Phase 4)

The API exposes the same checked retrieval artifacts to an eventual frontend.
`Library` loads handoffs and checksums once, executes synchronous searches in worker
threads, and lazily loads cached MiniLM. Pydantic validates Arabic requests and
response shapes. The app factory allows real-library tests with a fake provider.
Missing artifacts degrade readiness; unavailable embeddings fall back visibly to BM25.
Test endpoint behavior with `python -m unittest backend.tests.test_api -v`.
Interview explanation: “The API is a typed adapter over my retrieval pipeline, not a
second retrieval implementation. Sources retain the same IDs and PDF provenance.”

`Interpreter` separates evidence eligibility, budget checks, provider execution and
output validation. The provider protocol keeps HTTP details outside retrieval.
Strict JSON and exact quote checks reject invented citation metadata; the server
owns page numbers. These are mechanical checks, not proof that prose follows from
its quotes. Timeouts, provider rate limits, and invalid outputs retain source results.
Test with `python -m unittest backend.tests.test_provider -v` and the generation
cases in `test_api`. A live model still needs a separately judged faithfulness set.
Interview explanation: “I can trace every accepted citation to a retrieved chunk,
while explicitly distinguishing citation validity from semantic faithfulness.”
