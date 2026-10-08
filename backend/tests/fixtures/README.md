# Source-page fixtures

`source_pages.jsonl` contains 30 actual PDF-page extractions from the local sources:
Nabulsi pages 9–11, 193–198, 452, 459–463, 1057, 1357, 1405–1406;
Ibn Shahin pages 4, 7–8, 20, 52, 54–55, 58, 173, 304, 416.
Each record includes its book ID, PDF checksum, 1-based page number, original text,
span coordinates and candidate text. They are not a validated interpretation corpus.

Selected regressions: ordinary prose mistaken for symbols; conditional continuations;
pre/post-460 marker styles; decorated الكاف and native الواو headings; the author's
conclusion; blue Ibn Shahin headings versus body references; heading word fragments;
cross-page titles; and embedded glyph-order defects. Tests also use clearly synthetic
adversarial strings and temporary fake source bytes to exercise failure paths.

Three PDF pages are re-extracted in tests and compared to these fixture records.
The complete original PDFs are required for those checks. This does not claim all
30 fixture pages have received complete visual transcription review.
