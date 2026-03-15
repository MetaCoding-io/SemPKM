# S06: WorkflowSpec Model & Runner

**Goal:** Users can create workflows with ordered steps (view, dashboard, or form) via the API, and run them with a step indicator bar, prev/next navigation, and context flowing between steps.

**Demo:** A 3-step workflow (view Notes → create Note form → view Notes again) runs in a workspace tab with a stepper bar, prev/next buttons, and step content loading via htmx.

## Must-Haves

- WorkflowSpec SQLAlchemy model (SQLite JSON storage, mirroring DashboardSpec pattern)
- WorkflowService with CRUD
- Alembic migration for workflow_specs table
- Workflow runner route: `GET /browser/workflow/{id}/run`
- Stepper UI (step indicator bar, prev/next buttons)
- Step rendering: loads view, dashboard, or form per step config
- Workflow tab type in workspace-layout.js
- API routes: GET/POST/PATCH/DELETE /api/workflow
- Unit tests

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_workflow.py tests/ -x -q`
- Stepper HTML renders correctly with step labels

## Tasks

- [ ] **T01: WorkflowSpec model, service, and migration** `est:30m`
  - Why: Data layer — mirrors DashboardSpec pattern
  - Files: `backend/app/workflow/__init__.py`, `backend/app/workflow/models.py`, `backend/app/workflow/service.py`, `backend/migrations/versions/012_workflow_specs.py`
  - Do: WorkflowSpec model with steps_json column. WorkflowService with CRUD. Alembic migration.
  - Verify: tests pass
  - Done when: CRUD works with in-memory SQLite

- [ ] **T02: Workflow runner and API routes** `est:45m`
  - Why: Rendering pipeline — stepper bar + step content via htmx
  - Files: `backend/app/workflow/router.py`, `backend/app/templates/browser/workflow_runner.html`
  - Do: Runner page with stepper bar, step content area, prev/next buttons. API CRUD routes. Step rendering loads view/dashboard/form via htmx. Register in main.py.
  - Verify: runner page renders with step labels
  - Done when: workflow runner shows steps and navigates

- [ ] **T03: Frontend integration and tests** `est:30m`
  - Why: Tab opening + test coverage
  - Files: `frontend/static/js/workspace.js`, `frontend/static/css/workspace.css`, `backend/tests/test_workflow.py`
  - Do: openWorkflowTab function, workflow CSS, comprehensive tests.
  - Verify: full test suite passes
  - Done when: all tests pass, workflow tab opens

## Files Likely Touched

- `backend/app/workflow/__init__.py` (new)
- `backend/app/workflow/models.py` (new)
- `backend/app/workflow/service.py` (new)
- `backend/app/workflow/router.py` (new)
- `backend/app/templates/browser/workflow_runner.html` (new)
- `backend/migrations/versions/012_workflow_specs.py` (new)
- `backend/app/main.py`
- `frontend/static/js/workspace.js`
- `frontend/static/css/workspace.css`
- `backend/tests/test_workflow.py` (new)
