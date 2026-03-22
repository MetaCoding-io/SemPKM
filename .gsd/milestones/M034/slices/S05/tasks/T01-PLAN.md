---
estimated_steps: 5
estimated_files: 5
skills_used:
  - best-practices
  - review
---

# T01: Backend task template service and REST API

**Slice:** S05 — Task Templates & Review Workflows
**Milestone:** M034

## Description

Build the `TaskTemplateService` for RDF-backed task template CRUD operations, plus REST and htmx browser routes. Templates are stored as RDF resources in a dedicated named graph (`urn:sempkm:task-templates`) on RDF4J. Each template has a title, target class, default properties (JSON blob), and optional subtask definitions (JSON blob). The instantiation endpoint uses the existing batch command API with `@slot:` references to create the main task and linked subtasks in a single transaction.

## Steps

1. **Create `backend/app/task_templates/__init__.py`** — empty package init.

2. **Create `backend/app/task_templates/service.py`** — `TaskTemplateService` class:
   - Constructor takes `triplestore_client` (TriplestoreClient instance)
   - Named graph constant: `TEMPLATE_GRAPH = "urn:sempkm:task-templates"`
   - Template IRI format: `urn:sempkm:task-template:{uuid4}`
   - `async def create(title, target_class, default_properties=None, subtask_definitions=None) -> dict` — SPARQL INSERT DATA into named graph with `dcterms:title`, `sempkm:targetClass`, `sempkm:defaultProperties` (JSON string), `sempkm:subtaskDefinitions` (JSON string), `dcterms:created`
   - `async def list_all() -> list[dict]` — SPARQL SELECT from named graph returning id, title, target_class, created
   - `async def get(template_id: str) -> dict | None` — SELECT full template by IRI, parse JSON blobs back to dicts
   - `async def update(template_id: str, **updates) -> dict | None` — SPARQL DELETE/INSERT for changed fields
   - `async def delete(template_id: str) -> bool` — SPARQL DELETE WHERE matching IRI from named graph
   - `async def instantiate(template_id: str, user_overrides: dict | None = None) -> list[dict]` — builds batch command payload: `object.create` with `slot: "main"` + defaults merged with overrides, plus `edge.create` for each subtask linking to `@slot:main`. Returns the list of commands (caller submits to command API).

3. **Create `backend/app/task_templates/router.py`** — two routers:
   - `api_router` (prefix `/api/task-templates`):
     - `GET /` → list templates (JSON)
     - `POST /` → create template (JSON body: title, target_class, default_properties?, subtask_definitions?)
     - `GET /{template_id}` → get template (JSON)
     - `PATCH /{template_id}` → update template (JSON body: partial fields)
     - `DELETE /{template_id}` → delete template
     - `POST /{template_id}/instantiate` → instantiate template: calls service.instantiate() to build commands, then internally dispatches them via the command execution pipeline (import and call `_dispatch_single` or submit to `/api/commands` via internal call). Returns the created object IRI(s).
   - `browser_router` (prefix `/browser/task-templates`):
     - `GET /picker` → htmx partial listing templates for selection
   - Both routers use `Depends(get_current_user)` for auth
   - Get service via `request.app.state.template_service`

4. **Create `backend/app/templates/browser/template_picker.html`** — Jinja2 template:
   - Receives `templates` context (list of dicts from service.list_all())
   - Renders a list of clickable template items with title, target class label
   - Each item has `onclick` calling the instantiate endpoint, then `openTab()` for the new object
   - Empty state: "No templates yet. Create one from the API."

5. **Wire into main.py** — In the startup lifespan:
   - `from app.task_templates.router import api_router as templates_api_router, browser_router as templates_browser_router`
   - `app.state.template_service = TaskTemplateService(client)` after triplestore client init
   - Include both routers in the app
   - Add `/api/task-templates` to `_is_html_route()` exclusion (already covered by `/api/` prefix check)

## Must-Haves

- [ ] TaskTemplateService with create, list_all, get, update, delete, instantiate methods
- [ ] Templates stored in `urn:sempkm:task-templates` named graph via SPARQL INSERT/SELECT/DELETE
- [ ] REST endpoints: GET/POST collection, GET/PATCH/DELETE individual, POST instantiate
- [ ] Instantiation generates batch commands with `@slot:main` for subtask linking
- [ ] template_picker.html htmx partial renders template list
- [ ] Service wired onto `app.state.template_service` and routers mounted

## Verification

- `python3 -c "import ast; ast.parse(open('backend/app/task_templates/service.py').read()); ast.parse(open('backend/app/task_templates/router.py').read()); print('OK')"`
- `rg "template_service" backend/app/main.py` returns matches
- `rg "urn:sempkm:task-templates" backend/app/task_templates/service.py` confirms named graph
- `rg "instantiate" backend/app/task_templates/router.py` confirms instantiate endpoint

## Inputs

- `backend/app/triplestore/client.py` — TriplestoreClient with query() and update() methods
- `backend/app/commands/schemas.py` — ObjectCreateCommand, EdgeCreateCommand with slot field
- `backend/app/commands/router.py` — @slot: batch pattern (lines 129-166)
- `backend/app/workflow/router.py` — reference pattern for router structure (browser + API dual router)
- `backend/app/workflow/service.py` — reference pattern for service structure
- `backend/app/main.py` — app startup wiring pattern
- `backend/app/rdf/namespaces.py` — SEMPKM namespace

## Expected Output

- `backend/app/task_templates/__init__.py` — package init
- `backend/app/task_templates/service.py` — TaskTemplateService with full CRUD + instantiate
- `backend/app/task_templates/router.py` — REST + htmx routers
- `backend/app/templates/browser/template_picker.html` — template picker partial
- `backend/app/main.py` — updated with template service wiring and router mounts

## Observability Impact

- **New structured logs:** `TaskTemplateService` logs create/update/delete/instantiate at INFO level with template IRI and operation details (title on create, field list on update, command count on instantiate).
- **New inspection surface:** `GET /api/task-templates` returns all templates as JSON — agents can verify template storage without querying the triplestore directly.
- **Error visibility:** All router endpoints return structured JSON error responses with `detail` field. 400 for validation (empty title, no updates, unresolved slot). 404 for missing templates. 500 with `detail` for unexpected instantiation failures.
- **Instantiate audit trail:** The instantiate endpoint triggers `EventStore.commit()` and `validation_queue.enqueue()`, producing the same event graph and async validation as direct `POST /api/commands` — visible in the event log UI.
