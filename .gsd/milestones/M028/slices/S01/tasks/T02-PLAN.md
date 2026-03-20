---
estimated_steps: 6
estimated_files: 3
---

# T02: Add claim detection endpoint with prompt and response parsing

**Slice:** S01 — Backend AI endpoints with Bearer auth
**Milestone:** M028

## Description

Add `POST /api/ai/detect-claims` to the AI router created in T01. This endpoint accepts page text content, calls the LLM with a claim-extraction prompt, and returns a structured JSON array of detected claims. The key challenges are: (1) crafting a reliable prompt that produces parseable JSON across different LLM providers, and (2) defensively parsing the LLM response with fallback for malformed output.

The Research Workflow model defines claim confidence as: `established`, `supported`, `contested`, `speculative`, `refuted`. The detect-claims endpoint should use a compatible set: `established`, `likely`, `possible`, `speculative` — these are the *detected* confidence levels before graph matching (they map to the model's levels but without "refuted" which requires evidence analysis).

**Relevant skill:** `test` — for generating pytest unit tests.

## Steps

1. In `backend/app/api/ai.py`, add Pydantic request/response models:
   ```python
   class DetectClaimsRequest(BaseModel):
       content: str  # page text content
       url: str = ""
       title: str = ""

   class DetectedClaim(BaseModel):
       text: str
       confidence: str  # established|likely|possible|speculative
       type: str  # factual|causal|evaluative|predictive

   class DetectClaimsResponse(BaseModel):
       claims: list[DetectedClaim] = []
       parse_error: str | None = None
   ```

2. Create a helper function `_build_claim_extraction_prompt(content: str, title: str, url: str) -> list[dict]` that returns the messages array for the LLM call. The system message should instruct the LLM to:
   - Extract specific, testable claims from the text
   - Return ONLY valid JSON: `{"claims": [{"text": "...", "confidence": "...", "type": "..."}]}`
   - Confidence levels: established (widely accepted), likely (well-supported), possible (some support), speculative (hypothesis/conjecture)
   - Claim types: factual (verifiable statement of fact), causal (cause-and-effect), evaluative (judgment/assessment), predictive (forecast/projection)
   - Limit to 10 most significant claims
   - The user message should contain the page title, URL, and content (truncated to ~4000 chars to stay within context limits)

3. Create a helper function `_parse_claims_response(content: str) -> tuple[list[dict], str | None]` that:
   - Tries `json.loads(content)` first
   - If that fails, tries to extract JSON from a markdown code block (```json...```) using regex
   - If that fails, tries to find `{` and `}` boundaries and parse
   - If all parsing fails, returns `([], "Failed to parse LLM response")`
   - Validates that the result has a `claims` key with a list
   - Validates each claim has `text`, `confidence`, `type` fields
   - Filters out claims with empty `text`
   - Returns `(claims_list, error_or_none)`

4. Add `POST /ai/detect-claims` endpoint:
   - Depends on `get_current_user_or_api` and `get_db_session`
   - Validates `content` is not empty (400 if empty)
   - Checks LLM availability via `LLMConfigService` — returns 503 `{"error": "LLM not configured"}` if unavailable
   - Builds prompt via helper
   - Makes NON-streaming call to LLM: `httpx.AsyncClient` → `POST /v1/chat/completions` with `stream: false`
   - Parses response content via `_parse_claims_response()`
   - Returns `DetectClaimsResponse`

5. Write `backend/tests/test_claim_detection.py` with tests:
   - `test_parse_claims_valid_json` — direct JSON string → parsed correctly
   - `test_parse_claims_markdown_code_block` — JSON in ```json...``` → parsed correctly
   - `test_parse_claims_malformed_json` — garbage text → empty list + parse_error
   - `test_parse_claims_missing_fields` — JSON without required fields → filtered out
   - `test_parse_claims_empty_text_filtered` — claims with empty `text` removed
   - `test_detect_claims_endpoint_success` — mock LLM returning valid JSON → claims returned
   - `test_detect_claims_endpoint_llm_not_configured` — no LLM config → 503
   - `test_detect_claims_endpoint_empty_content` — empty content → 400
   - `test_detect_claims_endpoint_requires_auth` — no auth → 401
   - `test_detect_claims_endpoint_llm_error` — httpx error → empty claims with parse_error
   - `test_build_prompt_truncates_long_content` — verify content truncation in prompt
   - `test_build_prompt_includes_metadata` — verify title/URL in prompt

6. Run tests: `cd backend && python -m pytest tests/test_claim_detection.py -v`

## Must-Haves

- [ ] `POST /api/ai/detect-claims` accepts `{content, url, title}` and returns `{claims: [...], parse_error}`
- [ ] Claim extraction prompt produces structured JSON instructions for the LLM
- [ ] Response parser handles: valid JSON, JSON in markdown code blocks, and malformed output
- [ ] Returns 503 when LLM not configured
- [ ] Returns 400 when content is empty
- [ ] Content truncated to ~4000 chars in prompt to avoid context overflow
- [ ] All unit tests pass

## Verification

- `cd backend && python -m pytest tests/test_claim_detection.py -v` — all 12 tests pass
- Parser tests cover all three parsing strategies (direct JSON, markdown extraction, fallback)

## Inputs

- `backend/app/api/ai.py` — AI router from T01 (must exist with ai_router, llm_stream, llm_status)
- `backend/app/services/llm.py` — LLMConfigService for config/key access
- `backend/tests/test_llm_proxy.py` — reference for test fixtures and LLM mocking patterns from T01

## Observability Impact

- **New signal:** `logger.debug("Claim detection: user=%s, content_len=%d, claims_found=%d", ...)` on every request — shows throughput and extraction quality.
- **New signal:** `logger.warning("LLM call failed for claim detection", exc_info=True)` on httpx errors — surfaces connectivity/auth issues with the LLM provider.
- **Failure visibility:** `parse_error` field in response body tells callers (and logs) when the LLM returned unparseable output. Non-null `parse_error` with empty `claims` array indicates the LLM is reachable but returning bad JSON.
- **Inspection:** `POST /api/ai/detect-claims` with known content can be used as a smoke test — a non-empty `claims` array confirms the full LLM round-trip works.
- **Degradation:** Returns HTTP 503 `{"error": "LLM not configured"}` when no LLM base URL is set — matches the slice-wide convention for JSON AI endpoints.

## Expected Output

- `backend/app/api/ai.py` — updated with DetectClaimsRequest/Response models, prompt builder, parser, and endpoint
- `backend/tests/test_claim_detection.py` — 12 unit tests all passing
