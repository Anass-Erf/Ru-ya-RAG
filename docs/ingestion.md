# Ingestion and review

## Current pipeline

```bash
.venv/bin/python scripts/ingest.py all
.venv/bin/python scripts/ingest.py --books nabulsi ibn-Shahin
.venv/bin/python scripts/ingest.py --data-dir /path/to/data --output-root /path/to/runs
```

Run from the repository root, or use the absolute script path from another directory.
`--data-dir` must contain `raw/nabulsi.pdf`, `raw/ibn-Shahin.pdf`, and (unless omitted
with `--books`) `raw/ibn-sirine.pdf`. Output directories are created automatically.
No key, model download, network service or LLM is required for ingestion.

The source checksum identifies the supplied edition. Unknown editions are extracted
with a warning and produce no passages. Do not update catalog checksums just to
bypass this check: compare reading order, fonts, colors and headings first.
Ibn Sirin always stays OCR_PENDING, even if some extracted text is found.

## Text and positions

`Page.original_text` is PyMuPDF's native unsorted extraction, preserved exactly.
`Page.normalized_text` is NFKC of that extraction. Native spans are grouped within
1.5 points of baseline height, in native span sequence, then rows are sorted vertically.
`SourceSpan` retains PDF block/line/span indexes, bbox, baseline, color and original
text. `SourceLine.raw_text` is the direct concatenation of its retained nonblank
spans; whitespace-only spans remain accessible in the page's original extraction.

Candidate text normalizes whitespace and adds a word space only when adjacent
fragments have a visible gap of at least 1.8 points and alphanumeric endpoints.
Touching fragments, such as الخ + مسون, stay joined. These transformations are
recorded. Arabic glyph positions that jump forward within a span are flagged as
`nonmonotonic_arabic_glyph_order`, not silently rewritten. This is a heuristic warning,
not proof of error. Native span order still has defects, particularly in Ibn Shahin.

Passages contain `raw_text`, `unicode_normalized_text`, candidate `text`, a separate
search-normalized version, and initially null `validated_text`. Each source range
references **1-based PDF page and layout row numbers in that run's pages.jsonl**.
These are not printed book pages or the old TXT line numbers. Bboxes are PDF points.

Only observed footer patterns in the bottom page band are excluded. Every nonempty
row is accounted for in a passage or `excluded_lines.jsonl`; exclusion is not deletion.
Introduction, chapter-only titles and conclusion remain available there and in pages.

## Structure

Nabulsi uses exact alphabetic chapter names, including a decorative prefix, plus
quoted/dashed symbol starts. Whitespace-tolerant continuation recognition rejects
`ومن رأى`, `فإن رأى`, `وكذلك إن رأى`, and related forms. Ordinary lines and bare
quotations cannot become symbols. The author's transition on page 1405 terminates
the final entry before the conclusion heading on page 1406.

Ibn Shahin uses the supplied edition's blue Arabic heading spans as supporting
evidence for anchored chapter/section patterns. Body references to chapters are
rejected. Wrapped titles can continue onto the next page. Sections and substantive
chapter preambles become candidate passages; heading-only preambles are retained
as excluded rows. No new Ibn Shahin symbol boundaries are invented inside sections.
Long sections are preserved intact and flagged; token-aware splitting belongs to Phase 3.

## Reproducibility

Each run ID hashes source PDFs, current ingestion Python modules, schema/version,
normalization settings and installed PyMuPDF/Pydantic versions. Runs are constructed
in temporary sibling directories and published by rename after validation. A reused
run must pass all output checksums. Modifying an existing artifact causes an error;
restore the artifact or use a separate output root instead of overwriting history.

IDs use book, PDF checksum, page, layout row and boundary type. They are stable
across repeated runs and changes to boundaries elsewhere, given the same extraction
coordinate scheme. Changed editions or changed layout row grouping can change IDs.
Text hashes bind reviews to the specific extracted candidate. A run manifest is
reproducibility evidence, not a cryptographic signature against a malicious editor.

## Review workflow

Read `review_queue.jsonl`, then locate the full passage and its source ranges in
`passages.jsonl`. Compare the **whole passage**, its preceding/following boundaries
and every intervening page with the original PDF. A brief preview is insufficient.

Create a decisions JSON file:

```json
{
  "run_id": "copy the actual manifest run_id",
  "decisions": [{
    "passage_id": "copy the actual passage id",
    "source_sha256": "copy the source checksum",
    "text_sha256": "copy the candidate text checksum",
    "status": "needs_review",
    "reviewer": "your name",
    "method": "human_pdf_comparison",
    "reviewed_at": "2026-10-08T12:00:00Z",
    "scope": "full_passage_and_boundaries",
    "checked_pdf_pages": [462],
    "evidence": "Describe exactly what was checked and any unresolved differences."
  }]
}
```

The example IDs/checksums are placeholders and must not be submitted as actual reviews.
Use `verified` only after the complete fidelity/boundary check; all pages in the
passage's inclusive PDF range must be listed. AI-assisted checks use
`assisted_pdf_comparison`. The tool records a reviewer's attestation; it cannot
independently prove the quality of that review. Verification refers only to
transcription and segmentation, never to the truth or authority of an interpretation.

```bash
.venv/bin/python scripts/review.py --run data/processed/ingestion/RUN_ID \
  --decisions /path/to/decisions.json --output-root data/processed/reviewed
```

This publishes `passages.jsonl`, the full decisions and checksums in a separate
review directory. Stale, duplicate, unknown and incomplete verified decisions are
rejected. Warnings remain visible after verification. Corrections require a new
candidate/version and fresh review; this command never rewrites source text.
The active reviewed index is selected by `storage/manifests/phase3-handoff.json`.
After publishing a new review derivative, rebuild both index policies and their
evaluations before updating the active handoffs. The backend rejects indexes tied
to a different reviewed manifest. Successful extraction without quality flags is
not approval: visual comparison has also found split words and misplaced letters
in nominally clean candidates. See [the latest review batch](corpus-batch-01.md).

## Historical reproduction

The six old stages are frozen, not a second active ingestion path. Existing TXT and
JSONL outputs remain byte-identical. For historical comparisons only:

```bash
.venv/bin/python archive/previous_lessons/phase1_pipeline/run.py --help
```

The Phase 1 preservation tests still replay that archive into a temporary directory.
The old `extract/clean/structure/headings/detect/entries` CLI stages have moved there;
`scripts/ingest.py` now builds the complete versioned pipeline.
