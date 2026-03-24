# S04 Research: LLM Test Harness & E2E Integration

**Slice:** S04 — LLM Test Harness & E2E Integration  
**Risk:** Low  
**Depends:** S01 (copilot chat + SPARQL), S02 (graph context + conversations), S03 (personas + object creation)  
**Research depth:** Light — well-understood work using established patterns

## Summary

This slice wires the existing mock LLM server into the Docker test stack and writes Playwright E2E tests for the copilot features built in S01–S03. It also adds an Ollama Docker Compose variant for local integration testing and a cloud test tier helper with budget caps. All patterns are well-established in the codebase — 4 mock API servers already run in `docker-compose.test.yml`, and 50+ E2E test specs exist across 53 directories.

The work divides into three natural units:
1. **Mock LLM server upgrade** — add SSE streaming support and copilot-specific canned responses (SPARQL blocks, object creation JSON, persona-aware answers)
2. **Docker + E2E tests** — add mock-llm service to docker-compose.test.yml, write copilot E2E test spec, configure LLM via API at test time
3. **Ollama compose + cloud tier** — docker-compose.test-ollama.yml, test helper for tier auto-selection, cost tracking utility

## Recommendation

Follow the established mock server + E2E test patterns exactly. The mock LLM server needs SSE streaming (the copilot endpoint sends `"stream": true`) — the current server only returns single JSON responses. The E2E tests should be API-driven (use `ownerRequest` fixture for setup, `ownerPage` for UI verification) to stay fast and deterministic.

## Implementation Landscape

### What Exists

**Mock LLM server** (`e2e/mock-llm-api/server.py`, 348 lines):
- Stdlib `http.server`, no dependencies, runs on port 8080
- Serves `/health`, `/v1/models`, `/v1/chat/completions`
- Returns canned claim-detection JSON only (M028 AI extension use case)
- Does NOT support SSE streaming — always returns full JSON response
- Has 5-check selftest mode (`--selftest`)

**Docker test stack** (`docker-compose.test.yml`):
- 4 mock API servers (Linear, GitHub, Jira, Monday) on `python:3.12-slim`
- All use the same pattern: volume-mount `./e2e/mock-X-api:/app:ro`, healthcheck via Python urllib
- API service gets env vars for mock URLs (e.g., `LINEAR_API_URL: http://mock-linear:8080`)
- No mock-llm service yet — LLM config is database-stored, not env-var-driven

**LLM config mechanism** (`PUT /browser/llm/config`):
- Sets per-field config: `{field: "api_base_url", value: "http://mock-llm:8080"}`
- Also `api_key` and `default_model` fields
- E2E LLM config test already exists at `e2e/tests/06-settings/llm-config.spec.ts` — demonstrates the pattern

**E2E test infrastructure**:
- Playwright with `ownerPage`/`ownerRequest` auth fixtures (`e2e/fixtures/auth.ts`)
- `ApiClient` helper for direct API calls
- `SEL` selectors object for CSS selectors (no copilot selectors yet)
- `waitForIdle` helper for htmx settling
- `SEED` data constants including project/note/concept IRIs
- Tests run sequentially (1 worker), Docker stack on port 3901

**Copilot SSE event types** (from `copilot.py`):
- Standard `data: {...}` — OpenAI streaming chunks (forwarded)
- `event: sparql_query` — `{query, valid, error}` when SPARQL block detected
- `event: create_object` — `{action, type, label, properties}` when object creation JSON detected
- `event: conversation_created` — `{conversation_id, title}` when auto-creating conversation
- `event: error` — `{error: "message"}` on failures
- `data: [DONE]` — stream end sentinel

**Copilot UI selectors** (from `copilot.js`):
- `#copilot-container`, `#copilot-messages`, `#copilot-input`, `#copilot-send-btn`
- `#copilot-conv-header`, `#copilot-conv-title`, `#copilot-conv-dropdown`
- `.copilot-msg-assistant`, `.copilot-msg-user`
- `.copilot-iri-pill` (object links in responses)
- `.copilot-approval-card` (SPARQL approval cards, inferred from CSS classes)
- Persona selector is in the conv-header area

### What Needs to Be Built

**1. Mock LLM SSE streaming** — The server must handle `"stream": true` in the request body and return SSE-formatted `data: {...}\n\n` lines mimicking OpenAI streaming chunks. When `"stream": false` (or absent), return the existing single JSON response. The streaming response must include:
- Token-by-token content chunks (simulated by splitting the canned response into words)
- A final `data: [DONE]` sentinel
- Correct OpenAI streaming format: `{"choices": [{"delta": {"content": "word "}}]}`

**2. Copilot-specific canned responses** — The mock server must return different content based on the system prompt or user message. Pattern-matching approach (like mock-linear's substring matching):
- "SPARQL" or "SELECT" keywords in user message → return a response containing ` ```sparql\nSELECT ?s WHERE { ?s a bpkm:Project }\n``` `
- "create" + "task" keywords → return a response containing ` ```json\n{"action": "create_object", "type": "...", "label": "...", "properties": {...}}\n``` `
- "summarize" or "context" keywords → return a prose response referencing known seed data IRIs
- Default → return a generic helpful response

**3. Docker Compose integration**:
- Add `mock-llm` service to `docker-compose.test.yml` (same pattern as mock-linear)
- API service does NOT need an env var — LLM config is database-stored and set via API at test time
- The mock-llm hostname must be accessible from the API container (same Docker network)

**4. E2E test setup pattern** — Before copilot tests:
```typescript
// Configure LLM to point at mock server
await ownerRequest.put(`${BASE_URL}/browser/llm/config`, {
  data: { field: 'api_base_url', value: 'http://mock-llm:8080' }
});
await ownerRequest.put(`${BASE_URL}/browser/llm/config`, {
  data: { field: 'default_model', value: 'test-model' }
});
await ownerRequest.put(`${BASE_URL}/browser/llm/config`, {
  data: { field: 'api_key', value: 'sk-mock-test-key' }
});
```

**5. E2E test scenarios** (Playwright, `e2e/tests/XX-copilot/copilot.spec.ts`):
- **Chat basic flow**: open copilot tab, type a message, see streaming response appear
- **SPARQL generation + approval**: send a SPARQL-triggering message, see approval card, click Approve, see results
- **Conversation persistence**: send a message, reload page, verify conversation selector lists the thread
- **Persona switching**: load personas, switch to a different one, verify selector updates
- **Object creation**: send a create-triggering message, see confirmation card, click Create, verify object created

**6. Ollama Docker Compose variant** (`docker-compose.test-ollama.yml`):
- Extends `docker-compose.test.yml`
- Adds Ollama service with model pull on startup
- Volume for model cache persistence
- Tests configure LLM URL to `http://ollama:11434` at test time

**7. Cloud test tier helper** (TypeScript utility):
- Auto-selects tier: env var `OPENAI_API_KEY` → cloud, `OLLAMA_API_URL` → Ollama, default → mock
- Token counting from SSE stream (accumulate delta.content lengths)
- Budget tracking: configurable cap (default $1.00), fail test if exceeded
- Cost report: total tokens, estimated cost per test

### Constraints

- The copilot `POST /api/copilot/chat` sends `stream: True` to `{base_url}/v1/chat/completions` — the mock MUST implement SSE streaming, not just JSON responses
- The retry endpoint (`POST /api/copilot/approve` with `action: retry`) sends `stream: False` — the mock must also support non-streaming
- The mock server runs on `python:3.12-slim` (stdlib only, no pip) — SSE output is manual string formatting
- E2E tests run single-worker sequentially — copilot tests must clean up LLM config after themselves (or use a `test.afterAll`)
- The `api` container reaches the mock-llm via Docker network hostname `mock-llm` — but the test runner (outside Docker) uses `localhost:3901` to reach the frontend
- SSE streaming through nginx requires the existing `/api/copilot/chat` location block with `X-Accel-Buffering: no` (already configured in S01)
- Copilot tab is lazy-loaded — tests must click the AI COPILOT tab to activate it before interacting

### Risks

None significant. This is test infrastructure following established patterns. The only moderate risk is SSE streaming in the mock server — manual SSE formatting is straightforward but easy to get wrong (missing `\n\n` delimiters, wrong chunk format). The selftest should validate streaming output.

### Task Decomposition Recommendation

**T01: Upgrade mock LLM server with SSE streaming and copilot canned responses** (~60 lines of code)
- Add streaming support based on `"stream"` field in request body
- Add pattern-matching for copilot-specific responses (SPARQL, object creation, summarize)
- Add mock-llm service to docker-compose.test.yml
- Extend selftest to validate streaming output format
- Verification: `python server.py --selftest` passes with streaming checks

**T02: Copilot E2E tests** (~200 lines)
- Create `e2e/tests/XX-copilot/copilot.spec.ts` with the test scenarios above
- Add copilot selectors to `e2e/helpers/selectors.ts`
- Test LLM config setup/teardown helper
- Verification: tests pass against mock-llm in Docker test stack

**T03: Ollama compose + cloud tier helper + cost tracking** (~150 lines)
- Create `docker-compose.test-ollama.yml`
- Create `e2e/helpers/llm-tier.ts` tier auto-selection helper
- Create `e2e/helpers/cost-tracker.ts` token counting + budget cap
- Verification: compose file is valid, tier helper selects correctly based on env vars

### Verification Strategy

- Mock LLM selftest: `python e2e/mock-llm-api/server.py --selftest` (covers streaming + non-streaming + routing)
- Docker Compose syntax: `docker compose -f docker-compose.test.yml config --quiet` (validates with mock-llm service added)
- E2E tests: `npx playwright test tests/XX-copilot/` against running Docker test stack
- Unit tests: existing 156 tests pass unchanged (regression check)
- Ollama compose: `docker compose -f docker-compose.test-ollama.yml config --quiet`
