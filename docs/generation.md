# Grounded generation

The provider protocol accepts chat messages and returns text; `DeepSeek` implements
it with HTTPX, a fixed HTTPS endpoint, no redirects, bounded response size and a
wall timeout. Responses use JSON mode and bounded output. The default model is
configurable (`deepseek-flash`). The implementation follows the current official
[API introduction](https://api-docs.deepseek.com/en/),
[chat completion reference](https://api-docs.deepseek.com/api/create-chat-completion/),
and [JSON mode guide](https://api-docs.deepseek.com/guides/json_mode/).

1. Retrieve from the reviewed index and retain original scores/provenance.
2. Require an explicit normalized symbol match and verified passage status. This
   conservative heuristic is not a calibrated relevance or answerability model.
   It can reject useful paraphrases, and matching a symbol does not establish that
   every detail of a complex dream is supported.
3. Deduplicate parent passages and enforce context size. Experimental policy is
   always ineligible, even if some hits happen to be verified.
4. Put query and excerpts in a JSON data envelope. The system message treats both
   as untrusted data, forbids following embedded instructions, and requests historical
   attribution, abstention where needed, and no predictions or practical directives.
5. Parse strict structured output. Every substantive statement needs a known source
   ID and an exact quotation substring. The server supplies book, author and pages;
   provider-supplied metadata is rejected. Disagreement requires two distinct parents.
6. Reject malformed, empty, truncated or oversized responses, unknown citations,
   fabricated quotes, and several explicit certainty/instruction patterns. Preserve
   retrieval and return a generation failure instead of unchecked model text.

These checks establish mechanical citation validity, not semantic entailment. A
model could still misrepresent a real quote or evade the small phrase guard. Prompt
isolation reduces injection risk but cannot eliminate it. No adversarial or human
faithfulness benchmark has been completed. The current two AI-assisted reviewed
passages are insufficient for a broadly useful interpretation service. Historical
quotations may themselves contain predictions; they remain clearly labeled source
statements rather than endorsed facts. All responses include a historical-use
notice, including retrieval-only responses.

Tests use explicitly fabricated provider fixtures only to exercise the contract,
never as corpus data or product answers. No live DeepSeek request was made during
Phase 4; authentication, account availability and real-model behavior remain untested.
