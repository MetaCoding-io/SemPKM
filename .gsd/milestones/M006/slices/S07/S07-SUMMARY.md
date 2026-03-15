---
id: S07
parent: M006
milestone: M006
provides:
  - Workflow builder form (create and edit modes) with step type config and fetch()-based save
  - openWorkflowBuilderTab() JS function and workflow-builder specialType routing
  - WORKFLOWS explorer section in workspace sidebar with auto-refresh
  - Delete UI for both dashboards and workflows with confirmation
  - All 12 M006 success criteria verified end-to-end against live Docker
requires:
  - slice: S04
    provides: Dashboard builder pattern, explorer section pattern
  - slice: S05
    provides: Cross-view context system
  - slice: S06
    provides: WorkflowService CRUD, openWorkflowTab(), workflow runner
affects: []
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
  - "Workflow builder uses separate element IDs (wf-builder-*) to avoid conflicts when both builders are open"
  - "Delete buttons on explorer tree leaves use .tree-leaf-action class with hover-reveal opacity"
  - "Dashboard select in workflow builder fetches from /api/dashboard (existing API)"
patterns_established:
  - Tree-leaf delete buttons with hover-reveal (.tree-leaf-action opacity pattern)
  - Builder template namespaced window functions (_wfBuilder* vs _builder*) to avoid cross-template collisions
observability_surfaces:
  - "#builder-error element shows save errors inline in workflow builder"
  - "workflowsRefreshed event on document.body fires on create/update/delete"
  - "GET /browser/workflow/explorer returns current workflow list HTML"
  - "S07-UAT.md serves as persistent verification record for all 12 success criteria"
drill_down_paths:
  - .gsd/milestones/M006/slices/S07/tasks/T01-SUMMARY.md
  - .gsd/milestones/M006/slices/S07/tasks/T02-SUMMARY.md
duration: 45m
verification_result: passed
completed_at: 2026-03-15
---

# S07: Workflow Builder UI & Final Integration

**Workflow builder form, explorer section, and delete UI for both dashboards and workflows — completing the full CRUD lifecycle. All 12 M006 success criteria verified end-to-end against live Docker.**

## What Happened

**T01 (25m)** built the workflow builder form, explorer section, and delete wiring. Three browser routes added to `workflow/router.py` (`/explorer`, `/new`, `/{id}/edit`) registered before `/{workflow_id}/run` for path ordering. `workflow_builder.html` mirrors the dashboard builder — step rows with type-specific config (view: spec_iri dropdown + renderer; dashboard: dashboard_id dropdown; form: target_class input), fetch()-based save to POST/PATCH `/api/workflow`. `workflow_explorer.html` lists workflows as tree-leaf nodes with click-to-open and delete buttons. WORKFLOWS section added to `workspace.html` after DASHBOARDS. Delete buttons added to both dashboard and workflow explorer templates with `window.confirm()` → `fetch(DELETE)` → refresh event dispatch. 10 tests written.

**T02 (20m)** systematically verified all 12 M006 success criteria against live Docker. PROV-O predicates confirmed via triplestore query (0 old predicates). Explorer shows grouped model folders. VFS scope dropdown creates optgroups. Dashboard renders sidebar-main layout with cross-view context working (row click → context event → re-fetch → filtered results). 3-step workflow runs with stepper navigation. Both dashboards and workflows appear in explorer with delete. Data persists across `docker compose down/up`. Parameterized SPARQL uses safe VALUES binding (25 injection tests pass).

## Verification

- `pytest tests/test_workflow_builder.py -v` — 10/10 passed
- `pytest -x -q` — 641 passed, 0 failures
- `grep -rn "^<<<<<<< " backend/ frontend/` — zero conflict markers
- All 12 M006 success criteria documented as PASS in S07-UAT.md
- Docker restart persistence confirmed

## Requirements Advanced

- DASH-01 (Dashboard CRUD) — full CRUD via builder + explorer with delete
- WKFL-01 (Workflow CRUD) — full CRUD via builder + explorer with delete
- All milestone success criteria — verified end-to-end

## Deviations

- None

## Known Limitations

- Markdown block renders raw text (not rendered HTML) — v1 limitation
- Workflow form step config key mismatch (target_class vs model_iri) — cosmetic
- No drag-and-drop step reordering in workflow builder — steps added sequentially

## Files Created/Modified

- `backend/app/workflow/router.py` — added explorer, new, edit browser routes
- `backend/app/templates/browser/workflow_builder.html` — new builder form template
- `backend/app/templates/browser/workflow_explorer.html` — new explorer partial with delete
- `backend/app/templates/browser/workspace.html` — added WORKFLOWS section
- `backend/app/templates/browser/dashboard_explorer.html` — added delete buttons
- `frontend/static/js/workspace.js` — added openWorkflowBuilderTab()
- `frontend/static/js/workspace-layout.js` — added workflow-builder specialType
- `frontend/static/css/workspace.css` — added workflow builder + tree-leaf delete CSS
- `backend/tests/test_workflow_builder.py` — 10 tests
- `.gsd/milestones/M006/slices/S07/S07-UAT.md` — milestone verification results
