# S05: Task Templates & Review Workflows

**Goal:** Users can create reusable task templates and run structured PPV review workflows. Templates are RDF-backed with default properties and subtask structures. Review workflows are pre-seeded WorkflowSpecs accessible from the command palette.
**Demo:** Open command palette → "Create from Template" → select "Sprint Planning" → new task with preset properties and subtasks. Open palette → "Run Weekly Review" → stepper walks through review steps → ppv:WeeklyReview object created.

## Must-Haves

- TaskTemplateService with RDF CRUD (create, list, get, update, delete) against `urn:sempkm:task-templates` named graph
- REST API endpoints for template CRUD + instantiation (batch `object.create` + `edge.create` using `@slot:` references)
- 4 PPV review WorkflowSpecs (weekly, monthly, quarterly, yearly) seeded via `seed_sample_data()`
- Seed idempotency: review workflows seeded by name, not by count — user-created workflows preserved
- Command palette "Create from Template" parent with dynamically-populated template children
- Command palette "Run Weekly/Monthly/Quarterly/Yearly Review" direct-launch entries
- Template picker htmx partial for template selection in the command palette flow
- Unit tests for template CRUD, seed idempotency, and template instantiation

## Proof Level

- This slice proves: contract + integration
- Real runtime required: yes (RDF4J for template storage, SQLite for workflow seed)
- Human/UAT required: no

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_task_templates.py -v` — template CRUD unit tests pass
- `cd backend && .venv/bin/python -m pytest tests/test_seed_data.py -v` — seed idempotency tests pass (including new review workflow tests)
- `rg "urn:sempkm:task-templates" backend/app/task_templates/service.py` — confirms named graph usage
- `rg "Create from Template" frontend/static/js/workspace.js` — confirms command palette entry
- `rg "Run Weekly Review" frontend/static/js/workspace.js` — confirms workflow launch entries
- `python3 -c "import ast; ast.parse(open('backend/app/task_templates/service.py').read()); ast.parse(open('backend/app/task_templates/router.py').read()); print('OK')"` — syntax valid
- `rg "logger\." backend/app/task_templates/service.py | head -5` — confirms structured logging in service
- `rg "status_code=4" backend/app/task_templates/router.py` — confirms error responses with detail messages

## Observability / Diagnostics

- Runtime signals: structured logger in TaskTemplateService for create/delete/instantiate operations; seed_sample_data logs which review workflows were created
- Inspection surfaces: `GET /api/task-templates` lists all templates; `GET /api/workflow` lists all workflows including seeded reviews
- Failure visibility: template CRUD errors return structured JSON with detail message; seed failures logged as warnings (non-fatal)
- Redaction constraints: none — no secrets involved

## Integration Closure

- Upstream surfaces consumed: `backend/app/triplestore/client.py` (query/update), `backend/app/commands/router.py` (@slot: batch), `backend/app/workflow/service.py` (create), `backend/app/dashboard/seed.py` (seed_sample_data), `models/ppv/views/ppv.jsonld` (view spec IRIs), `models/ppv/ontology/ppv.jsonld` (type IRIs)
- New wiring introduced: `task_templates` package mounted on app, template service on `app.state`, router included in main app
- What remains before milestone is truly usable end-to-end: nothing — S05 is the final slice

## Tasks

- [x] **T01: Backend task template service and REST API** `est:2h`
  - Why: Core backend for task template CRUD — stores templates in RDF, exposes REST/htmx endpoints for create/list/get/update/delete/instantiate
  - Files: `backend/app/task_templates/__init__.py`, `backend/app/task_templates/service.py`, `backend/app/task_templates/router.py`, `backend/app/main.py`, `backend/app/templates/browser/template_picker.html`
  - Do: Create `task_templates` package with `TaskTemplateService` using TriplestoreClient for SPARQL against `urn:sempkm:task-templates` graph. Template IRIs: `urn:sempkm:task-template:{uuid}`. Properties: `dcterms:title`, `sempkm:targetClass`, `sempkm:defaultProperties` (JSON string), `sempkm:subtaskDefinitions` (JSON string), `dcterms:created`. REST router: `GET/POST /api/task-templates`, `GET/PATCH/DELETE /api/task-templates/{id}`, `POST /api/task-templates/{id}/instantiate` (calls batch command API internally). Browser route: `GET /browser/task-templates/picker` returning htmx partial. Wire service onto `app.state.template_service`, mount routers in main.py.
  - Verify: `python3 -c "import ast; ast.parse(open('backend/app/task_templates/service.py').read()); ast.parse(open('backend/app/task_templates/router.py').read()); print('OK')"` and `rg "template_service" backend/app/main.py`
  - Done when: TaskTemplateService has full CRUD + instantiation, routers mounted, template_picker.html renders template list

- [x] **T02: Seed PPV review workflows and fix idempotency** `est:1h`
  - Why: Pre-built review workflows so users don't have to create them from scratch. Current seed checks `if not existing_workflows` which blocks seeding review workflows once user has any workflow. Fix to per-name idempotency.
  - Files: `backend/app/dashboard/seed.py`, `backend/tests/test_seed_data.py`
  - Do: Add 4 review workflow definitions (weekly: 4 steps, monthly: 4 steps, quarterly: 3 steps, yearly: 3 steps) using existing PPV view spec IRIs and type IRIs. Change workflow seed from "skip if any exist" to "skip if this name already exists" — iterate over a list of seed workflows, check by name before creating. Update existing seed test to reflect the per-name logic. Add new tests: seed twice → 4 review workflows (not 8), seed with user workflow → user's preserved + reviews added.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_seed_data.py -v`
  - Done when: 4 review workflows seeded on first startup, idempotent on repeat, existing user workflows preserved

- [x] **T03: Command palette integration for templates and review workflows** `est:1.5h`
  - Why: Connects the backend services to the user's primary discovery mechanism — the command palette. Users need to find and use templates and review workflows without navigating to dedicated admin pages.
  - Files: `frontend/static/js/workspace.js`
  - Do: Add "Create from Template" parent entry with `children: []` to ninja.data. Add `_refreshTemplatePaletteItems(ninja)` function that fetches `GET /api/task-templates`, populates children with template names, each handler calling `POST /api/task-templates/{id}/instantiate` then opening the created task tab via `openTab()`. Add 4 workflow launch entries ("Run Weekly Review", "Run Monthly Review", "Run Quarterly Review", "Run Yearly Review") in a "Workflows" section — handlers fetch `/api/workflow` to find the workflow by name, then call `openWorkflowTab(id, name)`. Call `_refreshTemplatePaletteItems(ninja)` during ninja-keys init alongside the existing `_refreshLayoutPaletteItems` and `_refreshPersonaPaletteItems`.
  - Verify: `rg "Create from Template" frontend/static/js/workspace.js` and `rg "Run Weekly Review" frontend/static/js/workspace.js` and `rg "_refreshTemplatePaletteItems" frontend/static/js/workspace.js`
  - Done when: Command palette shows template and workflow entries; template children populate dynamically from API

- [ ] **T04: Unit tests for task template CRUD and instantiation** `est:1h`
  - Why: Contract verification for the template service — proves CRUD operations, instantiation via batch commands, and error handling without requiring a live triplestore
  - Files: `backend/tests/test_task_templates.py`
  - Do: Write pytest tests mocking TriplestoreClient. Tests: create template → verify SPARQL INSERT; list templates → verify SELECT returns expected data; get template by ID → verify result; update template title → verify SPARQL UPDATE; delete template → verify SPARQL DELETE; instantiate template → verify batch command generation with @slot: references for subtasks; instantiate template without subtasks → verify single object.create command; error case: get nonexistent template returns None.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_task_templates.py -v`
  - Done when: All template CRUD + instantiation tests pass with mocked triplestore

## Files Likely Touched

- `backend/app/task_templates/__init__.py`
- `backend/app/task_templates/service.py`
- `backend/app/task_templates/router.py`
- `backend/app/main.py`
- `backend/app/templates/browser/template_picker.html`
- `backend/app/dashboard/seed.py`
- `backend/tests/test_seed_data.py`
- `backend/tests/test_task_templates.py`
- `frontend/static/js/workspace.js`
