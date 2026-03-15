# S02: Operations Log & PROV-O Foundation

**Goal:** Admin/debug UI shows timestamped operations log entries using PROV-O vocabulary; model install/remove, inference runs, and validation runs are logged to RDF in `urn:sempkm:ops-log`.

**Demo:** Owner navigates to `/admin/ops-log`, sees a reverse-chronological table of system activities. Each entry shows time, activity type, actor, status, and duration. Installing a model then revisiting the log shows the new entry. Filtering by activity type narrows the list.

## Must-Haves

- `OperationsLogService` with `log_activity()` and `list_activities()` methods
- All entries stored as `prov:Activity` in `urn:sempkm:ops-log` named graph
- PROV-O Starting Point terms: `prov:startedAtTime`, `prov:endedAtTime`, `prov:wasAssociatedWith`, `prov:used`
- SemPKM extensions: `sempkm:activityType`, `sempkm:status`, `sempkm:errorMessage`, `rdfs:label`
- Model install/remove logged from admin router (has user context)
- Inference run logged from inference router (has user context)
- Validation run logged from validation queue (system actor)
- Admin UI page at `/admin/ops-log` with reverse-chronological table
- Sidebar navigation link under Admin group
- Activity type filter dropdown
- Cursor-based pagination (not OFFSET)
- Owner role required

## Proof Level

- This slice proves: integration
- Real runtime required: yes (triplestore + Docker stack for browser verification)
- Human/UAT required: no

## Verification

- `backend/tests/test_ops_log.py` — unit tests for SPARQL generation (INSERT DATA format, SELECT query construction, escaping, cursor pagination logic)
- Docker stack browser verification: navigate to `/admin/ops-log`, confirm page renders with correct layout; install a model, confirm entry appears in log; run inference, confirm entry appears
- `grep -rn "ops_log" backend/app/admin/router.py backend/app/inference/router.py backend/app/validation/queue.py` confirms instrumentation wired

## Observability / Diagnostics

- Runtime signals: each `log_activity()` call produces a structured SPARQL INSERT to `urn:sempkm:ops-log`; Python logger emits `"Logged ops activity: {activity_type}"` at INFO level
- Inspection surfaces: `/admin/ops-log` page; direct SPARQL query against `urn:sempkm:ops-log` graph via SPARQL console
- Failure visibility: `log_activity()` failures are caught and logged at WARNING level (fire-and-forget — never blocks the primary operation)
- Redaction constraints: none (no PII in ops log entries — user IRIs are internal identifiers)

## Integration Closure

- Upstream surfaces consumed: `TriplestoreClient` (SPARQL read/write), `PROV` namespace from `namespaces.py`, `SYSTEM_ACTOR_IRI` from `events/models.py`, admin router patterns, sidebar template
- New wiring introduced: `OperationsLogService` in DI (`dependencies.py` + `main.py` lifespan), ops log calls in admin router install/remove, inference router, validation queue worker
- What remains before the milestone is truly usable end-to-end: S06 (PROV-O Alignment Design doc) depends on this slice's PROV-O usage patterns; S09 (E2E Tests & Docs) will add Playwright tests

## Tasks

- [x] **T01: Build OperationsLogService with unit tests** `est:1h`
  - Why: Core service module — all other tasks depend on this API existing
  - Files: `backend/app/services/ops_log.py`, `backend/tests/test_ops_log.py`
  - Do: Create `OperationsLogService` following `QueryService` patterns — raw SPARQL strings, `_esc()` helper, `_now_iso()`. Methods: `log_activity()` (INSERT DATA to named graph), `list_activities()` (cursor-paginated SELECT), `get_activity()`, `count_activities()`. IRI pattern `urn:sempkm:ops-log:{uuid}`. Unit tests validate SPARQL string generation, escaping edge cases, cursor filter construction, and result parsing.
  - Verify: `cd backend && python -m pytest tests/test_ops_log.py -v` passes
  - Done when: Service module exists with all 4 methods, unit tests pass covering INSERT format, SELECT with/without cursor, activity type filtering

- [x] **T02: Wire DI and instrument model/inference/validation** `est:45m`
  - Why: The service must be instantiated in the app lifespan, injectable via DI, and called from the three target code paths
  - Files: `backend/app/main.py`, `backend/app/dependencies.py`, `backend/app/admin/router.py`, `backend/app/inference/router.py`, `backend/app/validation/queue.py`
  - Do: (1) Import and instantiate `OperationsLogService` in `main.py` lifespan, store on `app.state.ops_log_service`. (2) Add `get_ops_log_service()` to `dependencies.py`. (3) In `admin_models_install()` and `admin_models_remove()`, call `ops_log.log_activity()` after success/failure with user IRI from `require_role("owner")`. (4) In `inference/router.py` `run_inference()`, call `ops_log.log_activity()` after result with user IRI. (5) In `validation/queue.py` `_worker()`, accept `ops_log` in constructor, call `log_activity()` after validation completes with `SYSTEM_ACTOR_IRI`. All ops log calls wrapped in try/except — never block the primary operation.
  - Verify: `grep -rn "ops_log" backend/app/main.py backend/app/dependencies.py backend/app/admin/router.py backend/app/inference/router.py backend/app/validation/queue.py` shows all integration points wired
  - Done when: All 5 files updated; service injectable; model install/remove, inference, and validation all emit ops log entries

- [x] **T03: Admin UI — ops log page, route, and sidebar link** `est:45m`
  - Why: The visible surface that makes the operations log useful to admin users
  - Files: `backend/app/admin/router.py`, `backend/app/templates/admin/ops_log.html`, `backend/app/templates/admin/index.html`, `backend/app/templates/components/_sidebar.html`
  - Do: (1) Add `GET /admin/ops-log` route in admin router — calls `list_activities()` with optional `activity_type` query param and `cursor` param, renders template with htmx partial support. (2) Create `ops_log.html` template extending `base.html` — page title, lead text, activity type filter dropdown (htmx-driven), reverse-chronological table (Time, Activity, Type, Actor, Status, Duration columns), expandable row details (related resources, error messages), "Load more" button for cursor pagination. (3) Add "Operations Log" card to `admin/index.html` dashboard. (4) Add "Operations Log" nav link to `_sidebar.html` in Admin group after Webhooks, using `activity` Lucide icon.
  - Verify: Docker stack running → browser navigate to `/admin/ops-log` → page renders with correct layout, sidebar link visible and active
  - Done when: Ops log page renders, sidebar link works, filter dropdown narrows results, pagination loads more entries

## Files Likely Touched

- `backend/app/services/ops_log.py` (new)
- `backend/tests/test_ops_log.py` (new)
- `backend/app/main.py`
- `backend/app/dependencies.py`
- `backend/app/admin/router.py`
- `backend/app/inference/router.py`
- `backend/app/validation/queue.py`
- `backend/app/templates/admin/ops_log.html` (new)
- `backend/app/templates/admin/index.html`
- `backend/app/templates/components/_sidebar.html`
