---
estimated_steps: 9
estimated_files: 9
---

# T01: Workflow builder UI, explorer section, and delete wiring

**Slice:** S07 — Workflow Builder UI & Final Integration
**Milestone:** M006

## Description

Build the workflow builder form template (mirroring dashboard builder), workflow explorer section, delete UI for both dashboards and workflows, and all JS/route wiring. This is the single code-delivery task for S07 — all pieces must exist together to be testable.

## Steps

1. Add `/explorer`, `/new`, and `/{id}/edit` browser routes to `workflow/router.py` — register them BEFORE the existing `/{workflow_id}/run` route to avoid FastAPI path capture. Explorer returns HTML partial listing workflows. New/edit return the builder form template.
2. Create `workflow_builder.html` template mirroring `dashboard_builder.html`. Name input, dynamic step rows with type select (view/dashboard/form) and type-specific config fields (view: spec_iri dropdown + renderer select; dashboard: dashboard_id dropdown; form: target_class input). fetch()-based save to `POST /api/workflow` (create) or `PATCH /api/workflow/{id}` (edit). On success: dispatch `workflowsRefreshed`, open the workflow runner tab, close builder tab.
3. Create `workflow_explorer.html` template mirroring `dashboard_explorer.html`. List workflows as `.tree-leaf` nodes with `openWorkflowTab()` click handlers. Include "+ New Workflow" action leaf calling `openWorkflowBuilderTab()`.
4. Add WORKFLOWS section to `workspace.html` after DASHBOARDS section, before SHARED. Same pattern: `hx-get="/browser/workflow/explorer"` with `hx-trigger="load, workflowsRefreshed from:body"`.
5. Add `openWorkflowBuilderTab(workflowId)` to `workspace.js` mirroring `openDashboardBuilderTab()`. Uses `special-panel` component with `specialType: 'workflow-builder'`.
6. Add `workflow-builder` specialType handling to `workspace-layout.js` — route to `/browser/workflow/new` (create) or `/browser/workflow/{id}/edit` (edit).
7. Add delete buttons (trash icon with `onclick`) to both `dashboard_explorer.html` and `workflow_explorer.html`. Use `window.confirm()` → `fetch(DELETE /api/{dashboard|workflow}/{id})` → dispatch `{dashboardsRefreshed|workflowsRefreshed}` on success. Stop propagation to prevent opening the item.
8. Add builder CSS to `workspace.css` — step row styling, type config fields, reuse existing builder patterns.
9. Write `test_workflow_builder.py` — test builder routes (new, edit, edit-404), explorer route, following the `test_dashboard_builder.py` pattern.

## Must-Haves

- [ ] Workflow builder form creates workflows via `POST /api/workflow`
- [ ] Workflow builder form edits workflows via `PATCH /api/workflow/{id}`
- [ ] WORKFLOWS explorer section loads and auto-refreshes on `workflowsRefreshed`
- [ ] `openWorkflowBuilderTab()` opens builder in workspace tab
- [ ] `workflow-builder` specialType routes correctly in workspace-layout.js
- [ ] Delete button on dashboard explorer items with confirm + fetch DELETE
- [ ] Delete button on workflow explorer items with confirm + fetch DELETE
- [ ] Route ordering: `/explorer` and `/new` before `/{workflow_id}/run`
- [ ] Unit tests for builder and explorer routes pass

## Verification

- `cd backend && .venv/bin/pytest tests/test_workflow_builder.py -v` — all tests pass
- `cd backend && .venv/bin/pytest -x -q` — full suite passes with zero regressions
- `grep -rn "^<<<<<<< " backend/ frontend/ --include="*.py" --include="*.html" --include="*.js" --include="*.css"` — zero results

## Observability Impact

- Signals added/changed: `#builder-error` element in builder template shows save errors; fetch() errors logged to console; `workflowsRefreshed` event dispatched on body
- How a future agent inspects this: `GET /browser/workflow/explorer` for workflow list; browser console for "Workflow save error:" messages; `#builder-error` element text for inline errors
- Failure state exposed: save errors show inline in builder; delete errors in console

## Inputs

- `backend/app/templates/browser/dashboard_builder.html` — primary template to mirror for builder form structure
- `backend/app/templates/browser/dashboard_explorer.html` — primary template to mirror for explorer section
- `backend/app/dashboard/router.py` — route pattern to mirror (explorer + new + edit before ID routes)
- `frontend/static/js/workspace.js` — `openDashboardBuilderTab()` function to mirror
- `frontend/static/js/workspace-layout.js` — `dashboard-builder` specialType to mirror
- `backend/app/workflow/router.py` — existing runner + API routes to extend
- `backend/app/workflow/models.py` — `VALID_STEP_TYPES = {"view", "dashboard", "form"}`
- `backend/tests/test_dashboard_builder.py` — test pattern to mirror

## Expected Output

- `backend/app/workflow/router.py` — extended with `/explorer`, `/new`, `/{id}/edit` browser routes
- `backend/app/templates/browser/workflow_builder.html` — new builder form template
- `backend/app/templates/browser/workflow_explorer.html` — new explorer partial
- `backend/app/templates/browser/workspace.html` — WORKFLOWS section added after DASHBOARDS
- `backend/app/templates/browser/dashboard_explorer.html` — delete button added to each dashboard item
- `frontend/static/js/workspace.js` — `openWorkflowBuilderTab()` function added
- `frontend/static/js/workspace-layout.js` — `workflow-builder` specialType handling added
- `frontend/static/css/workspace.css` — workflow builder CSS added
- `backend/tests/test_workflow_builder.py` — new test file
