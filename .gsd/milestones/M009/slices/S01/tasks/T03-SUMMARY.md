---
id: T03
parent: S01
milestone: M009
provides:
  - AppRegistry in-memory manifest cache with register/unregister/get/list
  - AppManager lifecycle engine with install/start/stop/restart/uninstall/get_status/get_logs
  - Crash recovery with exponential backoff (1s, 2s, 4s) capped at 3 retries
  - Health check polling via httpx UDS transport
  - Log capture via deque(maxlen=100) ring buffers
key_files:
  - backend/app/apps/registry.py
  - backend/app/apps/manager.py
  - backend/tests/test_app_manager.py
key_decisions:
  - Restart counts tracked in-memory (_restart_counts dict) and synced to DB; reset to 0 on manual start/restart but preserved across crash-recovery restarts via _start_for_recovery()
  - _mark_error() separated from _watch_process() for testability and clarity
  - Settings() instantiated inside install() to get current app_version rather than passed as constructor arg — keeps constructor simple and avoids stale config
patterns_established:
  - Mock session factory pattern for async_sessionmaker — MagicMock returning AsyncMock context manager, not AsyncMock as the factory itself (required for `async with factory() as session` protocol)
  - Private _run_uv() helper centralizes all uv CLI calls with error raising on non-zero exit
observability_surfaces:
  - AppManager.get_status(app_id) returns {app_id, status, pid, uptime_seconds, restart_count, error_message, version}
  - AppManager.get_logs(app_id) returns last ≤100 stdout/stderr lines
  - app_instances.status transitions logged at INFO; crash recovery at WARNING; max-retry exhaustion at ERROR with error_message persisted to DB
duration: 35m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T03: AppRegistry + AppManager lifecycle engine

**Built AppRegistry manifest cache and AppManager subprocess lifecycle engine with install/start/stop/restart/uninstall, crash recovery (3x with exponential backoff), health checking over UDS, and log ring buffers — 30 tests passing.**

## What Happened

Created `AppRegistry` as a simple dict-backed cache keyed by app_id with register/unregister/get_manifest/list_apps/get_app methods. Created `AppManager` as the full lifecycle engine with:

- **install()**: Parses manifest, checks platform version compatibility via `packaging.specifiers.SpecifierSet`, creates venv and installs deps via `_run_uv()`, persists AppInstance row, registers manifest, and calls start(). Protected by `_install_lock` to prevent concurrent installs.
- **start()**: Cleans stale socket, builds `sempkm_app_sdk.runner` command, spawns subprocess via `asyncio.create_subprocess_exec`, attaches stdout/stderr capture tasks, launches watcher task for crash recovery, polls `/_health` endpoint via httpx UDS transport, updates DB to status=running.
- **stop()**: SIGTERM → 5s wait → SIGKILL fallback, cleans up all internal state, updates DB to status=stopped.
- **restart()**: stop then start.
- **uninstall()**: stop, remove socket, rmtree data dir, delete DB row, unregister.
- **Crash recovery** (`_watch_process`): Detects unexpected exits (checks `_stop_flags` for intentional stops), computes exponential backoff (2^count: 1s, 2s, 4s), calls `_start_for_recovery()` which preserves restart counter, marks error after 3 failed restarts.
- **Health check** (`_wait_for_health`): Polls `GET /_health` on Unix domain socket via httpx every 1s up to 30s timeout.
- **Log capture** (`_capture_output`): Reads lines from stdout/stderr into per-app `deque(maxlen=100)`.

## Verification

Ran `pytest tests/test_app_manager.py -v` — 30 tests pass covering all lifecycle methods, crash recovery paths, health check success/timeout, log capture, uv execution, and edge cases.

Ran import checks — `from app.apps.manager import AppManager; from app.apps.registry import AppRegistry` succeeds.

Ran all slice-level verification checks that apply to completed tasks (T01+T02+T03).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && python -m pytest tests/test_app_manager.py -v` | 0 | ✅ pass | 0.66s |
| 2 | `cd backend && python -m pytest tests/test_app_manifest.py -v` | 0 | ✅ pass | 0.08s |
| 3 | `cd backend && python -c "from app.apps.manager import AppManager; from app.apps.registry import AppRegistry; print('OK')"` | 0 | ✅ pass | <1s |
| 4 | `cd backend && python -c "from app.apps.models import AppInstance, ...; print('OK')"` | 0 | ✅ pass | <1s |
| 5 | `cd backend && python -c "from app.apps.manifest import AppManifestSchema, parse_app_manifest; print('OK')"` | 0 | ✅ pass | <1s |
| 6 | `cd backend && python -m pytest tests/test_app_lifecycle_contract.py -v` | — | ⏳ T04 scope | — |

## Diagnostics

- **Status inspection**: `await mgr.get_status("app-id")` returns dict with status/pid/uptime_seconds/restart_count/error_message/version
- **Log inspection**: `mgr.get_logs("app-id")` returns list of last ≤100 stdout/stderr lines
- **DB state**: `app_instances` table tracks status transitions, error_message captures last failure, restart_count increments on crash recovery
- **Logging**: INFO on start/stop/install/uninstall, WARNING on unexpected exit + recovery attempt, ERROR on max-retry exhaustion

## Deviations

- Removed unused `select` and `AppManifestSchema` imports from manager.py (only `parse_app_manifest` needed since manifest type is inferred)
- Restart count tracked in `_restart_counts` dict (memory) synced to DB, rather than reading from DB each time — simpler and avoids extra DB round-trips in the crash recovery hot path

## Known Issues

- `session.add(instance)` in install() triggers a benign RuntimeWarning about unawaited coroutine in tests because MockSession's `add()` returns a coroutine; this is a test mock artifact, not a production issue

## Files Created/Modified

- `backend/app/apps/registry.py` — AppRegistry class with register/unregister/get_manifest/list_apps/get_app
- `backend/app/apps/manager.py` — AppManager class with full lifecycle (install/start/stop/restart/uninstall), crash recovery, health check, log capture
- `backend/tests/test_app_manager.py` — 30 unit tests covering all lifecycle methods and edge cases
