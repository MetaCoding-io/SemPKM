# S01: Backend AI endpoints with Bearer auth

**Goal:** All 6 backend AI endpoints exist under `/api/`, accept Bearer token auth via `get_current_user_or_api`, return correct JSON/SSE responses, and degrade gracefully when LLM is not configured.

**Demo:** `curl -H "Authorization: Bearer <token>" POST /api/llm/stream` returns streamed SSE; `POST /api/ai/detect-claims` returns structured JSON claims array; `POST /api/ai/match-claims` returns matches with contradiction/corroboration indicators and research question gaps; `POST /api/ai/suggest-relationships` returns relationship suggestions; `POST /api/ai/summarize` returns personalized summary; `GET /api/llm/status` returns `{available: bool, provider: string|null}`. All endpoints return clear error JSON when LLM not configured.

## Must-Haves

- `POST /api/llm/stream` with dual-auth (cookie + Bearer) proxying OpenAI-compatible chat completions as SSE
- `GET /api/llm/status` returning LLM availability for feature gating
- `POST /api/ai/detect-claims` accepting page content, calling LLM, returning `{claims: [{text, confidence, type}]}`
- `POST /api/ai/match-claims` querying graph via SPARQL/FTS, returning matches with contradiction/corroboration indicators, capped at 5 per claim
- Research question gap detection in match-claims response
- `POST /api/ai/suggest-relationships` returning relationship suggestions based on shared references/topics
- `POST /api/ai/summarize` returning LLM-generated personalized summary with graph context
- All endpoints return clear error JSON when LLM is not configured (no 500s, no tracebacks)
- Unit tests proving all parsing, matching, and degradation paths

## Proof Level

- This slice proves: contract + integration
- Real runtime required: no (unit tests with mocked LLM and triplestore)
- Human/UAT required: no

## Verification

- `cd backend && python -m pytest tests/test_ai_endpoints.py -v` — all tests pass
- `cd backend && python -m pytest tests/test_llm_proxy.py -v` — all tests pass
- `cd backend && python -m pytest tests/test_claim_detection.py -v` — all tests pass
- `cd backend && python -m pytest tests/test_claim_matching.py -v` — all tests pass
- Tests cover: LLM proxy streaming, LLM status endpoint, claim extraction prompt parsing, malformed LLM response fallback, SPARQL graph matching, contradiction/corroboration indicator logic, research question gap detection, relationship suggestion logic, personalized summary, graceful degradation when LLM not configured, Bearer + cookie auth paths

## Observability / Diagnostics

- Runtime signals: `logger.debug/warning` on each endpoint for request/response flow, LLM call errors logged with `exc_info=True`
- Inspection surfaces: `GET /api/llm/status` returns `{available, provider}` — extension and tests can probe before calling AI endpoints
- Failure visibility: LLM-not-configured returns `{"error": "LLM not configured"}` with HTTP 200 (SSE) or 503 (JSON endpoints); malformed LLM response returns partial results with `parse_error` field
- Redaction constraints: LLM API key never appears in logs or responses (already handled by `LLMConfigService`)

## Integration Closure

- Upstream surfaces consumed: `backend/app/services/llm.py` (LLMConfigService), `backend/app/auth/dependencies.py` (get_current_user_or_api), `backend/app/services/search.py` (SearchService for FTS), `backend/app/triplestore/client.py` (TriplestoreClient for SPARQL)
- New wiring introduced: `backend/app/api/ai.py` router mounted in `backend/app/main.py`, new capabilities added to `/.well-known/sempkm`
- What remains before the milestone is truly usable end-to-end: S02 (extension sidebar UI consuming these endpoints), S03 (E2E tests + user guide)

## Tasks

- [x] **T01: Create AI router with LLM streaming proxy and status endpoint** `est:1h`
  - Why: The LLM proxy with Bearer auth is the gating dependency — the extension cannot call the LLM without it. The status endpoint enables feature gating in S02. Creating the router module first gives all subsequent tasks a home.
  - Files: `backend/app/api/ai.py`, `backend/app/main.py`, `backend/app/api/router.py`, `backend/tests/test_llm_proxy.py`
  - Do: Create `backend/app/api/ai.py` with `ai_router = APIRouter(prefix="/api", tags=["ai"])`. Add `POST /api/llm/stream` copying the SSE pattern from `settings.py` lines 218-290 but using `get_current_user_or_api` instead of `get_current_user`. Add `GET /api/llm/status` returning `{available: bool, provider: string|null}` by checking LLMConfigService. Mount router in `main.py`. Add "llm-stream" and "ai-insights" to well-known capabilities. Write unit tests for both endpoints covering: Bearer auth, cookie auth, LLM-not-configured degradation, SSE streaming format.
  - Verify: `cd backend && python -m pytest tests/test_llm_proxy.py -v`
  - Done when: `POST /api/llm/stream` with Bearer token returns SSE stream (or "LLM not configured" error), `GET /api/llm/status` returns availability JSON, all tests pass

- [x] **T02: Add claim detection endpoint with prompt and response parsing** `est:1h`
  - Why: Claim detection is the first AI feature — it extracts structured claims from page text via LLM. The prompt engineering and response parsing with fallback are the core logic. EXT-23 requires this endpoint.
  - Files: `backend/app/api/ai.py`, `backend/tests/test_claim_detection.py`
  - Do: Add `POST /api/ai/detect-claims` to the AI router. Request body: `{content: str, url: str, title: str}`. Build a claim-extraction prompt that instructs the LLM to return JSON `{claims: [{text: str, confidence: "established"|"likely"|"possible"|"speculative", type: "factual"|"causal"|"evaluative"|"predictive"}]}`. Make a non-streaming LLM call via httpx to `/v1/chat/completions` (same base URL / API key from LLMConfigService). Parse JSON from LLM response with fallback: try `json.loads()` on the message content, if that fails try extracting JSON from markdown code block, if that fails return `{claims: [], parse_error: "..."}`. Return 503 with `{"error": "LLM not configured"}` when LLM unavailable. Write unit tests covering: successful claim extraction, malformed LLM JSON fallback, LLM not configured, empty content, prompt structure validation.
  - Verify: `cd backend && python -m pytest tests/test_claim_detection.py -v`
  - Done when: Endpoint accepts page content, returns parsed claims array, handles malformed LLM output gracefully, returns 503 when LLM not configured

- [x] **T03: Add claim-to-graph matching endpoint with contradiction indicators** `est:1.5h`
  - Why: Graph matching is the core intelligence — connecting detected claims to existing knowledge. This is the most complex SPARQL work: FTS search, type-specific queries for Claims/Evidence/ResearchQuestions, contradiction/corroboration logic based on confidence levels, and result capping. Covers EXT-24, EXT-25, EXT-26.
  - Files: `backend/app/api/ai.py`, `backend/tests/test_claim_matching.py`
  - Do: Add `POST /api/ai/match-claims` to the AI router. Request body: `{claims: [{text: str, confidence: str, type: str}]}`. For each claim: (1) Run FTS via SearchService with claim text, limit 20. (2) Run type-specific SPARQL queries to find `res:Claim`, `res:Evidence`, and `res:ResearchQuestion` objects matching the claim text. (3) For matched Claims, compare confidence levels to determine `indicator`: if existing claim's confidence is "established"/"supported" and detected claim contradicts it → "contradicts"; if both align → "corroborates"; if existing is "contested" → "contested". (4) For matched ResearchQuestions with status "open"/"partially-answered", check if evidence exists linking to them — if not, flag as "evidence_gap". (5) Cap at 5 matches per claim, ranked by FTS score. Response: `{matches: [{claim_text, matched_objects: [{iri, label, type, type_label, match_type, indicator, confidence, fts_score}]}], research_gaps: [{iri, label, question_text, status}]}`. Handle case where Research model is not installed (no Claim/Evidence/RQ types found) — return matches from other types only. Write unit tests with mocked triplestore and search service.
  - Verify: `cd backend && python -m pytest tests/test_claim_matching.py -v`
  - Done when: Endpoint returns graph matches with contradiction/corroboration indicators, research question gaps detected, results capped at 5 per claim, graceful behavior when Research model not installed

- [x] **T04: Add relationship suggestions, personalized summary, and integration tests** `est:1.5h`
  - Why: Completes the endpoint surface. Relationship suggestions (EXT-27) reuse context-query SPARQL patterns. Personalized summary (EXT-28) is a single LLM call with context. Integration tests exercise the full stack together and verify degradation paths required by EXT-31.
  - Files: `backend/app/api/ai.py`, `backend/tests/test_ai_endpoints.py`
  - Do: (1) Add `POST /api/ai/suggest-relationships` — accepts `{url: str, title: str, claims: [{text, confidence, type}]}`. Query context-query patterns (URL match + keyword FTS) to find related objects. For each related object, generate a suggestion: `{type: "link"|"evidence"|"supports"|"contradicts", label: str, target_iri: str, target_label: str, reason: str}`. Return `{suggestions: [...]}`. (2) Add `POST /api/ai/summarize` — accepts `{content: str, graph_context: [{iri, label, type, snippet}]}`. Build a summarization prompt that includes the page content and the user's existing knowledge objects as context. Make non-streaming LLM call. Return `{summary: str}`. Return 503 when LLM not configured. (3) Update `/.well-known/sempkm` endpoints dict with new AI endpoint paths. (4) Write integration tests in `test_ai_endpoints.py` covering: all 6 endpoints accessible with Bearer auth, all endpoints return 401 without auth, all LLM-dependent endpoints return 503/error when LLM not configured, happy path with mocked LLM returning valid claims, full flow (detect → match → suggest → summarize) with mocked services.
  - Verify: `cd backend && python -m pytest tests/test_ai_endpoints.py tests/test_llm_proxy.py tests/test_claim_detection.py tests/test_claim_matching.py -v`
  - Done when: All 6 endpoints work with Bearer auth, well-known updated, integration tests pass covering happy path and degradation, zero test failures across all 4 test files

## Files Likely Touched

- `backend/app/api/ai.py` (new — all AI endpoints)
- `backend/app/api/router.py` (update well-known capabilities/endpoints)
- `backend/app/main.py` (mount ai_router)
- `backend/tests/test_llm_proxy.py` (new — LLM proxy + status tests)
- `backend/tests/test_claim_detection.py` (new — claim detection parsing tests)
- `backend/tests/test_claim_matching.py` (new — graph matching + indicator tests)
- `backend/tests/test_ai_endpoints.py` (new — integration tests for all endpoints)
