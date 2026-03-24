---
id: S03
milestone: M035
title: "AI Personas & Object Creation from Chat"
status: done
started: 2026-03-23
completed: 2026-03-23
tasks_completed: 3
tasks_total: 3
test_count: 126
risk_retired: none (low-risk slice)
---

# S03: AI Personas & Object Creation from Chat

## What This Slice Delivered

AI persona system with 4 built-in personas that switch the copilot's system prompt and behavior, plus natural language object creation that detects structured JSON in the LLM stream, shows a confirmation card, and dispatches to the Command API.

### Persona System (T01 + T02)

- **AIPersona SQLAlchemy model** with id, user_id, name, icon, system_prompt_template, model_preference, temperature, is_builtin, is_active, created_at, updated_at
- **Alembic migration 017** creates `ai_personas` table
- **AIPersonaService** — full CRUD with lazy seeding: `list_for_user()` auto-seeds 4 built-in personas on first call per user (General Assistant 🤖, Research Assistant 🔬, Project Manager 📋, Writing Coach ✍️). Built-in personas are immutable — update/delete raise ValueError with descriptive messages.
- **5 REST endpoints** on `copilot_router`: GET/POST `/personas`, PUT/DELETE `/personas/{id}`, POST `/personas/{id}/activate`
- **System prompt injection**: `_build_system_prompt()` accepts `persona_prompt` kwarg, prepended before SPARQL/schema instructions. Templates use `{installed_models}`, `{type_schemas}`, `{current_context}` slot variables rendered at chat time.
- **Persona selector dropdown** in copilot header — loads personas on init, shows active persona with icon+name, click opens dropdown for switching via `POST /personas/{id}/activate`, sends `persona_id` with every chat request.

### Object Creation from Chat (T02 + T03)

- **System prompt instructions** tell the LLM to output `{"action": "create_object", "type": "...", "label": "...", "properties": {...}}` in a ```json fence when users request object creation
- **`_detect_create_object_blocks()`** in `copilot.py` — mirrors `_detect_sparql_blocks()` pattern: scans accumulated stream content for JSON fences, parses, filters for `"action": "create_object"`, emits `event: create_object` SSE
- **Confirmation card UI** — shows type badge (local name extracted via `_iriLocalName()`), property key-value table, Create/Cancel buttons. Create dispatches to `POST /api/commands` with `object.create` payload. On success, shows clickable pill link to created object. On error, surfaces Command API error in card.
- **Label auto-population** — if the LLM's JSON includes `label` but properties lack `dcterms:title`, the label is set as `dcterms:title` in the command payload.

### Test Coverage (T01 + T03)

- **33 tests** in `test_ai_personas.py` — seeding (6), list/get (5), create (2), update (4), delete (3), activation (4), system prompt integration (4), schemas (3), template slots (2)
- **23 tests** in `test_object_creation_chat.py` — JSON block detection (15), command payload shape (2), system prompt content (6)
- **70 regression tests** — S01 copilot service (48) + S02 conversation service (22) all pass
- **17-check structural verification** script (`verify-s03.sh`)

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Built-in persona immutability | update/delete raise ValueError | Users can customize via new personas; built-ins provide reliable defaults |
| Lazy seeding via list_for_user() | Seed on first list, not on app startup | No separate init step needed; idempotent; per-user isolation |
| JSON fence detection for create_object | Reuse _detect_sparql_blocks() pattern | Proven approach from S01; consistent detection logic |
| Label → dcterms:title mapping | Auto-populate dcterms:title from label field | LLMs reliably produce "label" but not full IRI property keys |
| Persona selector placement | Between conv title and new-chat button | Natural header position; dropdown anchored right to avoid overflow |

## Patterns Established

- **AIPersonaService** follows ConversationService pattern — stateless class, AsyncSession passed in, no global state
- **`_detect_create_object_blocks()`** mirrors `_detect_sparql_blocks()` — same fence-scan → parse → filter → emit pattern for any future structured output detection
- **`_iriLocalName()`** utility extracts readable local name from IRI using hash/slash/colon fallback — reusable anywhere an IRI needs human-readable display
- **`_persona_to_response()`** dict helper converts ORM to API response without Pydantic serialization overhead — consistent with conversation endpoint pattern

## What S04 Needs to Know

- Persona endpoints are at `/api/copilot/personas/*` — the mock LLM E2E tests need to seed/activate personas to test behavior switching
- `create_object` SSE event carries `{type, label, properties}` — E2E tests should verify the confirmation card renders and the Command API call succeeds
- Object creation instructions are part of the system prompt — the mock LLM server needs canned responses that include `{"action": "create_object", ...}` JSON blocks
- All persona state is per-user (`user_id` FK) — test isolation needs separate user sessions or persona cleanup between tests

## Files Changed

### New Files
- `backend/app/copilot/personas.py` — AIPersonaService
- `backend/migrations/versions/017_ai_personas.py` — ai_personas table
- `backend/tests/test_ai_personas.py` — 33 persona tests
- `backend/tests/test_object_creation_chat.py` — 23 object creation tests
- `.gsd/milestones/M035/slices/S03/verify-s03.sh` — 17-check structural verification

### Modified Files
- `backend/app/copilot/models.py` — added AIPersona model
- `backend/app/copilot/schemas.py` — persona_id, PersonaResponse, CreatePersonaRequest, UpdatePersonaRequest
- `backend/app/copilot/service.py` — persona_prompt in _build_system_prompt(), object creation instructions
- `backend/app/api/copilot.py` — 5 persona endpoints, persona lookup in chat, create_object SSE detection+emission
- `frontend/static/js/copilot.js` — persona selector, create_object confirmation card
- `frontend/static/css/copilot.css` — persona selector styles, create-object card styles

## Verification

All 6 verification runs passed:

| Suite | Tests | Result |
|-------|-------|--------|
| test_ai_personas.py | 33 | ✅ |
| test_object_creation_chat.py | 23 | ✅ |
| test_copilot_service.py (S01 regression) | 48 | ✅ |
| test_conversation_service.py (S02 regression) | 22 | ✅ |
| verify-s03.sh structural checks | 17 | ✅ |
| test_ai_personas.py -k "reject" (failure path) | 2 | ✅ |
