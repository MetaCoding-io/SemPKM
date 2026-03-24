---
id: T01
parent: S03
milestone: M035
provides:
  - AIPersona SQLAlchemy model with all specified fields
  - Alembic migration 017 creating ai_personas table
  - AIPersonaService with full CRUD, 4 built-in seeding, activation
  - Built-in persona update/delete rejection with clear error messages
  - _build_system_prompt() persona_prompt parameter
  - 5 REST endpoints on copilot_router for persona management
  - copilot_chat() persona lookup and system prompt injection
  - 33 unit tests covering all persona functionality
key_files:
  - backend/app/copilot/models.py
  - backend/app/copilot/personas.py
  - backend/app/copilot/schemas.py
  - backend/app/copilot/service.py
  - backend/app/api/copilot.py
  - backend/migrations/versions/017_ai_personas.py
  - backend/tests/test_ai_personas.py
key_decisions:
  - Persona templates use {installed_models}, {type_schemas}, {current_context} slot variables rendered at chat time
  - Built-in personas are immutable — update/delete raise ValueError with descriptive messages
  - Lazy seeding on list_for_user() ensures builtins exist without a separate init step
  - General Assistant is the default active persona after seeding
patterns_established:
  - AIPersonaService follows ConversationService pattern — stateless class, AsyncSession passed in
  - _persona_to_response() helper in router converts ORM to dict (avoids Pydantic serialization overhead)
  - Persona lookup in copilot_chat() gracefully degrades — if persona fails, chat proceeds without persona prompt
observability_surfaces:
  - "copilot.persona.seeded" log with user_id and count
  - "copilot.persona.activated" log with user_id and persona_id
  - "copilot.chat.persona_applied" log with persona_id and name
  - "copilot.chat.persona_error" log for graceful degradation
  - GET /api/copilot/personas returns all personas with is_active flag
duration: 18m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T01: AI Persona Backend — Model, Service, Endpoints, Tests

**Added AIPersona model, migration 017, CRUD service with 4 built-in personas, 5 REST endpoints, system prompt injection, and 33 unit tests**

## What Happened

Built the complete AI persona backend in 8 steps as planned:

1. Added `AIPersona` model to `models.py` with all specified fields (id, user_id, name, icon, system_prompt_template, model_preference, temperature, is_builtin, is_active, created_at, updated_at).

2. Created Alembic migration 017 following the 016 pattern exactly — creates `ai_personas` table with proper FK, indexes, and defaults.

3. Created `AIPersonaService` in `personas.py` with complete CRUD: `seed_builtins()` creates 4 personas (General Assistant 🤖, Research Assistant 🔬, Project Manager 📋, Writing Coach ✍️) each with distinct, meaningful system prompt templates containing `{type_schemas}`, `{installed_models}`, `{current_context}` slot variables. `list_for_user()` triggers lazy seed on first call.

4. Updated `CopilotChatRequest` with `persona_id` field. Added `PersonaResponse`, `CreatePersonaRequest`, `UpdatePersonaRequest` schemas.

5. Updated `_build_system_prompt()` to accept `persona_prompt` parameter — prepended before the default SPARQL assistant instructions.

6. Added 5 REST endpoints to `copilot_router`: GET/POST /personas, PUT/DELETE /personas/{id}, POST /personas/{id}/activate. All use `get_current_user_or_api` auth and commit transactions.

7. Wired persona lookup into `copilot_chat()`: resolves persona from `chat_req.persona_id` or falls back to user's active persona, renders template with slot variables, passes to `_build_system_prompt()`. Gracefully degrades if persona lookup fails.

8. Wrote 33 unit tests covering seeding (6), list/get (5), create (2), update (4), delete (3), activation (4), system prompt integration (4), schemas (3), template slot variables (2).

## Verification

- `test_ai_personas.py`: 33/33 passed — covers full CRUD lifecycle, built-in protection, activation, prompt integration
- `test_copilot_service.py`: 48/48 passed — S01 regression clean
- `test_conversation_service.py`: 22/22 passed — S02 regression clean
- Import check: `AIPersonaService` imports OK, `AIPersona.__tablename__` == `ai_personas`

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_ai_personas.py -v` | 0 | ✅ pass | 0.91s |
| 2 | `cd backend && .venv/bin/python -c "from app.copilot.personas import AIPersonaService; print('OK')"` | 0 | ✅ pass | <1s |
| 3 | `cd backend && .venv/bin/python -c "from app.copilot.models import AIPersona; print(AIPersona.__tablename__)"` | 0 | ✅ pass | <1s |
| 4 | `cd backend && .venv/bin/python -m pytest tests/test_copilot_service.py -v` | 0 | ✅ pass | 0.46s |
| 5 | `cd backend && .venv/bin/python -m pytest tests/test_conversation_service.py -v` | 0 | ✅ pass | 0.73s |

## Diagnostics

- `GET /api/copilot/personas` — list all personas for current user (includes is_active flag for UI state)
- `POST /api/copilot/personas/{id}/activate` — switch active persona (returns activated persona)
- Log key `copilot.persona.seeded` — confirms builtins were created, with count
- Log key `copilot.chat.persona_applied` — confirms persona was rendered into system prompt
- Log key `copilot.chat.persona_error` — captures graceful degradation when persona lookup fails

## Deviations

- Removed unused `PersonaResponse` import from `copilot.py` — the router uses `_persona_to_response()` dict helper instead of Pydantic serialization, which is simpler and consistent with existing conversation endpoints.

## Known Issues

None.

## Files Created/Modified

- `backend/app/copilot/models.py` — added AIPersona ORM model with all specified fields
- `backend/app/copilot/personas.py` — new file: AIPersonaService with full CRUD and 4 built-in persona definitions
- `backend/app/copilot/schemas.py` — added persona_id to CopilotChatRequest, PersonaResponse, CreatePersonaRequest, UpdatePersonaRequest schemas
- `backend/app/copilot/service.py` — added persona_prompt parameter to _build_system_prompt()
- `backend/app/api/copilot.py` — added 5 persona REST endpoints + persona lookup in copilot_chat()
- `backend/migrations/versions/017_ai_personas.py` — new Alembic migration creating ai_personas table
- `backend/tests/test_ai_personas.py` — new file: 33 unit tests for persona CRUD, seeding, prompt integration
- `.gsd/milestones/M035/slices/S03/S03-PLAN.md` — added failure-path verification step per pre-flight observability gap
