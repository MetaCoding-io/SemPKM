---
id: T01
parent: S05
milestone: M009
provides:
  - AppScheduler with periodic tick, concurrency guard, exponential retry, DB recording
  - parse_interval_seconds for shorthand (30s/5m/1h/1d) and ISO 8601 (PT5M/PT1H30M)
  - AppProxy.invoke_task() for scheduler-initiated task calls over UDS
  - Admin task history section with config override UI on detail page
  - GET /admin/apps/{app_id}/tasks and POST /admin/apps/{app_id}/tasks/{task_id}/config endpoints
key_files:
  - backend/app/apps/scheduler.py
  - backend/app/apps/proxy.py
  - backend/app/apps/admin_router.py
  - backend/app/templates/admin/apps/detail.html
  - backend/app/main.py
  - backend/tests/test_app_scheduler.py
  - backend/tests/test_app_admin.py
key_decisions:
  - Scheduler tick interval set to 60s — matches task minimum granularity of 30s
  - invoke_task uses 300s timeout to accommodate long-running tasks
  - Task run recording happens in a finally block to guarantee persistence even on exception
patterns_established:
  - parse_interval_seconds as a public function reused by both scheduler and admin config validation
  - Concurrency guard via _running_tasks set keyed by (app_id, task_id) tuple
observability_surfaces:
  - app.apps.scheduler logger — INFO for dispatches/completions, WARNING for retries, ERROR for exhausted retries
  - app_task_runs table — full execution history with status/duration_ms/error_message
  - app_task_config table — user overrides for interval and pause state
  - Admin detail page task history <details> section
duration: 25m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: AppScheduler with interval parsing, concurrency guard, retry, and admin task history

**Built AppScheduler with 60s tick loop, concurrency guard, exponential backoff retry, DB recording, and admin task history UI with interval/pause config**

## What Happened

Created `scheduler.py` with the `AppScheduler` class and `parse_interval_seconds` utility. The scheduler ticks every 60s, queries running apps from the DB, evaluates each manifest task against its configured interval and last run timestamp, and dispatches due tasks via `AppProxy.invoke_task()`. A `_running_tasks` set prevents double-firing. Retry uses exponential backoff (`multiplier^attempt`) clamped to the manifest's `maxBackoff`. Every invocation is recorded as an `AppTaskRun` row.

Added `invoke_task(app_id, task_id, run_id)` to `AppProxy` — posts directly to `/_tasks/{task_id}` on the app's UDS with the `X-SemPKM-Task-Run` header, no Starlette Request needed.

Wired the scheduler into `main.py` lifespan: created after the proxy, started after `auto_start()`, stopped during shutdown before proxy/manager teardown.

Added two admin endpoints: `GET /admin/apps/{app_id}/tasks` returns task run JSON, `POST /admin/apps/{app_id}/tasks/{task_id}/config` saves interval overrides and pause state. Updated the detail template to replace the task history placeholder with a real `<details>` section showing task configs (interval, pause toggle, save button) and a runs table (task, started, status, duration, error).

Fixed the existing `test_app_admin.py` fixture to provide `async_session_factory` on app state and updated the placeholder text assertion since apps without tasks now show "This app has no scheduled tasks."

## Verification

- `pytest tests/test_app_scheduler.py -v` — 40 passed covering interval parsing (shorthand, ISO 8601, floor/ceiling, edge cases), backoff calculation, concurrency guard, retry behavior (success/failure/exception/zero-retries), task config (pause, override), tick logic (due/not-due/no-tasks), and lifecycle (start/stop).
- `pytest tests/test_app_admin.py -v` — 33 passed, zero regressions from detail route changes.
- `pytest tests/ -v` — 1293 passed, 0 failed.
- `grep -c "AppScheduler" backend/app/main.py` → 4 (present in lifespan).
- `grep -c "invoke_task" backend/app/apps/proxy.py` → 1 (method exists).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/pytest tests/test_app_scheduler.py -v` | 0 | ✅ pass | 0.2s |
| 2 | `cd backend && .venv/bin/pytest tests/ -v` | 0 | ✅ pass | 39.6s |
| 3 | `grep -c "AppScheduler" backend/app/main.py` | 0 | ✅ pass | <1s |
| 4 | `grep -c "invoke_task" backend/app/apps/proxy.py` | 0 | ✅ pass | <1s |

## Diagnostics

- **Logger:** `app.apps.scheduler` — INFO on task dispatch and completion, WARNING on retries, ERROR when retries exhausted.
- **DB tables:** `app_task_runs` has status/duration_ms/error_message per run. `app_task_config` has interval_override and paused per (app_id, task_id).
- **Admin UI:** `/admin/apps/{app_id}` detail page shows task configs with interval/pause form and recent runs table.
- **API:** `GET /admin/apps/{app_id}/tasks` returns JSON array of recent task runs for debugging.

## Deviations

None. All plan steps implemented as specified.

## Known Issues

None.

## Files Created/Modified

- `backend/app/apps/scheduler.py` — new: AppScheduler class, parse_interval_seconds, calculate_backoff
- `backend/app/apps/proxy.py` — added invoke_task() method for scheduler-initiated task calls
- `backend/app/apps/admin_router.py` — added task history and config endpoints, imports for models
- `backend/app/templates/admin/apps/detail.html` — replaced placeholder with task history details section
- `backend/app/main.py` — wired AppScheduler into lifespan (create/start/stop)
- `backend/tests/test_app_scheduler.py` — new: 40 tests across 8 test classes
- `backend/tests/test_app_admin.py` — fixed fixture to provide async_session_factory, updated assertion
