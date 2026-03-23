---
estimated_steps: 5
estimated_files: 5
skills_used:
  - test
---

# T02: Conversation persistence data model, service, API, and chat flow integration

**Slice:** S02 — Graph Context Injection & Conversation Persistence
**Milestone:** M035

## Description

Build SQLite-backed conversation persistence for the copilot. This includes SQLAlchemy models for conversations and messages, an Alembic migration (016), a ConversationService with CRUD methods, REST endpoints for conversation management, and integration into the existing `copilot_chat()` SSE flow so that messages are automatically created, loaded, and saved.

The S01 summary confirms `_messageThread` is an in-memory array in `copilot.js`, and `conversation_id` already exists in `CopilotChatRequest` but is not consumed. This task makes the backend the source of truth for message history.

## Steps

1. **Create SQLAlchemy models** in `backend/app/copilot/models.py`:
   ```python
   class CopilotConversation(Base):
       __tablename__ = "copilot_conversations"
       id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
       user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
       title: Mapped[str] = mapped_column(String(255), default="New Chat")
       created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
       updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

   class CopilotMessage(Base):
       __tablename__ = "copilot_messages"
       id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
       conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("copilot_conversations.id", ondelete="CASCADE"), index=True)
       role: Mapped[str] = mapped_column(String(20))  # 'user', 'assistant', 'system'
       content: Mapped[str] = mapped_column(Text())
       created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
   ```
   Follow the exact patterns from `backend/app/sparql/models.py` and `backend/app/auth/models.py` (mapped_column, no Enum for role).

2. **Create Alembic migration** `backend/migrations/versions/016_copilot_conversations.py`:
   - `revision = "016"`, `down_revision = "015"`
   - `upgrade()` creates both tables with all columns and indexes
   - `downgrade()` drops both tables (messages first due to FK)
   - Follow the pattern in `015_lint_filters.py` — use `op.create_table()` with `sa.Column()`

3. **Create ConversationService** in `backend/app/copilot/conversation.py`:
   - `async create_conversation(db: AsyncSession, user_id: UUID, title: str | None = None) -> CopilotConversation`
   - `async list_conversations(db: AsyncSession, user_id: UUID) -> list[CopilotConversation]` — ordered by updated_at DESC
   - `async get_conversation(db: AsyncSession, conversation_id: UUID, user_id: UUID) -> dict` — returns conversation with messages list, raises 404 if not found or wrong user
   - `async delete_conversation(db: AsyncSession, conversation_id: UUID, user_id: UUID) -> bool`
   - `async add_message(db: AsyncSession, conversation_id: UUID, role: str, content: str) -> CopilotMessage` — also touches conversation's updated_at
   - `async update_title(db: AsyncSession, conversation_id: UUID, title: str) -> None`
   - Auto-title: when creating with no title and adding the first user message, set title to first 50 chars of message content

4. **Add REST endpoints** to `backend/app/api/copilot.py`:
   - `GET /api/copilot/conversations` — list user's conversations (returns `[{id, title, created_at, updated_at}]`)
   - `POST /api/copilot/conversations` — create new conversation (body: `{title?: str}`, returns `{id, title}`)
   - `GET /api/copilot/conversations/{conversation_id}` — get conversation with messages
   - `DELETE /api/copilot/conversations/{conversation_id}` — delete conversation
   - All endpoints require auth via `get_current_user_or_api`

5. **Wire into `copilot_chat()` SSE flow**:
   - If `chat_req.conversation_id` is provided, load conversation and prepend stored messages to the messages list (after system prompt, before current user messages)
   - If `chat_req.conversation_id` is None, auto-create a conversation. After creation, emit an SSE event `event: conversation_created` with `data: {"conversation_id": "<uuid>", "title": "<auto-title>"}` as the first event in the stream
   - After the stream completes (in `_finishStream` equivalent on backend — add a post-stream callback), save the user's last message and the accumulated assistant response to the conversation via `add_message()`
   - The saves happen after streaming completes, not during — keeps the hot path simple
   - **Write unit tests** in `backend/tests/test_conversation_service.py`: CRUD operations against in-memory SQLite (use the existing test fixture pattern from the codebase — `create_async_engine("sqlite+aiosqlite://")`)

## Must-Haves

- [ ] CopilotConversation and CopilotMessage SQLAlchemy models follow codebase patterns
- [ ] Alembic migration 016 creates both tables with proper FKs and indexes
- [ ] ConversationService CRUD all methods work against SQLite
- [ ] REST endpoints registered on copilot_router with proper auth
- [ ] Chat flow auto-creates conversation when conversation_id is null
- [ ] Chat flow emits `conversation_created` SSE event with new ID
- [ ] Chat flow loads history and saves messages after exchange
- [ ] Unit tests pass with in-memory SQLite

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_conversation_service.py -v` — all tests pass
- `cd backend && python -c "from app.copilot.models import CopilotConversation, CopilotMessage; print('OK')"` — models import
- `cd backend && python -c "from app.copilot.conversation import ConversationService; print('OK')"` — service imports
- `cd backend && python -c "import ast; ast.parse(open('migrations/versions/016_copilot_conversations.py').read()); print('migration parses OK')"` — migration is valid Python

## Observability Impact

- Signals added: `copilot.conversation.created` (conversation_id, user_id), `copilot.conversation.loaded` (conversation_id, message_count), `copilot.message.saved` (conversation_id, role)
- How a future agent inspects this: query `copilot_conversations` and `copilot_messages` SQLite tables; GET /api/copilot/conversations endpoint
- Failure state exposed: conversation not-found returns 404 with conversation_id in error message; save failures logged with conversation_id

## Inputs

- `backend/app/copilot/schemas.py` — `CopilotChatRequest` already has `conversation_id` field (from S01)
- `backend/app/api/copilot.py` — existing `copilot_chat()` and SSE helpers (`_sse_event()`)
- `backend/app/db/base.py` — `Base` declarative base for models
- `backend/app/db/session.py` — `get_db_session` dependency
- `backend/app/sparql/models.py` — reference pattern for SQLAlchemy models (uuid PK, user_id FK, timestamps)
- `backend/migrations/versions/015_lint_filters.py` — reference for migration format

## Expected Output

- `backend/app/copilot/models.py` — CopilotConversation and CopilotMessage SQLAlchemy models
- `backend/app/copilot/conversation.py` — ConversationService with CRUD methods
- `backend/app/api/copilot.py` — modified with conversation REST endpoints and chat flow persistence
- `backend/migrations/versions/016_copilot_conversations.py` — Alembic migration
- `backend/tests/test_conversation_service.py` — unit tests for ConversationService
