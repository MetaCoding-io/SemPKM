# S03: Workspace Personas — Research

**Date:** 2026-03-17
**Status:** Complete

## Summary

The persona system lets users save named workspace configurations (dockview layout, sidebar panel positions, explorer mode) and switch between them. The codebase is well-prepared: `SemPKMLayouts` in `named-layouts.js` already saves/restores dockview JSON to localStorage, `DashboardSpec`/`WorkflowSpec` provide the SQLAlchemy CRUD + Alembic migration + FastAPI router pattern, `CanvasService` shows the upsert-to-`user_settings` alternative. Panel positions and explorer mode are already persisted to localStorage keys (`sempkm_panel_positions`, `sempkm_explorer_mode`).

The main risk is `dv.fromJSON()` failing on stale/incompatible layout JSON. The existing `initWorkspaceLayout()` in `workspace-layout.js` already wraps `fromJSON()` in try/catch with fallback to default layout — persona switch must replicate this pattern. The other risk is scope creep into settings overrides; D155 explicitly defers this.

## Recommendation

**Dedicated `personas` table** (D159) rather than shoehorning into `user_settings`. Personas have CRUD lifecycle + activation semantics that don't fit key-value storage. Follow the `DashboardSpec` model pattern (SQLAlchemy model + service + router), not the `CanvasService` JSON-in-user_settings pattern.

**Server-side persistence, client-side application.** Backend stores persona state (layout JSON, panel positions JSON, explorer mode string). Frontend fetches active persona on load and applies via existing `dv.fromJSON()`, `restorePanelPositions()`, and explorer mode select. Persona switch = fetch new persona → apply all three state pieces → save previous state to current persona before switching.

**Explicit save only** (D158). No auto-save to server on every `onDidLayoutChange`. Save current state to active persona on: (a) explicit "Save Persona" action, (b) before switching to another persona, (c) on `beforeunload`. localStorage auto-save continues independently for crash recovery.

**Default persona auto-creation** on first workspace load when no personas exist. Captures current localStorage state as "Default" persona and persists to server.

## Implementation Landscape

### Key Files

**Backend — New files:**
- `backend/app/persona/models.py` — `Persona` SQLAlchemy model. Columns: `id` (UUID PK), `user_id` (FK users), `name` (String 255), `layout_json` (Text, dockview JSON), `sidebar_positions_json` (Text), `explorer_mode` (String 50), `is_active` (Boolean), `created_at`, `updated_at`.
- `backend/app/persona/service.py` — `PersonaService` with CRUD + `activate()` + `get_active()` + `save_state()`. Follow `DashboardService` pattern (takes `session_factory`, returns dataclass read models).
- `backend/app/persona/router.py` — REST API routes. Browser routes for sidebar partial. API routes for CRUD + activate.
- `backend/app/persona/__init__.py` — empty.
- `backend/migrations/versions/013_personas.py` — Alembic migration creating `personas` table. Follow `012_workflow_specs.py` pattern.

**Backend — Modified files:**
- `backend/app/main.py` — Register persona routers (both `browser_router` and `api_router`). Follow dashboard/workflow router registration pattern.
- `backend/app/templates/components/_sidebar.html` — Add persona selector between "Settings" and "Layouts" items in user popover. Shows active persona name, dropdown to switch, "Manage Personas" link.
- `backend/app/templates/components/_persona_selector.html` — **New partial.** htmx-driven persona dropdown rendered inside user popover. Lists personas with active indicator, switch action, "New Persona" button.

**Frontend — Modified files:**
- `frontend/static/js/workspace.js` — (1) Add persona commands to command palette in `initCommandPalette()`: "Persona: Switch To..." (parent with children), "Persona: Save Current", "Persona: Create New...". (2) Add `_refreshPersonaPaletteItems(ninja)` similar to `_refreshLayoutPaletteItems()`. (3) Add `switchPersona(id)` function that: saves current state to active persona → fetches new persona → applies layout/positions/mode → updates UI. (4) Add `initPersonas()` called from workspace init that fetches active persona from API and applies state on first load. (5) Add `saveCurrentPersonaState()` that captures `dv.toJSON()`, reads `PANEL_POSITIONS_KEY` and `EXPLORER_MODE_KEY` from localStorage, POSTs to save endpoint.
- `frontend/static/js/workspace-layout.js` — No changes needed. `dv.toJSON()` and `dv.fromJSON()` already work. Persona system reads/writes dockview state through `window._dockview`.
- `frontend/static/js/named-layouts.js` — No changes needed. Named layouts remain a separate localStorage-only feature. Personas are server-persisted and include more state.
- `frontend/static/css/workspace.css` — Persona selector styling in user popover. Active persona indicator. Persona management list styles.

### Build Order

**Task 1: Backend model + migration + service** (foundation, no frontend dependency)
1. Create `backend/app/persona/models.py` with `Persona` SQLAlchemy model
2. Create `backend/migrations/versions/013_personas.py` Alembic migration
3. Create `backend/app/persona/service.py` with CRUD + activate + save_state
4. Unit tests for PersonaService (create, list, get, update, delete, activate, save_state, only-one-active constraint)

**Task 2: Backend API routes + sidebar partial** (depends on T1)
1. Create `backend/app/persona/router.py` with REST endpoints
2. Register routers in `main.py`
3. Create `_persona_selector.html` partial for user popover
4. Modify `_sidebar.html` to include persona selector
5. Test endpoints manually or via unit tests

**Task 3: Frontend persona switching + command palette** (depends on T2)
1. Add `switchPersona()`, `saveCurrentPersonaState()`, `initPersonas()` to workspace.js
2. Wire persona commands into ninja-keys command palette
3. Wire sidebar persona selector clicks to `switchPersona()`
4. Add `beforeunload` handler to save current persona state
5. Default persona auto-creation on first load when no personas exist
6. Browser verification: create persona, switch, verify layout restores

### Verification Approach

**Unit tests:**
- `backend/tests/test_persona_service.py` — CRUD operations, activation (only one active at a time), save_state updates layout/positions/mode, delete active persona activates another or none

**Integration tests:**
- API endpoint tests: POST create, GET list, PUT update, POST activate, DELETE, GET active
- Verify 404 on nonexistent persona, 403 on other user's persona

**Browser verification:**
1. Open workspace → user popover shows persona selector with "Default" active
2. Rearrange layout (move panels, change explorer mode) → click "Save" on persona
3. Create second persona → rearrange differently → save
4. Switch between personas → verify dockview layout, panel positions, and explorer mode all change
5. Ctrl+K → type "Persona" → see switch/save/create commands
6. Reload page → active persona's layout restored from server
7. Delete a persona → verify list updates, another persona activated

## Constraints

- **Layout-only personas (D155)** — No settings overrides. Personas store dockview layout JSON + sidebar panel positions + explorer mode. That's it.
- **Explicit save only (D158)** — No auto-save to server on `onDidLayoutChange`. Save on explicit action or persona switch.
- **Dedicated table (D159)** — Not `user_settings` key-value. New `personas` table with proper schema.
- **htmx + vanilla JS** — No React. Persona selector uses htmx for server-rendered partials, command palette uses ninja-keys API.
- **Single active persona per user** — `is_active` boolean on the table, enforced by service layer (deactivate old before activating new).

## Common Pitfalls

- **`dv.fromJSON()` failure on stale layout** — Persona layout JSON can reference panel types or IDs that no longer exist. Must wrap in try/catch and fall back to empty workspace (same as `initWorkspaceLayout()` does). Show toast: "Layout couldn't be fully restored".
- **Race between auto-save and persona switch** — `onDidLayoutChange` fires when `dv.fromJSON()` is called during persona switch, which would overwrite localStorage with the new persona's layout before the old persona's state is saved. Must save old persona state *before* calling `fromJSON()`. Consider a `_switchingPersona` guard flag that skips localStorage auto-save during the switch.
- **Panel positions JSON is DOM-order-dependent** — `savePanelPositions()` reads the current DOM to determine panel order. The persona must store the JSON string directly (snapshot of positions at save time), not re-derive it during switch.
- **Explorer mode requires triggering change event** — Setting `localStorage.setItem(EXPLORER_MODE_KEY, mode)` is not enough. Must also set the `<select>` value and trigger the htmx request to reload the explorer tree. Look at `initExplorerMode()` line 2192+ for the change handler.
- **Default persona migration from localStorage** — On first load, capture `dv.toJSON()`, `localStorage.getItem(PANEL_POSITIONS_KEY)`, `localStorage.getItem(EXPLORER_MODE_KEY)` as the "Default" persona. Only do this once (check if any personas exist via API first).

## Open Risks

- **Dockview layout JSON size** — Complex workspaces with many tabs produce 5-50KB layout JSON. SQLite `Text` column handles this fine, but API payloads get large if listing all personas with full layout JSON. List endpoint should return metadata only (id, name, is_active); full layout loaded on switch.
- **Persona switch visual flash** — Calling `dv.fromJSON()` rebuilds all panels, which triggers htmx fetches for each panel's content. Users will see a brief flash of empty panels filling in. This is acceptable for v1 but could be improved later with a loading overlay.

## Sources

- `SemPKMLayouts` API: `frontend/static/js/named-layouts.js` — `save()`, `restore()`, `list()` pattern for localStorage layout management
- `DashboardSpec` CRUD pattern: `backend/app/dashboard/models.py` + `service.py` + `router.py` — SQLAlchemy model + service + FastAPI router
- `CanvasService` upsert pattern: `backend/app/canvas/service.py` — `_upsert_setting()` for user_settings table (not used for personas, but instructive)
- Dockview restore: `frontend/static/js/workspace-layout.js` lines 289-316 — `fromJSON()` with try/catch fallback to `buildDefaultLayout()`
- Panel positions: `frontend/static/js/workspace.js` lines 2094-2115 — `savePanelPositions()` / `restorePanelPositions()`
- Explorer mode: `frontend/static/js/workspace.js` line 2182 — `EXPLORER_MODE_KEY` localStorage key, select change handler
- Alembic migration pattern: `backend/migrations/versions/012_workflow_specs.py` — next migration is `013`
- Command palette layout commands: `frontend/static/js/workspace.js` lines 1425-1710 — `_refreshLayoutPaletteItems()` pattern for dynamic command children
