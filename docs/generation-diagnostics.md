# Generation failure diagnostics — 2026-10-09

The previous interpretation service returned the same citation-check message for
provider HTTP errors, timeouts, truncated responses, malformed JSON and genuine
citation failures. A user seeing that message could not identify the real problem.

The adapter now distinguishes authentication (401), insufficient balance (402),
access denial (403), unavailable model/endpoint (404), invalid request (400/422),
rate limit (429), temporary failure, timeout, output truncation and invalid response.
Mappings follow [DeepSeek's official error documentation](https://api-docs.deepseek.com/quick_start/error_codes/).
The Arabic UI message comes from a fixed local mapping, never the raw provider body.

Grounding failures also have distinct sanitized codes: schema invalid, unknown
source, quote mismatch, unsupported assertion/disagreement, missing claims and
conflicting abstention. Exact quote/source checks are unchanged. Failed generation
still returns the original retrieved sources and no unchecked synthesis. Logs
record only `event` and `code`, without provider payload, dream text or credentials.

After explicit user approval, one bounded live request was made for the reported
dream and six source excerpts. DeepSeek returned HTTP 200 with `finish_reason=stop`,
1,307 prompt tokens and 510 completion tokens (1,817 total). Local validation failed
with `generation_schema_invalid`. This observed failure was not authentication,
account balance, truncation or timeout. The raw response was not retained, so the
specific failing field of that response cannot be established retrospectively.

The prompt previously showed an example but omitted validator limits (including a
maximum of five claims despite up to six supplied sources). It now includes the
exact Pydantic-generated JSON Schema, required keys and field limits, and asks for
at most three compact claims rather than one claim per source. No validation check
was removed. Future schema errors report only sanitized field paths/types, with
unknown extra key names redacted; no model text, error input values or error context
is logged.

The user then authorized one additional bounded verification call with the revised
prompt and the same dream/six reviewed excerpts. DeepSeek returned HTTP 200,
`finish_reason=stop`, 1,757 prompt tokens and 472 completion tokens (2,229 total).
The actual response passed schema validation and source/quote validation, producing
three cited claims and no disagreement claims. No raw model output or credential
was logged or retained. These were two individually authorized calls, not retries.

This confirms one successful live generation/validation result for this request.
It does not establish semantic faithfulness across arbitrary dreams or eliminate
future model/provider failures. The standard API still validates each new response.

To inspect the next failure after restarting the backend, read
`generation_issue.code` and `generation_issue.message` in the interpretation response,
or the sanitized `ruya.generation` log event. The frontend already displays the
message. Do not infer that a quote was rejected from a transport/account error.

Validation: 22 local mocked-provider/API/contract tests passed in 3.659 seconds.
New cases cover schema/prompt consistency, excess claims, short quotes, missing
fields and redaction of untrusted field names. Live observations are limited to
the two individually authorized requests described above.
