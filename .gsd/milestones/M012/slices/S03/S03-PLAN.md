# S03: Workspace Personas

**Goal:** Users can create named workspace configurations (personas) that save dockview layout, sidebar panel positions, and explorer mode — then switch between them to restore different workspace setups for different purposes.
**Demo:** User creates two named personas with different dockview layouts, switches between them via sidebar menu or Ctrl+K command palette, and layouts restore correctly including dockview panels, sidebar positions, and explorer mode. Default persona auto-created on first use.

## Must-Haves

- Persona SQLAlchemy model with Alembic migration `013_personas.py`
- PersonaService with CRUD + activate + get_active + save_state (single active persona per user)
- REST API: `GET/POST /api/personas`, `PUT/DELETE /api/personas/{id}`, `POST /api/personas/{id}/activate`, `POST /api/personas/{id}/save-state`
- Browser route for persona selector partial
- Persona selector in user popover menu (between Settings and Layouts)
- Frontend persona switch: save current state → fetch new persona → apply layout + positions + mode
- Command palette entries: "Persona: Switch To...", "Persona: Save Current", "Persona: Create New..."
- Default persona auto-created on first workspace load when none exist
- `dv.fromJSON()` wrapped in try/catch with fallback to default layout
- `beforeunload` saves current persona state
- Personas persist across Docker restarts (SQLite storage)

## Proof Level

- This slice proves: integration (backend CRUD + frontend state management + UI wiring)
- Real runtime required: yes (Docker for full integration, but unit tests cover service layer)
- Human/UAT required: yes (layout restore fidelity is subjective)

## Verification

- `cd backend && python -m pytest tests/test_persona_service.py -v` — unit tests for PersonaService CRUD, activation, save_state, only-one-active constraint
- Browser verification: open workspace → user popover shows persona selector with "Default" → rearrange layout → save → create second persona → switch → verify layout changes → Ctrl+K "Persona" → see commands → reload → active persona layout restored
- Failure-path diagnostic: `curl -s http://localhost:8001/api/personas/00000000-0000-0000-0000-000000000000 | python3 -m json.tool` returns 404 JSON error body with `"detail"` field; `GET /api/personas` returns empty `[]` for user with no personas (not 500)

## Observability / Diagnostics

- Runtime signals: `logger.info("Persona activated: %s", persona.name)` on switch, `logger.warning("Layout restore failed for persona %s", persona_id)` on fromJSON failure
- Inspection surfaces: `GET /api/personas` returns persona list with active indicator; `personas` SQLite table; browser console logs persona switch events
- Failure visibility: try/catch on `dv.fromJSON()` shows toast "Layout couldn't be fully restored" and falls back to default; API returns 404 on nonexistent persona, 403 on other user's persona
- Redaction constraints: none (no secrets in persona data)

## Integration Closure

- Upstream surfaces consumed: `DashboardSpec` model pattern (`backend/app/dashboard/`), `window._dockview` API (`workspace-layout.js`), `savePanelPositions()`/`restorePanelPositions()` (`workspace.js`), `EXPLORER_MODE_KEY` localStorage key, `_refreshLayoutPaletteItems()` command palette pattern, `_sidebar.html` user popover structure
- New wiring introduced in this slice: persona routers registered in `main.py`, `PersonaService` instantiated in `create_app()`, sidebar partial `hx-get` fetch, `initPersonas()` called from workspace init, `beforeunload` handler for persona state save
- What remains before the milestone is truly usable end-to-end: S04 (E2E Playwright tests + user guide docs)

## Tasks

- [x] **T01: Backend model, migration, service, and unit tests** `est:1h`
  - Why: Foundation for all persona functionality — the data model, persistence, and business logic must exist before routes or frontend can be built
  - Files: `backend/app/persona/__init__.py`, `backend/app/persona/models.py`, `backend/app/persona/service.py`, `backend/migrations/versions/013_personas.py`, `backend/tests/test_persona_service.py`
  - Do: (1) Create `persona/` module with `Persona` SQLAlchemy model — columns: id (UUID PK), user_id (FK users), name (String 255), layout_json (Text), sidebar_positions_json (Text), explorer_mode (String 50), is_active (Boolean default false), created_at, updated_at. (2) Create Alembic migration `013_personas.py` following `012_workflow_specs.py` pattern. (3) Create `PersonaService` with async CRUD methods following `DashboardService` pattern: `create()`, `list_for_user()`, `get()`, `update()`, `delete()`, `activate()` (deactivate-all-then-activate-one), `get_active()`, `save_state()` (updates layout_json, sidebar_positions_json, explorer_mode on a persona). (4) Write comprehensive unit tests using in-memory SQLite async session factory (same fixture pattern as `test_dashboard.py`): test create, list, get, update, delete, activate (only-one-active constraint), save_state, delete-active-persona-activates-another, get_active returns None when no personas exist, authorization (user_id check on update/delete).
  - Verify: `cd backend && python -m pytest tests/test_persona_service.py -v` — all tests pass
  - Done when: PersonaService passes 10+ unit tests covering all CRUD operations and the single-active-persona constraint

- [x] **T02: API routes, sidebar persona selector, and main.py wiring** `est:1h`
  - Why: The REST API and sidebar UI make personas accessible to both the frontend JS and the user's popover menu — without these, the service layer has no consumer
  - Files: `backend/app/persona/router.py`, `backend/app/main.py`, `backend/app/templates/components/_persona_selector.html`, `backend/app/templates/components/_sidebar.html`, `frontend/static/css/workspace.css`
  - Do: (1) Create `persona/router.py` with two routers following dashboard pattern: `browser_router` (prefix `/browser/personas`) for htmx partials, `api_router` (prefix `/api/personas`) for JSON API. API routes: `GET /` list (metadata only: id, name, is_active — no layout_json to keep payload small), `POST /` create, `GET /{id}` get (full payload with layout_json), `PUT /{id}` update (name only), `DELETE /{id}` delete, `POST /{id}/activate` activate, `POST /{id}/save-state` save state (accepts layout_json, sidebar_positions_json, explorer_mode in JSON body). Browser route: `GET /selector` returns `_persona_selector.html` partial. (2) Register routers in `main.py`: import and include both routers, instantiate `PersonaService` in `create_app()` as `app.state.persona_service`. (3) Create `_persona_selector.html` partial: list personas with active indicator (radio or checkmark), click-to-switch via JS `switchPersona(id)` call, "Save Current" button, "New Persona..." button that prompts for name. Style with `.persona-selector` CSS in workspace.css. (4) Modify `_sidebar.html` user popover: add persona selector section between "Layouts" and the theme row, using `hx-get="/browser/personas/selector" hx-trigger="toggle" hx-swap="innerHTML"` on a container div that loads when popover opens. Use `hx-trigger="popovershow from:#user-popover"` or load eagerly.
  - Verify: `docker compose up -d && curl -s http://localhost:8001/api/personas | python3 -m json.tool` returns JSON array; open workspace → user popover shows persona section
  - Done when: All 7 API endpoints respond correctly, persona selector renders in user popover with active persona indicated

- [ ] **T03: Frontend persona switching, command palette, and default persona** `est:1.5h`
  - Why: This is the core user-facing functionality — switching personas must save/restore dockview layout, sidebar positions, and explorer mode, and the command palette must provide keyboard-driven access
  - Files: `frontend/static/js/workspace.js`, `frontend/static/css/workspace.css`
  - Do: (1) Add `initPersonas()` function called from workspace init after dockview is ready: fetch `GET /api/personas` — if empty, auto-create "Default" persona by POSTing current `dv.toJSON()`, localStorage panel positions, and explorer mode, then activate it. If personas exist, fetch active persona and apply (but skip layout restore since workspace-layout.js already handles localStorage-based restore on first load). (2) Add `saveCurrentPersonaState()`: capture `window._dockview.toJSON()`, read `localStorage.getItem(PANEL_POSITIONS_KEY)`, read `localStorage.getItem(EXPLORER_MODE_KEY)`, POST to `/api/personas/{activePersonaId}/save-state`. (3) Add `switchPersona(id)`: save current persona state first → fetch `GET /api/personas/{id}` for full payload → POST activate → apply layout via `dv.fromJSON(JSON.parse(persona.layout_json))` wrapped in try/catch (show toast on failure, fall back to `buildDefaultLayout()`) → apply sidebar positions by writing to localStorage and calling `restorePanelPositions()` → apply explorer mode by setting localStorage, updating dropdown value, and triggering htmx change on the select → update UI to show new active persona name. Use a `_switchingPersona` guard flag to prevent `onDidLayoutChange` from overwriting localStorage during the fromJSON call. (4) Add `beforeunload` handler: call `saveCurrentPersonaState()` via `navigator.sendBeacon` or synchronous XHR to save before page close. (5) Add command palette entries in `initCommandPalette()`: parent "Persona: Switch To..." (id: `persona-switch`) with dynamically populated children, "Persona: Save Current" (id: `persona-save`, calls `saveCurrentPersonaState()`), "Persona: Create New..." (id: `persona-create`, prompts for name via ninja-keys search field pattern from layout-save-as). Add `_refreshPersonaPaletteItems(ninja)` following `_refreshLayoutPaletteItems()` pattern — fetches persona list from API and builds child commands under `persona-switch`. (6) Wire sidebar persona selector buttons: "Save Current" calls `saveCurrentPersonaState()`, persona items call `switchPersona(id)`, "New Persona..." opens a prompt or uses fetch to create + activate. (7) Add persona-related CSS: active persona indicator, persona list items in popover, save/new buttons.
  - Verify: Browser verification — create two personas with different layouts, switch between them, verify layout/positions/mode all change. Ctrl+K → "Persona" → see switch/save/create commands. Reload page → active persona layout persisted.
  - Done when: Full persona lifecycle works end-to-end: create, save, switch (with layout restore), rename, delete, command palette access, default persona auto-creation, beforeunload save

## Files Likely Touched

- `backend/app/persona/__init__.py` (new)
- `backend/app/persona/models.py` (new)
- `backend/app/persona/service.py` (new)
- `backend/app/persona/router.py` (new)
- `backend/migrations/versions/013_personas.py` (new)
- `backend/app/main.py` (modified — register routers + service)
- `backend/app/templates/components/_persona_selector.html` (new)
- `backend/app/templates/components/_sidebar.html` (modified — add persona section)
- `backend/tests/test_persona_service.py` (new)
- `frontend/static/js/workspace.js` (modified — persona switching + command palette)
- `frontend/static/css/workspace.css` (modified — persona selector styling)
