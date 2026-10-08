# Retrieval evaluation

`data/evaluation/retrieval-smoke.json` contains four Arabic queries and passage-ID
judgments for the two source-checked entries. Queries and labels were assigned by
the assistant using the recorded source review; they are available for human review.
They are **not** independently human-judged relevance ground truth.

The executable evaluation computes Recall@k, Precision@k and reciprocal rank@k,
then averages reciprocal ranks to obtain MRR@k. Chunk hits are deduplicated to parent
passages before scoring. Precision uses a fixed denominator k, including when fewer
results exist. Relevant labels missing from the selected corpus cause an error rather
than silently shrinking the test set. Draft/unreviewed judgment sets are not scored.

```bash
.venv/bin/python scripts/evaluate.py --index storage/indexes/INDEX_ID \
  --output data/evaluation/retrieval-smoke-report.json
```

The report includes per-query rankings, component modes, actual warm-query latency,
mean/max latency, dataset checksum and corpus checksum. Model/index loading and a
separate encoder warm-up are excluded from latency. This is one local CPU run, not
a throughput benchmark. Parent-level evaluation pools at most 50 chunk results per
query; larger or heavily duplicated corpora need a larger/document-level candidate
pool before their metrics are meaningful.

Even perfect results on two passages say almost nothing about a library of thousands
of candidates. This smoke set tests wiring and metric behavior only. A future
benchmark needs human review, diverse symbols/wording, cross-book questions,
multiple relevant sources, difficult negatives, no-answer cases and held-out queries.
No corpus-wide retrieval-quality claim follows from the smoke scores.

Ingestion checks remain separate: row accounting proves provenance, not source
fidelity, segmentation accuracy or relevance. See `docs/source-review.md` for the
limited PDF comparisons and the Phase 3 report for actual test/evaluation results.
