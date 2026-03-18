---
id: T04
parent: S05
milestone: M009
provides:
  - AppScheduler class with periodic due-check loop, concurrency guard, exponential backoff retry, and DB recording
  - parse_interval_seconds() for shorthand and ISO 8601 interval conversion
  - Admin endpoints POST /admin/apps/{app_id}/tasks/{task_id}/interval and /pause for user-adjustable task config
  - Admin detail page shows real scheduled task info with run history, pause/resume, and interval adjustment
key_files:
  - backend/app/apps/scheduler.py
  - backend/app/apps/admin_router.py
  - backend/app/templates/admin/apps/detail.html
  - backend/app/main.py
  - backend/tests/test_app_scheduler.py
key_decisions:
  - Scheduler invokes tasks directly via httpx over UDS rather than using AppProxy.forward() which requires a Starlette Request object — simpler, avoids request fabrication
  - Concurrency guard uses dict[tuple[str,str], datetime] — tracks start time for observability, not just presence
  - Task runs recorded as "running" immediately on invocation start, then updated to success/error on completion — enables detecting stuck tasks
patterns_established:
  - Scheduler due-check pattern: iterate registry → filter running apps → check each task's config (pause/override) → compare elapsed time → invoke as separate asyncio task
  - Admin endpoint upsert pattern for composite-PK config tables: GET existing row, create if None, update if exists
observability_surfaces:
  - app_task_runs table: SELECT * FROM app_task_runs WHERE app_id=? ORDER BY started_at DESC — full execution history with status, duration_ms, error_message
  - app_task_config table: interval_override and paused state per (app_id, task_id)
  - Scheduler logger at INFO (task invocations, completions), ERROR (failures with error messages), DEBUG (skipped tasks with reason)
  - Admin detail page task history section — visual rendering of run history with status badges
duration: 25m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T04: AppScheduler with task history and admin integration

**Built the platform-owned task scheduler with interval parsing, concurrency guard, exponential backoff retry, DB recording, and admin UI integration for task management.**

## What Happened

Created `AppScheduler` class that runs in the main asyncio event loop, checking for due tasks every 60 seconds. Each task's due state considers: (1) user config override interval vs manifest default, (2) pause state, (3) concurrency guard (one invocation per task at a time), (4) elapsed time since last run. First-run tasks are immediately due.

Task invocation happens via direct httpx POST over UDS to `/_tasks/{task_id}` on the app subprocess. On failure, retries with exponential backoff per the task's `retryPolicy` (maxRetries, backoffMultiplier, maxBackoff). Every invocation records an `AppTaskRun` row with status, duration_ms, and error_message.

Wired scheduler into `main.py` lifespan — starts after `auto_start()` completes (so apps are running), stops during shutdown before proxy/manager cleanup.

Extended admin router with two new endpoints: interval update (validates format, upserts `AppTaskConfig`) and pause toggle (upserts with flipped boolean). Extended `app_detail()` to query task history and config from DB.

Replaced the detail template's task placeholder with a full task management section: each manifest task shows its ID, description, current interval (with override indication), pause/resume toggle, configurable interval form, retry policy info, and a table of recent runs with status badges (success=green, error=red, running=yellow).

Updated existing admin tests to supply a mock `async_session_factory` since `app_detail()` now queries the DB.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_app_scheduler.py -v` — **31 passed** (interval parsing, concurrency guard, retry backoff, admin interval/pause endpoints, task run recording, detail rendering, loop resilience, config override, pause skip)
- `cd backend && .venv/bin/python -m pytest tests/test_app_admin.py -v` — **26 passed** (all existing admin tests pass with new session factory mock)
- `cd backend && .venv/bin/python -m pytest tests/test_app_permissions.py tests/test_bulk_eventstore.py tests/test_app_browser.py -v` — **53 passed** (prior slice tasks still green)
- Combined run: 57 + 53 = **110 tests all passing**, zero regressions

## Diagnostics

- Inspect task runs: `SELECT * FROM app_task_runs WHERE app_id = 'rss-reader' ORDER BY started_at DESC`
- Inspect config overrides: `SELECT * FROM app_task_config WHERE app_id = 'rss-reader'`
- Scheduler logging: `app.apps.scheduler` logger — INFO for invocations/completions, ERROR for failures, DEBUG for skipped tasks
- If a task appears stuck: check `_running_tasks` dict (task_key present = concurrency guard active); check `app_task_runs` for rows with `status='running'` and old `started_at`
- Admin visibility: `GET /admin/apps/{app_id}` shows full task history section with controls

## Deviations

- Used direct httpx-over-UDS for task invocation instead of adding `invoke_task()` to `AppProxy` — AppProxy.forward() requires a Starlette Request object which would need fabrication; direct httpx is cleaner and equivalent
- Plan's T04 task file on disk is "browserVisible" (already completed as T03-SUMMARY). The inlined task plan was authoritative — executed the scheduler task as dispatched.

## Known Issues

- None

## Files Created/Modified

- `backend/app/apps/scheduler.py` — new: AppScheduler class, parse_interval_seconds(), CHECK_INTERVAL constant
- `backend/app/main.py` — scheduler creation after auto_start, scheduler.stop() in shutdown
- `backend/app/apps/admin_router.py` — added imports, _format_duration_ms, _validate_interval, enriched app_detail() with task queries, new interval/pause endpoints
- `backend/app/templates/admin/apps/detail.html` — replaced task placeholder with full task management section
- `backend/tests/test_app_scheduler.py` — new: 31 tests covering scheduler logic and admin endpoints
- `backend/tests/test_app_admin.py` — updated _create_test_app to supply mock async_session_factory, updated placeholder assertion text
