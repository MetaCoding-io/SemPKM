---
id: S04
parent: M006
milestone: M006
provides:
  - Dashboard builder form (create and edit modes) with layout picker and dynamic block configuration
  - openDashboardBuilderTab() JS function and dashboard-builder specialType routing
  - DASHBOARDS explorer section in workspace sidebar with auto-refresh
  - Edit button on rendered dashboard pages
  - Explorer route (GET /browser/dashboard/explorer)
requires:
  - slice: S03
    provides: DashboardService CRUD, LAYOUT_DEFINITIONS, openDashboardTab(), block rendering infrastructure
  - slice: S02
    provides: Consolidated explorer template pattern (adds dashboard folder to it)
affects:
  - S07
key_files:
  - backend/app/dashboard/router.py
  - backend/app/templates/browser/dashboard_builder.html
  - backend/app/templates/browser/dashboard_explorer.html
  - backend/app/templates/browser/dashboard_page.html
  - backend/app/templates/browser/workspace.html
  - frontend/static/js/workspace.js
  - frontend/static/js/workspace-layout.js
  - frontend/static/css/workspace.css
  - backend/tests/test_dashboard_builder.py
key_decisions:
  - "D103: Builder uses fetch() with JSON body to POST/PATCH existing JSON API — htmx form encoding doesn't map to nested JSON"
  - "D104: Explorer refresh via htmx.trigger() JS dispatch instead of HX-Trigger header — JSON API responses aren't htmx-processed"
  - Builder uses inline script in template (same pattern as other partials)
  - Explorer route placed before /{dashboard_id} routes to avoid path conflict
  - Dashboard page gained header bar with title + edit button
patterns_established:
  - dashboard-builder specialType in workspace-layout.js with dashboardId param routing
  - dashboardsRefreshed custom htmx event pattern (same as favoritesRefreshed D048)
  - Block row dynamic creation with type-specific config field switching via onchange
observability_surfaces:
  - "#builder-error" element shows last save error message
  - fetch() errors logged to browser console with "Dashboard save error:" prefix
  - "#builder-saving" indicator visible during save operation
  - GET /browser/dashboard/explorer — HTML partial showing current dashboard list
  - dashboardsRefreshed event on document.body fires on create/update
drill_down_paths:
  - .gsd/milestones/M006/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M006/slices/S04/tasks/T02-SUMMARY.md
duration: 70m
verification_result: passed
completed_at: 2026-03-15
---

# S04: Dashboard Builder UI & Explorer Integration

**Form-based dashboard builder with layout picker, dynamic block configuration, and DASHBOARDS explorer section — users can create, edit, and discover dashboards entirely through the workspace UI.**

## What Happened

**T01** added the core builder form. Two new browser routes (`GET /browser/dashboard/new` and `GET /browser/dashboard/{id}/edit`) render `dashboard_builder.html` with layout picker (radio buttons for all 5 grid layouts with slot previews), dynamic block rows (add/remove, type select, type-specific config fields shown/hidden via JS onchange), and a fetch()-based save handler that POSTs or PATCHes the JSON API. On success, the rendered dashboard opens in a tab and the builder tab closes. On failure, error messages display inline. `openDashboardBuilderTab()` was added to workspace.js and `dashboard-builder` specialType routing to workspace-layout.js.

**T02** wired explorer integration. A `GET /browser/dashboard/explorer` route returns an HTML partial listing all user dashboards as clickable tree-leaf nodes. A DASHBOARDS section was added to workspace.html between MY VIEWS and SHARED, using `hx-trigger="load, dashboardsRefreshed from:body"` for auto-refresh. The builder's fetch() success handler dispatches `htmx.trigger(document.body, 'dashboardsRefreshed')` so the explorer updates after creates. A header bar with title and pencil edit button was added to `dashboard_page.html`.

## Verification

- `backend/tests/test_dashboard_builder.py` — 9/9 tests pass (6 builder + 3 explorer)
- Zero conflict markers: `grep -rn "^<<<<<<< " backend/ frontend/` returns empty
- Docker browser: created dashboard through builder → renders correctly → appears in explorer
- Docker browser: edit mode pre-populates form from existing dashboard
- Docker browser: empty name submission → inline error "Name is required."
- Docker browser: `GET /api/dashboard` returns created dashboards with IDs
- Docker browser: edit button (pencil) on dashboard page opens builder in edit mode
- Docker browser: "+ New Dashboard" action in explorer opens builder

## Requirements Advanced

- DASH-01 (Dashboard Builder UI) — user can create and edit dashboards through form-based UI in workspace
- DASH-02 (Dashboard Explorer) — dashboards appear in explorer sidebar with auto-refresh on create

## Requirements Validated

- none (dashboard requirements are new — will be formally added when milestone completes)

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- T02 plan called for `HX-Trigger: dashboardsRefreshed` response header on POST/DELETE JSON API endpoints. Since these return JSON (not htmx-processed responses), the header wouldn't fire. Used `htmx.trigger()` JS dispatch in the fetch() success handler instead — functionally equivalent (D104).
- Delete-triggered explorer refresh not wired yet — delete UI doesn't exist. When delete is added (S07), it should dispatch the same `dashboardsRefreshed` event.

## Known Limitations

- No delete dashboard UI — users can only delete via API (`DELETE /api/dashboard/{id}`). Delete UI deferred to S07.
- No drag-and-drop block reordering in builder — blocks are added sequentially. Acceptable for v1.
- View-embed spec dropdown only shows views from `/browser/views/available` — if that endpoint is slow or returns many items, the dropdown could be unwieldy.

## Follow-ups

- S07: Wire delete UI with `dashboardsRefreshed` event dispatch
- S07: Consider adding dashboard description display in explorer hover/tooltip

## Files Created/Modified

- `backend/app/dashboard/router.py` — added builder routes (new, edit) and explorer route
- `backend/app/templates/browser/dashboard_builder.html` — new builder form template
- `backend/app/templates/browser/dashboard_explorer.html` — new explorer partial
- `backend/app/templates/browser/dashboard_page.html` — added header bar with edit button
- `backend/app/templates/browser/workspace.html` — added DASHBOARDS explorer section
- `frontend/static/js/workspace.js` — added `openDashboardBuilderTab()` function
- `frontend/static/js/workspace-layout.js` — added `dashboard-builder` specialType routing
- `frontend/static/css/workspace.css` — added builder CSS (layout picker, block rows, config fields)
- `backend/tests/test_dashboard_builder.py` — new test file with 9 tests

## Forward Intelligence

### What the next slice should know
- The builder's fetch() success handler pattern (dispatch htmx event + open tab + close builder) is reusable for the workflow builder in S07
- `openDashboardBuilderTab(dashboardId)` follows the same pattern as `openDashboardTab(id, name)` — S07 should mirror this for workflows
- Explorer section pattern (`hx-trigger="load, {event} from:body"`) is the same as FAVORITES (D048) — reuse for WORKFLOWS section

### What's fragile
- Explorer route order in `dashboard/router.py` — `/explorer` must be registered before `/{dashboard_id}` to avoid FastAPI treating "explorer" as a dashboard ID. Same will apply for any new string-path routes.
- View-embed spec dropdown fetches from `/browser/views/available` lazily — if that endpoint changes or adds auth requirements, the builder's dropdown will silently break

### Authoritative diagnostics
- `GET /browser/dashboard/explorer` — returns current dashboard list HTML; inspect for content/empty state
- `#builder-error` element — shows last save error; check `.textContent` for debugging
- Browser console: search "Dashboard save error:" for fetch failures

### What assumptions changed
- Originally planned HX-Trigger header on JSON API responses — doesn't work because htmx only processes headers from htmx-initiated requests. JS dispatch is the correct pattern for fetch()-based forms.
