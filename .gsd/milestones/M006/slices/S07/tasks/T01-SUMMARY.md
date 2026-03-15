---
id: T01
parent: S07
milestone: M006
provides:
  - Workflow builder form (create/edit) with fetch()-based JSON save
  - Workflow explorer section in workspace sidebar with auto-refresh
  - openWorkflowBuilderTab() JS function and workflow-builder specialType routing
  - Delete UI for both dashboards and workflows with confirmation
key_files:
  - backend/app/workflow/router.py
  - backend/app/templates/browser/workflow_builder.html
  - backend/app/templates/browser/workflow_explorer.html
  - backend/app/templates/browser/workspace.html
  - backend/app/templates/browser/dashboard_explorer.html
  - frontend/static/js/workspace.js
  - frontend/static/js/workspace-layout.js
  - frontend/static/css/workspace.css
  - backend/tests/test_workflow_builder.py
key_decisions:
  - Workflow builder uses separate element IDs (wf-builder-*) to avoid conflicts when both builders are open simultaneously
  - Dashboard select in workflow builder fetches from /api/dashboard (existing API) rather than duplicating list logic
patterns_established:
  - Delete buttons on explorer tree leaves use .tree-leaf-action class with hover-reveal opacity pattern
  - Builder templates use _wfBuilder* / _builder* namespaced window functions to avoid cross-template collisions
observability_surfaces:
  - "#builder-error element shows save errors inline in workflow builder"
  - "Console: 'Workflow save error:' and 'Workflow delete error:' prefixes"
  - "workflowsRefreshed event on document.body fires on create/update/delete"
  - "GET /browser/workflow/explorer returns current workflow list HTML"
duration: 25m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Workflow builder UI, explorer section, and delete wiring

**Built workflow builder form, explorer section, delete UI for both dashboards and workflows, and all JS/route/CSS wiring.**

## What Happened

Implemented all 9 plan steps in order:

1. Added `/explorer`, `/new`, `/{id}/edit` browser routes to `workflow/router.py` — registered before `/{workflow_id}/run` to avoid FastAPI path capture. Added VALID_STEP_TYPES import.
2. Created `workflow_builder.html` mirroring dashboard builder — step rows with type select (view/dashboard/form), type-specific config fields (view: spec_iri dropdown + renderer select; dashboard: dashboard_id dropdown; form: target_class input), fetch()-based save to POST/PATCH `/api/workflow`. On success: dispatches `workflowsRefreshed`, opens workflow runner tab, closes builder tab.
3. Created `workflow_explorer.html` — lists workflows as `.tree-leaf` nodes with `openWorkflowTab()` click handlers, delete buttons, "+ New Workflow" action leaf.
4. Added WORKFLOWS section to `workspace.html` after DASHBOARDS with `hx-trigger="load, workflowsRefreshed from:body"`.
5. Added `openWorkflowBuilderTab(workflowId)` to `workspace.js` mirroring dashboard builder tab function.
6. Added `workflow-builder` specialType handling to `workspace-layout.js`.
7. Added delete buttons with `window.confirm()` → `fetch(DELETE)` → event dispatch to both `dashboard_explorer.html` and `workflow_explorer.html`.
8. Added workflow builder CSS and generic tree-leaf delete button styles to `workspace.css`.
9. Wrote `test_workflow_builder.py` with 10 tests covering builder new, edit (200/404/400), explorer (empty/populated/buttons/delete).

## Verification

- `cd backend && .venv/bin/pytest tests/test_workflow_builder.py -v` — 10/10 passed
- `cd backend && .venv/bin/pytest -x -q` — 641 passed, zero regressions
- `grep -rn "^<<<<<<< " backend/ frontend/` — zero conflict markers

### Slice-level verification status (partial — T01 of 2 tasks)
- ✅ `pytest tests/test_workflow_builder.py -v` — all tests pass
- ✅ `pytest -x -q` — full suite passes
- ✅ Conflict markers — zero
- ⏳ Browser: create/edit/delete workflow via builder (T02 — Docker verification)
- ⏳ Browser: delete dashboard from explorer (T02 — Docker verification)
- ⏳ Browser: builder error display (T02 — Docker verification)
- ⏳ All 12 M006 success criteria (T02 — Docker verification)

## Diagnostics

- `GET /browser/workflow/explorer` — returns HTML listing all user workflows
- `GET /browser/workflow/new` — returns builder form in create mode
- `GET /browser/workflow/{id}/edit` — returns builder form in edit mode with pre-populated data
- `#builder-error` element in builder template shows save errors inline
- Console prefix `Workflow save error:` / `Workflow delete error:` for fetch failures
- `workflowsRefreshed` custom event on `document.body` fires on create/update/delete

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/workflow/router.py` — added explorer, new, edit browser routes before run route
- `backend/app/templates/browser/workflow_builder.html` — new builder form template with step management
- `backend/app/templates/browser/workflow_explorer.html` — new explorer partial with delete buttons
- `backend/app/templates/browser/workspace.html` — added WORKFLOWS section after DASHBOARDS
- `backend/app/templates/browser/dashboard_explorer.html` — added delete buttons with confirm dialog
- `frontend/static/js/workspace.js` — added openWorkflowBuilderTab() function
- `frontend/static/js/workspace-layout.js` — added workflow-builder specialType routing
- `frontend/static/css/workspace.css` — added workflow builder CSS and tree-leaf delete button styles
- `backend/tests/test_workflow_builder.py` — new test file with 10 tests
