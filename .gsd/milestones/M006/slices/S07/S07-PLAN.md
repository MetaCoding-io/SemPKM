# S07: Workflow Builder UI & Final Integration

**Goal:** User can create/edit workflows through a form-based UI, workflows appear in the explorer sidebar, both dashboards and workflows have delete UI, and all 12 milestone success criteria pass end-to-end.
**Demo:** Create a 3-step workflow via the builder form → it appears in the explorer → run it → edit it → delete it. Delete a dashboard from the explorer. Verify all M006 success criteria against live Docker.

## Must-Haves

- Workflow builder form with step type config (view, dashboard, form) and fetch()-based JSON save
- WORKFLOWS explorer section in workspace sidebar with auto-refresh
- `openWorkflowBuilderTab()` JS function and `workflow-builder` specialType routing
- Delete UI for both dashboards and workflows (with confirmation)
- All 12 M006 success criteria verified end-to-end

## Proof Level

- This slice proves: final-assembly
- Real runtime required: yes
- Human/UAT required: no (agent verifies all criteria in browser)

## Verification

- `cd backend && .venv/bin/pytest tests/test_workflow_builder.py -v` — all tests pass (builder routes + explorer route)
- `cd backend && .venv/bin/pytest -x -q` — full suite passes, zero regressions
- `grep -rn "^<<<<<<< " backend/ frontend/ --include="*.py" --include="*.html" --include="*.js" --include="*.css"` — zero conflict markers
- Browser: create workflow via builder → appears in explorer → runs → edit pre-populates → delete removes it
- Browser: delete dashboard from explorer → removed from list
- Browser: workflow builder shows inline error in `#builder-error` when save fails (e.g. empty name)
- All 12 M006 success criteria checked against live Docker behavior

## Observability / Diagnostics

- Runtime signals: `#builder-error` element shows last save error; fetch() errors logged to console with "Workflow save error:" prefix
- Inspection surfaces: `GET /browser/workflow/explorer` returns current workflow list HTML; `workflowsRefreshed` event on document.body fires on create/update/delete
- Failure visibility: builder save errors displayed inline; delete errors in console
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `WorkflowService` CRUD (S06), `openWorkflowTab()` (S06), dashboard builder pattern (S04), explorer section pattern (S04), cross-view context system (S05)
- New wiring introduced: workflow builder routes, workflow explorer route, `openWorkflowBuilderTab()`, `workflow-builder` specialType, delete handlers for both dashboards and workflows
- What remains before the milestone is truly usable end-to-end: nothing — this slice closes the milestone

## Tasks

- [x] **T01: Workflow builder UI, explorer section, and delete wiring** `est:1h30m`
  - Why: This is the core deliverable — the builder form, explorer section, delete UI, and all JS/route wiring needed for full workflow CRUD through the UI. Also adds delete UI for dashboards (S04 deferred this).
  - Files: `backend/app/workflow/router.py`, `backend/app/templates/browser/workflow_builder.html`, `backend/app/templates/browser/workflow_explorer.html`, `backend/app/templates/browser/workspace.html`, `backend/app/templates/browser/dashboard_explorer.html`, `frontend/static/js/workspace.js`, `frontend/static/js/workspace-layout.js`, `frontend/static/css/workspace.css`, `backend/tests/test_workflow_builder.py`
  - Do: (1) Add `/explorer`, `/new`, `/{id}/edit` routes to `workflow/router.py` — register before `/{workflow_id}/run` for path ordering. (2) Create `workflow_builder.html` mirroring dashboard builder — step rows with type-specific config (view: spec_iri + renderer dropdown; dashboard: dashboard_id dropdown; form: target_class), fetch()-based save to POST/PATCH `/api/workflow`, `htmx.trigger(document.body, 'workflowsRefreshed')` on success. (3) Create `workflow_explorer.html` mirroring dashboard explorer — list workflows as tree-leafs, "+ New Workflow" action. (4) Add WORKFLOWS section to `workspace.html` after DASHBOARDS with `hx-trigger="load, workflowsRefreshed from:body"`. (5) Add `openWorkflowBuilderTab()` to workspace.js mirroring `openDashboardBuilderTab()`. (6) Add `workflow-builder` specialType to workspace-layout.js. (7) Add delete buttons (trash icon) to both dashboard_explorer.html and workflow_explorer.html with `window.confirm()` → `fetch(DELETE)` → dispatch refresh event. (8) Add builder CSS rules. (9) Write `test_workflow_builder.py` with builder route tests + explorer route test.
  - Verify: `cd backend && .venv/bin/pytest tests/test_workflow_builder.py -v` passes; `cd backend && .venv/bin/pytest -x -q` shows zero regressions
  - Done when: workflow builder creates/edits workflows, explorer lists them, delete works for both dashboards and workflows, all tests pass

- [x] **T02: Milestone-level end-to-end verification** `est:45m`
  - Why: S07 is the final slice — must verify all 12 M006 success criteria against live Docker behavior. Some criteria (PROV-O, explorer grouping, VFS scope) were completed in earlier slices and need regression checks.
  - Files: `.gsd/milestones/M006/slices/S07/S07-UAT.md`, `.gsd/milestones/M006/M006-ROADMAP.md`
  - Do: Start Docker stack, walk through all 12 success criteria in the browser: (1) PROV-O predicates in event log, (2) PROV-O predicates in comments, (3) explorer grouped by model, (4) VFS scope dropdown with optgroups, (5) VFS mount filtering, (6) create dashboard via UI, (7) dashboard renders with 3+ block types, (8) cross-view context filtering, (9) create/run workflow with 3+ steps, (10) dashboards and workflows in explorer with CRUD, (11) persistence across Docker restart, (12) parameterized SPARQL uses VALUES binding. Document results in S07-UAT.md. Mark roadmap slices complete.
  - Verify: All 12 criteria pass in live Docker; `grep -rn "^<<<<<<< " backend/ frontend/` returns empty
  - Done when: S07-UAT.md documents all 12 criteria as passing, roadmap S07 marked `[x]`

## Files Likely Touched

- `backend/app/workflow/router.py`
- `backend/app/templates/browser/workflow_builder.html`
- `backend/app/templates/browser/workflow_explorer.html`
- `backend/app/templates/browser/workspace.html`
- `backend/app/templates/browser/dashboard_explorer.html`
- `frontend/static/js/workspace.js`
- `frontend/static/js/workspace-layout.js`
- `frontend/static/css/workspace.css`
- `backend/tests/test_workflow_builder.py`
- `.gsd/milestones/M006/slices/S07/S07-UAT.md`
