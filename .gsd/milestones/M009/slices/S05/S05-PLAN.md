# S05: Scheduler, Permissions, Bulk EventStore & browserVisible

**Goal:** Platform scheduler triggers app tasks at configured intervals with concurrency guard and retry. SDK clients enforce command whitelist, IRI prefix, and network domain restrictions. `commit_bulk()` records summary metadata for batch operations. Types with `browserVisible: false` hidden from the object browser.
**Demo:** Admin task history shows a test task firing on interval, retrying on failure, respecting concurrency guard. SDK permission tests prove enforcement of all 4 scoping layers. Bulk event tests prove summary-metadata-only recording. Object browser excludes hidden types.

## Must-Haves

- `AppScheduler` with periodic tick loop, concurrency guard, retry with exponential backoff, DB recording
- Admin task history section on detail page with interval adjustment UI
- SDK `CommandClient` enforces command whitelist + IRI prefix on all created IRIs
- SDK `HttpClient` enforces network domain restriction via glob matching
- SDK `GraphClient` gates on `sparql_read` permission
- `EventStore.commit_bulk()` with summary metadata (~10 triples), batch size limit, all-or-nothing semantics
- SDK `bulk()` context manager on `CommandClient`
- `browserVisible` field on `ManifestIconDef`, `IconService.get_hidden_types()`, object browser filtering

## Proof Level

- This slice proves: contract (unit tests, no Docker required)
- Real runtime required: no — scheduler logic, permission enforcement, EventStore extension all testable with mocks
- Human/UAT required: no — live integration proof deferred to S07

## Verification

- `cd backend && .venv/bin/pytest tests/test_app_scheduler.py -v` — interval parsing, concurrency guard, retry backoff, task config CRUD, tick identifies due tasks
- `cd backend && .venv/bin/pytest tests/test_sdk_permissions.py -v` — command whitelist, IRI prefix, domain glob, sparql gate, state graph scoping
- `cd backend && .venv/bin/pytest tests/test_bulk_eventstore.py -v` — summary metadata, batch size, operation counts
- `cd backend && .venv/bin/pytest tests/test_browser_visible.py -v` — manifest parsing, icon service hidden set, explorer filtering
- `cd backend && .venv/bin/pytest tests/ -v` — full suite passes, zero regressions

## Observability / Diagnostics

- Runtime signals: `app.apps.scheduler` logger at INFO for task triggers, WARNING for retries, ERROR for max retries exceeded
- Inspection surfaces: `app_task_runs` table for execution history, `app_task_config` table for interval overrides, admin detail task history section
- Failure visibility: `AppTaskRun.error_message` captures last failure, `AppTaskRun.status` shows `error`/`timeout`/`skipped`, scheduler retry count tracked per invocation
- Redaction constraints: none — no secrets in scheduler/permission/bulk flows

## Integration Closure

- Upstream surfaces consumed: `AppProxy` connection pool (scheduler invokes tasks via UDS), `AppRegistry` (manifest permissions), `AppManager` (app status for scheduler), `EventStore.commit()` (base for `commit_bulk()`), `ManifestIconDef` (extension point for browserVisible), `_handle_by_type()` (filter point)
- New wiring introduced in this slice: `AppScheduler` started in `main.py` lifespan after `auto_start()`, admin detail template extended with task history section
- What remains before the milestone is truly usable end-to-end: S06 (frontend L2+3), S07 (test app + E2E), S08 (docs)

## Tasks

- [x] **T01: AppScheduler with interval parsing, concurrency guard, retry, and admin task history** `est:1h30m`
  - Why: Platform-owned scheduler is the backbone of app background tasks (APP-06). Tasks must fire on interval, not re-fire while running, retry with backoff, and record history. Admin needs visibility into task execution.
  - Files: `backend/app/apps/scheduler.py` (new), `backend/app/main.py`, `backend/app/apps/admin_router.py`, `backend/app/templates/admin/apps/detail.html`, `backend/tests/test_app_scheduler.py` (new)
  - Do:
    - Create `AppScheduler` class with `start()`/`stop()` lifecycle, `_tick()` loop (60s interval), `_check_tasks()` to find due tasks, `_invoke_task()` to POST via AppProxy
    - Implement `_parse_interval_seconds()` — shorthand ("30s", "5m", "1h", "1d") + ISO 8601 ("PT5M", "PT1H30M") → int seconds. Enforce floor 30s / ceiling 86400s.
    - Concurrency guard: `_running_tasks: dict[tuple[str, str], bool]` — skip task if already running
    - Retry: exponential backoff per manifest `retryPolicy` (max_retries, backoff_multiplier). Record each attempt status.
    - DB writes: `AppTaskRun` records with status (success/error/timeout/skipped), duration_ms, error_message. Read `AppTaskConfig` for interval overrides and pause state.
    - Wire into `main.py` lifespan — start after `auto_start()`, stop in shutdown before manager.
    - Add `invoke_task(app_id, task_id, run_id)` internal method on `AppProxy` that doesn't need a Starlette Request — uses the pooled httpx client directly with `X-SemPKM-Task-Run` header.
    - Admin: add `GET /admin/apps/{app_id}/tasks` endpoint returning task runs. Add task history `<details>` section to detail template with interval display and adjustment form (`POST /admin/apps/{app_id}/tasks/{task_id}/config`).
  - Verify: `pytest tests/test_app_scheduler.py -v` — all pass. Full suite no regressions.
  - Done when: interval parsing handles all formats, concurrency guard prevents double-fire, retry backoff computes correctly, task runs recorded in DB, admin shows history.

- [x] **T02: SDK permission enforcement on CommandClient, GraphClient, HttpClient** `est:45m`
  - Why: Permission enforcement (APP-05) is the "sandboxed" claim. Without it, apps can execute any command type, create IRIs outside their prefix, query any graph, and call any external URL.
  - Files: `backend/sdk/sempkm_app_sdk/clients/commands.py`, `backend/sdk/sempkm_app_sdk/clients/graph.py`, `backend/sdk/sempkm_app_sdk/clients/http.py`, `backend/sdk/sempkm_app_sdk/context.py`, `backend/sdk/sempkm_app_sdk/runner.py`, `backend/tests/test_sdk_permissions.py` (new)
  - Do:
    - `CommandClient.__init__` accepts `allowed_commands: set[str]` and `iri_prefix: str`. `execute()` raises `PermissionError` if command type not in whitelist. All IRI params validated against prefix (check `iri` for object.create, `subject`+`object` for edge.create, etc.).
    - `GraphClient.__init__` accepts `sparql_read: bool`. `query()` raises `PermissionError` if False.
    - `HttpClient.__init__` accepts `allowed_domains: list[str]`. `request()` extracts hostname from URL, validates against domain list using `fnmatch.fnmatch`. Empty list = no network access. `["*"]` = unrestricted.
    - `AppContext.__init__` accepts `permissions: dict` extracted from manifest. Threads to each client constructor.
    - `runner.py`: read `manifest.permissions` section, extract command types, IRI prefix from app_id, network domains. Pass to AppContext.
    - StateClient already scoped to `urn:sempkm:app:{appId}:state` — verify this in tests.
  - Verify: `pytest tests/test_sdk_permissions.py -v` — all pass. Full suite no regressions.
  - Done when: CommandClient rejects unpermitted types and IRI violations, GraphClient gates on sparql_read, HttpClient enforces domain globs, StateClient graph is scoped. All 5 clients covered.

- [ ] **T03: Bulk EventStore extension and SDK bulk context manager** `est:45m`
  - Why: Feed polling creates 50-150 operations per update — per-operation metadata overhead is unacceptable (APP-11, D145). `commit_bulk()` records ~10 triples per batch instead of ~5N.
  - Files: `backend/app/events/store.py`, `backend/app/events/models.py`, `backend/app/commands/router.py` (or new bulk endpoint), `backend/sdk/sempkm_app_sdk/clients/commands.py`, `backend/tests/test_bulk_eventstore.py` (new)
  - Do:
    - Add vocabulary constants in `events/models.py`: `BULK_EVENT_TYPE = "sempkm:BulkEvent"`, `EVENT_SUMMARY`, `EVENT_SOURCE`, `EVENT_OPERATION_COUNT`, `EVENT_AFFECTED_COUNT`.
    - Implement `EventStore.commit_bulk(operations, performed_by, summary, source)`. Same transactional pattern as `commit()` but: single event graph with `sempkm:BulkEvent` type, summary metadata (~10 triples: type, timestamp, actor, summary, source, operation_count, affected_count), data triples accumulated from all operations, materialization happens identically.
    - Batch size limit: raise `ValueError` if `len(operations) > 1000`.
    - Add `POST /api/commands/bulk` endpoint accepting `{"commands": [...], "summary": str, "source": str}`. Routes through `commit_bulk()`.
    - SDK `CommandClient.bulk()` — async context manager that accumulates operations, sends to `/api/commands/bulk` on `__aexit__`.
  - Verify: `pytest tests/test_bulk_eventstore.py -v` — all pass. Full suite no regressions.
  - Done when: `commit_bulk()` produces BulkEvent with summary metadata, batch size enforced, bulk API endpoint works, SDK context manager accumulates and sends.

- [ ] **T04: browserVisible field on Mental Model ManifestSchema** `est:30m`
  - Why: Apps create internal bookkeeping types (ReadActivity, sync cursors) that clutter the object browser (APP-12, D144). Hiding them improves UX without losing data access.
  - Files: `backend/app/models/manifest.py`, `backend/app/services/icons.py`, `backend/app/browser/workspace.py`, `backend/tests/test_browser_visible.py` (new)
  - Do:
    - Add `browser_visible: bool = True` field (alias `browserVisible`) to `ManifestIconDef` in `backend/app/models/manifest.py`.
    - Add `get_hidden_types(self) -> set[str]` to `IconService` — iterates `_cache`, returns type IRIs where `browserVisible` is False.
    - In `_handle_by_type()` in `workspace.py`, call `icon_service.get_hidden_types()` and filter results from `shapes_service.get_types()` before rendering.
    - Ensure filtering also applies to generic view type filter pills (same `get_types()` call in `views/router.py`).
  - Verify: `pytest tests/test_browser_visible.py -v` — all pass. Full suite no regressions.
  - Done when: ManifestIconDef parses `browserVisible: false` correctly, `get_hidden_types()` returns correct set, object browser excludes hidden types, generic view pills exclude hidden types.

## Files Likely Touched

- `backend/app/apps/scheduler.py` (new)
- `backend/app/apps/proxy.py` (add `invoke_task` method)
- `backend/app/apps/admin_router.py` (task history endpoints)
- `backend/app/templates/admin/apps/detail.html` (task history section)
- `backend/app/main.py` (scheduler lifespan wiring)
- `backend/sdk/sempkm_app_sdk/clients/commands.py` (permission enforcement + bulk)
- `backend/sdk/sempkm_app_sdk/clients/graph.py` (sparql gate)
- `backend/sdk/sempkm_app_sdk/clients/http.py` (domain enforcement)
- `backend/sdk/sempkm_app_sdk/context.py` (permissions threading)
- `backend/sdk/sempkm_app_sdk/runner.py` (manifest permissions reading)
- `backend/app/events/store.py` (commit_bulk)
- `backend/app/events/models.py` (bulk vocabulary constants)
- `backend/app/commands/router.py` (bulk endpoint)
- `backend/app/models/manifest.py` (browserVisible field)
- `backend/app/services/icons.py` (get_hidden_types)
- `backend/app/browser/workspace.py` (type filtering)
- `backend/tests/test_app_scheduler.py` (new)
- `backend/tests/test_sdk_permissions.py` (new)
- `backend/tests/test_bulk_eventstore.py` (new)
- `backend/tests/test_browser_visible.py` (new)
