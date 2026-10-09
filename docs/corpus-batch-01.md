# Corpus preparation — review batch 01

Phase 6 remains deferred. This batch expands source review beyond the demonstration
entries; it does not complete corpus preparation.

| Source | Candidates | Complete passages verified | Reviewed excerpts | Reviewed index chunks |
| --- | ---: | ---: | ---: | ---: |
| Nabulsi | 2,455 | 24 | 6 | 30 |
| Ibn Shahin | 319 | 7 | 0 | 9 |
| Attributed to Ibn Sirin | 0 | 0 | 0 | 0 |

The 31 complete approvals and six excerpts produce 39 searchable chunks from
35 parents. Longer sections can produce multiple chunks. Counts come from the
ledger and index, not from successful extraction alone. Ibn Sirin remains
`OCR_PENDING`.

## What was checked

The [cumulative ledger](../data/evaluation/corpus-batch-01-review-decisions.json)
retains the original four decisions and adds 35 complete-passage comparisons:
29 verified, six held as `needs_review`. All new decisions are explicitly
**AI-assisted visual PDF comparisons**, not independent human or scholarly review.
Original PDFs, candidate text, prior review runs and excerpt approvals are preserved.

Complete Nabulsi entries on PDF pages 334, 520, 533 and 1023 were compared with
rendered pages and neighboring boundaries. Approved entries include حصير، حلاب،
حنائي، حبار، رسام، رافي، ربان، رحال، رداد، رشاش، ركاب دار الملك، زبرباجة،
زلابية، زلبانى، زيات، زغلى، قصار الثياب، قاص الأخبار والسير، قصاص، قصاص الأثر،
قصاص الدواب، قزاز. Odd spellings actually visible in the edition are preserved.

Ibn Shahin's complete sections الأفلاك (10), الطل وهو الندى (19), السراب (22),
التابعين (26), التحول عن الإسلام (57), الصغار (66), and القيح والصديد (99)
were compared through their final lines and neighboring headings.

The [audit](../data/evaluation/corpus-batch-01-audit.json) records corpus-wide flag
counts, remaining statuses, held passages, and hashes of local rendered inspection
images. This batch deliberately favors short, inspectable passages; it is not a
random quality sample or broad topic-coverage benchmark.

## Problems found and held out

| Passage | PDF page | Finding |
| --- | ---: | --- |
| حشاش | 334 | Candidate splits الهموم as ال هموم. |
| حزام | 334 | Middle glyph in candidate يجزم needs higher-resolution adjudication. |
| ركاب | 520 | Candidate joins المداراةوبلوغ where the source separates the words. |
| زبال | 533 | Candidate splits تعب as تع ب. |
| زامر | 533 | Candidate splits رؤيته as رؤي ته. |
| البيت المعمور | 10 | Candidate moves م across punctuation: ابن سيرينم : ن رأى. |

Four confirmed defects and the uncertain حزام reading had no extraction quality
flags. The ركاب entry had only a length warning. These findings show why automatic
quality checks cannot approve the books. Held entries are excluded from both active
index policies. Their text is preserved pending a source-bound extraction repair;
this batch does not silently rewrite or repair those transcriptions.

## Backend changes

Interpretation previously matched only `symbol`, which excluded Ibn Shahin's
section-based passages. Explicit `فصل في رؤيا ...` headings now supply matching
topics. The source's `وهو` gloss also permits الطل / الندى matching. Quoted text,
source IDs, original section metadata and PDF page attribution remain unchanged.
Compound headings are not split on arbitrary conjunctions.

The loader also checks that both index policies refer to the selected reviewed
manifest. A stale index can no longer serve alongside newer review counts.
Indexes were built against a staged source handoff before publishing active paths.
Restart a running backend after changing the handoffs; the corpus loads at startup.

## Validation and remaining work

All 64 backend tests passed, including source preservation, source/index manifest
compatibility, exact Ibn Shahin citations and the original sea-and-ship query.
The isolated Next.js production build succeeded. Nine browser cases passed on
the first isolated run; the library test assumed only one partially available
book. After changing it to check every book's count against the API, its targeted
rerun passed. All ten browser cases are now verified. Browser tests use separate
ports and `.next-e2e/` output, with generation disabled.

The [14-query regression dataset](../data/evaluation/corpus-batch-01-smoke.json)
retains the sea-and-ship dream and adds examples from both books. Labels are
assistant-authored. At four unique parent results, reviewed BM25 and hybrid recall
are 0.9821; dense recall is 0.4643. Expanded coverage introduces real competition:
the sea-and-ship query retrieves three of four relevant parents in the first four
BM25/hybrid parents. Default retrieval can search deeper; this is not a claim of
perfect ranking or complete dream answerability.

The remaining collection is still small: 2,431 Nabulsi and 312 Ibn Shahin candidate
passages lack full verification. Further work is source-bound repair of spacing
and glyph order, fresh review of corrected candidates, wider complete-passage
review, and OCR for Ibn Sirin. No paid generation calls were made for this batch.
