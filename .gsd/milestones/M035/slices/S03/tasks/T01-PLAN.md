---
estimated_steps: 8
estimated_files: 7
skills_used:
  - test
  - review
---

# T01: AI Persona Backend — Model, Service, Endpoints, Tests

**Slice:** S03 — AI Personas & Object Creation from Chat
**Milestone:** M035

## Description

Build the full AI persona backend: SQLAlchemy model, Alembic migration, CRUD service with 4 seeded built-in personas, REST endpoints on copilot_router, and system prompt injection. This is the foundation that T02's frontend persona selector and T03's tests will consume.

The existing workspace `Persona` model (at `backend/app/persona/`) is for layout personas (dockview layout, sidebar positions) — completely separate. The AI persona table is named `ai_personas` and model is `AIPersona` to avoid any confusion.

## Steps

1. **Add AIPersona model to `backend/app/copilot/models.py`**: Fields: `id` (UUID PK, default uuid4), `user_id` (FK→users.id, CASCADE, indexed), `name` (String 100), `icon` (String 50, emoji or lucide icon name), `system_prompt_template` (Text), `model_preference` (String 100, nullable), `temperature` (Float, default 0.7), `is_builtin` (Boolean, default False), `is_active` (Boolean, default False), `created_at` (DateTime with timezone, server_default now), `updated_at` (DateTime with timezone, server_default now, onupdate now). Table name: `ai_personas`.

2. **Create Alembic migration `backend/migrations/versions/017_ai_personas.py`**: Create table `ai_personas` with all columns. `revision = "017"`, `down_revision = "016"`. Follow exact pattern of migration 016.

3. **Create `backend/app/copilot/personas.py` — AIPersonaService**: Stateless class (follows ConversationService pattern). Methods:
   - `seed_builtins(db, user_id)` — check if builtins exist for user, create 4 if not: General Assistant (🤖, default active), Research Assistant (🔬), Project Manager (📋), Writing Coach (✍️). Each with distinct system_prompt_template.
   - `list_for_user(db, user_id)` — return all personas, triggers seed on first call if empty.
   - `get(db, persona_id, user_id)` — get single persona.
   - `create(db, user_id, name, icon, system_prompt_template, ...)` — create custom persona.
   - `update(db, persona_id, user_id, **fields)` — update persona (reject if builtin).
   - `delete(db, persona_id, user_id)` — delete (reject if builtin with clear error).
   - `get_active(db, user_id)` — return the currently active persona.
   - `set_active(db, user_id, persona_id)` — deactivate current, activate specified.

4. **Update `backend/app/copilot/schemas.py`**: Add `persona_id: str | None = Field(None, ...)` to `CopilotChatRequest`. Add `PersonaResponse` Pydantic model for REST responses.

5. **Update `backend/app/copilot/service.py` — `_build_system_prompt()`**: Add `persona_prompt: str | None = None` parameter. When provided, prepend it before the existing content. The caller renders the template with slot variables before passing it.

6. **Add persona REST endpoints to `backend/app/api/copilot.py`**: `GET /api/copilot/personas` (list, triggers seed), `POST /api/copilot/personas` (create), `PUT /api/copilot/personas/{persona_id}` (update), `DELETE /api/copilot/personas/{persona_id}` (delete), `POST /api/copilot/personas/{persona_id}/activate` (set active). All require `get_current_user_or_api` auth.

7. **Wire persona into `copilot_chat()` in `copilot.py`**: After building schema_context and graph_context, look up the persona (from `chat_req.persona_id` or `get_active()`). If found, render its `system_prompt_template` (replace `{installed_models}`, `{type_schemas}`, `{current_context}` with actual values). Pass rendered prompt as `persona_prompt` to `_build_system_prompt()`. Log `copilot.chat.persona_applied`.

8. **Write `backend/tests/test_ai_personas.py`**: Tests for: seed_builtins creates exactly 4 personas with correct names/icons, seed is idempotent (second call is no-op), list_for_user triggers seed then returns all, create custom persona, update custom persona, reject update of builtin, delete custom persona, reject delete of builtin, get_active returns the active one, set_active switches correctly, _build_system_prompt with persona_prompt renders correctly, persona_id field exists on CopilotChatRequest.

## Must-Haves

- [ ] AIPersona SQLAlchemy model in models.py with all specified fields
- [ ] Migration 017 creates ai_personas table
- [ ] AIPersonaService with seed_builtins creating 4 distinct personas
- [ ] Built-in deletion and update are rejected with clear error messages
- [ ] `_build_system_prompt()` accepts and uses persona_prompt parameter
- [ ] All 5 REST endpoints return correct responses
- [ ] copilot_chat() applies active persona to system prompt
- [ ] All unit tests pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_ai_personas.py -v` — all tests pass
- `cd backend && python -c "from app.copilot.personas import AIPersonaService; print('OK')"` — import succeeds
- `cd backend && python -c "from app.copilot.models import AIPersona; print(AIPersona.__tablename__)"` — prints `ai_personas`
- `cd backend && .venv/bin/python -m pytest tests/test_copilot_service.py -v` — S01 regression passes (48 tests)

## Observability Impact

- Signals added: `copilot.persona.seeded` (user_id, count), `copilot.persona.activated` (user_id, persona_id), `copilot.chat.persona_applied` (persona_id, name)
- How a future agent inspects this: `GET /api/copilot/personas` returns all personas with is_active flag
- Failure state exposed: seed failure logged with user_id; persona lookup failure in copilot_chat logged with error

## Inputs

- `backend/app/copilot/models.py` — existing CopilotConversation/CopilotMessage models (add AIPersona alongside)
- `backend/app/copilot/schemas.py` — existing CopilotChatRequest (add persona_id field)
- `backend/app/copilot/service.py` — existing `_build_system_prompt()` (add persona_prompt parameter)
- `backend/app/api/copilot.py` — existing copilot_router (add persona endpoints and chat persona lookup)
- `backend/app/copilot/conversation.py` — reference for ConversationService pattern
- `backend/migrations/versions/016_copilot_conversations.py` — reference for migration pattern

## Expected Output

- `backend/app/copilot/models.py` — modified with AIPersona model added
- `backend/app/copilot/personas.py` — new file: AIPersonaService with full CRUD and 4 built-in persona definitions
- `backend/app/copilot/schemas.py` — modified with persona_id field and PersonaResponse
- `backend/app/copilot/service.py` — modified `_build_system_prompt()` with persona_prompt parameter
- `backend/app/api/copilot.py` — modified with 5 persona endpoints + persona lookup in copilot_chat()
- `backend/migrations/versions/017_ai_personas.py` — new Alembic migration
- `backend/tests/test_ai_personas.py` — new file: unit tests for persona CRUD, seeding, prompt integration
