# S03 Research: AI Personas & Object Creation from Chat

**Depth:** Light — both features follow established codebase patterns (CRUD + UI wiring). No unfamiliar technology, no risky integration.

## Summary

S03 delivers two independent capabilities that plug into the S01/S02 copilot infrastructure:

1. **AI Personas** — SQLAlchemy model, CRUD service, Alembic migration, REST endpoints, persona selector dropdown in copilot header, system prompt injection via `_build_system_prompt()`, 4 built-in personas seeded on first run.
2. **Object Creation from Chat** — LLM generates structured `object.create` commands from natural language, copilot renders a confirmation card, user approves, object created via existing Command API (`POST /api/commands`).

Both are low-risk applications of patterns already proven in this codebase.

## Requirement Coverage

- **AI-06 (AI personas)** — primary owner. Persona CRUD, selector, 4 built-ins, prompt template system.
- **AI-07 (object creation from chat)** — primary owner. NL → structured command → confirmation → Command API dispatch.

## Recommendation

Proceed with implementation. Three tasks:

1. **T01: AI Persona Backend** — SQLAlchemy model, Alembic migration 017, AIPersonaService, built-in persona seeding, persona REST endpoints on copilot_router, system prompt injection in `_build_system_prompt()`.
2. **T02: Persona Selector UI** — Dropdown in copilot header bar, persona switching, prompt template slot variables, CSS.
3. **T03: Object Creation from Chat** — Extraction prompt for structured commands, confirmation card UI, Command API dispatch, tests.

## Implementation Landscape

### AI Personas — Backend

**Model:** New `AIPersona` SQLAlchemy model in `backend/app/copilot/models.py` (alongside existing CopilotConversation/CopilotMessage). Fields: `id` (UUID), `user_id` (FK), `name`, `icon` (emoji or lucide icon name), `system_prompt_template` (Text), `model_preference` (optional), `temperature` (float, default 0.7), `is_builtin` (bool), `created_at`, `updated_at`. The `is_builtin` flag prevents deletion of seeded personas.

**Migration:** Alembic migration `017_ai_personas.py`. Next in sequence after `016_copilot_conversations.py`.

**Service:** `AIPersonaService` in `backend/app/copilot/personas.py`. Pattern follows `ConversationService` (stateless class, async methods, db session passed per call). Methods: `create()`, `list_for_user()`, `get()`, `update()`, `delete()`, `get_active()`, `set_active()`, `seed_builtins()`. The `seed_builtins()` method checks if built-in personas exist for the user and creates them if not — called lazily on first `list_for_user()` if no personas exist.

**Built-in personas (4):**
- **General Assistant** — balanced, helpful, default. System prompt: standard copilot instructions.
- **Research Assistant** — citation-heavy, evidence-chain responses, references specific objects. System prompt adds: "Always cite specific objects by name using [[iri|label]] markers. Structure responses with evidence chains."
- **Project Manager** — action-oriented, task generation, status summaries. System prompt adds: "Focus on actionable items, deadlines, and status. Suggest task creation when appropriate."
- **Writing Coach** — style feedback, editing suggestions, prose improvement. System prompt adds: "Provide detailed writing feedback. Suggest improvements to structure, clarity, and style."

**System prompt injection:** `_build_system_prompt()` in `service.py` already accepts `schema_context` and `graph_context`. Add a third kwarg: `persona_prompt: str | None = None`. The persona's `system_prompt_template` is rendered with slot variables (`{installed_models}`, `{type_schemas}`, `{current_context}`) and prepended to the system prompt. S02 forward intelligence confirms this is the intended injection point.

**Endpoints:** Add to `copilot_router` in `api/copilot.py`:
- `GET /api/copilot/personas` — list personas for current user (triggers seed on first call)
- `POST /api/copilot/personas` — create custom persona
- `PUT /api/copilot/personas/{id}` — update persona
- `DELETE /api/copilot/personas/{id}` — delete (rejects built-in deletion)
- `POST /api/copilot/personas/{id}/activate` — set active persona

**Chat request extension:** Add `persona_id: str | None = None` to `CopilotChatRequest` schema. The `copilot_chat()` endpoint looks up the persona, renders its template, and passes it to `_build_system_prompt()`.

### AI Personas — Frontend

**Persona selector:** Add to the copilot header bar (`.copilot-conv-header`), between the conversation title and the new-chat button. A dropdown button shows the active persona icon + name. Clicking opens a dropdown listing all personas with radio-style selection. Follows the same dropdown pattern as the conversation selector already in copilot.js.

**State:** `_activePersonaId` variable in copilot.js. Loaded on init from `GET /api/copilot/personas` (active persona has `is_active: true`). Sent with each chat request as `persona_id`.

**Persona management UI:** Not in S03 scope beyond the selector. Custom persona create/edit can be a future enhancement. The selector shows built-in + user-created personas; creation uses an "Add Persona" item that opens a simple inline form.

### Object Creation from Chat

**Detection:** The copilot system prompt instructs the LLM to output structured JSON when the user requests object creation. Format:

```json
{"action": "create_object", "type": "bpkm:Task", "properties": {"rdfs:label": "Review Q1 goals", "bpkm:dueDate": "2026-03-28"}}
```

The SSE stream accumulator in `copilot_chat()` already scans for SPARQL blocks. Add a parallel scan for `{"action": "create_object"` JSON blocks (fenced in ` ```json ` code blocks).

**Custom SSE event:** Emit `event: create_object` with the parsed JSON payload when detected. The frontend renders a confirmation card (similar pattern to SPARQL approval card).

**Confirmation card UI:** Shows:
- Type label (resolved via shapes data in schema context)
- Property list (key-value pairs, human-readable labels)
- "Create" and "Cancel" buttons

**Execution:** On "Create" click, the frontend sends `POST /api/commands` with an `object.create` command payload. The existing Command API handles IRI minting, triple generation, event store commit, and validation queue. No new backend endpoint needed — reuses the standard command pipeline.

**Post-creation:** The confirmation card transitions to a success state showing the created object's IRI as a clickable pill link. An assistant message is added: "Created [Type]: [[iri|label]]".

**System prompt addition:** Add instructions to `_build_system_prompt()`:
```
When the user asks you to create an object (task, note, project, etc.):
1. Identify the type from the schema above
2. Extract properties from the user's message
3. Output a JSON block: ```json\n{"action": "create_object", "type": "<type_iri>", "properties": {"predicate": "value", ...}}\n```
4. The system will show the user a confirmation card before creating the object.
```

### Integration Points

- **`_build_system_prompt()`** — persona prompt injection (S03 adds `persona_prompt` parameter)
- **`CopilotChatRequest`** — persona_id field addition
- **`copilot_chat()` endpoint** — persona lookup + prompt rendering; create_object JSON detection in stream
- **`copilot.js`** — persona selector UI; create_object confirmation card rendering; `POST /api/commands` dispatch
- **`copilot.css`** — persona selector styles; confirmation card styles
- **`Command API`** — standard `POST /api/commands` with `object.create` payload (no changes needed)
- **`workspace.html`** — no changes needed (copilot container already exists)

### File Inventory

**New files:**
- `backend/app/copilot/personas.py` — AIPersonaService
- `backend/migrations/versions/017_ai_personas.py` — Alembic migration
- `backend/tests/test_ai_personas.py` — unit tests for persona CRUD + seeding
- `backend/tests/test_object_creation_chat.py` — unit tests for creation detection + command generation

**Modified files:**
- `backend/app/copilot/models.py` — add AIPersona model
- `backend/app/copilot/schemas.py` — add persona_id to CopilotChatRequest, add CreateObjectPayload schema
- `backend/app/copilot/service.py` — add persona_prompt to `_build_system_prompt()`, add object creation instructions, add `_extract_create_object_from_response()` helper
- `backend/app/api/copilot.py` — add persona CRUD endpoints, persona lookup in chat flow, create_object SSE event emission
- `frontend/static/js/copilot.js` — persona selector, create_object confirmation card, Command API dispatch
- `frontend/static/css/copilot.css` — persona selector styles, confirmation card styles

### Constraints

- **No workspace persona confusion:** The existing `Persona` model in `backend/app/persona/` is for workspace layout personas (dockview layout, sidebar positions). AI personas are a completely separate concept — different table, different service, different purpose. Name the table `ai_personas` and the model `AIPersona` to avoid any confusion.
- **Schema context for object creation:** The LLM needs type information to generate valid `object.create` commands. The schema context already built by S01's `build_schema_context()` includes type IRIs, property paths, and datatypes — sufficient for the LLM to map "Create a task due Friday" to `{"type": "bpkm:Task", "properties": {"bpkm:dueDate": "2026-03-28"}}`.
- **Command API auth:** `POST /api/commands` requires `require_role_or_api("owner", "member")` auth. The copilot frontend already has session cookies. The frontend dispatches the command directly (not through the copilot backend), ensuring the user's own auth credentials are used.
- **Conversation-persona linking:** Per-persona conversation separation (mentioned in the roadmap) is deferred. All conversations are shared across personas in S03. The `persona_id` on the chat request controls which system prompt is used, not which conversation history is shown.

### Verification Strategy

- **Unit tests:** AIPersonaService CRUD + seeding (pytest), create_object extraction from LLM responses (pytest), system prompt with persona injection (pytest)
- **Integration checks:** Verify persona endpoints return correct data, verify persona selector renders in copilot header, verify create_object confirmation card dispatches to Command API
- **Structural verification script:** File existence, import checks, endpoint wiring, migration presence
