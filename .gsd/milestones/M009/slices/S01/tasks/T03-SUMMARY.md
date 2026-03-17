---
id: T03
parent: S01
milestone: M009
provides:
  - AppRegistry in-memory manifest cache with register/unregister/get/list
  - AppManager lifecycle engine with install/start/stop/restart/uninstall/get_status/get_logs
  - Crash recovery with exponential backoff (1s, 2s, 4s) up to 3 retries
  - Health check polling via httpx UDS transport
  - Log capture ring buffer (deque maxlen=100)
key_files:
  - backend/app/apps/registry.py
  - backend/app/apps/manager.py
  - backend/tests/test_app_manager.py
key_decisions:
  - Typed triplestore_client parameter as object to avoid circular import (TriplestoreClient lives in app.triplestore.client)
  - Used async_sessionmaker[AsyncSession] parameter type matching existing session.py pattern
  - _stop_flags set distinguishes intentional stop from crash — watcher checks membership before triggering recovery
  - _install_lock prevents concurrent install races (single asyncio.Lock since all installs share venv creation)
  - restart_count persisted to DB before restart attempt so count survives if restart itself crashes
patterns_established:
  - Lifecycle state machine pattern — install→start→[restart/stop]→uninstall with DB status tracking
  - Crash watcher pattern — asyncio.Task per app that awaits proc.wait() and decides restart vs error
  - Health check pattern — httpx AsyncClient with UDS transport polling /_health endpoint
observability_surfaces:
  - AppManager.get_status(app_id) returns {app_id, status, pid, uptime_seconds, restart_count, error_message, version}
  - AppManager.get_logs(app_id) returns last 100 stdout/stderr lines
  - app_instances.status transitions logged at INFO
  - Crash recovery logged at WARNING with exit code and attempt number
  - Max-retry exhaustion logged at ERROR with error_message persisted to DB
duration: 25m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T03: AppRegistry + AppManager lifecycle engine

**Built the core subprocess lifecycle manager with crash recovery, health checking, and log capture — 31 unit tests passing.**

## What Happened

Created `AppRegistry` as a thin in-memory dict wrapper providing O(1) manifest lookup by app_id, with register/unregister/get/list/get_app methods.

Built `AppManager` as the lifecycle orchestrator with:
- **install()** — validates manifest, checks platform version compatibility via `packaging.specifiers.SpecifierSet`, creates venv via `/bin/uv`, installs deps, persists `AppInstance` to DB, registers manifest, and starts the subprocess. Uses `_install_lock` to serialize concurrent installs.
- **start()** — cleans stale UDS socket, builds subprocess command (`venv python -m sempkm_app_sdk.runner`), launches via `asyncio.create_subprocess_exec`, starts log capture tasks and crash watcher, waits for `/_health` via httpx UDS transport, updates DB with pid/socket/status.
- **stop()** — SIGTERM → 5s wait → SIGKILL if needed. Sets `_stop_flags` to tell the watcher this was intentional. Cleans up process tracking and updates DB.
- **restart()** — stop then start.
- **uninstall()** — stop, remove socket, `shutil.rmtree` data dir, delete DB row, unregister from registry.
- **get_status()** — queries DB and computes uptime from `started_at`.
- **get_logs()** — returns ring buffer contents.

Crash recovery in `_watch_process`: awaits proc.wait(), checks stop flag (intentional → return), otherwise increments restart_count in DB, sleeps with exponential backoff (2^count seconds: 1s, 2s, 4s), then calls start(). After 3 failures, marks status='error' with descriptive error_message persisted to DB.

## Verification

- `cd backend && python -m pytest tests/test_app_manager.py -v` — **31 passed** (9 registry, 22 manager)
- `cd backend && python -c "from app.apps.manager import AppManager; from app.apps.registry import AppRegistry; print('OK')"` — **OK**

### Slice-level verification status (T03 checkpoint):
- ✅ `test_app_manifest.py` — 60 passed
- ✅ `test_app_manager.py` — 31 passed
- ⬜ `test_app_lifecycle_contract.py` — not yet created (T04 scope)
- ✅ models importable
- ✅ manifest importable
- ✅ manager + registry importable

## Diagnostics

- `AppManager.get_status(app_id)` returns dict: `{app_id, status, pid, uptime_seconds, restart_count, error_message, version}`
- `AppManager.get_logs(app_id)` returns `list[str]` of last 100 stdout/stderr lines
- `app_instances` table: status column tracks running/stopped/error/installing; restart_count and error_message persist crash info
- Structured logging: INFO on install/start/stop, WARNING on unexpected exit + restart attempt, ERROR on max-retry exhaustion

## Deviations

None — implementation follows the task plan exactly.

## Known Issues

- Test warnings about unawaited coroutines for `_capture_output` and `_watch_process` in 2 tests where `asyncio.create_task` is mocked to `MagicMock`. These are harmless mock artifacts — the actual code paths are tested in dedicated crash recovery and log buffer tests.

## Files Created/Modified

- `backend/app/apps/registry.py` — AppRegistry class (in-memory manifest cache)
- `backend/app/apps/manager.py` — AppManager class (full lifecycle: install/start/stop/restart/uninstall + crash recovery + health check + log capture)
- `backend/tests/test_app_manager.py` — 31 unit tests covering registry ops, install flow, start/stop/restart, crash recovery backoff/limits, status reporting, log buffer, health check success/timeout
