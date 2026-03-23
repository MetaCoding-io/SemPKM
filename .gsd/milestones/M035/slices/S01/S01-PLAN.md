# S01: Copilot Chat with SPARQL Generation

**Goal:** The AI COPILOT bottom panel is a functional chat interface where users can ask natural-language questions about their knowledge graph, the copilot generates SPARQL queries, shows them for approval, executes them against the triplestore, and returns prose answers with clickable object links — all streaming in real time.

**Demo:** User opens AI COPILOT tab, asks "How many projects do I have?", sees the generated SPARQL query for approval, approves it, and gets a prose answer with clickable object links — all streaming in real time against real triplestore data.

## Must-Haves

- `CopilotService` class with `build_schema_context()`, `generate_sparql()`, `validate_query()`, `execute_and_format()` methods
- `POST /api/copilot/chat` SSE endpoint accepting `{messages, conversation_id?, model?}` with system prompt injection and schema context
- `ai_router` from `app.api.ai` wired into `main.py`
- Chat UI in `#panel-ai-copilot` with message thread (user/assistant/system), markdown rendering, and IRI object pill links
- SSE streaming display with typing indicator and incremental token rendering
- SPARQL query approval widget: show generated query → approve/edit/reject controls
- SPARQL validation: parse check, read-only guard, predicate verification against installed model schemas
- Self-correction loop: if query execution fails, feed error back to LLM for retry (max 2 retries)
- Query results formatted as prose with clickable object links (reuse SPARQL console IRI pill pattern)
- Graceful degradation when LLM is not configured (show setup instructions)
- nginx SSE proxy config for `/api/copilot/`

## Proof Level

- This slice proves: integration (copilot generates SPARQL, executes against real triplestore, returns formatted results)
- Real runtime required: yes (triplestore + LLM provider or mock)
- Human/UAT required: yes (copilot answer quality is subjective — verify via Docker stack with basic-pkm data)

## Verification

- `cd backend && python -m pytest tests/test_copilot_service.py -v` — unit tests for CopilotService (schema context, SPARQL validation, query formatting, self-correction)
- `cd backend && python -m pytest tests/test_ai_endpoints.py -v` — existing AI endpoint tests still pass after ai_router wiring
- `bash .gsd/milestones/M035/slices/S01/verify-s01.sh` — integration check: confirm endpoint responds, chat UI renders, nginx proxies SSE

## Observability / Diagnostics

- Runtime signals: structured logging in CopilotService (`copilot.sparql_gen`, `copilot.query_exec`, `copilot.self_correct`) with user, model, query, and error fields
- Inspection surfaces: `GET /api/llm/status` for LLM availability; browser DevTools Network tab for SSE stream inspection; copilot UI shows SPARQL queries inline
- Failure visibility: SPARQL validation errors shown in approval widget; LLM errors streamed as system messages; self-correction retry count visible in logs
- Redaction constraints: API keys never logged; user message content logged only at DEBUG level

## Integration Closure

- Upstream surfaces consumed: `backend/app/services/llm.py` (LLMConfigService), `backend/app/sparql/client.py` (scope_to_current_graph), `backend/app/services/shapes.py` (ShapesService), `backend/app/services/labels.py` (LabelService), `backend/app/triplestore/client.py` (TriplestoreClient), `backend/app/commands/dispatcher.py` (HANDLER_REGISTRY)
- New wiring introduced: `ai_router` added to `main.py` include_router chain; new `copilot_router` registered; nginx location block for `/api/copilot/`; `initCopilotChat()` called from workspace.js panel tab handler
- What remains before the milestone is truly usable end-to-end: S02 (graph context injection, conversation persistence), S03 (personas, object creation), S04 (test harness)

## Tasks

- [x] **T01: Build CopilotService with schema context and SPARQL generation** `est:2h`
  - Why: The core backend logic — builds schema context from installed models, generates SPARQL via LLM, validates queries, executes them, formats results with labels. This is the brain of the copilot.
  - Files: `backend/app/services/copilot.py`, `backend/tests/test_copilot_service.py`
  - Do: Create CopilotService class with: (1) `build_schema_context()` that queries ShapesService for all installed types + property shapes and serializes them as a compact text block for the LLM system prompt; (2) `generate_sparql()` that builds a prompt with schema context + user question and calls LLM (non-streaming) to get a SPARQL query; (3) `validate_query()` that parses the query string, checks it's SELECT-only (no INSERT/DELETE/DROP), verifies predicates reference known model schemas; (4) `execute_query()` that runs via scope_to_current_graph with timeout; (5) `format_results()` that takes SPARQL JSON results and uses LabelService to build prose with IRI references; (6) `self_correct()` that feeds the error message + original query back to LLM for retry. Include structured logging for each step.
  - Verify: `cd backend && python -m pytest tests/test_copilot_service.py -v` — all tests pass
  - Done when: CopilotService can build schema context, generate SPARQL from a mock LLM response, validate queries, and format results with labels

- [ ] **T02: Create copilot chat SSE endpoint and wire routers into main.py** `est:1h`
  - Why: The copilot needs its own streaming endpoint that injects system prompt + schema context before proxying to the LLM, plus the existing ai_router needs to be registered. Also needs nginx SSE proxy config.
  - Files: `backend/app/api/copilot.py`, `backend/app/main.py`, `frontend/nginx.conf`
  - Do: (1) Create `backend/app/api/copilot.py` with `POST /api/copilot/chat` endpoint: accepts `{messages, model?, approve_query?}` body, builds system prompt with schema context via CopilotService, prepends to messages, streams response via SSE; implement query detection in streamed content (detect ```sparql blocks), return query-approval events in the SSE stream; (2) Wire both `ai_router` and new `copilot_router` into main.py; (3) Add nginx location block for `/api/copilot/` with SSE proxy settings (proxy_buffering off, X-Accel-Buffering no, Cache-Control no-cache).
  - Verify: `cd backend && python -m pytest tests/test_ai_endpoints.py -v` — existing tests pass; `grep "copilot_router\|ai_router" backend/app/main.py` confirms both routers wired
  - Done when: `POST /api/copilot/chat` returns SSE stream; ai_router endpoints accessible; nginx proxies SSE correctly

- [ ] **T03: Build copilot chat UI with streaming and markdown rendering** `est:2h`
  - Why: Replace the placeholder in #panel-ai-copilot with a functional chat interface: message input, streaming response display, markdown rendering, and IRI pill links.
  - Files: `frontend/static/js/copilot.js`, `frontend/static/css/copilot.css`, `backend/app/templates/browser/workspace.html`, `frontend/static/js/workspace.js`
  - Do: (1) Create `copilot.js` module (lazy-loaded like sparql-console.js): manages SSE connection to /api/copilot/chat, renders user/assistant/system messages, handles streaming token display with typing indicator, renders markdown in responses (reuse markdown-render.js pattern), converts IRI references to clickable object pills (reuse SPARQL console pill pattern from sparql_result_embed.html), shows "LLM not configured" state with link to Settings; (2) Create `copilot.css` with chat message styles: message bubbles (user right-aligned, assistant left-aligned), streaming indicator, code block syntax highlighting for SPARQL, object pill styles; (3) Replace placeholder in workspace.html `#panel-ai-copilot` div with copilot chat container (message thread + input area); (4) Add lazy-load hook in workspace.js `initPanelTabs()` for ai-copilot tab (same pattern as sparql console).
  - Verify: `grep -q "copilot" frontend/static/js/copilot.js && grep -q "initCopilot" frontend/static/js/workspace.js` — files exist and are wired
  - Done when: AI COPILOT tab shows chat UI, user can type messages, responses stream in with markdown rendering and IRI pills

- [ ] **T04: Implement SPARQL approval flow with self-correction** `est:1.5h`
  - Why: The demo requires showing generated SPARQL for user approval before execution. This is the key trust/safety feature — users see what query will run and can approve, edit, or reject.
  - Files: `frontend/static/js/copilot.js`, `frontend/static/css/copilot.css`, `backend/app/api/copilot.py`, `backend/app/services/copilot.py`
  - Do: (1) Backend: extend copilot chat endpoint to detect when LLM response contains SPARQL, pause streaming, emit a `query_approval` SSE event with the query text and validation result; when client sends approval (`POST /api/copilot/approve`), execute the query and stream the formatted results; on rejection, stream a "Query cancelled" message; on edit, re-validate the edited query before execution; (2) Frontend: render approval card in chat thread when `query_approval` event received — shows SPARQL in syntax-highlighted code block with Approve/Edit/Reject buttons; on approve, send approval request and show execution result; on edit, show inline textarea for query editing; on reject, show cancelled state; (3) Self-correction: if query execution fails (SPARQL error), automatically feed error back to LLM (up to 2 retries), show each retry attempt in the chat as a system message; after 3 failures, show the error and suggest rephrasing.
  - Verify: `grep -q "query_approval\|approve" frontend/static/js/copilot.js && grep -q "approve" backend/app/api/copilot.py` — approval flow code exists in both frontend and backend
  - Done when: SPARQL queries shown for approval before execution; approve/edit/reject buttons work; self-correction retries on failure up to 2 times

- [ ] **T05: Unit tests for CopilotService and integration verification script** `est:1h`
  - Why: S01 verification requires passing unit tests and an integration check script. This task writes the comprehensive test suite and verification script.
  - Files: `backend/tests/test_copilot_service.py`, `.gsd/milestones/M035/slices/S01/verify-s01.sh`
  - Do: (1) Write pytest unit tests for CopilotService: test `build_schema_context()` returns expected format with mock ShapesService; test `validate_query()` rejects INSERT/DELETE/DROP, accepts valid SELECT; test `validate_query()` checks predicates against known schemas; test `format_results()` resolves labels and builds prose; test `self_correct()` builds correct retry prompt; test schema context truncation when too large; (2) Write `verify-s01.sh` integration script that: checks copilot.js and copilot.css exist, checks copilot_router is in main.py, checks nginx.conf has copilot location block, checks workspace.html has copilot container (not placeholder), runs pytest for copilot tests.
  - Verify: `cd backend && python -m pytest tests/test_copilot_service.py -v && bash .gsd/milestones/M035/slices/S01/verify-s01.sh`
  - Done when: All unit tests pass; verification script exits 0

## Files Likely Touched

- `backend/app/services/copilot.py` (new)
- `backend/app/api/copilot.py` (new)
- `backend/app/main.py` (wire routers)
- `frontend/static/js/copilot.js` (new)
- `frontend/static/css/copilot.css` (new)
- `backend/app/templates/browser/workspace.html` (replace placeholder)
- `frontend/static/js/workspace.js` (lazy-load hook)
- `frontend/nginx.conf` (SSE proxy)
- `backend/tests/test_copilot_service.py` (new)
- `.gsd/milestones/M035/slices/S01/verify-s01.sh` (new)
