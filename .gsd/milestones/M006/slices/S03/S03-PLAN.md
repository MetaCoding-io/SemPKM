# S03: DashboardSpec Model & Static Rendering

**Goal:** Users can create dashboards (via API) that compose view-embeds, markdown blocks, and create-form blocks in a CSS Grid layout, rendered as workspace tabs with real triplestore data.

**Demo:** A dashboard with 3+ blocks (view-embed showing real Notes, markdown header, create-form for Notes) renders in a workspace tab at `/browser/dashboard/{id}`.

## Must-Haves

- DashboardSpec SQLAlchemy model (SQLite JSON storage)
- DashboardService with CRUD (create, get, list, update, delete)
- Alembic migration for dashboard_specs table
- Dashboard renderer route: `GET /browser/dashboard/{id}`
- CSS Grid layout templates (single, sidebar-main, grid-2x2)
- Block rendering: view-embed (htmx loads existing view), markdown, create-form, divider
- Dashboard tab type in workspace-layout.js
- Command handlers: dashboard.create, dashboard.patch, dashboard.delete
- Unit tests for model and service CRUD

## Proof Level

- This slice proves: integration (dashboards render real ViewSpec data from triplestore)
- Real runtime required: yes (renders htmx partials with real data)
- Human/UAT required: no (tests verify structure)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_dashboard.py -x -q` — new tests pass
- `cd backend && .venv/bin/python -m pytest tests/ -x -q` — all tests pass
- Alembic migration applies cleanly

## Tasks

- [ ] **T01: DashboardSpec model and Alembic migration** `est:30m`
  - Why: Foundation — need the data model before anything else
  - Files: `backend/app/dashboard/models.py` (new), `backend/migrations/versions/011_dashboard_specs.py` (new)
  - Do:
    1. Create `app/dashboard/` package with `__init__.py` and `models.py`
    2. Define `DashboardSpec` SQLAlchemy model: id (UUID PK), user_id (FK users), name, description, layout (string — template name), blocks (JSON column), created_at, updated_at
    3. Blocks JSON schema: `[{type, config}]` where type is one of: view-embed, markdown, object-embed, create-form, sparql-result, divider; config varies by type
    4. Write Alembic migration `011_dashboard_specs.py`
  - Verify: migration applies, model imports cleanly
  - Done when: table exists, model works

- [ ] **T02: DashboardService CRUD** `est:30m`
  - Why: Business logic layer for dashboard management
  - Files: `backend/app/dashboard/service.py` (new)
  - Do:
    1. DashboardService class with async methods: create, get, list_for_user, update, delete
    2. Create accepts name, layout, blocks JSON, user_id
    3. Get returns DashboardSpec or None
    4. Update supports partial updates (name, layout, blocks)
    5. Delete verifies ownership
    6. Add to app dependencies (get_dashboard_service)
  - Verify: unit tests for CRUD
  - Done when: service methods work with SQLite

- [ ] **T03: Dashboard renderer and routes** `est:45m`
  - Why: The core rendering pipeline — dashboard page with CSS Grid and htmx blocks
  - Files: `backend/app/dashboard/router.py` (new), `backend/app/templates/browser/dashboard_page.html` (new), `backend/app/templates/browser/dashboard_block_*.html` (new)
  - Do:
    1. Router with prefix `/browser/dashboard`
    2. `GET /{id}` — renders dashboard page: CSS Grid container with slots
    3. Each block rendered as an htmx-loaded partial: `hx-get="/browser/dashboard/{id}/block/{index}"` with `hx-trigger="load"`
    4. `GET /{id}/block/{index}` — renders individual block based on type:
       - view-embed: renders existing view endpoint via htmx include
       - markdown: renders markdown to HTML
       - create-form: renders SHACL form for target class
       - divider: renders `<hr>`
    5. CSS Grid layouts: define 3 named templates (single, sidebar-main, grid-2x2)
    6. Register router in app
  - Verify: dashboard page renders with blocks
  - Done when: GET /{id} returns a rendered dashboard

- [ ] **T04: Dashboard tab type and command handlers** `est:30m`
  - Why: Dashboards need to open as workspace tabs and be created via the command system
  - Files: `frontend/static/js/workspace.js`, `backend/app/commands/dispatcher.py` (or new handler file)
  - Do:
    1. Add `openDashboardTab(id, name)` function to workspace.js
    2. Register dashboard tab type in dockview (like views and objects)
    3. Add command handlers: `dashboard.create`, `dashboard.patch`, `dashboard.delete`
    4. Wire to DashboardService methods
    5. Add dashboard API endpoints for JSON CRUD: `GET/POST /api/dashboard`, `PATCH/DELETE /api/dashboard/{id}`
  - Verify: command handlers work, dashboard opens in tab
  - Done when: full CRUD via commands + tab opening

- [ ] **T05: Tests** `est:30m`
  - Why: Verify model, service, and rendering
  - Files: `backend/tests/test_dashboard.py` (new)
  - Do:
    1. Test DashboardSpec model creation and JSON serialization
    2. Test DashboardService CRUD operations
    3. Test block rendering endpoint returns correct HTML
    4. Test layout CSS class generation
    5. Test command handler routing
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_dashboard.py -x -q`
  - Done when: all new tests pass, full suite passes

## Files Likely Touched

- `backend/app/dashboard/__init__.py` (new)
- `backend/app/dashboard/models.py` (new)
- `backend/app/dashboard/service.py` (new)
- `backend/app/dashboard/router.py` (new)
- `backend/app/templates/browser/dashboard_page.html` (new)
- `backend/app/templates/browser/dashboard_block_view.html` (new)
- `backend/app/templates/browser/dashboard_block_markdown.html` (new)
- `backend/app/templates/browser/dashboard_block_form.html` (new)
- `backend/migrations/versions/011_dashboard_specs.py` (new)
- `backend/app/dependencies.py`
- `backend/app/main.py` (register router)
- `frontend/static/js/workspace.js`
- `frontend/static/css/workspace.css`
- `backend/tests/test_dashboard.py` (new)
