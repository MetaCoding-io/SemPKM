---
estimated_steps: 6
estimated_files: 6
---

# T02: DASHBOARDS explorer section and edit-from-dashboard wiring

**Slice:** S04 — Dashboard Builder UI & Explorer Integration
**Milestone:** M006

## Description

Add a DASHBOARDS section to the explorer sidebar so users can discover and open their dashboards. Add a `dashboardsRefreshed` htmx trigger event so the section auto-refreshes when dashboards are created or deleted. Wire an edit button on the rendered dashboard page to re-open the builder.

## Steps

1. Add `GET /browser/dashboard/explorer` route to `dashboard/router.py` — calls `DashboardService.list_for_user()`, renders `dashboard_explorer.html` partial.
2. Create `dashboard_explorer.html` partial — clickable leaf nodes for each dashboard calling `openDashboardTab(id, name)`, plus a "+ New Dashboard" link/button calling `openDashboardBuilderTab()`. Show "No dashboards yet" when list is empty.
3. Include DASHBOARDS section in `workspace.html` between MY VIEWS and SHARED sections. Use same `explorer-section` pattern as FAVORITES: `hx-get="/browser/dashboard/explorer"`, `hx-trigger="load, dashboardsRefreshed from:body"`.
4. Add `HX-Trigger: dashboardsRefreshed` response header to POST `/api/dashboard` and DELETE `/api/dashboard/{id}` endpoints. Since these return JSON (not htmx), the builder's `fetch()` success handler must manually dispatch `htmx.trigger(document.body, 'dashboardsRefreshed')` after a successful create/delete.
5. Add an edit button to `dashboard_page.html` header — small pencil icon button calling `openDashboardBuilderTab(dashboardId)`. Follow existing panel-btn pattern with Lucide icon.
6. Add tests for the explorer endpoint to `test_dashboard_builder.py`.

## Must-Haves

- [ ] DASHBOARDS section appears in explorer sidebar
- [ ] Section lists user's dashboards as clickable leaf nodes
- [ ] Clicking a dashboard opens it in a workspace tab
- [ ] "+ New Dashboard" button opens the builder in create mode
- [ ] Section refreshes when a dashboard is created or deleted
- [ ] Edit button on rendered dashboard opens builder in edit mode
- [ ] Explorer endpoint tests pass

## Verification

- `cd backend && python -m pytest tests/test_dashboard_builder.py -v` — all tests pass
- Docker: DASHBOARDS section visible in explorer, create a dashboard → it appears, delete → it disappears, edit button opens builder

## Observability Impact

- **New signal:** `dashboardsRefreshed` htmx event on `document.body` — fires after dashboard create/update, triggers explorer section reload
- **Inspection:** `GET /browser/dashboard/explorer` returns HTML partial listing all user dashboards — useful for verifying the explorer content server-side
- **Failure visibility:** Explorer route returns empty state ("No dashboards yet") rather than erroring when no dashboards exist; fetch errors in builder save still surface via `#builder-error` and console
- **Future agent:** Check `#dashboards-tree` innerHTML in browser to see current explorer state; `hx-trigger` attribute on that element confirms event wiring

## Inputs

- `backend/app/dashboard/router.py` — service wiring, API endpoints (from S03 + T01)
- `backend/app/templates/browser/partials/favorites_section.html` — explorer section pattern
- `backend/app/templates/browser/workspace.html` — sidebar structure
- `frontend/static/js/workspace.js` — `openDashboardTab()`, `openDashboardBuilderTab()` (from T01)
- `backend/app/templates/browser/dashboard_page.html` — rendered dashboard template (from S03)

## Expected Output

- `backend/app/templates/browser/dashboard_explorer.html` — new partial
- `backend/app/templates/browser/workspace.html` — DASHBOARDS section included
- `backend/app/templates/browser/dashboard_page.html` — edit button added
- `backend/app/dashboard/router.py` — explorer route added
- `frontend/static/js/workspace.js` — `dashboardsRefreshed` trigger dispatch in builder save handler
- `backend/tests/test_dashboard_builder.py` — explorer tests added
