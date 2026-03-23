# S02: Graph Context Injection & Conversation Persistence

**Goal:** Copilot injects the active object's 1-hop graph neighborhood into LLM context and persists conversation threads in SQLite with CRUD endpoints and a frontend conversation selector.
**Demo:** User views a Project object, opens copilot, asks "Summarize this project" — the LLM sees the project's linked tasks and notes and references them by name in its answer. User reloads the page — conversation history loads from the database. User switches to a different conversation thread.

## Must-Haves

- GraphContextService with `get_neighborhood(iri)` and `serialize_context(triples, token_budget)` that queries the triplestore for literal properties, outbound edges, and inbound edges
- Token budget enforcement (default 2000 tokens = 8000 chars) with truncation priority: own properties > outbound > inbound
- `active_object_iri` field added to `CopilotChatRequest` and wired into the chat endpoint system prompt
- Graceful skip when no active object (non-object tabs, no tab active)
- SQLAlchemy models for `CopilotConversation` and `CopilotMessage` tables with Alembic migration 016
- ConversationService with create/list/get/delete/add_message CRUD
- REST endpoints: GET/POST/DELETE on `/api/copilot/conversations`, GET by ID
- Chat flow integration: auto-create conversation on first message, load history from DB, save after exchange
- SSE `conversation_created` event to signal new conversation ID to frontend
- Frontend conversation selector with new/switch/delete controls
- Frontend tracks active object IRI via `sempkm:tab-activated` event and sends with each request

## Proof Level

- This slice proves: integration (graph data flows from triplestore through service into LLM prompt; conversation data persists across reloads)
- Real runtime required: yes (triplestore for graph context, SQLite for persistence)
- Human/UAT required: no (unit tests + structural verification sufficient for this slice)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_graph_context.py -v` — all tests pass
- `cd backend && .venv/bin/python -m pytest tests/test_conversation_service.py -v` — all tests pass
- `bash .gsd/milestones/M035/slices/S02/verify-s02.sh` — structural checks pass (file existence, import chains, endpoint registration, migration validity, frontend wiring)

## Observability / Diagnostics

- Runtime signals: `copilot.context.neighborhood` (log IRI, triple count, estimated tokens), `copilot.context.truncated` (when budget exceeded), `copilot.conversation.created`, `copilot.conversation.loaded`, `copilot.message.saved`
- Inspection surfaces: conversation list endpoint (`GET /api/copilot/conversations`), conversation detail endpoint (`GET /api/copilot/conversations/{id}`), SQLite `copilot_conversations` and `copilot_messages` tables
- Failure visibility: empty graph context logged as info (not error — expected for non-object tabs), conversation load failures logged with conversation_id and user_id
- Redaction constraints: none (no secrets in graph context or conversation messages)

## Integration Closure

- Upstream surfaces consumed: `backend/app/copilot/service.py` (`_build_system_prompt`), `backend/app/copilot/schemas.py` (`CopilotChatRequest`), `backend/app/api/copilot.py` (copilot_router, `copilot_chat()`), `frontend/static/js/copilot.js` (`_messageThread`, `_streamCopilotResponse`)
- New wiring introduced: GraphContextService instantiated in copilot_chat(), conversation CRUD endpoints on copilot_router, conversation auto-create/load/save in chat flow, frontend active-object tracking + conversation selector UI
- What remains before the milestone is truly usable end-to-end: S03 (personas + object creation), S04 (E2E test harness)

## Tasks

- [ ] **T01: GraphContextService with neighborhood SPARQL and token-budgeted serialization** `est:1h`
  - Why: Provides the backend service that queries a 1-hop graph neighborhood for any IRI and serializes it as human-readable text within a configurable token budget — the core of graph context injection
  - Files: `backend/app/copilot/context.py`, `backend/app/copilot/service.py`, `backend/app/copilot/schemas.py`, `backend/app/api/copilot.py`, `backend/tests/test_graph_context.py`
  - Do: Create GraphContextService with get_neighborhood() (SPARQL for properties + outbound + inbound edges from urn:sempkm:current), serialize_context() (resolve labels, group by predicate, truncate at budget with priority ordering). Add `active_object_iri` to CopilotChatRequest. Add `graph_context` parameter to `_build_system_prompt()`. Wire into copilot_chat() endpoint — call GraphContextService when active_object_iri is provided, inject result into system prompt. Write unit tests with mocked triplestore.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_graph_context.py -v` passes, `cd backend && python -c "from app.copilot.context import GraphContextService; print('OK')"`
  - Done when: GraphContextService returns human-readable context text for a mocked IRI, token budget truncation works, and copilot_chat() injects graph context into system prompt when active_object_iri is provided

- [ ] **T02: Conversation persistence data model, service, API, and chat flow integration** `est:1h`
  - Why: Delivers SQLite-backed conversation persistence — the data model, CRUD service, REST endpoints, and integration into the chat SSE flow so messages survive page reloads
  - Files: `backend/app/copilot/models.py`, `backend/app/copilot/conversation.py`, `backend/app/api/copilot.py`, `backend/migrations/versions/016_copilot_conversations.py`, `backend/tests/test_conversation_service.py`
  - Do: Create SQLAlchemy models (CopilotConversation with user_id/title/timestamps, CopilotMessage with conversation_id/role/content/timestamp). Create Alembic migration 016. Build ConversationService with create/list/get/delete/add_message/update_title. Add REST endpoints to copilot_router. Wire into copilot_chat(): on first message with null conversation_id auto-create conversation and emit SSE `conversation_created` event; load history from DB and prepend to messages; save user and assistant messages after exchange. Write unit tests.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_conversation_service.py -v` passes, migration file parses without error
  - Done when: ConversationService CRUD works against in-memory SQLite, REST endpoints registered, chat flow auto-creates conversations and saves messages

- [ ] **T03: Frontend conversation selector, active-object tracking, and slice verification** `est:1h`
  - Why: Connects both backend features to the UI — tracks the active object IRI and sends it with each request, builds the conversation selector for switching/creating/deleting threads, and provides the slice-level verification script
  - Files: `frontend/static/js/copilot.js`, `frontend/static/css/copilot.css`, `.gsd/milestones/M035/slices/S02/verify-s02.sh`
  - Do: Add `_activeObjectIri` tracking via `sempkm:tab-activated` listener (read `detail.tabId` when `detail.isObjectTab`, clear otherwise). Include `active_object_iri` in chat request body. Add conversation header bar above messages area with title display, "New Chat" button, conversation list dropdown. On init fetch conversations from GET endpoint, display current or most recent. Handle `conversation_created` SSE event to store new ID. On switch/new/delete, call appropriate REST endpoints and re-render. Write verification script checking file existence, imports, endpoint registration, migration validity, and frontend wiring.
  - Verify: `bash .gsd/milestones/M035/slices/S02/verify-s02.sh` — all checks pass
  - Done when: Frontend sends active_object_iri with chat requests, conversation selector allows new/switch/delete, verification script passes all structural checks

## Files Likely Touched

- `backend/app/copilot/context.py` (new)
- `backend/app/copilot/models.py` (new)
- `backend/app/copilot/conversation.py` (new)
- `backend/app/copilot/service.py` (modified — `_build_system_prompt` gains graph_context param)
- `backend/app/copilot/schemas.py` (modified — add active_object_iri to CopilotChatRequest)
- `backend/app/api/copilot.py` (modified — graph context wiring, conversation CRUD endpoints, chat flow persistence)
- `backend/migrations/versions/016_copilot_conversations.py` (new)
- `backend/tests/test_graph_context.py` (new)
- `backend/tests/test_conversation_service.py` (new)
- `frontend/static/js/copilot.js` (modified — active-object tracking, conversation selector)
- `frontend/static/css/copilot.css` (modified — conversation selector styles)
- `.gsd/milestones/M035/slices/S02/verify-s02.sh` (new)
