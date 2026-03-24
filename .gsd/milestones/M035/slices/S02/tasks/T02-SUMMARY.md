---
id: T02
parent: S02
milestone: M035
provides:
  - CopilotConversation and CopilotMessage SQLAlchemy models
  - Alembic migration 016 for copilot_conversations and copilot_messages tables
  - ConversationService with full CRUD (create/list/get/delete/add_message/update_title)
  - REST endpoints for conversation management on copilot_router
  - Chat flow auto-creates conversations, loads history, saves messages after exchange
  - SSE conversation_created event emission for frontend notification
key_files:
  - backend/app/copilot/models.py
  - backend/app/copilot/conversation.py
  - backend/app/api/copilot.py
  - backend/migrations/versions/016_copilot_conversations.py
  - backend/tests/test_conversation_service.py
key_decisions:
  - Auto-title check runs BEFORE add to avoid SQLAlchemy auto-flush timing issue (SELECT sees pending adds)
  - Messages saved after stream completes, not during — keeps SSE hot path simple and avoids partial saves on errors
  - ConversationService is stateless — accepts AsyncSession per call, no internal commit (caller controls transaction)
patterns_established:
  - ConversationService follows DashboardService pattern — stateless class, async methods, db passed per call
  - Auto-title on first user message with 50-char truncation + ellipsis
  - conversation_created SSE event pattern for streaming endpoints that need to notify frontend of new server-created resources
observability_surfaces:
  - copilot.conversation.created log (conversation_id, user_id)
  - copilot.conversation.loaded log (conversation_id, message_count)
  - copilot.conversation.deleted log (conversation_id, user_id)
  - copilot.conversation.auto_titled log (conversation_id, title)
  - copilot.message.saved log (conversation_id, role)
  - copilot.chat.messages_saved log (conversation_id) on post-stream save
  - copilot.chat.message_save_error log on save failures
  - GET /api/copilot/conversations endpoint for inspection
  - GET /api/copilot/conversations/{id} endpoint for conversation detail with messages
duration: 20m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T02: Conversation persistence data model, service, API, and chat flow integration

**Built SQLite-backed conversation persistence with CRUD service, REST endpoints, and SSE chat flow integration — 22 unit tests pass**

## What Happened

Created the full conversation persistence stack:

1. **SQLAlchemy models** (`models.py`): `CopilotConversation` (user_id, title, timestamps) and `CopilotMessage` (conversation_id, role, content, created_at) following the same mapped_column/ForeignKey patterns as `sparql/models.py`.

2. **Alembic migration 016**: Creates both tables with proper FK constraints and indexes, drops in reverse order for downgrade.

3. **ConversationService** (`conversation.py`): Stateless service with `create_conversation`, `list_conversations`, `get_conversation`, `delete_conversation`, `add_message`, and `update_title`. Auto-titles conversations from the first user message (50-char truncation). The auto-title check runs before the message is added to avoid a SQLAlchemy auto-flush timing issue where pending adds become visible in subsequent SELECT queries.

4. **REST endpoints** on `copilot_router`: `GET /api/copilot/conversations` (list), `POST /api/copilot/conversations` (create), `GET /api/copilot/conversations/{id}` (detail with messages), `DELETE /api/copilot/conversations/{id}` (delete). All use `get_current_user_or_api` auth.

5. **Chat flow integration**: When `conversation_id` is null, auto-creates a conversation and emits `event: conversation_created` SSE event before the LLM stream begins. When `conversation_id` is provided, loads stored messages and prepends them to the LLM context. After the stream completes, saves both the user's message and the assistant's accumulated response. All persistence operations are wrapped in try/except for graceful degradation.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_conversation_service.py -v` — 22/22 pass
- `cd backend && .venv/bin/python -m pytest tests/test_graph_context.py -v` — 13/13 pass (no regressions)
- Models import check: `from app.copilot.models import CopilotConversation, CopilotMessage` — OK
- Service import check: `from app.copilot.conversation import ConversationService` — OK
- Migration parse: `ast.parse(open('migrations/versions/016_copilot_conversations.py').read())` — OK
- Endpoint registration: all 6 routes on copilot_router confirmed (chat, approve, 4 conversation endpoints)
- LSP diagnostics: clean on models.py, conversation.py, copilot.py

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_conversation_service.py -v` | 0 | ✅ pass | 0.53s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_graph_context.py -v` | 0 | ✅ pass | 0.27s |
| 3 | `cd backend && .venv/bin/python -c "from app.copilot.models import CopilotConversation, CopilotMessage; print('OK')"` | 0 | ✅ pass | <1s |
| 4 | `cd backend && .venv/bin/python -c "from app.copilot.conversation import ConversationService; print('OK')"` | 0 | ✅ pass | <1s |
| 5 | `cd backend && .venv/bin/python -c "import ast; ast.parse(open('migrations/versions/016_copilot_conversations.py').read()); print('migration parses OK')"` | 0 | ✅ pass | <1s |

## Diagnostics

- Grep backend logs for `copilot.conversation.` and `copilot.message.saved` to trace conversation lifecycle
- `copilot.chat.auto_created_conversation` logs when a chat creates a new thread
- `copilot.chat.messages_saved` logs after post-stream persistence succeeds
- `copilot.chat.message_save_error` logs persistence failures (chat still completes)
- Query `copilot_conversations` and `copilot_messages` SQLite tables directly for data inspection
- GET `/api/copilot/conversations` returns all user threads; GET by ID returns full message history

## Deviations

- Auto-title check reordered to execute BEFORE `db.add(msg)` — SQLAlchemy auto-flushes pending objects before executing SELECT queries, so the newly added message was being counted as an existing message, preventing auto-titling. Moving the check before the add resolved this cleanly.

## Known Issues

None.

## Files Created/Modified

- `backend/app/copilot/models.py` — new CopilotConversation and CopilotMessage SQLAlchemy models
- `backend/app/copilot/conversation.py` — new ConversationService with full CRUD + auto-title logic
- `backend/app/api/copilot.py` — added conversation REST endpoints, ConversationService import, chat flow persistence (auto-create, history load, message save, conversation_created SSE event)
- `backend/migrations/versions/016_copilot_conversations.py` — new Alembic migration creating both tables
- `backend/tests/test_conversation_service.py` — 22 unit tests covering create, list, get, delete, add_message, auto-title, update_title, user isolation, and full lifecycle
