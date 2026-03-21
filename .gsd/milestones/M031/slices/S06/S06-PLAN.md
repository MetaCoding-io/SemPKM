# S06: Dashboard & Workflow Builder UX

**Goal:** Dashboard and workflow builder forms are easier to use: every field has contextual help text, IRI reference fields have search-as-you-type autocomplete, the workflow "view" step uses a single picker instead of redundant renderer dropdown, and fresh installs include sample seed data.
**Demo:** Open the dashboard builder (`/browser/dashboard/new`), see help text under every field, add a "create-form" block and type in the Target Class IRI field — autocomplete suggestions appear. Open the workflow builder, add a "view" step — a single view picker (no separate renderer dropdown). On a fresh install with no dashboards, the explorer shows a "Getting Started" sample dashboard.

## Must-Haves

- Every field in both builders has a `<small class="field-help">` element with a descriptive hint
- Target Class IRI fields (dashboard create-form block, workflow form step) offer autocomplete from class search
- Object IRI field (dashboard object-embed block) offers autocomplete from object search
- Workflow "view" step shows a single view picker; renderer_type is auto-set from the selected view spec
- A seed data function creates sample dashboard + workflow for users who have none
- Seed data is idempotent (runs only when user has 0 dashboards/workflows)

## Verification

- `grep -c 'field-help' backend/app/templates/browser/dashboard_builder.html` returns ≥ 10 (help text on all fields)
- `grep -c 'field-help' backend/app/templates/browser/workflow_builder.html` returns ≥ 5 (help text on all fields)
- `grep -c 'step-config-renderer' backend/app/templates/browser/workflow_builder.html` returns 0 (renderer dropdown removed)
- `grep -q 'class-search' backend/app/templates/browser/dashboard_builder.html` succeeds (autocomplete wired)
- `grep -q 'class-search' backend/app/templates/browser/workflow_builder.html` succeeds (autocomplete wired)
- `python3 -c "import ast; ast.parse(open('backend/app/dashboard/seed.py').read())"` succeeds (seed module valid Python)
- `rg 'seed_sample' backend/app/main.py` returns a match (startup hook wired)
- `cd backend && python -m pytest tests/test_seed_data.py -x -q` passes (seed data unit test)
- `grep -q 'builder-error' backend/app/templates/browser/dashboard_builder.html && grep -q 'builder-error' backend/app/templates/browser/workflow_builder.html` succeeds (error display divs present for failure visibility)

## Tasks

- [x] **T01: Add help text to all builder fields and simplify workflow view step** `est:45m`
  - Why: DBUIX-01 and DBUIX-03 — both are template-only changes to the same two files. Help text makes the builders self-documenting. Removing the redundant renderer dropdown simplifies the view step (the renderer is already part of the view spec).
  - Files: `backend/app/templates/browser/dashboard_builder.html`, `backend/app/templates/browser/workflow_builder.html`
  - Do: Add `<small class="field-help">...</small>` after every label/input in both builders using the content table from S06 research. In the workflow builder, remove the renderer `<select>` from the "view" `getTypeConfigHTML` case and add JS to auto-set `renderer_type` from `_cachedViews` when a view is selected (store in a hidden input with `data-key="renderer_type"`). Show renderer as a read-only badge next to the view dropdown.
  - Verify: `grep -c 'field-help' backend/app/templates/browser/dashboard_builder.html` ≥ 10; `grep -c 'step-config-renderer' backend/app/templates/browser/workflow_builder.html` returns 0
  - Done when: Every builder field has contextual help text and the workflow view step has one dropdown (not two)

- [x] **T02: Add autocomplete for Target Class IRI and Object IRI fields** `est:1h`
  - Why: DBUIX-02 — users currently must type exact IRIs from memory. Autocomplete makes these fields usable.
  - Files: `backend/app/browser/search.py`, `backend/app/templates/browser/dashboard_builder.html`, `backend/app/templates/browser/workflow_builder.html`, `frontend/static/css/forms.css`
  - Do: (1) Add a `/browser/class-search` JSON endpoint in `search.py` that wraps `OntologyService.search_classes()` and returns `[{iri, label}]`. (2) In both builders, replace the plain text `<input>` for `target_class` with a `.reference-field` wrapper containing a visible search input, a hidden input with `data-key="target_class"`, and a `.suggestions-dropdown` div. Wire the search input to fetch from `/browser/class-search?q=...` on input with 300ms debounce (vanilla JS, matching the builder's existing fetch pattern). Render suggestion items and on click set the hidden input value + show selected label. (3) Same pattern for `object_iri` field using the existing `/browser/search` endpoint (search all types). (4) Add `htmx.process()` calls after dynamic DOM insertion in both builders. (5) Verify `.reference-field` and `.suggestions-dropdown` CSS works inside `.dashboard-builder` / `.workflow-builder` context — adjust if needed.
  - Verify: `grep -q 'class-search' backend/app/templates/browser/dashboard_builder.html && grep -q 'class-search' backend/app/templates/browser/workflow_builder.html && echo OK`
  - Done when: Typing in Target Class IRI or Object IRI fields shows autocomplete suggestions from the backend

- [x] **T03: Create seed data module for sample dashboards and workflows** `est:45m`
  - Why: DBUIX-04 — first-time users see empty builders with no examples. Seed data provides a "Getting Started" dashboard and a "Create & Review" workflow as learning aids.
  - Files: `backend/app/dashboard/seed.py`, `backend/app/main.py`, `backend/tests/test_seed_data.py`
  - Do: (1) Create `backend/app/dashboard/seed.py` with a `seed_sample_data(dashboard_service, workflow_service, user_id)` async function. The function checks `list_for_user()` — if the user has 0 dashboards, it creates a "Getting Started" dashboard (sidebar-main layout, markdown welcome block + view-embed block). If 0 workflows, it creates a "Create & Review" two-step workflow. (2) Wire into app startup in `main.py` — after services are initialized, call seed on a `@app.on_event("startup")` or existing startup hook, using the first user from the DB (or skip if no users). (3) Write a unit test in `backend/tests/test_seed_data.py` that mocks the services and verifies seed creates data when empty and skips when data already exists.
  - Verify: `cd backend && python -m pytest tests/test_seed_data.py -x -q`
  - Done when: Seed module creates sample data on first run and is idempotent on subsequent runs

## Observability / Diagnostics

- **Help text coverage:** `grep -c 'field-help' backend/app/templates/browser/dashboard_builder.html` — should return ≥ 10. Same pattern for workflow builder ≥ 5.
- **Renderer dropdown removal:** `grep -c 'step-config-renderer' backend/app/templates/browser/workflow_builder.html` — must return 0 to confirm the old dropdown is gone.
- **Auto-renderer wiring:** The `_wfUpdateRendererFromView` function logs no errors; verify the hidden input value updates by inspecting the DOM after selecting a view in the workflow builder (`document.querySelector('[data-key="renderer_type"]').value`).
- **Seed data startup:** The app startup log should include a line from `seed_sample_data` indicating whether seed data was created or skipped. Inspect via `docker compose logs backend | grep seed`.
- **Failure visibility:** If the builder save fails, the `#builder-error` div becomes visible with the error message. No silent failures.
- **Autocomplete diagnostics:** If the class-search endpoint returns an error, the suggestions dropdown shows "No results" rather than silently failing.

## Files Likely Touched

- `backend/app/templates/browser/dashboard_builder.html`
- `backend/app/templates/browser/workflow_builder.html`
- `backend/app/browser/search.py`
- `backend/app/dashboard/seed.py`
- `backend/app/main.py`
- `backend/tests/test_seed_data.py`
- `frontend/static/css/forms.css`
