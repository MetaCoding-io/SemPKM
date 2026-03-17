---
estimated_steps: 7
estimated_files: 5
---

# T04: AppScheduler with task history and admin integration

**Slice:** S05 — Scheduler, Permissions, Bulk EventStore & browserVisible
**Milestone:** M009

## Description

The platform-owned scheduler (D141) triggers app tasks at configured intervals, enforces concurrency (one invocation per task at a time), retries on failure with exponential backoff, records history in `app_task_runs`, and exposes controls in the admin detail page. This is the most complex new module in S05.

The scheduler runs in the main asyncio event loop (fine for <10 apps with minute-level intervals). It checks due tasks every 60 seconds, invokes them via HTTP POST through the `AppProxy`, and records results. Users can adjust intervals and pause tasks via the admin UI.

Key constraint: scheduler should start *after* `auto_start()` completes so it doesn't check tasks for apps that haven't started yet.

## Steps

1. **Create `backend/app/apps/scheduler.py`** with `AppScheduler` class:
   - `__init__(self, manager, proxy, session_factory)` — stores refs, initializes `_running_tasks: dict[tuple[str, str], datetime]` for concurrency guard, `_task: asyncio.Task | None = None`
   - `async start()` — creates asyncio task for `_loop()`
   - `async stop()` — cancels the asyncio task, logs shutdown
   - `async _loop()` — `while True: await asyncio.sleep(60); await _check_due_tasks()`. Wrap body in try/except to prevent loop death on transient errors.
   - `async _check_due_tasks()` — iterate `manager.registry.list_apps()`, skip non-running apps, check each task's due state
   - `_is_due(app_id, task, config_override)` — compare `now - last_run_at >= interval_seconds`. On first run (no history), task is immediately due.
   - `async _invoke_task(app_id, task)` — set concurrency guard, POST to app via proxy `forward()`, record `AppTaskRun` row with status/duration/error. On failure, check retry policy and schedule retries.
   - `async _get_last_run(session, app_id, task_id)` — query most recent `AppTaskRun` for this app/task
   - `async _get_config(session, app_id, task_id)` — query `AppTaskConfig` for overrides

2. **Add `parse_interval_seconds(interval: str) -> int`** function (in `scheduler.py` or a shared util):
   - Handle shorthand: regex `^(\d+)(s|m|h|d)$` → multiply by unit factor
   - Handle ISO 8601: regex `^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$` → sum hours*3600 + minutes*60 + seconds
   - Raise `ValueError` for unparseable intervals
   - The manifest validator already accepts these formats, so this just needs to convert to seconds

3. **Wire into `main.py` lifespan**:
   - After `await app_manager.auto_start()` block, create `AppScheduler(app_manager, app_proxy, async_session_factory)`
   - `await scheduler.start()`
   - `app.state.app_scheduler = scheduler`
   - In shutdown section (before `app_manager.shutdown_all()`), add `await scheduler.stop()`

4. **Extend admin router** (`backend/app/apps/admin_router.py`):
   - `POST /admin/apps/{app_id}/tasks/{task_id}/interval` — accepts form field `interval`, validates format (same regex as manifest), upserts `AppTaskConfig` row with `interval_override`. Returns redirect to detail page.
   - `POST /admin/apps/{app_id}/tasks/{task_id}/pause` — toggles `AppTaskConfig.paused`. Upserts row if not exists. Returns redirect to detail page.
   - Extend `app_detail()` context: query `AppTaskRun` (last 20 per task, ordered by `started_at` desc) and `AppTaskConfig` (overrides/pause state). Pass `task_history` and `task_configs` to template.
   - Also pass `manifest.tasks` list to template so it can show all declared tasks even if none have run yet.

5. **Replace task history placeholder** in `backend/app/templates/admin/apps/detail.html`:
   - Replace the `<p>Tasks will appear here...</p>` placeholder
   - For each task in manifest: show task_id, description, current interval (override or default), pause toggle button, interval adjustment form
   - Below each task: table of recent runs (status badge, started_at formatted, duration in human-readable form, error message if any)
   - Status badges: `success` = green, `error` = red, `running` = yellow
   - Pause toggle: htmx POST to pause endpoint, swaps detail content
   - Interval form: small inline form with text input + submit button, htmx POST

6. **Write tests** (`backend/tests/test_app_scheduler.py`):
   - `parse_interval_seconds("5m")` → 300
   - `parse_interval_seconds("1h")` → 3600
   - `parse_interval_seconds("30s")` → 30
   - `parse_interval_seconds("PT5M")` → 300
   - `parse_interval_seconds("PT1H30M")` → 5400
   - `parse_interval_seconds("invalid")` → ValueError
   - Due check: task is due when `now - last_run_at >= interval` (mock datetime)
   - Due check: task with no history is immediately due
   - Concurrency guard: skip task if key in `_running_tasks`
   - Concurrency guard: key removed after task completes
   - Retry backoff calculation: 1s, 2s, 4s for maxRetries=3, backoffMultiplier=2
   - Config override: `interval_override` takes precedence over manifest default
   - Pause: paused task skipped in due check
   - Admin endpoints: interval update creates/updates `AppTaskConfig` row
   - Admin endpoints: pause toggle flips `AppTaskConfig.paused`
   - Task run recording: `AppTaskRun` row created with correct fields

7. **Verify**: `cd backend && python -m pytest tests/test_app_scheduler.py tests/test_app_admin.py -v`

## Must-Haves

- [ ] `parse_interval_seconds()` handles shorthand and ISO 8601 formats
- [ ] Scheduler due-check logic correct (interval comparison, first-run handling)
- [ ] Concurrency guard prevents duplicate task invocations
- [ ] Retry with exponential backoff on task failure
- [ ] Task runs recorded in `app_task_runs` table with status/duration/error
- [ ] User-adjustable intervals via `app_task_config` overrides
- [ ] Pause/resume via `app_task_config.paused` flag
- [ ] Scheduler wired into platform lifespan (start after auto_start, stop on shutdown)
- [ ] Admin detail page shows real task history with controls
- [ ] Admin endpoints for interval adjustment and pause toggle

## Verification

- `cd backend && python -m pytest tests/test_app_scheduler.py -v` — all pass
- `cd backend && python -m pytest tests/test_app_admin.py -v` — existing + new admin tests pass
- Scheduler `_loop()` handles exceptions without crashing the loop

## Observability Impact

- Signals added: scheduler logs task invocations at INFO, failures at ERROR with error message; `app_task_runs` table records every execution
- How a future agent inspects this: `SELECT * FROM app_task_runs WHERE app_id = ? ORDER BY started_at DESC` for task history; admin detail page renders this visually
- Failure state exposed: `AppTaskRun.error_message` captures failure details; `AppTaskRun.status = 'error'` flags failed runs; scheduler concurrency guard logs skipped tasks at DEBUG

## Inputs

- `backend/app/apps/manager.py` — `AppManager` with `registry`, `get_status()` for iterating apps
- `backend/app/apps/proxy.py` — `AppProxy` with `forward()` for HTTP POST to app subprocesses
- `backend/app/apps/models.py` — `AppTaskRun`, `AppTaskConfig` SQLAlchemy models (already created in S01 migration)
- `backend/app/apps/manifest.py` — `AppTask` with `id`, `interval`, `retryPolicy`, `configurable` fields
- `backend/app/apps/admin_router.py` — existing admin router with `app_detail()` endpoint (~7.6K)
- `backend/app/templates/admin/apps/detail.html` — existing template with task history placeholder at line ~159
- `backend/app/main.py` — lifespan function where scheduler gets wired (~lines 336-396)
- T01/T02/T03 outputs — permission enforcement, bulk EventStore, browserVisible (scheduler is independent of these)

## Expected Output

- `backend/app/apps/scheduler.py` — new file with `AppScheduler` class and `parse_interval_seconds()` function
- `backend/app/main.py` — scheduler creation and lifecycle wiring in lifespan
- `backend/app/apps/admin_router.py` — interval and pause endpoints, extended detail context
- `backend/app/templates/admin/apps/detail.html` — real task history section with controls
- `backend/tests/test_app_scheduler.py` — ~15-20 tests covering scheduler logic and admin endpoints
