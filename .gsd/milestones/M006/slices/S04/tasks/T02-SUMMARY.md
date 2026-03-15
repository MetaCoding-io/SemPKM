---
id: T02
parent: S04
milestone: M006
provides:
  - DASHBOARDS explorer section in workspace sidebar
  - dashboardsRefreshed htmx event for auto-refresh
  - Edit button on rendered dashboard pages
  - Explorer route (GET /browser/dashboard/explorer)
key_files:
  - backend/app/dashboard/router.py
  - backend/app/templates/browser/dashboard_explorer.html
  - backend/app/templates/browser/workspace.html
  - backend/app/templates/browser/dashboard_page.html
  - backend/app/templates/browser/dashboard_builder.html
  - backend/tests/test_dashboard_builder.py
key_decisions:
  - Explorer route placed before /{dashboard_id} routes in router to avoid path conflict
  - Used htmx.trigger() dispatch from builder fetch() success handler instead of HX-Trigger header (JSON API endpoints don't return htmx-processed responses)
  - Dashboard page gained a header bar with title + edit button (previously had no header)
patterns_established:
  - dashboardsRefreshed custom htmx event pattern — same approach as favoritesRefreshed
  - Explorer section with hx-trigger="load, dashboardsRefreshed from:body" for event-driven refresh
observability_surfaces:
  - GET /browser/dashboard/explorer — HTML partial showing current dashboard list
  - dashboardsRefreshed event on document.body fires on create/update
  - "#dashboards-tree" element innerHTML shows current explorer state
duration: 25m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: DASHBOARDS explorer section and edit-from-dashboard wiring

**Added DASHBOARDS explorer section with auto-refresh, clickable dashboard leaf nodes, "+ New Dashboard" action, and pencil edit button on rendered dashboard pages.**

## What Happened

Added `GET /browser/dashboard/explorer` route to `dashboard/router.py` that calls `DashboardService.list_for_user()` and renders a new `dashboard_explorer.html` partial. The partial lists each dashboard as a clickable `tree-leaf` node calling `openDashboardTab(id, name)`, shows "No dashboards yet" when empty, and always includes a "+ New Dashboard" action calling `openDashboardBuilderTab()`.

Included a new DASHBOARDS explorer section in `workspace.html` between MY VIEWS and SHARED, using the same pattern as FAVORITES: `hx-trigger="load, dashboardsRefreshed from:body"` on the section body.

Added `htmx.trigger(document.body, 'dashboardsRefreshed')` to the builder's `fetch()` success handler in `dashboard_builder.html` so the explorer auto-refreshes when a dashboard is created or updated.

Added a header bar to `dashboard_page.html` with the dashboard name and a pencil edit button (`panel-btn` pattern with Lucide icon) that calls `openDashboardBuilderTab(dashboardId)`.

Added three tests to `test_dashboard_builder.py` for the explorer endpoint: empty state, listing dashboards, and new dashboard button.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_dashboard_builder.py -v` — 9/9 passed (6 existing + 3 new explorer tests)
- `grep -rn "^<<<<<<< " backend/ frontend/ --include="*.py" --include="*.html" --include="*.js" --include="*.css"` — zero conflict markers
- Browser: DASHBOARDS section visible in explorer sidebar
- Browser: Created "Test Explorer Dashboard" via builder → appeared in explorer after save (dashboardsRefreshed event fired)
- Browser: Edit button (pencil icon) visible on dashboard page → clicked → builder opened in edit mode with correct name pre-populated
- Browser: "+ New Dashboard" action visible and calls openDashboardBuilderTab()

### Slice-level verification status (T02 is final task):
- [x] `test_dashboard_builder.py` — 9/9 tests pass
- [x] Docker: create dashboard through builder, verify it renders, verify it appears in explorer
- [x] Zero conflict markers
- [x] Failure-path: submit builder with empty name → API returns 400, builder shows error message inline (verified in T01)
- [x] Diagnostic: `GET /api/dashboard` returns full list of created dashboards

## Diagnostics

- `GET /browser/dashboard/explorer` — returns HTML partial of current dashboard list
- `#dashboards-tree` element — inspect innerHTML to see explorer section content
- `dashboardsRefreshed` event — dispatched on `document.body` after create/update; listen via `document.body.addEventListener('dashboardsRefreshed', ...)`
- `.dashboard-header .panel-btn` — edit button on rendered dashboard pages

## Deviations

- Plan called for `HX-Trigger: dashboardsRefreshed` response header on POST/DELETE endpoints, but since these are JSON API endpoints consumed by `fetch()` (not htmx), the header wouldn't be processed. Used `htmx.trigger()` JS dispatch in the success handler instead — functionally equivalent.
- Delete UI doesn't exist yet, so `dashboardsRefreshed` is only wired for create/update. When delete UI is added, it should similarly dispatch the event.

## Known Issues

None.

## Files Created/Modified

- `backend/app/dashboard/router.py` — added `GET /browser/dashboard/explorer` route
- `backend/app/templates/browser/dashboard_explorer.html` — new partial: dashboard list with leaf nodes and "+ New Dashboard" action
- `backend/app/templates/browser/workspace.html` — added DASHBOARDS explorer section between MY VIEWS and SHARED
- `backend/app/templates/browser/dashboard_page.html` — added header bar with dashboard name and pencil edit button
- `backend/app/templates/browser/dashboard_builder.html` — added `htmx.trigger(document.body, 'dashboardsRefreshed')` in save success handler
- `backend/tests/test_dashboard_builder.py` — added `TestDashboardExplorer` class with 3 tests
- `.gsd/milestones/M006/slices/S04/tasks/T02-PLAN.md` — added Observability Impact section
