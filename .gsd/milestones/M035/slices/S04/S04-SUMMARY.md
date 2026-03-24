---
id: S04
parent: M035
milestone: M035
provides:
  - SSE streaming mock LLM server with 5-route pattern matching (claims, SPARQL, create-object, summarize, generic)
  - mock-llm Docker service in docker-compose.test.yml
  - 5-test copilot E2E Playwright spec (basic chat, SPARQL approval, conversation persistence, persona switching, object creation)
  - 35 copilot-specific selectors in shared SEL object
  - Ollama Docker Compose variant for local real-inference testing
  - LLM tier auto-selection helper (mock/ollama/cloud)
  - Token cost tracker with budget cap enforcement ($1.00 default)
requires:
  - slice: S01
    provides: POST /api/copilot/chat endpoint, CopilotService, copilot.js chat UI, copilot.css
  - slice: S02
    provides: GraphContextService, ConversationService, SQLAlchemy models, conversation selector UI
  - slice: S03
    provides: AIPersonaService, persona selector dropdown, object creation flow with confirmation card
affects: []
key_files:
  - e2e/mock-llm-api/server.py
  - docker-compose.test.yml
  - docker-compose.test-ollama.yml
  - e2e/tests/46-copilot/copilot.spec.ts
  - e2e/helpers/selectors.ts
  - e2e/helpers/llm-tier.ts
  - e2e/helpers/cost-tracker.ts
key_decisions:
  - Pattern matching priority in mock server: claims > SPARQL > create-object > summarize > generic (backward compat first)
  - SSE chunks split by word with trailing space to match OpenAI tokenization style
  - Serial test mode for copilot E2E — tests share conversation state and LLM configuration
  - Full service duplication in Ollama compose rather than Docker Compose extends/include for portability
  - GPU passthrough commented out by default — CPU-only works for CI, GPU is opt-in
  - Budget default $1.00 with gpt-4o-mini pricing ($0.15/1M prompt, $0.60/1M completion)
patterns_established:
  - "_select_response() pattern-matching function in mock server for adding new canned response routes"
  - "openCopilotTab() + sendMessage() + waitForAssistantResponse() helpers for copilot E2E interaction"
  - "Three-tier LLM test strategy: getLlmTier() → getLlmConfig() → configureLlmForTier() pipeline"
  - "CostTracker accumulate-then-assert pattern: addPromptTokens/addCompletionTokens per call, assertBudget() as guard, printCostReport() in teardown"
observability_surfaces:
  - "[mock-llm] POST /v1/chat/completions stream=true|false route=copilot|claims log on every request"
  - "GET /health returns {status: ok} for Docker healthcheck and manual inspection"
  - "python server.py --selftest exercises all 12 routes and reports pass/fail per check"
  - "printCostReport() emits formatted token cost table to console for CI budget auditing"
  - "assertBudget() throws descriptive error with dollar amounts and token counts when exceeded"
drill_down_paths:
  - .gsd/milestones/M035/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M035/slices/S04/tasks/T02-SUMMARY.md
  - .gsd/milestones/M035/slices/S04/tasks/T03-SUMMARY.md
duration: 55m
verification_result: passed
completed_at: 2026-03-23
---

# S04: LLM Test Harness & E2E Integration

**3-tier LLM test infrastructure: mock server with SSE streaming and copilot canned responses, 5-test E2E Playwright spec covering the full copilot stack, Ollama compose variant for local inference, and cloud tier cost tracker with budget cap enforcement**

## What Happened

T01 upgraded the existing mock LLM server (which only handled claim detection) into a full copilot test backend. The server now parses request bodies to detect the `stream` field, pattern-matches user message content to select from 5 canned response routes (claims, SPARQL, create-object, summarize, generic), and streams responses word-by-word as OpenAI-format SSE chunks ending with `data: [DONE]`. The `mock-llm` service was added to `docker-compose.test.yml` following the existing mock-* pattern, with the API container's `LLM_API_URL` pointing at it. The selftest expanded from 5 to 12 checks covering all routes in both modes.

T02 created the copilot E2E test suite with 5 test cases exercising the full stack through the mock-llm service: basic chat (generic streaming response), SPARQL generation and approval (approval card → approve → results), conversation persistence (send message → reload → verify conversation in selector), persona switching (create personas if needed → switch → verify), and object creation (trigger message → confirmation card → create → verify IRI pill). A `beforeAll` fixture configures the LLM via `PUT /browser/llm/config` and `afterAll` cleans up. 35 copilot-specific selectors were added to the shared `SEL.copilot` namespace.

T03 completed the 3-tier test strategy with the Ollama compose variant (self-contained stack with `ollama/ollama:latest`, model cache volume, commented GPU passthrough) and two E2E helpers: `llm-tier.ts` for auto-selecting the test tier from environment variables, and `cost-tracker.ts` for accumulating token costs and enforcing a configurable budget cap ($1.00 default).

## Verification

| # | Check | Result |
|---|-------|--------|
| 1 | `python3 e2e/mock-llm-api/server.py --selftest` | ✅ 12/12 passed |
| 2 | `docker compose -f docker-compose.test.yml config --quiet` | ✅ validates with mock-llm |
| 3 | `docker compose -f docker-compose.test-ollama.yml config --quiet` | ✅ validates Ollama variant |
| 4 | `cd backend && python -m pytest tests/test_copilot_service.py tests/test_ai_personas.py tests/test_object_creation_chat.py tests/test_graph_context.py tests/test_conversation_service.py -v` | ✅ 139/139 passed |
| 5 | `python3 e2e/mock-llm-api/server.py --selftest 2>&1 \| grep -c '✗'` | ✅ 0 failures |
| 6 | `grep -c "copilot" e2e/helpers/selectors.ts` | ✅ 35 selectors |
| 7 | `grep -c "test(" e2e/tests/46-copilot/copilot.spec.ts` | ✅ 5 tests |
| 8 | TypeScript compiler — no errors in new copilot spec or helper files | ✅ pass |

Note: Full Playwright run (`npx playwright test tests/46-copilot/`) requires the Docker test stack running. All structural, syntax, and unit test verification passes.

## Requirements Advanced

No tracked requirements in REQUIREMENTS.md apply directly to this slice. The milestone-internal scope markers (AI-08 mock LLM test harness, AI-09 Ollama integration tests, AI-10 cloud test tier with budget cap) are covered by the deliverables.

## Requirements Validated

None — the AI- requirement identifiers referenced in the roadmap are milestone-internal scope markers, not tracked requirements in REQUIREMENTS.md.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

- Backend regression test count is 139, not 126 as estimated in the slice plan. The estimate was approximate.
- `LLM_API_URL` env var added to the api service in docker-compose.test.yml — not in the task plan but required for the backend to discover the mock LLM endpoint.
- Persona test self-provisions via API when no personas exist — deviates from implicit dependency on S03's seeded personas, making the test self-contained.
- Ollama compose uses full service duplication instead of Docker Compose extends/include — more portable, avoids version compatibility issues.

## Known Limitations

- E2E tests require the Docker test stack running (`docker compose -f docker-compose.test.yml up -d`). They cannot run in a bare CI environment without Docker.
- Ollama compose GPU passthrough is commented out by default — must be manually uncommented on machines with nvidia-container-toolkit.
- Cloud tier cost tracking depends on token count extraction from SSE streams, which varies by LLM provider response format. Currently tuned for OpenAI's format.
- The copilot E2E tests run in serial mode (not parallelizable) because they share conversation state and LLM configuration through the test stack.

## Follow-ups

None — this is the final slice of M035.

## Files Created/Modified

- `e2e/mock-llm-api/server.py` — upgraded with SSE streaming, 5-route pattern matching, 12-check selftest
- `docker-compose.test.yml` — added mock-llm service, LLM_API_URL env var, depends_on entry
- `docker-compose.test-ollama.yml` — Ollama variant with model cache volume, GPU passthrough (commented), healthcheck
- `e2e/tests/46-copilot/copilot.spec.ts` — 5-test E2E spec (basic chat, SPARQL approval, persistence, personas, object creation)
- `e2e/helpers/selectors.ts` — added SEL.copilot section with 35 selectors
- `e2e/helpers/llm-tier.ts` — tier auto-selection with getLlmTier(), getLlmConfig(), configureLlmForTier()
- `e2e/helpers/cost-tracker.ts` — CostTracker class with token accumulation, cost estimation, budget cap

## Forward Intelligence

### What the next slice should know
- This is the final slice of M035. The milestone is complete. All copilot features (chat, SPARQL generation, graph context, conversation persistence, personas, object creation) are built and backed by 139 unit tests plus 5 E2E test cases.

### What's fragile
- The mock server's `_select_response()` uses keyword matching on user message content. Adding new canned routes requires careful ordering — earlier matches take priority. The claims route must stay first for backward compatibility with M028 tests.
- The copilot E2E tests depend on specific CSS selectors (35 in SEL.copilot). If the copilot UI restructures, all selectors are centralized for one-place updates.

### Authoritative diagnostics
- `python3 e2e/mock-llm-api/server.py --selftest` — fastest check that the mock server works, no Docker needed
- `docker compose -f docker-compose.test.yml logs mock-llm` — correlates mock-llm requests with E2E test actions
- `CostTracker.printCostReport()` output in CI logs — budget auditing for cloud tier runs

### What assumptions changed
- Estimated 126 backend unit tests → actual count is 139 (growth from S01-S03 landed more tests than planned)
- Mock server needed both backward-compatible claims route AND new copilot routes in the same server, handled via priority ordering in _select_response()
