---
id: T02
parent: S03
milestone: M012
provides:
  - REST API for persona CRUD (7 endpoints) at /api/personas
  - Browser route GET /browser/personas/selector returning htmx partial
  - PersonaService wired into FastAPI app.state
  - Persona selector UI in user popover with active indicator
  - CSS styling for persona selector matching popover design language
key_files:
  - backend/app/persona/router.py
  - backend/app/templates/components/_persona_selector.html
  - backend/app/templates/components/_sidebar.html
  - backend/app/main.py
  - frontend/static/css/workspace.css
key_decisions:
  - Auto-activate newly created personas (POST creates then immediately activates)
  - List endpoint returns metadata only (id, name, is_active, created_at) — no layout_json to keep payloads small
  - GET by ID returns full payload (with layout_json, sidebar_positions_json, explorer_mode)
  - Persona selector loads eagerly via hx-trigger="load" rather than on popover toggle
patterns_established:
  - Persona router follows dashboard dual-router pattern (browser_router + api_router)
  - Cookie name is sempkm_session for all API auth testing
observability_surfaces:
  - GET /api/personas returns persona list with active indicator for inspection
  - POST/activate/delete logged at INFO level via logger.getLogger(__name__)
  - 404 with {"detail":"Persona not found"} on bad ID or wrong user
  - 204 No Content on successful delete
duration: 25m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T02: API routes, sidebar persona selector, and main.py wiring

**Added persona REST API (7 endpoints), htmx browser route for selector partial, and sidebar popover integration with active-persona indicator**

## What Happened

All T02 deliverables were already implemented in a prior session. This session verified correctness against the task plan:

1. **Router** (`backend/app/persona/router.py`): 7 API endpoints on `api_router` (prefix `/api/personas`) — list, create, get-by-id, update name, delete, activate, save-state. Plus 1 browser route on `browser_router` (`GET /browser/personas/selector`) returning the htmx partial. Follows the dashboard dual-router pattern with `_get_persona_service()` helper and `Depends(get_current_user)` on all routes.

2. **main.py wiring**: `PersonaService` instantiated from `async_session_factory` and stored on `app.state.persona_service`. Both routers imported and registered alongside dashboard/workflow routers.

3. **Persona selector partial** (`_persona_selector.html`): Renders persona list with active indicator (check-circle vs circle icons), "New Persona" button, and "Save Current" button. Calls `switchPersona()`, `createNewPersona()`, `saveCurrentPersonaState()` JS functions (defined in T03). Uses `hx-on::after-settle` to render Lucide icons after htmx swap.

4. **Sidebar integration** (`_sidebar.html`): Persona selector container added between "Layouts" and theme row in user popover, loading eagerly via `hx-get="/browser/personas/selector" hx-trigger="load"`.

5. **CSS** (`workspace.css`): Full persona selector styling — header with uppercase title, action button with flex-shrink:0 SVG sizing per CLAUDE.md rules, scrollable list, active state with accent color, save button, empty state.

## Verification

All 7 API endpoints tested via curl against running Docker instance:
- `GET /api/personas` → `[]` (empty list for user with no personas)
- `POST /api/personas` → 201 with created+activated persona (metadata only excluded layout_json from list, included in create response)
- `GET /api/personas/{id}` → full payload with layout_json, sidebar_positions_json, explorer_mode
- `PUT /api/personas/{id}` → updated name
- `POST /api/personas/{id}/save-state` → updated layout_json and explorer_mode
- `POST /api/personas/{id}/activate` → activated persona
- `DELETE /api/personas/{id}` → 204 No Content
- `GET /api/personas/00000000-...` → 404 with `{"detail":"Persona not found"}`
- `GET /browser/personas/selector` → HTML partial with persona list, active indicator, lucide icon rendering

Unit tests: 20/20 pass (T01 tests still green).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -m pytest tests/test_persona_service.py -v --tb=short` | 0 | ✅ pass | 0.5s |
| 2 | `curl GET /api/personas` (empty) | 0 | ✅ pass | <1s |
| 3 | `curl POST /api/personas {"name":"Test T02"}` (201) | 0 | ✅ pass | <1s |
| 4 | `curl GET /api/personas/{id}` (full payload) | 0 | ✅ pass | <1s |
| 5 | `curl PUT /api/personas/{id} {"name":"Renamed"}` | 0 | ✅ pass | <1s |
| 6 | `curl POST /api/personas/{id}/save-state` | 0 | ✅ pass | <1s |
| 7 | `curl POST /api/personas/{id}/activate` | 0 | ✅ pass | <1s |
| 8 | `curl DELETE /api/personas/{id}` (204) | 0 | ✅ pass | <1s |
| 9 | `curl GET /api/personas/00000000-...` (404) | 0 | ✅ pass | <1s |
| 10 | `curl GET /browser/personas/selector` (HTML partial) | 0 | ✅ pass | <1s |

## Diagnostics

- **API inspection:** `curl -b "sempkm_session=$TOKEN" http://localhost:8001/api/personas | python3 -m json.tool`
- **Full persona data:** `curl -b "sempkm_session=$TOKEN" http://localhost:8001/api/personas/{id}`
- **Selector partial:** `curl -b "sempkm_session=$TOKEN" http://localhost:8001/browser/personas/selector`
- **DB table:** `sqlite3 backend/sempkm.db "SELECT id, name, is_active FROM personas"`
- **Logs:** Router logs at INFO for create/activate/delete, WARNING for auth failures

## Deviations

None — all files were already implemented matching the plan. Prior session had completed all code; this session verified correctness.

## Known Issues

None.

## Files Created/Modified

- `backend/app/persona/router.py` — REST API (7 endpoints) + browser route for persona selector
- `backend/app/main.py` — PersonaService instantiation + router registration (already wired)
- `backend/app/templates/components/_persona_selector.html` — htmx partial with persona list, active indicator, action buttons
- `backend/app/templates/components/_sidebar.html` — persona selector container added to user popover
- `frontend/static/css/workspace.css` — persona selector CSS (header, list, items, save button, empty state)
