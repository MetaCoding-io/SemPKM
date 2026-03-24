# S03: AI Personas & Object Creation from Chat

**Goal:** AI persona system with 4 built-in personas switches the copilot's behavior; object creation from natural language shows a confirmation card and creates objects via Command API.
**Demo:** User picks "Research Assistant" from the persona selector — copilot shifts to citation-heavy responses. User says "Create a task: Review Q1 goals, due Friday" — copilot shows a confirmation card with type + properties, user clicks Create, object appears in the workspace.

## Must-Haves

- AIPersona SQLAlchemy model + Alembic migration 017 + full CRUD service with 4 seeded built-in personas
- REST endpoints for persona list/create/update/delete/activate on copilot_router
- Persona selector dropdown in copilot header that switches the active persona
- `_build_system_prompt()` accepts and renders persona prompt templates with slot variables
- Object creation instructions in system prompt; backend detects `create_object` JSON blocks in LLM stream
- `event: create_object` SSE event emitted to frontend with structured command payload
- Confirmation card UI with type, properties, Create/Cancel buttons; Create dispatches to `POST /api/commands`
- Unit tests for persona CRUD+seeding, object creation extraction, and system prompt integration

## Proof Level

- This slice proves: contract + integration (persona CRUD + system prompt composition + object creation pipeline)
- Real runtime required: no (unit tests with mock; live Docker validation deferred to S04 E2E)
- Human/UAT required: no (persona tone shift requires human judgment but is verified structurally here)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_ai_personas.py -v` — persona CRUD, seeding, prompt integration
- `cd backend && .venv/bin/python -m pytest tests/test_object_creation_chat.py -v` — create_object extraction, command generation
- `cd backend && .venv/bin/python -m pytest tests/test_copilot_service.py -v` — S01 regression (48 tests)
- `cd backend && .venv/bin/python -m pytest tests/test_conversation_service.py -v` — S02 regression (22 tests)
- `bash .gsd/milestones/M035/slices/S03/verify-s03.sh` — structural checks (file existence, imports, endpoint wiring, migration, frontend elements)
- `cd backend && .venv/bin/python -m pytest tests/test_ai_personas.py -v -k "reject"` — failure-path: built-in modification/deletion rejection returns clear error messages

## Observability / Diagnostics

- Runtime signals: `copilot.persona.activated` (user, persona_id), `copilot.persona.seeded` (user, count), `copilot.chat.create_object_detected` (type, properties), `copilot.chat.persona_applied` (persona_id)
- Inspection surfaces: `GET /api/copilot/personas` (list), `POST /api/copilot/personas/{id}/activate` (set active)
- Failure visibility: persona seed failures logged; create_object JSON parse failures logged with raw content; Command API errors surfaced in confirmation card UI
- Redaction constraints: none (no secrets in persona prompts or object properties)

## Integration Closure

- Upstream surfaces consumed: `backend/app/copilot/service.py` (`_build_system_prompt()`), `backend/app/api/copilot.py` (copilot_router, `copilot_chat()` SSE stream), `frontend/static/js/copilot.js` (SSE parser, header), `frontend/static/css/copilot.css`
- New wiring introduced: persona_id flows from frontend → CopilotChatRequest → persona lookup → system prompt; create_object JSON detection in SSE stream → custom SSE event → frontend confirmation card → `POST /api/commands`
- What remains before the milestone is truly usable end-to-end: S04 (mock LLM E2E tests, Ollama integration, cloud test tier)

## Tasks

- [x] **T01: AI Persona Backend — Model, Service, Endpoints, Tests** `est:35m`
  - Why: The persona system needs a SQLAlchemy model, Alembic migration, CRUD service with built-in seeding, REST endpoints, and system prompt injection — all backend-only, no frontend changes
  - Files: `backend/app/copilot/models.py`, `backend/app/copilot/personas.py`, `backend/app/copilot/schemas.py`, `backend/app/copilot/service.py`, `backend/app/api/copilot.py`, `backend/migrations/versions/017_ai_personas.py`, `backend/tests/test_ai_personas.py`
  - Do: (1) Add AIPersona model to models.py with fields: id (UUID), user_id (FK→users), name, icon (emoji/lucide), system_prompt_template (Text), model_preference (nullable), temperature (float, 0.7), is_builtin (bool), is_active (bool), created_at, updated_at. Table name: `ai_personas`. (2) Write Alembic migration 017. (3) Create AIPersonaService in personas.py: create, list_for_user, get, update, delete (reject built-in deletion), get_active, set_active, seed_builtins (4 personas: General Assistant, Research Assistant, Project Manager, Writing Coach — each with distinct system_prompt_template). Seed lazily on first list_for_user if no personas exist. (4) Add persona_id to CopilotChatRequest in schemas.py. Add PersonaResponse schema. (5) Add `persona_prompt` kwarg to `_build_system_prompt()` — prepended before schema context when provided. The template supports `{installed_models}`, `{type_schemas}`, `{current_context}` slot variables. (6) Add REST endpoints to copilot_router: GET /personas, POST /personas, PUT /personas/{id}, DELETE /personas/{id}, POST /personas/{id}/activate. (7) In copilot_chat(), look up active persona (from persona_id on request or user's active), render template, pass to _build_system_prompt(). (8) Write unit tests covering CRUD lifecycle, built-in seeding, built-in deletion rejection, active persona switching, system prompt with persona injection.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_ai_personas.py -v` — all tests pass; `cd backend && python -c "from app.copilot.personas import AIPersonaService; print('import OK')"`
  - Done when: AIPersonaService CRUD works, 4 built-ins seed on first call, persona prompt renders into system prompt, all endpoints return correct responses, tests pass
- [ ] **T02: Persona Selector UI + Object Creation from Chat** `est:40m`
  - Why: The persona selector dropdown makes personas switchable from the UI; the object creation flow detects structured JSON from the LLM, emits a custom SSE event, and renders a confirmation card that dispatches to the Command API
  - Files: `frontend/static/js/copilot.js`, `frontend/static/css/copilot.css`, `backend/app/copilot/service.py`, `backend/app/api/copilot.py`
  - Do: (1) In copilot.js, add persona state (_activePersonaId, _personas), load personas on init from GET /api/copilot/personas, add _renderPersonaSelector() that inserts a dropdown button between the conv title and new-chat button in the header, handle persona switching via POST /personas/{id}/activate, send persona_id with each chat request. (2) In service.py, add object creation instructions to the system prompt telling the LLM to output `{"action": "create_object", "type": "...", "properties": {...}}` JSON blocks when users request object creation. (3) In copilot.py event_stream(), add JSON block detection (scan for `{"action": "create_object"` in accumulated content, similar to SPARQL detection), emit `event: create_object` SSE with the parsed payload. (4) In copilot.js SSE parser, handle `create_object` event — call _renderCreateObjectCard() that shows type label + property list + Create/Cancel buttons. Create button calls `POST /api/commands` with an `object.create` command. On success, show created object as clickable pill link. (5) CSS for persona selector dropdown and create-object confirmation card.
  - Verify: `node --check frontend/static/js/copilot.js` — syntax valid; `rg "create_object" frontend/static/js/copilot.js` — handler exists; `rg "persona" frontend/static/js/copilot.js` — selector wired; `rg "create_object" backend/app/api/copilot.py` — SSE event emission exists
  - Done when: Persona selector renders in copilot header, switching persists via API, persona_id sent with chat requests; create_object JSON detected in stream, confirmation card renders, Create dispatches to Command API
- [ ] **T03: Object Creation Unit Tests + Slice Verification** `est:20m`
  - Why: Closes the slice with unit tests for object creation extraction logic and a structural verification script that proves all S03 deliverables are wired correctly
  - Files: `backend/tests/test_object_creation_chat.py`, `.gsd/milestones/M035/slices/S03/verify-s03.sh`
  - Do: (1) Write test_object_creation_chat.py with tests for: extracting create_object JSON from LLM responses (fenced code block, inline JSON, malformed JSON), generating valid object.create command payloads, system prompt containing object creation instructions, edge cases (missing type, empty properties, invalid JSON). (2) Write verify-s03.sh checking: file existence for all new/modified files, AIPersona import, AIPersonaService import, persona endpoints wired, migration 017 exists, persona_id in CopilotChatRequest, persona_prompt in _build_system_prompt, create_object in copilot.py SSE stream, persona selector in copilot.js, create_object handler in copilot.js, CSS for persona and confirmation card, all prior tests still pass (S01: 48, S02: 22). (3) Run all tests and fix any issues.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_object_creation_chat.py -v` — all pass; `bash .gsd/milestones/M035/slices/S03/verify-s03.sh` — all checks pass; `cd backend && .venv/bin/python -m pytest tests/test_copilot_service.py tests/test_conversation_service.py -v` — regressions clean
  - Done when: All object creation tests pass, verification script passes all checks, S01+S02 regression tests pass

## Files Likely Touched

- `backend/app/copilot/models.py` — add AIPersona model
- `backend/app/copilot/personas.py` — new AIPersonaService
- `backend/app/copilot/schemas.py` — persona_id, PersonaResponse, CreateObjectPayload
- `backend/app/copilot/service.py` — persona_prompt in _build_system_prompt(), object creation instructions
- `backend/app/api/copilot.py` — persona endpoints, persona lookup in chat, create_object SSE detection
- `backend/migrations/versions/017_ai_personas.py` — new migration
- `backend/tests/test_ai_personas.py` — persona CRUD + seeding tests
- `backend/tests/test_object_creation_chat.py` — object creation extraction tests
- `frontend/static/js/copilot.js` — persona selector, create_object confirmation card
- `frontend/static/css/copilot.css` — persona + confirmation card styles
- `.gsd/milestones/M035/slices/S03/verify-s03.sh` — structural verification
