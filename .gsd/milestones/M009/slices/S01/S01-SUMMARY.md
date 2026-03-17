---
id: S01
parent: M009
milestone: M009
provides:
  - AppManifestSchema Pydantic model with 17 nested models and full validation (60 unit tests)
  - 5 SQLAlchemy ORM models (AppInstance, AppTaskRun, AppTaskConfig, AppRendererPref, AppPermission)
  - Alembic migration 013 creating all app platform tables with FK cascade
  - AppRegistry in-memory manifest cache (register/unregister/get/list)
  - AppManager lifecycle engine (install/start/stop/restart/uninstall/get_status/get_logs)
  - Crash recovery with exponential backoff (1s, 2s, 4s) up to 3 retries
  - Health check polling via httpx UDS transport (/_health, 30s timeout)
  - Per-app stdout/stderr ring buffer (deque maxlen=100)
  - Platform lifespan wiring (auto_start on boot, shutdown_all on exit)
  - PyJWT ~=2.10 and packaging ~=25.0 added to pyproject.toml
requires:
  - slice: none
    provides: first slice — no upstream dependencies
affects:
  - S02 (consumes AppManager, AppRegistry, AppManifestSchema, SQLAlchemy models)
  - S03 (consumes AppManager, AppRegistry, SQLAlchemy models)
key_files:
  - backend/app/apps/__init__.py
  - backend/app/apps/manifest.py
  - backend/app/apps/models.py
  - backend/app/apps/registry.py
  - backend/app/apps/manager.py
  - backend/migrations/versions/013_app_tables.py
  - backend/app/main.py
  - backend/tests/test_app_manifest.py
  - backend/tests/test_app_manager.py
  - backend/tests/test_app_lifecycle_contract.py
  - backend/tests/fixtures/test_health_server.py
key_decisions:
  - D138: Apps as sandboxed subprocesses communicating via HTTP/UDS
  - D149: uv venv + uv pip install for app venvs (not stdlib venv/pip)
  - D152: App log capture via in-memory ring buffer, not SQLite
  - D154: Platform shutdown preserves 'running' status in DB for auto-start
  - D155: Contract tests use standalone test_health_server, not SDK runner
  - D156: Install lock via asyncio.Lock in AppManager
patterns_established:
  - App platform modules live in backend/app/apps/ (manifest, models, registry, manager)
  - Lifecycle state machine: install→start→[restart/stop]→uninstall with DB status tracking
  - Crash watcher: asyncio.Task per app awaiting proc.wait(), deciding restart vs error
  - Health check: httpx AsyncClient with UDS transport polling /_health
  - Contract test pattern: real subprocess on real UDS with patched start command redirected to test fixture
  - Mapped[T] + mapped_column() ORM pattern (matching WorkflowSpec) for new models
observability_surfaces:
  - AppManager.get_status(app_id) → {app_id, status, pid, uptime_seconds, restart_count, error_message, version}
  - AppManager.get_logs(app_id) → last 100 stdout/stderr lines
  - app_instances.status tracks running/stopped/error/installing
  - app_instances.restart_count increments on crash recovery
  - app_instances.error_message captures last failure
  - Structured logging: INFO install/start/stop, WARNING crash+restart, ERROR max-retry exhaustion
  - auto_start logs INFO per app, WARNING on failures (non-blocking)
  - shutdown_all logs INFO on clean stop, WARNING on SIGKILL fallback
drill_down_paths:
  - .gsd/milestones/M009/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M009/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M009/slices/S01/tasks/T03-SUMMARY.md
  - .gsd/milestones/M009/slices/S01/tasks/T04-SUMMARY.md
duration: 75m
verification_result: passed
completed_at: 2026-03-16
---

# S01: Manifest, DB Schema & Subprocess Lifecycle

**Full app platform foundation: manifest validation (17 Pydantic models), 5 SQLAlchemy tables, and subprocess lifecycle engine with crash recovery — proven via 101 tests including 10 real-subprocess contract tests on UDS.**

## What Happened

Built the app platform foundation in 4 tasks across the `backend/app/apps/` package.

**T01 (Manifest):** Implemented `AppManifestSchema` with all 17 nested Pydantic models from design §14 — identity, dependencies, permissions, backend, tasks, frontend, UI contributions, settings. Field validators enforce appId pattern, strict semver, interval parsing (30s floor/24h ceiling), version ranges via `packaging.specifiers`. Cross-field validators check tasks↔backgroundTasks permission, settings↔settings permission, command palette action-type→target requirements, and renderer at-least-one-mode. `parse_app_manifest()` loads and validates from YAML. 60 unit tests cover all constraint boundaries.

**T02 (Models + Migration):** Defined 5 SQLAlchemy ORM models matching design §11: `AppInstance` (lifecycle state), `AppTaskRun` (execution history), `AppTaskConfig` (user-adjustable intervals), `AppRendererPref` (type→app renderer mapping), `AppPermission` (approved permissions snapshot). All child tables FK to `app_instances.app_id` with CASCADE. Alembic migration 013 creates tables in dependency order with proper indexes. Added `PyJWT~=2.10` and `packaging~=25.0` to pyproject.toml.

**T03 (Registry + Manager):** `AppRegistry` is a thin in-memory dict with O(1) manifest lookup. `AppManager` is the lifecycle orchestrator: `install()` validates manifest, checks platform version compatibility, creates venv via `uv`, installs deps, persists to DB, and starts. `start()` cleans stale sockets, launches subprocess, starts log capture + crash watcher, polls `/_health` via httpx UDS transport. `stop()` sends SIGTERM with 5s timeout, SIGKILL fallback. Crash recovery in `_watch_process` uses exponential backoff (1s, 2s, 4s), stops at 3 retries and marks status='error'. 31 unit tests with mocked subprocess.

**T04 (Lifespan + Contract Tests):** Added `auto_start()` (queries DB for status='running', starts each, non-blocking on individual failures) and `shutdown_all()` (SIGTERM + 10s wait + SIGKILL, preserves 'running' status for next boot). Wired into `main.py` lifespan. Built `test_health_server.py` fixture — a minimal asyncio UDS HTTP server with zero external deps. 10 contract tests prove the full lifecycle with real subprocesses on real unix sockets: install→health→stop→restart→crash recovery→exhaustion→shutdown→auto-start.

## Verification

All 6 slice-level verification checks pass:

| Check | Result |
|---|---|
| `pytest tests/test_app_manifest.py -v` | ✅ 60 passed (0.11s) |
| `pytest tests/test_app_manager.py -v` | ✅ 31 passed (5.5s, 4 harmless mock warnings) |
| `pytest tests/test_app_lifecycle_contract.py -v` | ✅ 10 passed (21s) |
| `from app.apps.models import ...` | ✅ All 5 models importable |
| `from app.apps.manifest import ...` | ✅ Schema + parser importable |
| `from app.apps.manager import AppManager; from app.apps.registry import AppRegistry` | ✅ OK |

**Observability verified:**
- `AppManager.get_status()` returns structured dict with status, PID, uptime, restart_count, error_message, version
- `AppManager.get_logs()` returns ring buffer contents
- Crash recovery increments restart_count in DB, logs at WARNING, exhaustion logs at ERROR with persisted error_message
- auto_start and shutdown_all logging confirmed via contract tests

## Requirements Advanced

- APP-01 (manifest validation) — fully implemented. `AppManifestSchema` validates all fields from design §14 with clear error messages. 60 tests cover all constraint boundaries. Ready to validate in S07 E2E.
- APP-02 (subprocess lifecycle) — core lifecycle operational. Install/start/stop/restart with crash recovery proven via 10 contract tests on real UDS. Auto-start and shutdown wired into platform lifespan. SDK subprocess (S02) and Docker integration (S03) remain.
- APP-13 (DB tables + migrations) — fully implemented. 5 SQLAlchemy models + Alembic migration 013. Tables populated correctly during lifecycle tests.

## Requirements Validated

- none — APP-01, APP-02, APP-13 are advanced but not fully validated until E2E proves them in the Docker stack (S07)

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- Platform URL hardcoded to `http://localhost:8000` instead of dynamic `settings.port` — no `port` field exists in Settings model. 8000 matches Dockerfile CMD.
- `packaging` pinned to ~=25.0 per spec, which downgraded from 26.0 in venv. No breakage observed.

## Known Limitations

- `_capture_output` and `_watch_process` mock tests produce 4 RuntimeWarnings about unawaited coroutines — harmless artifacts from mocking `asyncio.create_task` with `MagicMock`. Actual code paths tested in dedicated tests.
- Health check uses 1s polling interval over 30s — adequate for local/Docker but may need tuning for slow container starts.
- No venv caching — `uv venv` + `uv pip install` runs on every install. Adequate for v1.
- Contract tests use a test fixture server, not the real SDK runner (which doesn't exist until S02).

## Follow-ups

- S02 should replace `test_health_server.py` fixture with real SDK runner in integration tests once the SDK exists.
- S03 Docker integration should verify venv creation works inside the API container (uv binary availability confirmed by research).

## Files Created/Modified

- `backend/app/apps/__init__.py` — new package init
- `backend/app/apps/manifest.py` — AppManifestSchema with 17 nested models, field/cross-field validators, parse_app_manifest()
- `backend/app/apps/models.py` — 5 SQLAlchemy ORM models (AppInstance, AppTaskRun, AppTaskConfig, AppRendererPref, AppPermission)
- `backend/app/apps/registry.py` — AppRegistry in-memory manifest cache
- `backend/app/apps/manager.py` — AppManager lifecycle engine (install/start/stop/restart/uninstall + crash recovery + health check + log capture + auto_start + shutdown_all)
- `backend/migrations/versions/013_app_tables.py` — Alembic migration creating 5 tables
- `backend/pyproject.toml` — added PyJWT~=2.10 and packaging~=25.0
- `backend/app/main.py` — AppManager lifespan wiring (init, auto_start, shutdown_all)
- `backend/tests/test_app_manifest.py` — 60 manifest validation tests
- `backend/tests/test_app_manager.py` — 31 lifecycle unit tests
- `backend/tests/test_app_lifecycle_contract.py` — 10 contract tests with real subprocess on UDS
- `backend/tests/fixtures/__init__.py` — test fixtures package
- `backend/tests/fixtures/test_health_server.py` — minimal UDS HTTP health server fixture

## Forward Intelligence

### What the next slice should know
- `AppManager` is accessed at runtime via `request.app.state.app_manager` (set in lifespan)
- Socket paths follow `/tmp/sempkm-app-{appId}.sock` convention
- The subprocess command template is: `{venv}/bin/python -m sempkm_app_sdk.runner --app-dir {dir} --socket {sock} --platform-url {url}` — S02's SDK runner must accept these CLI args
- `install()` calls `start()` automatically — the install flow is atomic (validate → venv → deps → DB → start)
- `auto_start()` re-reads manifests from disk and re-registers them before starting — S02 can assume manifests are always in the registry for running apps

### What's fragile
- Health check httpx UDS transport — the 30s timeout with 1s polling is generous but if the SDK runner (S02) has a slow startup, the timeout may need adjustment
- `_run_uv()` shells out to `/bin/uv` — must exist in the Docker image (confirmed by research, but not yet exercised in CI)
- `_install_lock` is a single asyncio.Lock — sufficient for single-process but would need upgrade for multi-worker

### Authoritative diagnostics
- `app_instances` table status column is the single source of truth for app state — always check DB, not in-memory `_processes` dict
- `AppManager.get_status()` is the canonical status API — returns both DB state and computed uptime
- Contract test `test_crash_recovery` is the authoritative proof that the watcher/restart/backoff chain works end-to-end

### What assumptions changed
- Assumed `settings.port` existed for platform URL — it doesn't; hardcoded to 8000. S02/S03 may need to parameterize this.
- Assumed `packaging` 26.x would be fine — pinned to 25.0 per spec, no issues but worth noting if SpecifierSet behavior differs between versions.
