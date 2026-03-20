---
id: T02
parent: S01
milestone: M028
provides:
  - POST /api/ai/detect-claims endpoint accepting {content, url, title} and returning {claims, parse_error}
  - _build_claim_extraction_prompt() helper for structured LLM claim extraction
  - _parse_claims_response() helper with 3-strategy JSON parsing fallback
key_files:
  - backend/app/api/ai.py
  - backend/tests/test_claim_detection.py
key_decisions:
  - "Invalid confidence/type values from LLM are silently normalized to 'possible'/'factual' rather than rejected — maximizes extraction even with imperfect LLM compliance"
  - "Content truncation at 4000 chars with explicit marker — balances context window limits vs extraction quality"
patterns_established:
  - "Non-streaming LLM call pattern: httpx.AsyncClient POST to /v1/chat/completions with stream:false, parse response.json()['choices'][0]['message']['content']"
  - "3-strategy JSON parsing: direct json.loads → markdown code block extraction → brace boundary extraction → error"
  - "Pydantic request/response models for AI endpoints: DetectClaimsRequest, DetectedClaim, DetectClaimsResponse"
observability_surfaces:
  - "logger.debug on every detect-claims request with user, content_len, claims_found, parse_error"
  - "logger.warning on LLM call failures with exc_info=True"
  - "parse_error field in response body surfaces LLM output parsing failures to callers"
  - "HTTP 503 with {error: 'LLM not configured'} for missing LLM config"
duration: 25m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T02: Add claim detection endpoint with prompt and response parsing

**Added POST /api/ai/detect-claims with structured LLM claim extraction, 3-strategy response parser, and 12 unit tests**

## What Happened

Added the claim detection endpoint to the existing AI router. The endpoint accepts page text content with optional URL and title, calls the LLM with a claim-extraction prompt, and returns structured JSON claims. Three main components were built:

1. **Pydantic models** — `DetectClaimsRequest`, `DetectedClaim`, `DetectClaimsResponse` with the four confidence levels (established/likely/possible/speculative) and four claim types (factual/causal/evaluative/predictive).

2. **Prompt builder** (`_build_claim_extraction_prompt`) — system message instructs the LLM to return JSON-only output with the exact schema. User message includes page title, URL, and content truncated to 4000 chars.

3. **Response parser** (`_parse_claims_response`) — three fallback strategies for extracting JSON from LLM output: direct `json.loads`, markdown code block regex extraction, and brace-boundary parsing. Validates claim structure and filters empty/invalid entries. Invalid confidence/type values are normalized to defaults rather than rejected.

The endpoint uses a non-streaming httpx call with `temperature: 0.2` for consistent structured output, returns 503 when LLM is not configured, and 400 for empty content.

## Verification

All 12 unit tests pass covering:
- 5 parser tests: valid JSON, markdown code block, malformed input, missing fields, empty text filtering
- 2 prompt builder tests: content truncation, metadata inclusion
- 5 endpoint tests: success path, LLM not configured (503), empty content (400), auth required (401), LLM error handling

T01's existing 8 tests also still pass.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_claim_detection.py -v` | 0 | ✅ pass | 0.52s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_llm_proxy.py -v` | 0 | ✅ pass | 0.54s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_ai_endpoints.py -v` | — | ⬜ not yet created (T04) | — |
| 4 | `cd backend && .venv/bin/python -m pytest tests/test_claim_matching.py -v` | — | ⬜ not yet created (T03) | — |

## Diagnostics

- **Smoke test:** `POST /api/ai/detect-claims` with any text content — non-empty `claims` array confirms full LLM round-trip
- **Parse failures:** Non-null `parse_error` in response body with empty `claims` means LLM returned unparseable output
- **LLM unavailable:** HTTP 503 with `{"error": "LLM not configured"}` 
- **Logs:** `logger.debug` on every request includes user email, content length, claim count, and parse error status; `logger.warning` with `exc_info=True` on LLM connectivity failures

## Deviations

- Had to install `pytest-asyncio` in the venv — it was listed in pyproject.toml dev dependencies but not installed. This also fixed T01's test suite which had the same issue.
- Used `Mock` (not `AsyncMock`) for `httpx.Response.json()` since it's synchronous — `AsyncMock` wraps return values in coroutines which broke the `data["choices"]` subscript.

## Known Issues

None.

## Files Created/Modified

- `backend/app/api/ai.py` — Added Pydantic models, `_build_claim_extraction_prompt()`, `_parse_claims_response()`, and `POST /ai/detect-claims` endpoint
- `backend/tests/test_claim_detection.py` — 12 unit tests covering parser, prompt builder, and endpoint
- `.gsd/milestones/M028/slices/S01/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
