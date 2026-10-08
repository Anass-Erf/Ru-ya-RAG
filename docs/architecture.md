# Architecture

The current application foundation is a local ingestion pipeline with explicit review.
Retrieval has no external service dependencies at runtime; optional synthesis calls DeepSeek.

```text
PDF catalog and edition checksums
  -> native text + positioned spans + text-layer assessment
  -> NFKC/whitespace normalization + recorded geometry spaces + quality flags
  -> book-specific boundaries (Nabulsi symbols / Ibn Shahin chapters and sections)
  -> source-checked reconstruction and complete row accounting
  -> immutable candidate run: pages, passages, diagnostics, checksums
  -> explicit review decisions -> separate reviewed derivative
  -> explicit reviewed/experimental corpus policy
  -> tokenizer-bounded source chunks -> MiniLM vectors + FAISS / BM25
  -> rank fusion -> CLI / inspection / evaluation / FastAPI
  -> reviewed-symbol evidence gate -> bounded DeepSeek request
  -> strict citation validation -> separate sources and generated statements
```

Pydantic records keep raw, normalized, candidate and validated text separate. Shared
extraction and reconstruction operate on both supported books; parser rules remain
edition-specific. Each boundary must match book, coordinates and source text. Missing
pages, duplicate positions or mismatches abort publication. The source PDFs are never
written, and old intermediates remain intact. Ibn Sirin is assessed but excluded from
passage generation until a separate OCR/validation implementation is approved.

Quality flags are explainable diagnostics, not probabilities. Long parent sections remain intact while derived chunks use the actual model token budget. Verified status means an explicit
full-text/boundary source check with recorded reviewer/method, not religious authority.
The reviewed index admits only verified passages without blocking quality flags. A
separate experimental index retains unreviewed status and is excluded from any
claim of source verification.

FastAPI and bounded DeepSeek synthesis are implemented. Planned after confirmation:
an Arabic RTL Next.js application. Historical quotations
and generated synthesis must remain distinguishable, with traceable PDF citations.

Archived educational code demonstrates TF-IDF and MiniLM on five artificial examples.
The frozen Phase 1 extraction code exists only to reproduce historical outputs.
