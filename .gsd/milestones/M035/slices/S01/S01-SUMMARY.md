---
id: S01
parent: M035
milestone: M035
provides:
  - CopilotService class with build_schema_context, generate_sparql, validate_query, execute_and_format, self-correction loop
  - POST /api/copilot/chat SSE endpoint with schema-aware system prompt injection and inline SPARQL detection
  - POST /api/copilot/approve endpoint for query approval/rejection/editing/retry
  - ai_router wired into main.py (enables 6 existing AI endpoints from M028)
  - copilot_router wired into main.py
  - Chat UI in #panel-ai-copilot with streaming, markdown rendering, IRI object pills
  - SPARQL approval card with Approve/Edit/Reject buttons, syntax highlighting, self-correction retry
  - LLM-not-configured graceful degradation state
  - nginx SSE proxy config for /api/copilot/chat
  - Pydantic schemas for copilot chat request/response
  - 48 unit tests for CopilotService
  - 13-check integration verification script
requires:
  - slice: none (first slice)
    provides: n/a
affects:
  - S02 (consumes copilot endpoint, chat UI, system prompt injection point for graph context)
  - S03 (consumes copilot endpoint, chat UI, system prompt injection point for personas)
  - S04 (consumes copilot endpoint and service for mock LLM E2E tests)
key_files:
  - backend/app/copilot/__init__.py
  - backend/app/copilot/service.py
  - backend/app/copilot/schemas.py
  - backend/app/api/copilot.py
  - frontend/static/js/copilot.js
  - frontend/static/css/copilot.css
  - backend/app/templates/browser/workspace.html
  - frontend/static/js/workspace.js
  - frontend/nginx.conf
  - backend/tests/test_copilot_service.py
  - .gsd/milestones/M035/slices/S01/verify-s01.sh
key_decisions:
  - D328: Non-blocking predicate validation (warn on unknown predicates, block mutation keywords)
  - D329: ReadableStream SSE client instead of EventSource (POST requires JSON body)
  - D330: CopilotService in backend/app/copilot/ package, not backend/app/services/
patterns_established:
  - Copilot service uses character-based token estimation (~4 chars/token) for schema context budget
  - SPARQL extraction from LLM responses: fenced code block first, then generic block, then heuristic line detection
  - Self-correction loop appends error feedback as user messages to the conversation
  - Custom SSE events (sparql_query, error) coexist with OpenAI streaming data lines in a single stream
  - Approval card state machine: approve → loading → result; edit → textarea → run/cancel; reject → greyed-out; error → retry/edit/dismiss
  - Copilot lazy-load follows the SPARQL console pattern (_applyPanelState checks activeTab, imports module once)
observability_surfaces:
  - Backend structured logs: copilot.schema_context.built, copilot.sparql.generated, copilot.sparql.validated, copilot.sparql.failed, copilot.sparql.retry, copilot.sparql.executed, copilot.sparql.formatted, copilot.chat.request, copilot.chat.sparql_detected, copilot.chat.complete, copilot.approve.request, copilot.approve.executed, copilot.approve.retry
  - SSE error events visible in browser Network tab
  - UI shows SPARQL queries inline, validation errors on approval cards, retry attempt count
  - GET /api/llm/status drives LLM availability check on init
drill_down_paths:
  - .gsd/milestones/M035/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M035/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M035/slices/S01/tasks/T03-SUMMARY.md
  - .gsd/milestones/M035/slices/S01/tasks/T04-SUMMARY.md
  - .gsd/milestones/M035/slices/S01/tasks/T05-SUMMARY.md
duration: ~1.5h (5 tasks)
verification_result: passed
completed_at: 2026-03-23
---

# S01: Copilot Chat with SPARQL Generation

**Full-stack AI copilot with streaming chat, schema-aware SPARQL generation, query approval flow (approve/edit/reject), self-correction retry, markdown rendering, and clickable object links — all wired through a new SSE endpoint with nginx proxy.**

## What Happened

Built the AI copilot from backend service through API endpoint to frontend UI across 5 tasks.

**T01 (CopilotService)** created the `backend/app/copilot/` package with the core intelligence: `build_schema_context()` queries all installed SHACL shapes and serializes type names, property paths, datatypes, and constraint values as readable text for the LLM system prompt (truncated at configurable token budget). `validate_query()` applies a two-tier check: strict rejection for mutation keywords (INSERT, DELETE, DROP, etc.) and non-blocking warnings for unknown predicates. `execute_and_format()` runs queries through `scope_to_current_graph()` and formats results as prose with `[[iri|label]]` markers. `generate_sparql()` orchestrates the self-correction loop — up to 2 retries with error feedback.

**T02 (Endpoint + Wiring)** created `POST /api/copilot/chat` as an SSE streaming endpoint that builds the schema-aware system prompt, prepends it to user messages, and proxies the LLM stream. As tokens accumulate, the endpoint scans for complete ` ```sparql ` code blocks and emits custom `event: sparql_query` SSE events with validation results inline. A separate `POST /api/copilot/approve` endpoint handles query execution. Both `ai_router` (6 existing AI endpoints from M028, previously orphaned) and `copilot_router` were wired into `main.py`. nginx SSE proxy config added.

**T03 (Chat UI)** replaced the "coming in v2.1" placeholder in `#panel-ai-copilot` with a functional chat interface. `copilot.js` is a lazy-loaded ES module (same pattern as SPARQL console) that manages SSE via `fetch()` + `ReadableStream` reader (EventSource doesn't support POST). Features: user/assistant/system message bubbles, streaming token display with typing indicator, markdown rendering via `marked.parse()` with DOMPurify, IRI pill conversion for clickable object links (reuses `window.openTab()` pattern), LLM-not-configured detection with Settings link.

**T04 (Approval Flow)** implemented the full SPARQL approval card: syntax-highlighted query display, Approve/Edit/Reject buttons, inline textarea for query editing, loading spinner during execution, and self-correction retry. On execution failure, the card shows Retry/Edit/Dismiss — Retry sends the error to the LLM for a corrected query (max 2 retries), with each attempt shown as a system message in the thread.

**T05 (Tests + Verification)** extended the test suite to 48 unit tests covering all service methods and edge cases, and created a 13-check integration verification script.

## Verification

| Check | Result |
|-------|--------|
| `cd backend && python -m pytest tests/test_copilot_service.py -v` | 48/48 passed (0.39s) |
| `cd backend && python -m pytest tests/test_ai_endpoints.py -v` | 16/17 passed (1 pre-existing failure on well-known test, unrelated) |
| `bash .gsd/milestones/M035/slices/S01/verify-s01.sh` | 13/13 passed |
| `cd backend && python -c "from app.api.copilot import copilot_router; print('import OK')"` | pass |

## Requirements Advanced

- AI-01 (copilot chat UI) — chat interface with streaming, markdown, object pills now functional
- AI-02 (SPARQL generation) — schema-aware generation with validation and self-correction loop implemented
- AI-03 (query approval flow) — approve/edit/reject/retry controls with inline display implemented
- AI-08 (mock LLM test harness) — 48 unit tests with mock LLM callable established; full E2E in S04

## Requirements Validated

- none (full end-to-end validation requires live Docker stack + LLM — deferred to UAT)

## New Requirements Surfaced

- AI-01 through AI-10 need to be formally added to REQUIREMENTS.md (referenced in roadmap but not yet tracked)

## Requirements Invalidated or Re-scoped

- none

## Deviations

- **CopilotService location:** Plan specified `backend/app/services/copilot.py`. Implemented as `backend/app/copilot/` package (service.py + schemas.py + __init__.py). Better accommodates S02/S03 additions.
- **Predicate validation severity:** Plan said "verifies predicates reference known model schemas" (implies blocking). Implemented as non-blocking warnings because SHACL shape coverage is incomplete — common predicates like `rdf:type` aren't in shapes.
- **ai_router wiring:** Discovered the `ai_router` from M028 was never wired into `main.py`. T02 wired it alongside `copilot_router`, enabling 6 previously orphaned AI endpoints.
- **Markdown rendering:** Plan referenced `window.renderMarkdown()` which doesn't exist. Used `globalThis.marked.parse()` with DOMPurify, matching the actual codebase pattern.

## Known Limitations

- **Mutation keyword check is regex-based** — catches `DELETE` inside SPARQL string literals. Low risk since copilot queries are read-focused, but a future improvement could strip string literals before checking.
- **No conversation persistence** — messages are in-memory only; page reload loses the thread. S02 delivers SQLite persistence.
- **No graph context injection** — copilot sees schema structure but not the user's actual data neighborhood. S02 delivers 1-hop context.
- **No personas** — single default system prompt. S03 delivers switchable AI personas.
- **Pre-existing test failure** — `test_well_known_includes_ai_capabilities` fails because `ai-insights` was never added to the well-known endpoint's capabilities list. Not introduced by this slice.

## Follow-ups

- S02 should add conversation persistence tables to the `copilot/` package and inject graph context into the system prompt at the injection point in `copilot.py`
- S03 should add persona prompt templates at the system prompt injection point in `copilot.py`
- The `ai-insights` well-known capability should be added (pre-existing gap, not slice-related)

## Files Created/Modified

- `backend/app/copilot/__init__.py` — new module init
- `backend/app/copilot/service.py` — CopilotService with schema context, validation, execution, self-correction
- `backend/app/copilot/schemas.py` — Pydantic models for copilot chat request/response
- `backend/app/api/copilot.py` — copilot router with /chat SSE and /approve JSON endpoints
- `backend/app/main.py` — wired ai_router and copilot_router
- `frontend/static/js/copilot.js` — chat UI module (SSE, markdown, pills, approval cards)
- `frontend/static/css/copilot.css` — chat styles (messages, approval cards, syntax highlighting)
- `backend/app/templates/browser/workspace.html` — replaced placeholder with copilot container, added CSS link
- `frontend/static/js/workspace.js` — added copilot lazy-load hook and focus handler
- `frontend/nginx.conf` — SSE proxy location for /api/copilot/chat
- `backend/tests/test_copilot_service.py` — 48 unit tests
- `.gsd/milestones/M035/slices/S01/verify-s01.sh` — 13-check integration verification script

## Forward Intelligence

### What the next slice should know
- CopilotService is at `backend/app/copilot/service.py`, not `backend/app/services/copilot.py`
- The system prompt is built in `_build_system_prompt()` in `service.py` — S02 graph context and S03 persona prompts should be injected here
- The SSE stream in `copilot.py` instantiates CopilotService per-request from `request.app.state` services — conversation history should be loaded and prepended to messages at request time
- `copilot.js` uses `_messageThread` array for in-memory message storage — S02 persistence should save/load from this structure
- The approval endpoint accepts `action: "retry"` with `retry_count` — the self-correction flow is fully backend-driven

### What's fragile
- SPARQL extraction heuristic (`_extract_sparql_from_response`) — depends on LLMs consistently using code fences. If an LLM returns bare SPARQL without fences or SELECT keyword, extraction may miss it.
- The regex mutation check — any new SPARQL update keyword not in the list would slip through. The list is comprehensive for SPARQL 1.1 but future SPARQL extensions could add new mutation forms.

### Authoritative diagnostics
- `cd backend && python -m pytest tests/test_copilot_service.py -v` — 48 tests, covers all service methods, runs in <1s
- `bash .gsd/milestones/M035/slices/S01/verify-s01.sh` — 13 structural checks for file existence and wiring
- Backend logs: grep for `copilot.chat.request` to trace a chat interaction end-to-end

### What assumptions changed
- Plan assumed CopilotService as a single file in services/ — actual structure is a dedicated package in copilot/
- Plan assumed ai_router was already wired — it was orphaned, T02 wired it
- Plan assumed `window.renderMarkdown()` existed — actual pattern is `globalThis.marked.parse()`
