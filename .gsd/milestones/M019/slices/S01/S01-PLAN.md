# S01: Auth + Client + Pull Sync

**Goal:** Todoist API token auth, REST client, field mapping, and pull sync creating bpkm:Task objects — fully proven by unit tests.
**Demo:** User enters Todoist PAT, connects, selects projects, triggers sync, sees tasks with correct priorities/dates/labels — proven by 100+ unit tests.

## Must-Haves

- PAT authentication with token storage, verification, and connection status
- TodoistClient wrapping SDK HttpClient for REST v2 endpoints (tasks, projects, labels)
- Field mapper with correct priority inversion (1→low, 2→medium, 3→high, 4→critical) and all field transforms
- PersonMatcher adapted from GitHub sync (email-based SPARQL lookup)
- pull_sync() creating bpkm:Task objects via two-phase bulk pattern
- App manifest, route handlers, connect/disconnect flow, project selection UI
- 100+ unit tests covering all modules

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_todoist_*.py -v` — 100+ tests pass
- Auth tests: token storage, verification, masking, connection status, disconnect
- Client tests: get_tasks, get_projects, get_labels, auth header, error handling
- Field mapper tests: all 4 priority levels both directions, status mapping, due date extraction, label mapping, URL/ID preservation
- Sync engine tests: two-phase bulk create, existing task detection, delta handling, per-task error isolation

## Observability / Diagnostics

- Runtime signals: `todoist.sync` logger — INFO per sync (created/updated/unchanged counts), WARNING on per-task failures
- Inspection surfaces: `get_connection_status()` returns `{connected, auth_method, todoist_email, projects_count}`
- Failure visibility: `last_pull_result` state key — structured JSON with counts and error arrays

## Tasks

- [x] **T01: App scaffold + manifest + auth** `est:45m`
  - Why: Foundation for the entire app — manifest, directory structure, PAT auth module
  - Files: `apps/todoist-sync/manifest.yaml`, `apps/todoist-sync/app.py`, `apps/todoist-sync/services/__init__.py`, `apps/todoist-sync/services/auth.py`, `apps/todoist-sync/frontend/templates/connect.html`, `apps/todoist-sync/frontend/templates/connect_status.html`
  - Do: Clone github-sync structure. Manifest with appId "todoist-sync", network domain "api.todoist.com". Auth module with store_token(), verify_token() (GET /rest/v2/projects as health check), get_connection_status(), clear_credentials(), mask_token(). Route handlers: connect page, PAT submission, disconnect. Templates with PAT input form and status display. All htmx URLs use `/app/todoist-sync/` prefix per knowledge base.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_todoist_auth.py -v`
  - Done when: 15+ auth unit tests pass covering storage, verification, masking, status, disconnect

- [x] **T02: TodoistClient + field mapper** `est:45m`
  - Why: Core data access and transformation — client wraps REST API, mapper handles all field transforms
  - Files: `apps/todoist-sync/services/todoist_client.py`, `apps/todoist-sync/services/field_mapper.py`, `backend/tests/test_todoist_client.py`, `backend/tests/test_todoist_field_mapper.py`
  - Do: TodoistClient with get_tasks(project_id=None), get_projects(), get_labels() — simple GET requests, no pagination needed. Auth header via stored token. Field mapper with build_task_properties() mapping all fields per research table. Priority inversion: TODOIST_TO_BPKM_PRIORITY = {1:"low", 2:"medium", 3:"high", 4:"critical"} and reverse. Status: is_completed false→"todo", true→"done". Due date: extract due.date as xsd:date. Labels: direct to bpkm:tags array. URL, external ID, project name resolution.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_todoist_client.py tests/test_todoist_field_mapper.py -v`
  - Done when: 15+ client tests + 40+ field mapper tests pass. All 4 priority levels tested in both directions. Due date edge cases (no due, date-only, datetime) tested.

- [x] **T03: PersonMatcher + sync engine + pull routes** `est:45m`
  - Why: Completes the pull sync pipeline — person resolution, sync orchestration, and route wiring
  - Files: `apps/todoist-sync/services/person_matcher.py`, `apps/todoist-sync/services/sync_engine.py`, `apps/todoist-sync/app.py`, `apps/todoist-sync/frontend/templates/connect_status.html`, `backend/tests/test_todoist_person_matcher.py`, `backend/tests/test_todoist_sync_engine.py`
  - Do: Copy person_matcher from github-sync (email-based SPARQL lookup, creation on miss, LRU cache). Sync engine with pull_sync(): fetch tasks from selected projects, fetch labels for lookup, build properties via field mapper, two-phase bulk create (object.create → SPARQL discover IRI → body.set + edge.create), existing task detection by bpkm:externalId, per-task error isolation, structured result logging. Route handlers: sync_now (POST), poll-tasks task handler, project selection (GET projects, POST selected). Connect status template with project checkboxes.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_todoist_person_matcher.py tests/test_todoist_sync_engine.py -v`
  - Done when: 10+ person matcher tests + 40+ sync engine tests pass. Pull sync creates correct commands, handles errors per-task, reports structured results.

## Files Likely Touched

- `apps/todoist-sync/manifest.yaml`
- `apps/todoist-sync/app.py`
- `apps/todoist-sync/services/__init__.py`
- `apps/todoist-sync/services/auth.py`
- `apps/todoist-sync/services/todoist_client.py`
- `apps/todoist-sync/services/field_mapper.py`
- `apps/todoist-sync/services/person_matcher.py`
- `apps/todoist-sync/services/sync_engine.py`
- `apps/todoist-sync/frontend/templates/connect.html`
- `apps/todoist-sync/frontend/templates/connect_status.html`
- `backend/tests/test_todoist_auth.py`
- `backend/tests/test_todoist_client.py`
- `backend/tests/test_todoist_field_mapper.py`
- `backend/tests/test_todoist_person_matcher.py`
- `backend/tests/test_todoist_sync_engine.py`
