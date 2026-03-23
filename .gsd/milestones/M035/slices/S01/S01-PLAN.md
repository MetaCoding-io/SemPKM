# S01: Copilot Chat with SPARQL Generation

**Goal:** User opens an AI COPILOT tab in the workspace, asks a natural-language question about their knowledge graph, sees the generated SPARQL query for approval, approves it, and gets a streaming prose answer with clickable object links — all against real triplestore data.
**Demo:** User opens AI COPILOT tab → types "How many projects do I have?" → copilot streams a SPARQL query in an approval card → user clicks Approve → query executes against triplestore → copilot streams a prose answer like "You have 3 projects" with clickable IRI pill links to each project.

## Must-Haves

- `POST /api/copilot/chat` endpoint accepting `{messages, conversation_id?, model?}` and returning SSE stream with system prompt injection, schema context, and SPARQL generation
- `CopilotService` class with `build_schema_context()`, `generate_sparql()`, `validate_query()`, `execute_and_format()` methods
- Schema context builder that serializes installed model types, properties, and prefixes into a system prompt section
- SPARQL validation: parse check (regex + structural), predicate verification against known schema, read-only guard
- Self-correction loop: if generated SPARQL fails execution, feed error back to LLM for retry (max 2 retries per D324)
- Chat UI panel registered as a dockview `copilot-panel` component, openable from workspace
- Message rendering with markdown support and IRI object pill links (reuse SPARQL console pattern)
- SSE streaming display with typing indicator during generation
- Query approval widget: show generated SPARQL with Approve / Edit / Reject buttons
- Graceful degradation when LLM is not configured (show configuration instructions)
- Backend wired into `main.py` router registry
- Frontend wired into `workspace.html` (sidebar section + JS entry) and `workspace.js` (openCopilotTab function)

## Proof Level

- This slice proves: integration
- Real runtime required: yes (triplestore for SPARQL execution, LLM or mock for generation)
- Human/UAT required: no (pytest + mock LLM verify the contract)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_copilot_service.py -v` — unit tests for schema context building, SPARQL validation, self-correction loop, execute-and-format
- `cd backend && .venv/bin/python -m pytest tests/test_copilot_endpoint.py -v` — endpoint tests for SSE streaming, error handling, graceful degradation
- Manual: start Docker stack, configure LLM (or mock), open AI COPILOT tab, ask "How many projects do I have?", verify approval card appears with SPARQL, approve, verify prose answer with object links

## Observability / Diagnostics

- Runtime signals: structured logging in CopilotService — `copilot.chat.start`, `copilot.sparql.generated`, `copilot.sparql.validated`, `copilot.sparql.failed`, `copilot.sparql.retry`, `copilot.sparql.executed`
- Inspection surfaces: SSE stream includes `event: status` messages for phase transitions (generating, validating, executing, responding), visible in browser DevTools Network tab
- Failure visibility: SPARQL validation errors and retry attempts are logged with the query text and error message; SSE stream sends `event: error` with user-friendly message
- Redaction constraints: LLM API key never appears in logs or SSE stream (already handled by LLMConfigService encryption)

## Integration Closure

- Upstream surfaces consumed: `backend/app/services/llm.py` (LLMConfigService for API key/config), `backend/app/sparql/client.py` (scope_to_current_graph, inject_prefixes), `backend/app/triplestore/client.py` (query execution), `backend/app/services/shapes.py` (ShapesService for type schemas), `backend/app/services/labels.py` (LabelService for IRI→label resolution), `backend/app/services/prefixes.py` (PrefixRegistry for prefix compaction), `backend/app/api/ai.py` (existing SSE streaming pattern reference)
- New wiring introduced in this slice: `backend/app/copilot/router.py` registered in `main.py`, `copilot-panel` dockview component in `workspace-layout.js`, AI COPILOT sidebar section in `workspace.html`, `copilot.js` + `copilot.css` frontend assets
- What remains before the milestone is truly usable end-to-end: S02 (graph context injection, conversation persistence), S03 (AI personas, object creation from chat), S04 (E2E test harness)

## Tasks

- [x] **T01: Build CopilotService backend — schema context, SPARQL generation, validation, and self-correction** `est:2h`
  - Why: The core intelligence layer — builds LLM system prompts with schema context, validates generated SPARQL, handles self-correction retries, and executes queries against the triplestore
  - Files: `backend/app/copilot/__init__.py`, `backend/app/copilot/service.py`, `backend/app/copilot/schemas.py`
  - Do: Create `backend/app/copilot/` module. Implement `CopilotService` with: (1) `build_schema_context()` — queries ShapesService for all NodeShapes, serializes type IRIs + property paths + datatypes + in-values as readable text for the LLM system prompt, (2) `validate_query()` — regex parse check for SELECT/CONSTRUCT, predicate extraction and verification against known schema predicates from vocabulary endpoint, read-only guard (reject INSERT/DELETE/DROP), (3) `execute_and_format()` — run query through `scope_to_current_graph()` + `inject_prefixes()` + `client.query()`, format results as prose with IRI references, (4) `generate_sparql()` — orchestrates the self-correction loop: send user question + schema context to LLM, parse SPARQL from response, validate, execute — if execution fails, feed error back to LLM for retry (max 2 retries per D324). Define Pydantic schemas for request/response in `schemas.py`. Use character-based token estimation (~4 chars/token per D326) for schema context budget.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_copilot_service.py -v`
  - Done when: CopilotService correctly builds schema context from installed models, validates SPARQL queries (accepting valid SELECTs, rejecting UPDATEs), and the self-correction loop retries with error feedback

- [ ] **T02: Build copilot chat SSE endpoint and wire into FastAPI** `est:1.5h`
  - Why: The HTTP layer — accepts chat messages, orchestrates CopilotService, streams responses as SSE events with status phases, and handles graceful degradation
  - Files: `backend/app/copilot/router.py`, `backend/app/main.py`
  - Do: Create `POST /api/copilot/chat` endpoint with dual-auth (`get_current_user_or_api`). Accept JSON body `{messages, conversation_id?, model?}`. Stream SSE events: `event: status` (phase transitions), `event: delta` (streaming text chunks), `event: sparql` (generated query for approval), `event: result` (formatted query results), `event: error` (error messages), `event: done` (stream end). When LLM not configured, return `event: error` with configuration instructions. Wire `copilot_router` into `main.py` `include_router()` list. Follow the existing `ai_router` SSE streaming pattern from `backend/app/api/ai.py` (httpx streaming proxy with `StreamingResponse`). Add `POST /api/copilot/chat/execute` endpoint for executing an approved SPARQL query (user clicks Approve → this runs the query and streams formatted results).
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_copilot_endpoint.py -v`
  - Done when: `/api/copilot/chat` accepts messages, streams SSE events, and `/api/copilot/chat/execute` runs approved SPARQL queries

- [ ] **T03: Build copilot chat frontend — dockview panel, message rendering, SSE streaming, approval widget** `est:2h`
  - Why: The user-facing layer — renders the chat UI, handles SSE streaming display, and provides the SPARQL approval flow
  - Files: `frontend/static/js/copilot.js`, `frontend/static/css/copilot.css`, `backend/app/templates/browser/workspace.html`, `frontend/static/js/workspace-layout.js`, `frontend/static/js/workspace.js`
  - Do: (1) Create `copilot.js` IIFE module with: message list rendering (user messages right-aligned, assistant messages left-aligned), SSE EventSource connection to `/api/copilot/chat`, streaming text display with typing indicator, markdown rendering (reuse existing `markdown-render.js` pattern), IRI pill links (reuse SPARQL console `renderIriPill` pattern from `sparql-console.js`), SPARQL approval widget (show query in a code block with Approve/Edit/Reject buttons — Approve calls `/api/copilot/chat/execute`, Edit opens inline editor, Reject dismisses). (2) Create `copilot.css` with chat layout styles using existing CSS custom properties (`--color-bg`, `--color-surface`, etc.). (3) Register `copilot-panel` component in `workspace-layout.js` `createComponentFn` — loads the chat UI HTML into the panel element. (4) Add `openCopilotTab()` function to `workspace.js` (follows `openSettingsTab` pattern — component: 'special-panel', specialType: 'copilot'). (5) Add AI COPILOT section to workspace sidebar in `workspace.html` with a click handler to open the copilot tab. (6) Handle LLM-not-configured state with a helpful message pointing to Settings.
  - Verify: Start Docker stack, navigate to `/browser/`, verify AI COPILOT section appears in sidebar, click it to open copilot tab, verify chat input and empty state render correctly
  - Done when: Copilot tab opens in dockview, messages render with markdown and IRI pills, SSE streaming works, approval widget shows generated SPARQL with Approve/Edit/Reject

- [ ] **T04: Add unit tests for CopilotService and endpoint** `est:1h`
  - Why: Contract verification — ensures schema context building, SPARQL validation, self-correction, and SSE streaming work correctly with deterministic mock LLM responses
  - Files: `backend/tests/test_copilot_service.py`, `backend/tests/test_copilot_endpoint.py`
  - Do: (1) `test_copilot_service.py`: test `build_schema_context()` returns formatted text with type names and properties from mock ShapesService, test `validate_query()` accepts valid SELECT and rejects UPDATE/DELETE/DROP, test `validate_query()` detects unknown predicates, test self-correction loop retries on first failure and succeeds on second attempt, test execute_and_format returns prose with IRI references. Use mocked TriplestoreClient and ShapesService. (2) `test_copilot_endpoint.py`: test `/api/copilot/chat` returns SSE stream with correct event types, test graceful degradation when LLM not configured, test `/api/copilot/chat/execute` runs provided SPARQL and returns formatted results, test auth requirement (401 without session). Mock the LLM HTTP call to return canned SPARQL generation responses.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_copilot_service.py tests/test_copilot_endpoint.py -v`
  - Done when: All tests pass, covering schema context building, SPARQL validation (accept/reject), self-correction retry, SSE streaming format, and graceful degradation

## Files Likely Touched

- `backend/app/copilot/__init__.py`
- `backend/app/copilot/service.py`
- `backend/app/copilot/schemas.py`
- `backend/app/copilot/router.py`
- `backend/app/main.py`
- `frontend/static/js/copilot.js`
- `frontend/static/css/copilot.css`
- `frontend/static/js/workspace.js`
- `frontend/static/js/workspace-layout.js`
- `backend/app/templates/browser/workspace.html`
- `backend/tests/test_copilot_service.py`
- `backend/tests/test_copilot_endpoint.py`
