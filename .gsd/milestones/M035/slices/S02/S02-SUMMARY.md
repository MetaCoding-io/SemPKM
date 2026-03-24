---
id: S02
parent: M035
milestone: M035
provides:
  - GraphContextService with 1-hop neighborhood SPARQL and token-budgeted serialization
  - active_object_iri field on CopilotChatRequest, wired into copilot_chat() endpoint
  - CopilotConversation and CopilotMessage SQLAlchemy models with Alembic migration 016
  - ConversationService with full CRUD (create/list/get/delete/add_message/update_title)
  - REST endpoints for conversation management (GET/POST/DELETE on /api/copilot/conversations)
  - Chat flow auto-creates conversations, loads history, saves messages, emits SSE conversation_created
  - Frontend active object IRI tracking via sempkm:tab-activated
  - Frontend conversation selector with new/switch/delete controls
requires:
  - slice: S01
    provides: CopilotService, copilot_chat endpoint, _build_system_prompt(), copilot.js, copilot.css
affects:
  - S03 (personas inject into same system prompt; conversation persistence available)
  - S04 (E2E tests can verify graph context and conversation persistence)
key_files:
  - backend/app/copilot/context.py
  - backend/app/copilot/models.py
  - backend/app/copilot/conversation.py
  - backend/app/copilot/service.py
  - backend/app/copilot/schemas.py
  - backend/app/api/copilot.py
  - backend/migrations/versions/016_copilot_conversations.py
  - backend/tests/test_graph_context.py
  - backend/tests/test_conversation_service.py
  - frontend/static/js/copilot.js
  - frontend/static/css/copilot.css
key_decisions:
  - D331 — Human-readable grouped text for graph context serialization, not raw RDF triples
  - D332 — Per-message rows in copilot_messages table, not JSON blob
  - D333 — Separate 2000-token budget for graph context, independent of 4000-token schema context
  - Single UNION SPARQL query for types + literals + outbound + inbound (efficiency over 4 separate queries)
  - Priority truncation order: header > properties > outbound > inbound (highest-value context first)
  - Auto-title check runs BEFORE db.add() to avoid SQLAlchemy auto-flush timing issue
  - Messages saved after stream completes, not during — keeps SSE hot path simple
patterns_established:
  - GraphContextService dependency injection pattern (TriplestoreClient, LabelService, PrefixRegistry)
  - ConversationService follows DashboardService pattern — stateless class, async methods, db passed per call
  - conversation_created SSE event for streaming endpoints that create server-side resources
  - _build_system_prompt() optional graph_context parameter — backward compatible extension point
  - Conversation list dropdown with relative-time display and per-item hover-revealed delete
observability_surfaces:
  - copilot.context.neighborhood log (iri, triple_count, category breakdown)
  - copilot.context.truncated log (iri, budget, actual_chars)
  - copilot.chat.graph_context log (iri, chars)
  - copilot.chat.graph_context_error log (iri, error)
  - copilot.conversation.created/loaded/deleted/auto_titled logs
  - copilot.message.saved / copilot.chat.messages_saved logs
  - GET /api/copilot/conversations (list) and GET /api/copilot/conversations/{id} (detail) inspection endpoints
  - Browser console copilot: prefix for frontend event tracing
drill_down_paths:
  - .gsd/milestones/M035/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M035/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M035/slices/S02/tasks/T03-SUMMARY.md
duration: ~65m (T01:25m + T02:20m + T03:20m)
verification_result: passed
completed_at: 2026-03-23
---

# S02: Graph Context Injection & Conversation Persistence

**Copilot now injects the active object's 1-hop graph neighborhood into LLM context (within a 2000-token budget) and persists conversation threads in SQLite with full CRUD, history loading, and a frontend conversation selector**

## What Happened

Three tasks delivered two independent capabilities that wire into the copilot chat flow established in S01:

**T01 — GraphContextService** built the graph context injection pipeline. A single UNION SPARQL query retrieves types, literal properties, outbound object edges, and inbound edges for any IRI from `urn:sempkm:current`. The `serialize_context()` method resolves IRIs to human-readable labels via LabelService, compacts predicates via PrefixRegistry, and assembles grouped text with priority truncation (header always, then properties, then outbound, then inbound) within a configurable 2000-token budget (~8000 chars). This was wired into `copilot_chat()` — when the request includes `active_object_iri`, the service queries the neighborhood, serializes it, and injects it into the system prompt between schema context and instructions. Failures degrade gracefully (logged warning, chat proceeds without context). 13 unit tests cover neighborhood parsing, serialization, truncation, empty/error cases, and system prompt integration.

**T02 — Conversation Persistence** created the full persistence stack: SQLAlchemy models (`CopilotConversation`, `CopilotMessage`), Alembic migration 016, and a stateless `ConversationService` with create/list/get/delete/add_message/update_title CRUD. The chat flow was extended: when `conversation_id` is null, a new conversation is auto-created and a `conversation_created` SSE event is emitted; when provided, stored messages are loaded and prepended to LLM context; after stream completion, both user and assistant messages are saved. Auto-titling uses the first user message (50-char truncation). A SQLAlchemy auto-flush timing issue was discovered and resolved — the title check must run before `db.add()` to avoid the pending message being visible in the subsequent SELECT. 22 unit tests cover the full CRUD lifecycle plus user isolation.

**T03 — Frontend Integration** connected both backends to the UI. Active object tracking listens for `sempkm:tab-activated` events and sends the IRI with each chat request. The conversation selector header bar provides new/switch/delete controls with a dropdown listing all threads with relative timestamps. `conversation_created` SSE events are handled to store auto-created conversation IDs. A 22-check verification script validates the full slice integration.

## Verification

| Check | Result |
|-------|--------|
| `bash verify-s02.sh` — 22 structural checks (files, imports, endpoints, migration, schema, frontend) | 22/22 pass |
| `pytest tests/test_graph_context.py -v` — neighborhood, serialization, truncation, prompt integration | 13/13 pass |
| `pytest tests/test_conversation_service.py -v` — CRUD, auto-title, user isolation, lifecycle | 22/22 pass |
| `pytest tests/test_copilot_service.py -v` — S01 regression check | 48/48 pass |
| `_build_system_prompt('schema', graph_context='test')` — context present when provided, absent when not | pass |
| `node --check copilot.js` — JS syntax valid | pass |
| LSP diagnostics on context.py, models.py, conversation.py, copilot.py | clean |

## Requirements Advanced

- AI-04 (graph context injection) — graph neighborhood is queried, serialized with token budget, and injected into LLM system prompt when active object is provided
- AI-05 (conversation persistence) — conversations and messages persist in SQLite across page reloads, with full CRUD and REST endpoints

## Requirements Validated

- None — AI-04 and AI-05 are advanced but not yet validated. Full validation requires E2E tests in S04 against a live Docker stack.

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- Auto-title check reordered to execute before `db.add(msg)` — SQLAlchemy auto-flush causes pending objects to become visible in subsequent SELECT queries, which prevented auto-titling. Not a plan deviation but a discovery during implementation.
- Verification script needed a `check_sub()` helper with explicit subshell `(eval ...)` — `cd backend` in the parent scope was leaking between checks. Plan didn't anticipate this but the fix was minimal.

## Known Limitations

- Graph context queries `urn:sempkm:current` only — event history graphs are excluded (consistent with SPARQL API scoping behavior, see KNOWLEDGE.md)
- Token estimation is character-based (~4 chars/token per D326) — not tiktoken-precise
- No pagination on conversation list endpoint — fine for typical use but could be slow with hundreds of threads
- Conversation history prepended to LLM context without summarization — long threads will hit LLM context limits
- No conversation search or export

## Follow-ups

- S03 will add persona system prompts that compose with graph context in `_build_system_prompt()`
- S04 E2E tests should verify graph context injection against real triplestore data and conversation persistence across page reloads
- Future: conversation summarization for long threads (compress older messages to stay within LLM context window)

## Files Created/Modified

- `backend/app/copilot/context.py` — new GraphContextService with get_neighborhood() and serialize_context()
- `backend/app/copilot/models.py` — new CopilotConversation and CopilotMessage SQLAlchemy models
- `backend/app/copilot/conversation.py` — new ConversationService with full CRUD + auto-title
- `backend/app/copilot/service.py` — modified _build_system_prompt() to accept optional graph_context parameter
- `backend/app/copilot/schemas.py` — added active_object_iri field to CopilotChatRequest
- `backend/app/api/copilot.py` — added GraphContextService wiring, conversation CRUD endpoints, chat flow persistence
- `backend/migrations/versions/016_copilot_conversations.py` — new Alembic migration for conversation tables
- `backend/tests/test_graph_context.py` — 13 unit tests for graph context service
- `backend/tests/test_conversation_service.py` — 22 unit tests for conversation service
- `frontend/static/js/copilot.js` — active object tracking, conversation selector, SSE event handling
- `frontend/static/css/copilot.css` — conversation header bar and dropdown styles
- `.gsd/milestones/M035/slices/S02/verify-s02.sh` — 22-check structural verification script

## Forward Intelligence

### What the next slice should know
- `_build_system_prompt()` now accepts three optional keyword arguments: `schema_context` (S01), `graph_context` (S02), and whatever S03 adds for persona prompts. The function signature is the integration point.
- The `CopilotChatRequest` schema now has `active_object_iri`, `conversation_id`, and `model` fields. S03 will likely add `persona_id`.
- Conversation auto-creation happens in `copilot_chat()` before the LLM stream starts. The `conversation_created` SSE event notifies the frontend of the new ID.
- The copilot_router now has 6 routes: chat, approve, and 4 conversation CRUD endpoints. S03 will add persona routes to the same router.

### What's fragile
- The auto-flush timing workaround in `add_message()` (checking title before `db.add()`) is correct but non-obvious — if someone reorders those lines, auto-titling silently breaks.
- Character-based token estimation has ~15% error margin — context injection stays within soft limits but won't be exact.

### Authoritative diagnostics
- `copilot.context.neighborhood` log — confirms neighborhood query ran with triple count breakdown. If missing, the `active_object_iri` wasn't passed or triplestore query failed.
- `copilot.conversation.created` / `copilot.chat.messages_saved` — confirms the full persistence pipeline. If `created` fires but `messages_saved` doesn't, the stream errored.
- `GET /api/copilot/conversations` — returns all user threads with message counts for inspection.

### What assumptions changed
- No assumptions changed — implementation matched the plan closely. The SQLAlchemy auto-flush timing issue was the only surprise, resolved with a simple reordering.
