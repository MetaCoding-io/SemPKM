---
estimated_steps: 8
estimated_files: 6
---

# T01: AppScheduler with interval parsing, concurrency guard, retry, and admin task history

**Slice:** S05 — Scheduler, Permissions, Bulk EventStore & browserVisible
**Milestone:** M009

## Description

Create the platform-owned `AppScheduler` that fires app tasks at configured intervals, skips tasks still running (concurrency guard), retries with exponential backoff, records results in `app_task_runs` table, and extends the admin detail page with a task history section and interval adjustment UI.

## Steps

1. Create `backend/app/apps/scheduler.py` with `AppScheduler` class. Constructor takes `app_registry`, `app_manager`, `app_proxy`, `async_sessionmaker`. Lifecycle: `start()` creates asyncio task for `_tick()` loop, `stop()` cancels it and awaits drain.
2. Implement `_parse_interval_seconds(interval_str: str) -> int` — supports shorthand (30s, 5m, 1h, 1d) and ISO 8601 (PT5M, PT1H30M). Enforce floor=30, ceiling=86400. Raise `ValueError` on invalid format.
3. Implement `_tick()` — runs every 60s. For each running app, iterate manifest tasks. Check `app_task_config` for overrides (paused, custom interval). Check `app_task_runs` for last run timestamp. If due and not in `_running_tasks`, dispatch `_invoke_task()`.
4. Implement `_invoke_task(app_id, task_id)` — add entry to `_running_tasks`, call `AppProxy.invoke_task(app_id, task_id, run_id, token)` (new internal method, uses pooled httpx client with `X-SemPKM-Task-Run` header), record `AppTaskRun` with status/duration_ms/error_message, remove from `_running_tasks`. Retry on failure per manifest `retryPolicy`.
5. Add `invoke_task(app_id, task_id, run_id)` method on `AppProxy` — uses `_get_or_create_client(app_id)` to POST to `/_tasks/{task_id}` on the app's UDS. Returns status code and response body. No Starlette Request needed.
6. Wire `AppScheduler` into `main.py` lifespan — create after proxy, start after `auto_start()`, stop in shutdown before proxy/manager.
7. Add admin endpoints: `GET /admin/apps/{app_id}/tasks` → task runs list, `POST /admin/apps/{app_id}/tasks/{task_id}/config` → interval override / pause toggle. Extend `detail.html` with task history `<details>` section.
8. Write `test_app_scheduler.py` — interval parsing (all formats + edge cases), concurrency guard, retry backoff calculation, task config CRUD, tick identifies due tasks.

## Must-Haves

- [ ] `_parse_interval_seconds` handles shorthand + ISO 8601, enforces floor/ceiling
- [ ] Concurrency guard prevents double-fire of same task
- [ ] Retry with exponential backoff up to manifest max_retries
- [ ] Task runs recorded in `app_task_runs` with status, duration, error
- [ ] Admin task history visible on detail page
- [ ] Interval adjustment and pause via admin UI

## Verification

- `cd backend && .venv/bin/pytest tests/test_app_scheduler.py -v` — all pass
- `cd backend && .venv/bin/pytest tests/ -v` — full suite, zero regressions
- `grep -c "AppScheduler" backend/app/main.py` — present in lifespan
- `grep -c "invoke_task" backend/app/apps/proxy.py` — method exists

## Inputs

- `backend/app/apps/proxy.py` — existing `AppProxy` with `_get_or_create_client()` and connection pooling (S02)
- `backend/app/apps/models.py` — `AppTaskRun`, `AppTaskConfig` SQLAlchemy models (S01)
- `backend/app/apps/manifest.py` — `AppTask` with `validate_interval`, `AppRetryPolicy` (S01)
- `backend/app/apps/admin_router.py` — existing admin routes (S03)
- `backend/app/templates/admin/apps/detail.html` — existing detail template with S05 placeholder (S03)

## Expected Output

- `backend/app/apps/scheduler.py` — new file, AppScheduler class
- `backend/app/apps/proxy.py` — modified, `invoke_task()` method added
- `backend/app/main.py` — modified, scheduler wired into lifespan
- `backend/app/apps/admin_router.py` — modified, task history and config endpoints
- `backend/app/templates/admin/apps/detail.html` — modified, task history section
- `backend/tests/test_app_scheduler.py` — new, ~15-20 tests

## Observability Impact

- **New logger:** `app.apps.scheduler` — INFO for task triggers and completions, WARNING for retries, ERROR for max retries exceeded
- **DB tables:** `app_task_runs` records every execution with status (`success`/`error`/`timeout`/`skipped`), `duration_ms`, `error_message`, `started_at`. `app_task_config` holds user overrides (interval, paused state).
- **Admin surface:** Task history `<details>` section on `/admin/apps/{app_id}` detail page shows recent runs with status and timing.
- **Failure state:** `AppTaskRun.error_message` captures task failure details. `AppTaskRun.status` distinguishes error types. Scheduler concurrency guard logs when a task invocation is skipped because a prior run is still active.
- **Inspection:** `GET /admin/apps/{app_id}/tasks` returns task run history. Future agents can query `app_task_runs` directly for debugging.
