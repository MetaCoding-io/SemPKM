# S05: Scheduler, Permissions, Bulk EventStore & browserVisible

**Goal:** Platform scheduler triggers app tasks at configured intervals with concurrency guard and retry. SDK clients enforce command whitelist, IRI prefix, and network domain restrictions. `commit_bulk()` records summary metadata. Types with `browserVisible: false` hidden from object browser.
**Demo:** A scheduled task fires at its configured interval. SDK rejects unpermitted commands and unapproved external URLs. Bulk commit creates a single summary event. Hidden types don't appear in the type picker or nav tree.

## Must-Haves

- SDK `CommandClient` rejects commands not in `manifest.permissions.commands` whitelist
- SDK `CommandClient` rejects IRIs not prefixed with `urn:sempkm:app:{app_id}:` (recursive scan of params)
- SDK `HttpClient` rejects URLs whose hostname doesn't match `manifest.permissions.network` globs
- `AppContext` passes permissions from manifest to clients at construction
- SDK runner reads manifest permissions and passes to `AppContext`
- `EventStore.commit_bulk()` creates summary-only event metadata (~10 triples) instead of per-operation
- SDK `ctx.commands.bulk()` context manager collecting operations with per-add permission enforcement
- Platform `POST /api/commands/bulk` endpoint dispatching batch and calling `commit_bulk()`
- Batch size limit enforced (1000 operations max)
- `ManifestIconDef.browserVisible` field (default `True`)
- `ShapesService.get_types()` filters out types with `browserVisible: false`
- `AppScheduler` with interval parsing, due-check, concurrency guard, retry with exponential backoff
- Scheduler wired into platform lifespan (start after `auto_start()`, stop on shutdown)
- Task invocation via HTTP POST through `AppProxy`
- Task history recorded in `app_task_runs` table
- User-adjustable intervals and pause via `app_task_config` table
- Admin detail page shows real task history with interval/pause controls
- Admin endpoints for interval adjustment and pause/resume

## Proof Level

- This slice proves: contract
- Real runtime required: no (all unit-testable without Docker)
- Human/UAT required: no (integration testing deferred to S07)

## Verification

- `cd backend && python -m pytest tests/test_app_permissions.py -v` — all permission enforcement tests pass
- `cd backend && python -m pytest tests/test_bulk_eventstore.py -v` — all bulk EventStore tests pass
- `cd backend && python -m pytest tests/test_browser_visible.py -v` — all browserVisible tests pass
- `cd backend && python -m pytest tests/test_app_scheduler.py -v` — all scheduler tests pass
- `cd backend && python -m pytest tests/test_app_admin.py -v` — admin endpoint tests still pass with new task management endpoints
- Failure path: `CommandClient.execute()` with unpermitted command raises `PermissionError` with clear message
- Failure path: `HttpClient.get()` with unapproved domain raises `PermissionError` with hostname and allowed list
- Failure path: `commit_bulk()` with >1000 operations raises `ValueError`
- Failure path: Scheduler logs task failure with error message and records in `app_task_runs`

## Observability / Diagnostics

- Runtime signals: scheduler logs task invocations and failures at INFO/ERROR level; `app_task_runs` table records every execution with status, duration_ms, error_message
- Inspection surfaces: `GET /admin/apps/{app_id}` detail page shows task history table; `app_task_config` table holds user overrides
- Failure visibility: `AppTaskRun.error_message` captures task failure details; `AppTaskRun.status` tracks running/success/error; scheduler concurrency guard prevents duplicate runs
- Redaction constraints: none (no secrets in task metadata)

## Integration Closure

- Upstream surfaces consumed: S02's SDK client stubs (`CommandClient`, `HttpClient`, `GraphClient`, `StateClient`), `AppContext`, SDK `runner.py`, `AppProxy`, `AppManifestSchema` with `AppPermissions`; S01's `AppManager`, `AppRegistry`, SQLAlchemy models (`AppTaskRun`, `AppTaskConfig`); S03's `admin_router.py` and `detail.html` template
- New wiring introduced in this slice: `AppScheduler` created in `lifespan()` after `auto_start()`, stopped on shutdown; bulk commands endpoint added to commands router
- What remains before the milestone is truly usable end-to-end: S06 (frontend L2+3 workspace contributions), S07 (test app + E2E), S08 (docs)

## Tasks

- [x] **T01: SDK permission enforcement in CommandClient and HttpClient** `est:1h30m`
  - Why: APP-05 requires SDK clients to enforce command whitelist, IRI prefix restrictions, and network domain restrictions. The SDK client stubs were built in S02 with enforcement explicitly deferred to S05.
  - Files: `backend/sdk/sempkm_app_sdk/clients/commands.py`, `backend/sdk/sempkm_app_sdk/clients/http.py`, `backend/sdk/sempkm_app_sdk/context.py`, `backend/sdk/sempkm_app_sdk/runner.py`, `backend/tests/test_app_permissions.py`
  - Do: (1) Add `allowed_commands` and `app_id` params to `CommandClient.__init__()`, reject `command_type not in allowed_commands` with `PermissionError`, recursively scan all string values in `params` dict for IRIs and reject any not starting with `urn:sempkm:app:{app_id}:` (ignore non-IRI strings — heuristic: starts with `urn:` or `http`). (2) Add `allowed_domains` param to `HttpClient.__init__()`, parse URL hostname (strip port), match against globs via `fnmatch.fnmatch`, raise `PermissionError` on mismatch. Empty list = block all. `["*"]` = allow all. (3) Update `AppContext` to accept a `permissions` dict and pass `allowed_commands`/`app_id`/`allowed_domains` to client constructors. (4) Update SDK `runner.py` to parse `manifest.permissions` from YAML and pass to `AppContext`. (5) Write comprehensive tests.
  - Verify: `cd backend && python -m pytest tests/test_app_permissions.py -v`
  - Done when: All permission tests pass — whitelisted commands succeed, non-whitelisted are rejected, IRI prefix enforced recursively, network globs matched correctly with port stripping, AppContext wires permissions to clients.

- [x] **T02: Bulk EventStore commit and SDK bulk context manager** `est:1h30m`
  - Why: APP-11 requires `EventStore.commit_bulk()` with summary-only metadata and SDK `ctx.commands.bulk()` context manager for batch ingestion. This supports the RSS app (M010) which creates 50-150 objects per feed poll.
  - Files: `backend/app/events/store.py`, `backend/app/events/models.py`, `backend/app/commands/router.py`, `backend/sdk/sempkm_app_sdk/clients/commands.py`, `backend/tests/test_bulk_eventstore.py`
  - Do: (1) Add bulk event constants to `events/models.py`: `BULK_EVENT_TYPE = SEMPKM.BulkEvent`, `BULK_SUMMARY = SEMPKM.summary`, `BULK_SOURCE = SEMPKM.source`, `BULK_OP_COUNT = SEMPKM.operationCount`, `BULK_AFFECTED_COUNT = SEMPKM.affectedCount`. (2) Add `commit_bulk()` to `EventStore` — same signature as `commit()` plus `summary: str` and `source: str` params. Creates event graph with ~10 metadata triples (type, timestamp, actor, summary, source, op count, affected count) instead of per-operation metadata. Data triples and materializations identical to `commit()`. Enforce max 1000 operations with `ValueError`. (3) Add `POST /api/commands/bulk` endpoint in commands router — accepts `{"commands": [...], "summary": "...", "source": "..."}`, dispatches all, collects `Operation` objects, calls `commit_bulk()`. (4) Add `bulk()` async context manager to SDK `CommandClient` — collects commands, enforces permissions per-add, posts to `/api/commands/bulk` on exit. (5) Write tests.
  - Verify: `cd backend && python -m pytest tests/test_bulk_eventstore.py -v`
  - Done when: `commit_bulk()` creates correct summary metadata, materializes identically to `commit()`, rejects >1000 ops. SDK `bulk()` context manager collects and posts. Platform endpoint dispatches and commits.

- [ ] **T03: browserVisible field and type filtering** `est:45m`
  - Why: APP-12 requires types marked `browserVisible: false` in Mental Model manifests to be hidden from the object browser while remaining queryable. Internal bookkeeping types (ReadActivity, sync cursors) clutter the browser.
  - Files: `backend/app/models/manifest.py`, `backend/app/services/shapes.py`, `backend/app/services/models.py`, `backend/tests/test_browser_visible.py`
  - Do: (1) Add `browserVisible: bool = True` to `ManifestIconDef` in `backend/app/models/manifest.py`. (2) Add `get_hidden_type_iris()` method to `ModelService` (or as a standalone function in `shapes.py`) — iterates installed model manifests, expands prefixed type names against each manifest's `prefixes` dict, returns `set[str]` of full IRIs where `browserVisible == False`. Returns empty set when no models are installed. (3) Modify `ShapesService.get_types()` to accept an optional `hidden_iris: set[str]` parameter and filter them out. The callers (`_handle_by_type()`, type filter pills, mount form) should pass the hidden set. Alternatively, wire `ModelService` into `ShapesService` as a dependency for cleaner call sites. (4) Write tests covering: field default, field parsing, filtering logic, no-models-installed edge case.
  - Verify: `cd backend && python -m pytest tests/test_browser_visible.py -v`
  - Done when: `ManifestIconDef` accepts `browserVisible`, `get_types()` excludes hidden types, types not in icons list remain visible, no crash when no models installed.

- [ ] **T04: AppScheduler with task history and admin integration** `est:2h`
  - Why: APP-06 requires a platform-owned scheduler that triggers app tasks at configured intervals with concurrency guard, retry, and admin visibility. The scheduler is the most complex new module in S05, with async loop, DB interaction, HTTP invocation, and admin UI.
  - Files: `backend/app/apps/scheduler.py` (new), `backend/app/main.py`, `backend/app/apps/admin_router.py`, `backend/app/templates/admin/apps/detail.html`, `backend/tests/test_app_scheduler.py`
  - Do: (1) Create `backend/app/apps/scheduler.py` with `AppScheduler` class: `__init__(manager, proxy, session_factory)`, `start()` creates asyncio task for `_loop()`, `stop()` cancels it. `_loop()` sleeps 60s then calls `_check_due_tasks()`. `_check_due_tasks()` iterates running apps, checks each task's due state (now - last_run >= interval), respects `app_task_config` overrides and pause flag. `_invoke_task(app_id, task)` posts to `/app/{app_id}/_tasks/{task_id}` via proxy, records `AppTaskRun` row. Concurrency guard via `_running_tasks: dict[tuple[str,str], datetime]` — skip if key present. Retry: on failure, decrement remaining retries, sleep backoff (1s × backoffMultiplier^attempt), retry. (2) Add `parse_interval_seconds(interval: str) -> int` function — handles shorthand (`5m`→300, `1h`→3600) and ISO 8601 (`PT5M`→300). (3) Wire into `main.py` lifespan: create `AppScheduler` after `auto_start()`, `await scheduler.start()`, store on `app.state.app_scheduler`. On shutdown, `await scheduler.stop()` before manager shutdown. (4) Extend `admin_router.py`: add `POST /admin/apps/{app_id}/tasks/{task_id}/interval` (update `app_task_config.interval_override`), `POST /admin/apps/{app_id}/tasks/{task_id}/pause` (toggle pause). Extend `app_detail()` to query `AppTaskRun` history and `AppTaskConfig` for each task. (5) Replace task history placeholder in `detail.html` with real table (task_id, status badge, started_at, duration, error) and per-task controls (interval input, pause toggle). (6) Write comprehensive tests: interval parsing, due-check logic, concurrency guard, retry backoff calculation, task history recording, config overrides, pause behavior, admin endpoints.
  - Verify: `cd backend && python -m pytest tests/test_app_scheduler.py tests/test_app_admin.py -v`
  - Done when: Scheduler loop logic is correct (due-check, concurrency, retry). Interval parsing handles all formats. Task runs recorded in DB. Admin detail shows real task history with controls. Admin endpoints adjust interval and toggle pause. All tests pass.

## Files Likely Touched

- `backend/sdk/sempkm_app_sdk/clients/commands.py`
- `backend/sdk/sempkm_app_sdk/clients/http.py`
- `backend/sdk/sempkm_app_sdk/context.py`
- `backend/sdk/sempkm_app_sdk/runner.py`
- `backend/app/events/store.py`
- `backend/app/events/models.py`
- `backend/app/commands/router.py`
- `backend/app/models/manifest.py`
- `backend/app/services/shapes.py`
- `backend/app/services/models.py`
- `backend/app/apps/scheduler.py` (new)
- `backend/app/main.py`
- `backend/app/apps/admin_router.py`
- `backend/app/templates/admin/apps/detail.html`
- `backend/tests/test_app_permissions.py` (new)
- `backend/tests/test_bulk_eventstore.py` (new)
- `backend/tests/test_browser_visible.py` (new)
- `backend/tests/test_app_scheduler.py` (new)
