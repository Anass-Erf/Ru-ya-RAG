# Phase 2 source review — 2026-10-08

Method: Codex AI-assisted visual comparison of rendered **local original PDF pages**
with extracted candidate text and detected boundaries. This was not human review,
religious adjudication, or a complete transcription audit. The dates and source
checksums are retained with explicit review decisions.

## Observed boundaries and fidelity issues

| Book / PDF page | Observation from the rendered source | Implemented consequence |
|---|---|---|
| Nabulsi 460 | Both the early quote/dash layout and later leading-dash layout occur; ذراع and ذبح are entries, ومن رأى is continuation. | Recognize both marker positions and reject conditional labels. |
| Nabulsi 195 | Repeated فإن رأى paragraphs continue the preceding discussion. | Whitespace-tolerant conditional exclusion prevents false entry splits. |
| Nabulsi 1057 | A decorated باب الكاف heading precedes كوثر. | Strip only the anchored decorative prefix before an exact chapter-name match. |
| Nabulsi 1357 | Source reads باب الواو; وصى and وضوء are distinct entries. | Native spans recover the heading without the old reversed-word artifact. |
| Nabulsi 462–463 | ذل is a complete two-line entry at the end of page 462; page 463 starts ذل عن الأعراض. | Full ذل passage and surrounding boundaries visually checked. |
| Nabulsi 463 | ذم لأرباب المدح has a separate heading, but its candidate contains االله. | Keep needs_review; do not silently repair the font artifact. |
| Nabulsi 1405–1406 | يعسوب ends after أغنياء on page 1405. Authorial closing prose starts immediately afterward; the formal conclusion heading is on page 1406. | Terminate the entry before the author transition; retain all closing text as excluded evidence. |
| Ibn Shahin 4 | Chapter, wrapped title and section heading are blue; body text is black. | Color corroborates anchored chapter/section patterns. |
| Ibn Shahin 7 | Several sections and الباب الثاني occur; the final فصل starts at the page bottom. | Maintain section context across page boundaries. |
| Ibn Shahin 20 | الباب السادس is visibly two words despite a missing extracted space between spans. | Record a geometry-derived word-space insertion. |
| Ibn Shahin 304 | الباب الثامن والخمسون is intact in the source. A body paragraph beginning وأما المداد has wrongly ordered text inside a native span. | Join touching heading fragments; flag nonmonotonic Arabic glyph order in body text instead of reconstructing its wording. |

Additional rendered inspection of Nabulsi pages 1356 and 1397 provided context only;
it did not produce full-passage verification. Fixture-based extraction comparisons
cover other pages but are not described as visual reviews.

## Full-passage review decisions

Decisions: [phase2-review-decisions.json](../data/evaluation/phase2-review-decisions.json).
They are tied to candidate run `b0217c73dfa8a89464281d47`, specific source checksums,
passage IDs and candidate text checksums. The reviewed derivative is
`data/processed/reviewed/576bd911d9e8cb2946d9cd1b/`.

| Symbol | PDF page | Decision | Scope |
|---|---|---|---|
| ذل | 462 | verified | Complete two-line text and adjacent entry boundaries; AI-assisted comparison. |
| يعسوب | 1405 | verified | Complete three-line text, preceding entry and following author transition; AI-assisted comparison. |
| وصى | 1357 | needs_review | Boundary supported; font-encoding artifact retained. |
| ذم لأرباب المدح | 463 | needs_review | Boundary supported; font-encoding artifact retained. |

Only the two explicitly checked passages have `validated_text` in the derivative.
All other passages retain unreviewed/needs_review status. “Verified” here refers to
this recorded source-fidelity check; it does not establish historical authorship,
interpretive truth, or scholarly authority. Human review is still recommended before
using even these samples in a published application.

The candidate ingestion run itself stays immutable with zero verified records.
There is no approved index or corpus-wide accuracy score. Visual inspection of a
small, deliberately selected sample cannot estimate segmentation precision/recall.

## Targeted excerpt review — 2026-10-09

A reported sea-and-ship dream exposed that the default index contained only the two
small smoke-test entries above. Relevant longer entries were present but excluded
because their parents contain extraction defects. Promoting those parents would
misrepresent source fidelity.

Six exact excerpts were instead compared visually with the local PDF, including
nearby context. The ledger `data/evaluation/source-excerpt-reviews-2026-10-09.json`
records parent/source checksums, character offsets, exact quotes, checked pages,
review scope and observations. No source text was corrected or paraphrased.

| Parent symbol | PDF page | Scope |
| --- | --- | --- |
| سفينة | 619 | Introductory clause ending at قحط, before the following conditional example |
| سفينة | 620 | Complete isolated paragraph about a ship filled with people |
| بحر | 84 | Complete two-line paragraph about crossing to the other side |
| بحر | 87 | Conditional clause about a surging sea and clashing waves |
| سفر | 637 | Clause about travel and transition from one state to another |
| موج الماء | 1171 | Introductory clause; subsequent citations with extraction artifacts excluded |

This is AI-assisted review of those exact excerpts only. The full parents retain
`needs_review` or `unreviewed`; the original two complete reviewed passages and all
candidate runs remain unchanged. An excerpt chunk carries `excerpt_source_review`,
parent status, original character offsets and actual source rows. Quotes remain
substrings of the parent text. The API/UI exposes `review_scope=excerpt` and counts
full-passage reviews separately from six excerpt reviews. These statements are
historical quotations, not claims about the user's future or advice.
