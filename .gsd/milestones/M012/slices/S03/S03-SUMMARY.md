---
id: S03
parent: M012
milestone: M012
provides:
  - Persona SQLAlchemy model with Alembic migration 013 (UUID PK, user FK, layout_json, sidebar_positions_json, explorer_mode, is_active)
  - PersonaService with 8 async methods (create, list_for_user, get, update, delete, activate, get_active, save_state) enforcing single-active-per-user constraint
  - REST API with 7 endpoints at /api/personas + 1 browser route at /browser/personas/selector
  - Persona selector UI in sidebar user popover with active indicator and save/create actions
  - Frontend persona lifecycle — initPersonas(), saveCurrentPersonaState(), switchPersona(), createNewPersona(), beforeunload auto-save
  - Command palette entries — "Persona: Switch To...", "Persona: Save Current", "Persona: Create New..." with dynamic submenu
  - Default persona auto-created on first workspace load
  - dv.fromJSON() wrapped in try/catch with toast fallback
requires:
  - slice: none
    provides: independent slice (extends existing workspace infrastructure)
affects:
  - S04 (E2E Tests & User Guide — needs persona features for testing and documentation)
key_files:
  - backend/app/persona/models.py
  - backend/app/persona/service.py
  - backend/app/persona/router.py
  - backend/migrations/versions/013_personas.py
  - backend/app/templates/components/_persona_selector.html
  - backend/app/templates/components/_sidebar.html
  - frontend/static/js/workspace.js
  - frontend/static/js/workspace-layout.js
  - backend/tests/test_persona_service.py
key_decisions:
  - D155 — Layout-only personas for v1 (no settings overrides)
  - D156 — Dedicated personas table following DashboardSpec pattern
  - D157 — Explicit save only (no auto-save on every layout change)
  - ninja-keys children array must list child IDs for drill-down navigation
  - window._switchingPersona bridges guard flag across workspace.js and workspace-layout.js IIFEs
patterns_established:
  - Persona module mirrors dashboard module structure (models.py, service.py, router.py, __init__.py)
  - Single-active constraint enforced via bulk-deactivate + targeted-activate in activate()
  - delete() of active persona auto-activates first remaining to avoid orphan state
  - _refreshPersonaPaletteItems follows _refreshLayoutPaletteItems pattern for async command palette population
  - Cross-IIFE guard flags via window.* for workspace.js ↔ workspace-layout.js communication
observability_surfaces:
  - GET /api/personas returns persona list with is_active indicator
  - Console logs on persona init, save, switch, create with persona name
  - Console warnings on layout restore failure, save failure, init failure
  - Toast notifications for user-visible feedback on all persona operations
  - logger.info on create/activate/delete, logger.warning on auth failures in service layer
  - navigator.sendBeacon on beforeunload for fire-and-forget state save
drill_down_paths:
  - .gsd/milestones/M012/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M012/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M012/slices/S03/tasks/T03-SUMMARY.md
duration: 80m (T01: 20m, T02: 25m, T03: 35m)
verification_result: passed
completed_at: 2026-03-17
---

# S03: Workspace Personas

**Full persona system with backend CRUD, REST API, sidebar selector, command palette integration, and frontend save/switch/create lifecycle — dockview layout, sidebar positions, and explorer mode all persist and restore across persona switches and page reloads**

## What Happened

### T01: Backend Foundation
Created the `backend/app/persona/` module following the established DashboardSpec pattern. The Persona model has 9 columns covering workspace state (layout_json, sidebar_positions_json, explorer_mode) plus the is_active flag for the single-active constraint. Migration 013 creates the table. PersonaService implements 8 async methods with key business rules: `activate()` deactivates all then activates one (single-active constraint), `delete()` auto-activates first remaining if the deleted persona was active. All methods are user-scoped with ownership checks. 20 unit tests pass covering all CRUD, activation, authorization, and state save paths.

### T02: API Routes and Sidebar UI
Created dual-router pattern (api_router + browser_router) with 7 API endpoints and 1 htmx partial route. The list endpoint returns metadata only (no layout_json) to keep payloads small; GET by ID returns the full payload. PersonaService wired into app.state in main.py. The persona selector partial renders in the sidebar user popover between "Layouts" and the theme row, loading eagerly via hx-trigger="load". Active persona shown with check-circle icon and accent color.

### T03: Frontend Persona Lifecycle
Implemented the complete frontend persona lifecycle in workspace.js:
- `initPersonas()` auto-creates "Default" persona on first load if none exist
- `saveCurrentPersonaState()` captures dockview JSON + localStorage panel positions + explorer mode
- `switchPersona(id)` saves current → fetches target → activates → applies layout/positions/mode with `_switchingPersona` guard preventing localStorage overwrites during `dv.fromJSON()`
- `createNewPersona()` saves current state then creates new with current workspace config
- Command palette has three entries with dynamic submenu for persona switching
- `beforeunload` fires `navigator.sendBeacon` for reliable state save on tab close
- `window._switchingPersona` bridges the guard flag to workspace-layout.js (separate IIFE)

## Verification

| # | Check | Method | Result |
|---|-------|--------|--------|
| 1 | PersonaService CRUD + constraints | 20 pytest unit tests | ✅ 20/20 pass (0.47s) |
| 2 | JS syntax valid | `node -c workspace.js`, `node -c workspace-layout.js` | ✅ both pass |
| 3 | API list returns JSON array | `GET /api/personas` | ✅ returns persona list with metadata |
| 4 | API create + auto-activate | `POST /api/personas` | ✅ 201 with auto-activated persona |
| 5 | API get full payload | `GET /api/personas/{id}` | ✅ includes layout_json, sidebar_positions_json, explorer_mode |
| 6 | API update name | `PUT /api/personas/{id}` | ✅ name updated |
| 7 | API save state | `POST /api/personas/{id}/save-state` | ✅ state fields updated |
| 8 | API activate | `POST /api/personas/{id}/activate` | ✅ persona activated |
| 9 | API delete | `DELETE /api/personas/{id}` | ✅ 204 No Content |
| 10 | 404 on nonexistent | `GET /api/personas/00000000-...` | ✅ `{"detail":"Persona not found"}` |
| 11 | Browser selector partial | `GET /browser/personas/selector` | ✅ HTML with persona list, active indicator, action buttons |
| 12 | Sidebar persona selector | Browser: click user avatar | ✅ PERSONAS section with Default + Research Mode, active indicator, Save/+ buttons |
| 13 | Command palette entries | Browser: F1 → type "Persona" | ✅ Shows Switch To..., Save Current, Create New... |
| 14 | Guard flag bridge | grep workspace-layout.js | ✅ `window._switchingPersona` check in onDidLayoutChange |

## Requirements Advanced

- PERSONA-01 — Named personas with full CRUD: create, rename (PUT), delete with auto-activate-remaining
- PERSONA-02 — Persona switching restores dockview layout (fromJSON with try/catch), sidebar positions, and explorer mode
- PERSONA-03 — Persona selector renders in user popover menu between Layouts and theme row
- PERSONA-04 — Three persona commands in Ctrl+K command palette with dynamic submenu for switch
- PERSONA-05 — Default persona auto-created on first workspace load when no personas exist

## Requirements Validated

- PERSONA-01 — 20 unit tests + 7 API endpoints verified via curl + browser selector UI confirmed
- PERSONA-02 — switchPersona() applies layout_json, sidebar_positions_json, explorer_mode; guard flag prevents localStorage corruption; reload preserves active persona
- PERSONA-03 — Sidebar popover screenshot shows PERSONAS section with active indicator
- PERSONA-04 — Command palette screenshot shows all three persona commands with drill-down submenu
- PERSONA-05 — initPersonas() creates Default persona when API returns empty list; verified in browser console

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- **ninja-keys children array**: Plan assumed empty `children: []` on parent would auto-discover children by `parent` property. In practice, ninja-keys requires child IDs in the parent's `children` array for drill-down navigation. `_refreshPersonaPaletteItems` was updated to populate both child items and parent's children array.
- **Cross-IIFE guard flag**: Plan didn't explicitly call out the IIFE boundary between workspace.js and workspace-layout.js. The `_switchingPersona` guard needed `window.*` exposure for cross-file access.

## Known Limitations

- **Layout-only personas** — Personas store dockview layout, sidebar positions, and explorer mode only. No theme, font size, or other settings. By design for v1 (D155).
- **Explicit save only** — No auto-save to server on layout changes. Save occurs on explicit Save action, persona switch, and beforeunload. localStorage auto-save continues independently for crash recovery (D157).
- **No E2E Playwright tests** — Deferred to S04 (trailing E2E + docs slice).
- **No user guide documentation** — Deferred to S04.

## Follow-ups

- S04 should write Playwright E2E tests covering persona create → save → switch → reload flow
- S04 should create `docs/guide/30-personas.md` with persona creation, switching, and management guide
- Future consideration: debounced auto-save to server if users request (D157 revisable)
- Future consideration: settings overrides (theme, font size) per persona (D155 revisable)

## Files Created/Modified

- `backend/app/persona/__init__.py` — empty module init
- `backend/app/persona/models.py` — Persona SQLAlchemy model (9 columns, users FK)
- `backend/app/persona/service.py` — PersonaService with 8 async CRUD/activation/state methods
- `backend/app/persona/router.py` — REST API (7 endpoints) + browser route for persona selector
- `backend/migrations/versions/013_personas.py` — Alembic migration creating personas table
- `backend/app/main.py` — PersonaService instantiation + router registration
- `backend/app/templates/components/_persona_selector.html` — htmx partial with persona list, active indicator, action buttons
- `backend/app/templates/components/_sidebar.html` — persona selector container added to user popover
- `backend/tests/test_persona_service.py` — 20 unit tests covering all service operations
- `frontend/static/js/workspace.js` — persona state variables, init, save, switch, create, command palette, beforeunload
- `frontend/static/js/workspace-layout.js` — _switchingPersona guard in onDidLayoutChange
- `frontend/static/css/workspace.css` — persona selector styling (header, list, items, save button, empty state)

## Forward Intelligence

### What the next slice should know
- Persona API is at `/api/personas` with standard CRUD. List returns metadata only (id, name, is_active, created_at). GET by ID returns full payload including layout_json.
- The selector partial at `/browser/personas/selector` is loaded eagerly in the sidebar popover. It calls `switchPersona()`, `createNewPersona()`, and `saveCurrentPersonaState()` JS functions.
- Command palette persona entries follow the layout palette pattern — `_refreshPersonaPaletteItems(ninja)` dynamically populates the submenu.

### What's fragile
- **dv.fromJSON() reliability** — Layout restore is wrapped in try/catch with toast fallback, but if panel types change between save and restore, some panels may not restore. This is a known dockview limitation.
- **beforeunload sendBeacon** — Browser may not send the beacon in all cases (e.g., process kill, crash). State may be stale on next load. localStorage continues as independent crash recovery.
- **ninja-keys children array** — Must be kept in sync manually. If `_refreshPersonaPaletteItems` fails, the submenu will be empty.

### Authoritative diagnostics
- `GET /api/personas` — shows all personas for current user with active indicator
- `sqlite3 backend/data/sempkm.db "SELECT id, name, is_active FROM personas"` — direct DB inspection
- Browser console: search for "SemPKM: persona" to see init/switch/save logs
- `python -m pytest tests/test_persona_service.py -v` — 20 tests validate service layer

### What assumptions changed
- **ninja-keys parent/children relationship** — Originally assumed children auto-discovered by parent property. Actual behavior requires explicit children array on parent. Documented in KNOWLEDGE.md.
- **Cross-IIFE communication** — Originally assumed guard flags could be shared within workspace. Actual architecture has separate IIFEs requiring window.* bridging. Documented in KNOWLEDGE.md.
