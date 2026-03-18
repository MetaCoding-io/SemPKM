---
id: T04
parent: S01
milestone: M009
provides:
  - AppManager.auto_start() queries DB for previously-running apps and starts them on boot
  - AppManager.shutdown_all() sends SIGTERM with 10s timeout + SIGKILL fallback, preserves 'running' status for next boot
  - main.py lifespan creates AppManager after SQL init, calls auto_start on startup and shutdown_all on teardown
  - test_health_server.py standalone UDS fixture for contract tests
  - 8 contract tests proving real subprocess lifecycle (install, health, stop, restart, crash recovery, exhaustion, auto_start, shutdown_all)
key_files:
  - backend/app/apps/manager.py
  - backend/app/main.py
  - backend/tests/fixtures/test_health_server.py
  - backend/tests/test_app_lifecycle_contract.py
key_decisions:
  - Platform shutdown preserves DB status='running' so auto_start picks apps up on next boot; only explicit user stop() sets status='stopped'
  - auto_start() re-loads manifests from disk if registry is empty (covers cold-restart where in-memory state is lost)
  - Contract tests use real backoff waits (1s, 2s, 4s) rather than patching asyncio.sleep — patching sleep globally prevents event loop yielding and breaks watcher task scheduling
patterns_established:
  - Test health server uses asyncio.start_unix_server with raw HTTP parsing — zero external deps, handles SIGTERM cleanly
  - Contract test pattern: _patch_start_command() monkey-patches AppManager.start() to spawn test_health_server.py instead of venv-based SDK runner, preserving all DB/state logic
observability_surfaces:
  - auto_start logs INFO per app started, WARNING on individual failures (does not block boot)
  - shutdown_all logs INFO on clean stop, WARNING on SIGKILL fallback
  - app.state.app_manager accessible from any request handler for runtime inspection
duration: 30min
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T04: Lifespan integration + auto-start + contract tests

**Wired AppManager into FastAPI lifespan with auto_start/shutdown_all and proved full subprocess lifecycle via 8 contract tests on real UDS**

## What Happened

Added `auto_start()` and `shutdown_all()` methods to AppManager, then wired the manager into `main.py` lifespan — created after SQL engine init, auto_start called on boot, shutdown_all called before engine dispose. Created a standalone test health server (`test_health_server.py`) that binds to a Unix domain socket and responds to `GET /_health` with 200 JSON. Built 8 contract tests proving real subprocess lifecycle: install+start, health check over UDS, stop, restart with new PID, crash recovery (SIGKILL → automatic restart with backoff), crash recovery exhaustion (4 kills → error status), auto_start from DB, and shutdown_all preserving DB status.

## Verification

- `cd backend && python -m pytest tests/test_app_lifecycle_contract.py -v` — 8/8 passed
- `cd backend && python -m pytest tests/test_app_manifest.py -v` — 61/61 passed
- `cd backend && python -m pytest tests/test_app_manager.py -v` — 30/30 passed
- `cd backend && python -c "from app.apps.models import ..."` — OK
- `cd backend && python -c "from app.apps.manifest import ..."` — OK
- `cd backend && python -c "from app.apps.manager import AppManager; ..."` — OK
- `grep -n "app_manager" backend/app/main.py` — confirmed 4 references (init, state, auto_start, shutdown_all)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -m pytest tests/test_app_lifecycle_contract.py -v` | 0 | ✅ pass | 28.7s |
| 2 | `python -m pytest tests/test_app_manifest.py -v` | 0 | ✅ pass | 0.1s |
| 3 | `python -m pytest tests/test_app_manager.py -v` | 0 | ✅ pass | 0.7s |
| 4 | `python -c "from app.apps.models import AppInstance, ..."` | 0 | ✅ pass | <1s |
| 5 | `python -c "from app.apps.manifest import AppManifestSchema, ..."` | 0 | ✅ pass | <1s |
| 6 | `python -c "from app.apps.manager import AppManager; ..."` | 0 | ✅ pass | <1s |
| 7 | `grep -n "app_manager" backend/app/main.py` | 0 | ✅ pass | <1s |

## Diagnostics

- **Runtime inspection:** `app.state.app_manager.get_status(app_id)` returns dict with status/pid/uptime/restart_count/error_message
- **Log inspection:** `app.state.app_manager.get_logs(app_id)` returns ring buffer contents (last 100 lines)
- **Auto-start behavior:** On boot, queries `app_instances` for `status='running'` rows. Each failure logged at WARNING but doesn't block startup.
- **Shutdown behavior:** Sends SIGTERM to all processes concurrently, waits 10s, SIGKILL fallback. DB status preserved as 'running' for next auto_start cycle.

## Deviations

- Removed `@pytest.mark.timeout()` decorators — `pytest-timeout` plugin not installed in this environment. Tests are self-limiting via finite retry loops.
- `settings.port` does not exist in the config — used `settings.app_base_url or "http://localhost:8000"` for platform_url instead.
- `auto_start()` includes manifest re-loading from disk — the plan didn't specify this but it's necessary for cold restarts where the in-memory registry is empty.

## Known Issues

None.

## Files Created/Modified

- `backend/app/apps/manager.py` — added `auto_start()` and `shutdown_all()` methods
- `backend/app/main.py` — wired AppManager init, auto_start, and shutdown_all into lifespan
- `backend/tests/fixtures/__init__.py` — new package init
- `backend/tests/fixtures/test_health_server.py` — standalone asyncio HTTP server on UDS for testing
- `backend/tests/test_app_lifecycle_contract.py` — 8 contract tests proving real subprocess lifecycle
