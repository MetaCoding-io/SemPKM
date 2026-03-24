# S04: LLM Test Harness & E2E Integration

**Goal:** Mock LLM E2E tests run in CI in <5s with deterministic copilot assertions, Ollama docker-compose variant runs real inference locally, cloud tier enforces per-run budget cap and reports token costs.
**Demo:** `npx playwright test tests/46-copilot/` passes against the Docker test stack with mock-llm service — covering chat streaming, SPARQL generation + approval, conversation persistence, persona switching, and object creation from chat.

## Must-Haves

- Mock LLM server supports SSE streaming (OpenAI-compatible chunk format with `data: [DONE]` sentinel)
- Mock server returns copilot-specific canned responses: SPARQL code blocks, object creation JSON, persona-aware prose, generic helpful text
- `mock-llm` service added to `docker-compose.test.yml` following the existing mock-* pattern
- E2E test spec covers: basic chat flow, SPARQL approval, conversation persistence, persona switching, object creation confirmation
- Copilot selectors added to `e2e/helpers/selectors.ts`
- Ollama docker-compose variant for local integration testing
- Cloud tier helper with budget cap enforcement and token cost tracking
- All 126 existing backend unit tests pass (regression)

## Proof Level

- This slice proves: integration (mock LLM → copilot endpoint → chat UI → approval flow → persistence)
- Real runtime required: yes (Docker test stack with triplestore + mock LLM)
- Human/UAT required: no

## Verification

- `python e2e/mock-llm-api/server.py --selftest` — all checks pass (streaming + non-streaming + copilot routes)
- `docker compose -f docker-compose.test.yml config --quiet` — validates with mock-llm service
- `docker compose -f docker-compose.test-ollama.yml config --quiet` — validates Ollama variant
- `cd backend && python -m pytest tests/test_copilot_service.py tests/test_ai_personas.py tests/test_object_creation_chat.py tests/test_graph_context.py tests/test_conversation_service.py -v` — all 126 tests pass (regression)
- `npx playwright test tests/46-copilot/` — all copilot E2E tests pass against Docker test stack

## Observability / Diagnostics

- Runtime signals: mock-llm server logs `[mock-llm] POST /v1/chat/completions stream=true|false` for request tracing
- Inspection surfaces: `GET mock-llm:8080/health` from Docker network; `GET /api/copilot/conversations` to inspect persistent threads after E2E run
- Failure visibility: Playwright trace-on-retry captures SSE stream, approval card state, and conversation list on failure
- Redaction constraints: mock API keys only (`sk-mock-test-key`) — no real secrets in test infrastructure

## Integration Closure

- Upstream surfaces consumed: `POST /api/copilot/chat` (S01), `POST /api/copilot/approve` (S01), `GET/POST/DELETE /api/copilot/conversations` (S02), `GET/POST /api/copilot/personas` (S03), `POST /api/commands` (S03 object creation)
- New wiring introduced in this slice: `mock-llm` Docker service, `PUT /browser/llm/config` for test-time LLM configuration
- What remains before the milestone is truly usable end-to-end: nothing — this is the final slice

## Tasks

- [ ] **T01: Upgrade mock LLM server with SSE streaming and copilot canned responses** `est:45m`
  - Why: The existing mock server only returns single JSON responses for claim detection. The copilot endpoint sends `stream: True` and expects OpenAI SSE chunks. E2E tests need pattern-matched canned responses for SPARQL blocks, object creation JSON, and persona-aware prose.
  - Files: `e2e/mock-llm-api/server.py`, `docker-compose.test.yml`
  - Do: (1) Add request body parsing in `do_POST` to detect `stream` field. (2) When `stream: true`, send SSE chunks (word-by-word from canned response) in OpenAI format. (3) Add pattern matching on user message content: "how many"/"project" → SPARQL response, "create"+"task" → object creation JSON, default → generic helpful response. (4) Add `mock-llm` service to `docker-compose.test.yml` following mock-linear pattern. (5) Extend selftest to validate streaming output format and routing.
  - Verify: `python e2e/mock-llm-api/server.py --selftest` passes all checks; `docker compose -f docker-compose.test.yml config --quiet` succeeds
  - Done when: selftest passes with streaming + non-streaming + copilot routing checks; docker-compose.test.yml validates with mock-llm service

- [ ] **T02: Copilot E2E Playwright tests** `est:1h`
  - Why: Validates the entire copilot stack end-to-end: chat streaming through mock LLM, SPARQL generation and approval, conversation persistence across page reloads, persona switching, and object creation from chat. This is the primary deliverable of the slice.
  - Files: `e2e/tests/46-copilot/copilot.spec.ts`, `e2e/helpers/selectors.ts`
  - Do: (1) Add copilot selectors to `SEL` object. (2) Create test spec with beforeAll that configures LLM to point at `http://mock-llm:8080` via `PUT /browser/llm/config` and afterAll that cleans up. (3) Write test cases: basic chat (send message, see streaming response), SPARQL generation (trigger message, see approval card, approve, see results), conversation persistence (send message, reload, verify conversation appears in selector), persona switching (load selector, switch persona, verify selection), object creation (trigger message, see confirmation card, confirm, verify object created). (4) Handle copilot lazy-load — click AI COPILOT tab to activate before each test.
  - Verify: test file has valid TypeScript syntax (`npx tsc --noEmit e2e/tests/46-copilot/copilot.spec.ts` or equivalent check); selectors are added to SEL.copilot
  - Done when: `e2e/tests/46-copilot/copilot.spec.ts` exists with 5+ test cases covering all must-have scenarios; copilot selectors present in `e2e/helpers/selectors.ts`

- [ ] **T03: Ollama compose variant, cloud tier helper, and cost tracking** `est:30m`
  - Why: Completes the 3-tier test strategy: mock (CI), Ollama (local real inference), cloud (real API with budget cap). The Ollama compose file enables local developers to test with real LLM inference. The tier helper auto-selects the right backend based on environment. The cost tracker prevents runaway cloud test bills.
  - Files: `docker-compose.test-ollama.yml`, `e2e/helpers/llm-tier.ts`, `e2e/helpers/cost-tracker.ts`
  - Do: (1) Create `docker-compose.test-ollama.yml` extending test stack with Ollama service, model cache volume, and GPU passthrough. (2) Create `e2e/helpers/llm-tier.ts` that auto-selects tier based on env vars (`LLM_TEST_TIER`, `OPENAI_API_KEY`, `OLLAMA_API_URL`). (3) Create `e2e/helpers/cost-tracker.ts` with token accumulation from SSE stream content, cost estimation, and configurable budget cap (default $1.00) that fails the test when exceeded.
  - Verify: `docker compose -f docker-compose.test-ollama.yml config --quiet` succeeds; `npx tsc --noEmit e2e/helpers/llm-tier.ts e2e/helpers/cost-tracker.ts` (or equivalent syntax check)
  - Done when: Ollama compose file validates; tier helper exports `getLlmTier()` and `configureLlmForTier()` functions; cost tracker exports `CostTracker` class with `addTokens()`, `estimateCost()`, and `assertBudget()` methods

## Files Likely Touched

- `e2e/mock-llm-api/server.py`
- `docker-compose.test.yml`
- `docker-compose.test-ollama.yml`
- `e2e/tests/46-copilot/copilot.spec.ts`
- `e2e/helpers/selectors.ts`
- `e2e/helpers/llm-tier.ts`
- `e2e/helpers/cost-tracker.ts`
