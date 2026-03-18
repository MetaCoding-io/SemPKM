# S01: Manifest, DB Schema & Subprocess Lifecycle

**Goal:** Establish the app platform foundation — manifest validation, persistent state tracking, and subprocess lifecycle management with crash recovery.
**Demo:** A test fixture app installs from disk (manifest validated, venv created, deps installed, process started on UDS), reports its status (running/stopped/error with PID), stops and restarts cleanly, and auto-restarts after simulated crash — all proven via contract tests.

## Must-Haves

- `AppManifestSchema` validates all manifest fields from design §14 with clear error messages
- 5 SQLAlchemy models + Alembic migration 013 for app tables
- `AppRegistry` provides in-memory manifest cache with `get_app()`, `list_apps()`, `get_manifest()`
- `AppManager` orchestrates install (uv venv, uv pip install, DB register, start), start, stop, restart, uninstall, get_status
- Process supervision via `asyncio.create_subprocess_exec` with health check polling (`GET /_health`)
- Crash recovery restarts up to 3 times with exponential backoff (1s, 2s, 4s)
- Platform lifespan auto-starts previously running apps on boot
- Platform shutdown sends SIGTERM to all running apps
- Per-app stdout/stderr captured in ring buffer (last 100 lines)
- Socket file cleanup before process start
- `PyJWT` and `packaging` added to pyproject.toml

## Proof Level

- This slice proves: operational (lifecycle state machine with real subprocess patterns)
- Real runtime required: yes (contract tests use a test-fixture HTTP server on UDS)
- Human/UAT required: no (no UI yet — admin portal is S03)

## Verification

- `cd backend && python -m pytest tests/test_app_manifest.py -v` — manifest validation: all field constraints, cross-field validators, error messages
- `cd backend && python -m pytest tests/test_app_manager.py -v` — lifecycle state machine: install/start/stop/restart transitions, crash recovery logic, status reporting
- `cd backend && python -m pytest tests/test_app_lifecycle_contract.py -v` — contract verification: install→start→health→stop→restart cycle with real subprocess on UDS
- `cd backend && python -c "from app.apps.models import AppInstance, AppTaskRun, AppTaskConfig, AppRendererPref, AppPermission; print('OK')"` — models importable
- `cd backend && python -c "from app.apps.manifest import AppManifestSchema, parse_app_manifest; print('OK')"` — manifest schema importable
- `cd backend && python -c "from app.apps.manager import AppManager; from app.apps.registry import AppRegistry; print('OK')"` — manager + registry importable

## Observability / Diagnostics

- Runtime signals: `app_instances.status` tracks running/stopped/error/installing; `app_instances.restart_count` increments on crash recovery; `app_instances.error_message` captures last failure
- Inspection surfaces: `AppManager.get_status(app_id)` returns dict with status, PID, uptime, restart_count, error; `AppManager.get_logs(app_id)` returns ring buffer contents
- Failure visibility: crash recovery logs at WARNING with app_id, exit code, restart attempt; health check failures logged at WARNING; max-retry exhaustion logged at ERROR with final error_message persisted to DB
- Redaction constraints: none (no secrets in app lifecycle — JWT tokens are S02 scope)

## Integration Closure

- Upstream surfaces consumed: none (first slice)
- New wiring introduced: `AppManager` initialized in `main.py` `lifespan()` after DB setup; `backend/app/apps/` package created; Alembic migration 013; `PyJWT` + `packaging` deps
- What remains before the milestone is truly usable end-to-end: SDK package (S02), IPC proxy (S02), admin UI (S03), frontend integration (S04+), scheduler/permissions (S05), renderer overrides (S06)

## Tasks

- [x] **T01: AppManifestSchema Pydantic model + validation tests** `est:1h`
  - Why: Foundation — every downstream slice depends on a validated manifest. Design §14 provides the exact schema spec. Must be right first time since it's the app developer-facing contract.
  - Files: `backend/app/apps/__init__.py`, `backend/app/apps/manifest.py`, `backend/tests/test_app_manifest.py`
  - Do: Create `backend/app/apps/` package. Implement full `AppManifestSchema` from design doc §14 — all nested models (AppAuthor, AppModelDependency, AppDependencies, AppPermissions, AppBackend, AppTask, AppFrontend, AppPage, AppUI, AppSettingDef, etc.), field validators (appId pattern, semver, interval parsing, version range via `packaging.specifiers`), cross-field validators (tasks require backgroundTasks permission, settings require settings permission, dialog actions require fragment). Implement `parse_app_manifest()` to load from YAML path. Write comprehensive unit tests covering all constraint boundaries, valid manifests, and clear error messages.
  - Verify: `cd backend && python -m pytest tests/test_app_manifest.py -v`
  - Done when: All Pydantic validators fire on invalid input with descriptive messages. Valid manifests (including the RSS Reader example from design §13) parse cleanly. Every field constraint from design §14 validation table is covered by a test.

- [x] **T02: SQLAlchemy models + Alembic migration 013 + new deps** `est:30m`
  - Why: Persistent state tracking for app lifecycle, task execution history, and permissions. Unblocks AppManager in T03 which writes to these tables.
  - Files: `backend/app/apps/models.py`, `backend/migrations/versions/013_app_tables.py`, `backend/pyproject.toml`
  - Do: Define 5 SQLAlchemy models matching design §11 SQL schemas: `AppInstance` (app_id PK, version, status, pid, socket_path, started_at, installed_at, manifest_hash, error_message, restart_count), `AppTaskRun` (autoincrement id, app_id FK, task_id, run_id UUID, started_at, finished_at, status, duration_ms, error_message, summary), `AppTaskConfig` (composite PK app_id+task_id, interval_override, paused), `AppRendererPref` (composite PK type_iri+mode, app_id FK), `AppPermission` (app_id PK FK, permissions_json, approved_at, approved_by). Create Alembic migration 013 (revision="013", down_revision="012"). Add `PyJWT~=2.10` and `packaging~=25.0` to pyproject.toml dependencies list.
  - Verify: `cd backend && python -c "from app.apps.models import AppInstance, AppTaskRun, AppTaskConfig, AppRendererPref, AppPermission; print('OK')"` and migration file parseable
  - Done when: All 5 models importable with correct column types. Migration 013 creates all tables with proper FKs and indexes. New deps in pyproject.toml.

- [x] **T03: AppRegistry + AppManager lifecycle engine** `est:2h`
  - Why: Core subprocess lifecycle management — the critical-path risk of the entire M009 milestone. Everything else (SDK, proxy, admin, scheduler) depends on being able to reliably start, monitor, and recover app processes.
  - Files: `backend/app/apps/registry.py`, `backend/app/apps/manager.py`, `backend/tests/test_app_manager.py`
  - Do: **AppRegistry** — in-memory dict keyed by app_id, stores parsed `AppManifestSchema`; methods: `register(app_id, manifest)`, `unregister(app_id)`, `get_manifest(app_id)`, `list_apps()`, `get_app(app_id)` returning status dict. **AppManager** — constructor takes `SessionFactory`, `TriplestoreClient`, `apps_dir` (Path), `data_dir` (Path), `platform_url` (str); stores `_processes: dict[str, asyncio.subprocess.Process]`, `_log_buffers: dict[str, collections.deque]`, `_registry: AppRegistry`, `_restart_counts: dict[str, int]`. Methods: `install(app_dir: Path) → AppInstance` — validate manifest, check platform version, create venv via `/bin/uv venv`, install deps via `/bin/uv pip install -r requirements.txt`, insert into `app_instances` table, call `start()`. `start(app_id) → None` — cleanup stale socket file, build command (`venv/bin/python -m sempkm_app_sdk.runner --app-dir ... --socket ... --platform-url ...`), `asyncio.create_subprocess_exec` with stdout/stderr PIPE, launch `_watch_process()` task, poll `/_health` via httpx UDS transport (up to 30s, 1s interval), update DB status to 'running' with PID. `stop(app_id) → None` — SIGTERM, wait 5s, SIGKILL if still alive, update DB status to 'stopped', reset restart_count. `restart(app_id) → None` — stop then start. `uninstall(app_id) → None` — stop, remove venv dir, remove socket, delete from DB. `get_status(app_id) → dict` — status, pid, uptime, restart_count, error_message. `get_logs(app_id) → list[str]` — ring buffer contents. **Crash recovery** — `_watch_process(app_id)` async task: await process exit, if unexpected (not stopped by manager), increment restart_count, if < 3 restart with backoff `2^count` seconds, else mark 'error' in DB with error_message. **Log capture** — `_capture_output(app_id, stream)` async task reads stdout/stderr line by line into a `collections.deque(maxlen=100)`. **Health check** — `_wait_for_health(app_id, socket_path, timeout=30)` polls `GET /_health` via httpx with `uds=socket_path`. Unit tests use mocked subprocess (AsyncMock for create_subprocess_exec) to test: install flow, start/stop state transitions, crash recovery backoff timing, restart count limits, status reporting, log buffer capture.
  - Verify: `cd backend && python -m pytest tests/test_app_manager.py -v`
  - Done when: All lifecycle methods handle happy path and error cases. Crash recovery backs off exponentially and stops at 3 retries. Status accurately reflects process state. Log buffer captures output.

- [x] **T04: Lifespan integration + auto-start + contract tests** `est:1h`
  - Why: Wire the AppManager into the running platform so apps start/stop with the server. Prove the lifecycle contract with a real subprocess on a real UDS — not just mocked unit tests.
  - Files: `backend/app/main.py`, `backend/tests/test_app_lifecycle_contract.py`, `backend/tests/fixtures/test_health_server.py`
  - Do: **Lifespan wiring** — after SQL engine creation in `main.py` `lifespan()`, create `AppManager(session_factory, client, apps_dir=Path("/app/apps"), data_dir=Path("/app/data/apps"), platform_url=f"http://localhost:{settings.port}")`, store on `app.state.app_manager`. Call `await app_manager.auto_start()` which queries `app_instances` for status='running' and starts each (logging failures, not blocking boot). In shutdown section before `sql_engine.dispose()`, call `await app_manager.shutdown_all()` which sends SIGTERM to all running apps and waits up to 10s. **Test fixture** — `tests/fixtures/test_health_server.py`: minimal Python script (~30 lines) that creates an HTTP server on a UDS path (passed as argv[1]), responds to `GET /_health` with 200 `{"status":"ok"}`, handles SIGTERM for graceful shutdown. This is a test-only fixture, not SDK code. **Contract tests** — `test_app_lifecycle_contract.py`: create a temp dir with a valid `manifest.yaml` (minimal fields), create AppManager with a temp data dir, install the app (skip venv creation by patching `_create_venv`), start using the test health server fixture, assert health check passes, assert status is 'running' with valid PID, stop and assert status is 'stopped', restart and assert status is 'running' again. Test crash recovery: start, kill the process, assert it restarts automatically.
  - Verify: `cd backend && python -m pytest tests/test_app_lifecycle_contract.py -v`
  - Done when: Platform lifespan creates AppManager. Auto-start queries DB. Shutdown sends SIGTERM. Contract tests prove real subprocess lifecycle works end-to-end.

## Files Likely Touched

- `backend/app/apps/__init__.py` (new)
- `backend/app/apps/manifest.py` (new)
- `backend/app/apps/models.py` (new)
- `backend/app/apps/registry.py` (new)
- `backend/app/apps/manager.py` (new)
- `backend/migrations/versions/013_app_tables.py` (new)
- `backend/pyproject.toml` (modified — add PyJWT, packaging)
- `backend/app/main.py` (modified — lifespan wiring)
- `backend/tests/test_app_manifest.py` (new)
- `backend/tests/test_app_manager.py` (new)
- `backend/tests/test_app_lifecycle_contract.py` (new)
- `backend/tests/fixtures/test_health_server.py` (new)
