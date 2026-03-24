# S04: LLM Test Harness & E2E Integration — UAT

**Milestone:** M035
**Written:** 2026-03-23

## UAT Type

- UAT mode: mixed (artifact-driven for compose/selftest, live-runtime for E2E Playwright)
- Why this mode is sufficient: The mock server selftest validates response routing without Docker. Compose config validation confirms service definitions. The Playwright E2E tests exercise the full copilot stack through a real Docker stack with mock-llm.

## Preconditions

- Docker and Docker Compose available
- Node.js and npx available (for Playwright)
- Python 3.12+ available (for mock server selftest)
- Backend virtualenv at `backend/.venv/` with all dependencies installed
- No Docker test stack needs to be running for checks 1-5 (standalone verification)
- Docker test stack (`docker compose -f docker-compose.test.yml up -d`) running for check 6+

## Smoke Test

Run `python3 e2e/mock-llm-api/server.py --selftest` — all 12 checks should print ✓. This confirms the mock server handles all copilot response routes in both streaming and non-streaming modes with zero Docker dependency.

## Test Cases

### 1. Mock LLM Server — SSE Streaming Format

1. Run `python3 e2e/mock-llm-api/server.py --selftest`
2. Check the streaming checks (checks 8-10) in the output
3. **Expected:** All streaming checks pass. Each SSE stream contains `data: {"choices":[{"delta":{"content":"..."}}]}` chunks ending with `data: [DONE]`

### 2. Mock LLM Server — Copilot Route Selection

1. Run the selftest and inspect checks 3-7 (non-streaming routes)
2. Verify: claims route returns JSON with "claims" key
3. Verify: SPARQL route returns content containing `SELECT`
4. Verify: create-task route returns content containing `create_object`
5. Verify: summarize route returns prose text
6. Verify: default route returns generic helpful response
7. **Expected:** Each route returns the correct canned response type based on keyword matching in the user message

### 3. Docker Compose — Test Stack with Mock LLM

1. Run `docker compose -f docker-compose.test.yml config --quiet`
2. Inspect the config: `docker compose -f docker-compose.test.yml config | grep -A 5 'mock-llm'`
3. **Expected:** Config validates without error. `mock-llm` service defined with `python:3.12-slim` image, volume mount for `./e2e/mock-llm-api`, healthcheck on port 8080, and the api service has `LLM_API_URL: http://mock-llm:8080` in its environment.

### 4. Docker Compose — Ollama Variant

1. Run `docker compose -f docker-compose.test-ollama.yml config --quiet`
2. Inspect: `docker compose -f docker-compose.test-ollama.yml config | grep -A 10 'ollama'`
3. **Expected:** Config validates. Ollama service uses `ollama/ollama:latest` image, `ollama_models` named volume, healthcheck on `/api/tags`. API service has `LLM_API_URL: http://ollama:11434`.

### 5. Backend Unit Test Regression

1. Run `cd backend && .venv/bin/python -m pytest tests/test_copilot_service.py tests/test_ai_personas.py tests/test_object_creation_chat.py tests/test_graph_context.py tests/test_conversation_service.py -v`
2. **Expected:** 139/139 tests pass. All copilot service tests (SPARQL validation, context serialization, token estimation), persona tests (CRUD, built-in seeding), object creation tests (JSON parsing, confirmation flow), graph context tests (neighborhood parsing, serialization, truncation), and conversation tests (lifecycle, persistence, auto-title) pass.

### 6. Copilot E2E — Basic Chat Flow (requires Docker test stack)

1. Start Docker test stack: `docker compose -f docker-compose.test.yml up -d`
2. Wait for all services healthy
3. Run `npx playwright test tests/46-copilot/ -g "basic chat"`
4. **Expected:** Test sends a generic message, mock-llm returns the GENERIC_RESPONSE via SSE, and the assistant message containing "knowledge graph" appears in the chat

### 7. Copilot E2E — SPARQL Generation and Approval (requires Docker test stack)

1. Run `npx playwright test tests/46-copilot/ -g "SPARQL"`
2. **Expected:** Test sends "How many projects do I have?", mock-llm returns SPARQL code block, approval card appears with SELECT query text, Approve button click triggers execution, success indicator shown

### 8. Copilot E2E — Conversation Persistence (requires Docker test stack)

1. Run `npx playwright test tests/46-copilot/ -g "persistence"`
2. **Expected:** Test sends a message, reloads the page, re-opens copilot tab, opens conversation dropdown, and at least one persisted conversation item exists

### 9. Copilot E2E — Persona Switching (requires Docker test stack)

1. Run `npx playwright test tests/46-copilot/ -g "persona"`
2. **Expected:** Test creates personas via API if needed, opens persona dropdown, clicks a non-active persona, persona button text updates to the selected persona name

### 10. Copilot E2E — Object Creation from Chat (requires Docker test stack)

1. Run `npx playwright test tests/46-copilot/ -g "create"`
2. **Expected:** Test sends "Please create a task called Review Q1 goals", confirmation card appears with type/properties preview, Create button click dispatches to Command API, success state shown with IRI pill containing "Review Q1 goals"

### 11. LLM Tier Helper — Export Verification

1. Run `grep -c 'getLlmTier\|getLlmConfig\|configureLlmForTier' e2e/helpers/llm-tier.ts`
2. **Expected:** At least 6 matches — all three functions exported and referenced

### 12. Cost Tracker — Export and Budget Verification

1. Run `grep -c 'CostTracker\|assertBudget\|totalCostUsd' e2e/helpers/cost-tracker.ts`
2. **Expected:** At least 8 matches — CostTracker class, assertBudget(), and totalCostUsd() exported and used

## Edge Cases

### Mock server backward compatibility with M028 claims detection

1. Send a POST to the mock server with a message containing "extract claims from this article"
2. **Expected:** Returns claims JSON (not generic response) — the claims route has highest priority to preserve M028 test compatibility

### Cost tracker budget exceeded

1. Create a CostTracker with budgetUsd = 0.001
2. Call addPromptTokens(1000000) (1M tokens at $0.15/1M = $0.15)
3. Call assertBudget()
4. **Expected:** Throws an error with descriptive message including dollar amounts and token counts

### Copilot tab lazy-loading

1. Open the workspace without clicking the AI COPILOT tab
2. Click the AI COPILOT tab
3. **Expected:** Copilot container appears, conversation header renders after async initialization completes

## Failure Signals

- `python3 e2e/mock-llm-api/server.py --selftest` reports any ✗ — mock server routing or SSE format broken
- `docker compose -f docker-compose.test.yml config` exits non-zero — compose file syntax or service definition error
- Backend pytest reports failures — copilot service, persona, or conversation logic regression
- E2E tests timeout waiting for `#copilot-container` — copilot lazy-loading broken or tab activation failed
- E2E tests see no assistant response — SSE streaming not reaching the frontend, or mock-llm not reachable from the api container
- Approval card never appears — mock-llm SPARQL route not matching, or SSE `event: sparql_query` not parsed by copilot.js

## Requirements Proved By This UAT

- AI-08 (mock LLM test harness) — selftest + docker-compose mock-llm service + deterministic E2E assertions
- AI-09 (Ollama integration tests) — docker-compose.test-ollama.yml validates and defines local inference stack
- AI-10 (cloud test tier with budget cap) — CostTracker with assertBudget() and printCostReport()

## Not Proven By This UAT

- Real Ollama inference (requires pulling a model and running actual LLM completion — only compose structure verified)
- Real cloud API cost enforcement (requires live OpenAI API key with actual token consumption)
- Full Playwright E2E run time under 5 seconds (depends on Docker stack startup and test runner overhead)
- Copilot answer quality with real LLMs (mock responses are canned — quality testing requires human evaluation)

## Notes for Tester

- The selftest (check 1-2) and compose validation (checks 3-4) are fast standalone checks that don't need Docker running.
- Backend unit tests (check 5) run in ~1.5 seconds without Docker.
- Checks 6-10 require the full Docker test stack running. Start it and wait for all services to be healthy before running Playwright.
- The copilot E2E tests run in serial mode — don't use `--workers` flag.
- If the mock-llm container isn't reachable, check `docker compose logs mock-llm` for startup errors and verify the health endpoint: `docker compose exec api curl http://mock-llm:8080/health`.
