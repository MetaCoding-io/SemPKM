---
id: T04
parent: S01
milestone: M009
provides:
  - AppManager lifespan wiring (auto-start on boot, shutdown_all on exit)
  - auto_start() method queries DB for previously-running apps
  - shutdown_all() method sends SIGTERM with 10s timeout + SIGKILL fallback
  - 10 contract tests proving real subprocess lifecycle on UDS
  - test_health_server.py fixture for contract testing
key_files:
  - backend/app/main.py
  - backend/app/apps/manager.py
  - backend/tests/test_app_lifecycle_contract.py
  - backend/tests/fixtures/test_health_server.py
key_decisions:
  - Platform shutdown leaves DB status as 'running' (not 'stopped') so auto_start resumes apps on next boot; only explicit user stop() sets 'stopped'
  - Platform URL hardcoded to http://localhost:8000 (matches Dockerfile CMD); no settings.port field exists
patterns_established:
  - Contract test pattern: real subprocess on real UDS with patched start command redirected to test fixture
  - Test health server: asyncio.start_unix_server with minimal HTTP parsing — zero external deps
observability_surfaces:
  - auto_start logs INFO per app started, WARNING on individual failures
  - shutdown_all logs INFO on clean shutdown, WARNING on SIGKILL fallback
  - app.state.app_manager accessible from any request handler
  - auto_start failures logged but don't block platform boot
duration: 20m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T04: Lifespan integration + auto-start + contract tests

**Wired AppManager into platform lifespan with auto-start on boot and graceful shutdown, plus 10 contract tests proving real subprocess lifecycle on UDS.**

## What Happened

Added `auto_start()` and `shutdown_all()` methods to AppManager. `auto_start()` queries `app_instances` for rows with status='running', re-registers their manifests, and starts each — individual failures logged but don't block boot. `shutdown_all()` sends SIGTERM to all tracked processes, waits up to 10s per process, SIGKILLs stragglers, and deliberately leaves DB status as 'running' so next boot auto-starts them.

Wired both into `main.py` lifespan: AppManager created after SQL engine init (using `async_session_factory`, triplestore `client`, and container paths), auto_start called before `yield`, shutdown_all called in shutdown before `sql_engine.dispose()`.

Built a minimal test health server (`tests/fixtures/test_health_server.py`) using `asyncio.start_unix_server` — handles `GET /_health` over UDS with proper HTTP/1.1 responses, zero external deps. Contract tests use a real in-memory SQLite database (via `aiosqlite`) and spawn this server as a real subprocess, with the start command patched to use the test fixture instead of the SDK runner.

## Verification

All slice-level verification checks pass:

- `tests/test_app_lifecycle_contract.py`: **10 passed** (21s) — install+start, health check, stop, restart, crash recovery, crash exhaustion, shutdown_all, auto_start resume, auto_start skip
- `tests/test_app_manifest.py`: **60 passed** — all manifest validation
- `tests/test_app_manager.py`: **31 passed** — unit-level lifecycle state machine
- All import checks: OK (models, manifest, manager+registry importable)
- `grep -n "app_manager" backend/app/main.py` confirms lifespan wiring at lines 334, 341, 345, 384

## Diagnostics

- `app.state.app_manager.get_status(app_id)` — runtime status dict from any request handler
- `auto_start` logs at INFO per app started, WARNING per failure (with exc_info)
- `shutdown_all` logs at INFO for clean shutdown, WARNING for SIGKILL fallback
- auto_start failures do not block platform boot — wrapped in try/except with `logger.error`

## Deviations

- Used `http://localhost:8000` instead of `f"http://localhost:{settings.port}"` — no `port` field exists in Settings; 8000 is hardcoded in Dockerfile CMD
- No `pytest-timeout` available — omitted `--timeout` flag; tests complete in ~21s

## Known Issues

- T03 unit tests produce 4 RuntimeWarnings about unawaited coroutines (pre-existing from mocked `asyncio.create_task`); not related to T04 changes

## Files Created/Modified

- `backend/app/apps/manager.py` — added `auto_start()` and `shutdown_all()` methods
- `backend/app/main.py` — added AppManager init, auto_start, and shutdown_all to lifespan
- `backend/tests/fixtures/__init__.py` — new package init
- `backend/tests/fixtures/test_health_server.py` — standalone UDS HTTP health server for testing
- `backend/tests/test_app_lifecycle_contract.py` — 10 contract tests proving real subprocess lifecycle
