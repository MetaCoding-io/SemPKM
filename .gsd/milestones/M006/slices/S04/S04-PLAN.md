# S04: Dashboard Builder UI & Explorer Integration

**Goal:** Users can create and edit dashboards through a form-based UI in the workspace, and dashboards appear in the explorer sidebar.
**Demo:** Click "New Dashboard" in the DASHBOARDS explorer section → builder tab opens with layout picker, block configuration rows → save → dashboard renders in a new tab → dashboard appears in explorer.

## Must-Haves

- Form-based dashboard builder opens in a workspace tab (create and edit modes)
- Layout picker with visual labels for all 5 layouts
- Dynamic block configuration rows: add/remove blocks, pick type, configure type-specific fields
- Block type config: view-embed (spec_iri + renderer_type), markdown (content), create-form (target_class), object-embed (object_iri), sparql-result (query), divider (no config)
- Slot assignment per block matching selected layout
- Builder submits via `fetch()` to existing JSON API (POST for create, PATCH for edit)
- On successful save, opens the dashboard tab and closes the builder tab
- DASHBOARDS section in explorer sidebar with lazy-loaded list
- Explorer refreshes after create/delete via custom htmx trigger event
- Edit action accessible from existing dashboards (re-opens builder in edit mode)

## Proof Level

- This slice proves: integration
- Real runtime required: yes (needs triplestore for view-embed dropdowns, DB for dashboard CRUD)
- Human/UAT required: no

## Verification

- `backend/tests/test_dashboard_builder.py` — unit tests for new builder routes (GET /new, GET /{id}/edit, GET /explorer)
- Docker manual check: create a dashboard through the builder, verify it renders, verify it appears in explorer
- Zero conflict markers: `grep -rn "^<<<<<<< " backend/ frontend/ --include="*.py" --include="*.html" --include="*.js" --include="*.css"` returns empty
- Failure-path: submit builder with empty name → API returns 400, builder shows error message inline (no silent failure)
- Diagnostic: `GET /api/dashboard` returns full list of created dashboards with IDs for inspection

## Observability / Diagnostics

- Runtime signals: builder form validation errors shown inline; fetch() errors surface as user-visible error messages
- Inspection surfaces: `GET /api/dashboard` lists all dashboards; browser console shows fetch errors
- Failure visibility: JSON API returns 400/422 with detail message on validation failure; builder displays these to user
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `DashboardService` CRUD (S03), `LAYOUT_DEFINITIONS` (S03), `openDashboardTab()` (S03), `available_views` endpoint (S02), explorer section pattern (FAVORITES partial)
- New wiring introduced: `dashboard-builder` specialType in workspace-layout.js, `openDashboardBuilderTab()` in workspace.js, DASHBOARDS explorer section in workspace.html
- What remains before the milestone is truly usable end-to-end: S05 (cross-view context), S07 (workflow builder + final integration)

## Tasks

- [x] **T01: Dashboard builder form — routes, template, and tab integration** `est:2h`
  - Why: Core of S04 — without the builder form, users can only create dashboards via raw API calls. This adds the full create/edit UI.
  - Files: `backend/app/dashboard/router.py`, `backend/app/templates/browser/dashboard_builder.html`, `frontend/static/js/workspace.js`, `frontend/static/js/workspace-layout.js`, `frontend/static/css/workspace.css`, `backend/tests/test_dashboard_builder.py`
  - Do: Add `GET /browser/dashboard/new` and `GET /browser/dashboard/{id}/edit` routes. Create `dashboard_builder.html` template with layout picker (radio buttons for 5 layouts with slot preview), dynamic block rows (add/remove, type select, type-specific config fields shown/hidden by JS), and submit handler using `fetch()` to POST/PATCH the JSON API. Add `openDashboardBuilderTab()` to workspace.js. Add `dashboard-builder` specialType routing in workspace-layout.js. Add builder-specific CSS. Write unit tests for the new routes.
  - Verify: `cd backend && python -m pytest tests/test_dashboard_builder.py -v` passes; Docker: navigate to builder, configure a dashboard, save, verify it opens
  - Done when: Builder form renders in both create and edit modes, saves successfully via JSON API, opens dashboard tab on success

- [x] **T02: DASHBOARDS explorer section and edit-from-dashboard wiring** `est:45m`
  - Why: Dashboards need to be discoverable in the sidebar, and editable from their rendered view. Without this, users have no way to find or re-edit their dashboards.
  - Files: `backend/app/dashboard/router.py`, `backend/app/templates/browser/dashboard_explorer.html`, `backend/app/templates/browser/workspace.html`, `backend/app/templates/browser/dashboard_page.html`, `frontend/static/js/workspace.js`, `backend/tests/test_dashboard_builder.py`
  - Do: Add `GET /browser/dashboard/explorer` route returning dashboard list HTML. Create `dashboard_explorer.html` partial with clickable leaf nodes calling `openDashboardTab()` and a "+ New" button calling `openDashboardBuilderTab()`. Include as a new explorer section in workspace.html between MY VIEWS and SHARED. Add `dashboardsRefreshed` htmx trigger event on create/delete API responses. Wire `HX-Trigger` header on POST/DELETE dashboard API endpoints. Add edit button to `dashboard_page.html` header calling `openDashboardBuilderTab(id)`. Add tests for explorer endpoint.
  - Verify: `cd backend && python -m pytest tests/test_dashboard_builder.py -v` passes; Docker: dashboards appear in explorer, clicking opens them, creating a new one refreshes the list
  - Done when: DASHBOARDS section appears in explorer, lists user's dashboards, refreshes on create/delete, edit button on dashboard page opens builder

## Files Likely Touched

- `backend/app/dashboard/router.py` — new builder + explorer routes
- `backend/app/templates/browser/dashboard_builder.html` — new builder form template
- `backend/app/templates/browser/dashboard_explorer.html` — new explorer partial
- `backend/app/templates/browser/dashboard_page.html` — add edit button
- `backend/app/templates/browser/workspace.html` — include DASHBOARDS section
- `frontend/static/js/workspace.js` — `openDashboardBuilderTab()` function
- `frontend/static/js/workspace-layout.js` — `dashboard-builder` specialType routing
- `frontend/static/css/workspace.css` — builder form styles
- `backend/tests/test_dashboard_builder.py` — new test file
