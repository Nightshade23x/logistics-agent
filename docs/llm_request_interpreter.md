# LLM request interpreter

The request interpreter is a guarded input-normalization layer in front of the existing deterministic agent pipeline.

## Flow

1. Conservatively normalize whitespace, punctuation, Unicode characters, and a small set of obvious logistics typos.
2. Run the existing deterministic User Agent once.
3. In `fallback` mode, call Gemini only when routing is weak, no agent was selected, a route was not understood, or probable typos were detected.
4. Validate Gemini's JSON with Pydantic.
5. Reject any rewrite that adds, removes, or changes explicit numbers.
6. Rerun the existing deterministic pipeline with the validated rewrite.
7. Keep whichever deterministic response scores higher.
8. Preserve the user's original text in `request_metadata.input_source`.

The LLM does not calculate CBM, weight, landed cost, container fit, compliance, risk, or booking readiness. Those remain deterministic and auditable.

## Configuration

- `LLM_INTERPRETER_MODE=fallback` — recommended; use Gemini only when needed.
- `LLM_INTERPRETER_MODE=always` — send every non-empty text request through interpretation.
- `LLM_INTERPRETER_MODE=off` — disable network interpretation while keeping the existing backend.
- `LLM_INTERPRETER_TIMEOUT_SECONDS=8` — bounded network timeout.
- `LLM_INTERPRETER_MIN_CONFIDENCE=0.65` — reject low-confidence rewrites.

The interpreter reuses `GEMINI_API_KEY` and `GEMINI_MODEL`. If Gemini is unavailable, quota-limited, malformed, or too slow, the request continues through the deterministic backend instead of failing.

## Safety guarantees

- Strict JSON schema validation.
- Temperature zero.
- Explicit instruction not to infer or calculate.
- Exact numeric multiset guard.
- Low-confidence rejection.
- Five-minute circuit breaker after quota or transient server failures.
- Original request text retained for history and clarification reruns.
- Existing deterministic response used when it scores better.
