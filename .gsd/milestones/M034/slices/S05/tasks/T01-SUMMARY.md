---
id: T01
parent: S05
milestone: M034
provides:
  - TaskTemplateService with full CRUD (create/list/get/update/delete) + instantiate against urn:sempkm:task-templates named graph
  - REST API endpoints at /api/task-templates for template management and instantiation
  - htmx browser route at /browser/task-templates/picker for template selection
  - template_picker.html Jinja2 partial with interactive template list
key_files:
  - backend/app/task_templates/__init__.py
  - backend/app/task_templates/service.py
  - backend/app/task_templates/router.py
  - backend/app/templates/browser/template_picker.html
  - backend/app/main.py
key_decisions:
  - Instantiate endpoint dispatches through the same dispatch() + EventStore.commit() pipeline as POST /api/commands — no internal HTTP call, reuses slot_map resolution directly
  - Template IRI format is urn:sempkm:task-template:{uuid4}, stored in urn:sempkm:task-templates named graph
  - Subtask linking uses sempkm:subtaskOf predicate by default, overridable per subtask definition
patterns_established:
  - RDF-backed service with dedicated named graph and SPARQL CRUD (mirrors triplestore patterns in query_service, validation)
  - Internal batch command dispatch for features that create objects via templates (avoids HTTP round-trip)
observability_surfaces:
  - GET /api/task-templates — lists all templates for inspection
  - Structured logger at INFO for create/update/delete/instantiate with template IRI
  - Instantiate produces event graph visible in event log UI
  - Error responses with detail field on all endpoints (400/404/500)
duration: 25m
verification_result: passed
completed_at: 2026-03-22T02:00:00-04:00
blocker_discovered: false
---

# T01: Backend task template service and REST API

**Built TaskTemplateService with RDF CRUD and REST/htmx endpoints for reusable task templates, wired into app startup with batch command instantiation pipeline**

## What Happened

Created the `task_templates` package with three files:

1. **`service.py`** — `TaskTemplateService` class with `create`, `list_all`, `get`, `update`, `delete`, and `instantiate` methods. Templates are stored as RDF resources in the `urn:sempkm:task-templates` named graph using SPARQL INSERT/SELECT/DELETE against RDF4J. JSON blobs (default_properties, subtask_definitions) are stored as escaped string literals and parsed back on read. The `instantiate` method builds a batch command payload with `@slot:main` for the primary object and `@slot:subtask_N` for each subtask, with `edge.create` commands linking subtasks to main via `sempkm:subtaskOf`.

2. **`router.py`** — Two FastAPI routers: `api_router` (prefix `/api/task-templates`) with full CRUD + instantiate, and `browser_router` (prefix `/browser/task-templates`) with a picker endpoint. The instantiate endpoint dispatches commands through the same `dispatch()` + `EventStore.commit()` pipeline used by `POST /api/commands`, including `@slot:` resolution and async validation queue enqueue. Uses Pydantic request models for input validation.

3. **`template_picker.html`** — Jinja2 partial rendering a clickable list of templates with title and compact IRI type label. Includes inline JS for calling the instantiate endpoint and opening the created object via `openTab()`.

Wired the service onto `app.state.template_service` in the lifespan function and included both routers in the main app, positioned after the workflow routers.

## Verification

All task-level checks pass:
- AST parse of service.py and router.py succeeds
- `template_service` wiring confirmed in main.py
- Named graph `urn:sempkm:task-templates` confirmed in service.py
- `instantiate` endpoint confirmed in router.py
- Structured logging confirmed in service (4 logger.info calls)
- Error responses with status codes 400/404 confirmed in router

Slice-level checks for this task:
- Syntax validity: ✅
- Named graph usage: ✅
- Test files (T04), palette entries (T03), seed data (T02): not yet — later tasks

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('backend/app/task_templates/service.py').read()); ast.parse(open('backend/app/task_templates/router.py').read()); print('OK')"` | 0 | ✅ pass | <1s |
| 2 | `rg "template_service" backend/app/main.py` | 0 | ✅ pass | <1s |
| 3 | `rg "urn:sempkm:task-templates" backend/app/task_templates/service.py` | 0 | ✅ pass | <1s |
| 4 | `rg "instantiate" backend/app/task_templates/router.py` | 0 | ✅ pass | <1s |
| 5 | `rg "logger\." backend/app/task_templates/service.py` | 0 | ✅ pass | <1s |
| 6 | `rg "status_code=4" backend/app/task_templates/router.py` | 0 | ✅ pass | <1s |
| 7 | `python3 -c "import ast; ast.parse(open('backend/app/main.py').read()); print('OK')"` | 0 | ✅ pass | <1s |

## Diagnostics

- **Inspect templates:** `GET /api/task-templates` returns all stored templates as JSON array
- **Inspect single template:** `GET /api/task-templates/{iri}` returns full detail including parsed JSON blobs
- **Structured logs:** `TaskTemplateService` logs at INFO level for create (template IRI + title), update (template IRI + field list), delete (template IRI), and instantiate (template IRI + command count + subtask count)
- **Error shapes:** All error responses include `{"detail": "..."}` JSON body with specific messages
- **Instantiation audit:** Instantiate triggers EventStore.commit() producing an event graph, plus validation_queue.enqueue() for async SHACL validation — both visible in event log UI

## Deviations

None — implementation follows the task plan closely.

## Known Issues

None.

## Files Created/Modified

- `backend/app/task_templates/__init__.py` — package init
- `backend/app/task_templates/service.py` — TaskTemplateService with SPARQL CRUD + instantiate (285 lines)
- `backend/app/task_templates/router.py` — REST API + htmx browser routes (230 lines)
- `backend/app/templates/browser/template_picker.html` — template picker htmx partial with inline instantiate JS
- `backend/app/main.py` — added import, state wiring, and router includes for task_templates
- `.gsd/milestones/M034/slices/S05/S05-PLAN.md` — added observability verification checks
- `.gsd/milestones/M034/slices/S05/tasks/T01-PLAN.md` — added Observability Impact section
