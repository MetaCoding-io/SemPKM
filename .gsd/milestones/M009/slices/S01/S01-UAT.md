# S01: Manifest, DB Schema & Subprocess Lifecycle — UAT

**Milestone:** M009
**Written:** 2026-03-16

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S01 has no UI (admin portal is S03). All deliverables are backend modules proven via contract tests. The 101 automated tests cover manifest validation, lifecycle state machine, and real subprocess communication on UDS.

## Preconditions

- Backend venv active with all deps installed (including PyJWT, packaging)
- Working directory: `backend/`
- Python 3.14 available at `.venv/bin/python`
- No stale `/tmp/sempkm-app-*.sock` files from prior test runs

## Smoke Test

```bash
cd backend && .venv/bin/python -m pytest tests/test_app_manifest.py tests/test_app_manager.py tests/test_app_lifecycle_contract.py -v --tb=short
```
**Expected:** 101 passed (60 manifest + 31 manager + 10 contract), 4 warnings (harmless mock artifacts), ~25s total.

## Test Cases

### 1. Manifest validation rejects invalid appId

1. Run: `.venv/bin/python -c "from app.apps.manifest import AppManifestSchema; AppManifestSchema(appId='INVALID', version='1.0.0', name='Test', backend={'entrypoint': 'x'})"`
2. **Expected:** `ValidationError` with error on `appId` field — must match `^[a-z][a-z0-9-]*$`

### 2. Manifest validation rejects non-semver version

1. Run: `.venv/bin/python -c "from app.apps.manifest import AppManifestSchema; AppManifestSchema(appId='test', version='1.0', name='Test', backend={'entrypoint': 'x'})"`
2. **Expected:** `ValidationError` with error on `version` field — must be strict semver (X.Y.Z)

### 3. Manifest cross-validation: tasks require backgroundTasks permission

1. Run: `.venv/bin/python -c "from app.apps.manifest import AppManifestSchema; AppManifestSchema(appId='test', version='1.0.0', name='Test', backend={'entrypoint': 'x'}, tasks=[{'taskId': 't1', 'name': 'T', 'interval': '5m'}])"`
2. **Expected:** `ValidationError` — tasks defined without `permissions.backgroundTasks: true`

### 4. Manifest parses valid YAML file

1. Create temp file `/tmp/test_manifest.yaml`:
   ```yaml
   appId: test-app
   version: "1.0.0"
   name: Test App
   backend:
     entrypoint: "app:TestApp"
   ```
2. Run: `.venv/bin/python -c "from app.apps.manifest import parse_app_manifest; m = parse_app_manifest('/tmp/test_manifest.yaml'); print(m.appId, m.version)"`
3. **Expected:** Output `test-app 1.0.0`

### 5. All 5 SQLAlchemy models importable with correct table names

1. Run:
   ```python
   .venv/bin/python -c "
   from app.apps.models import AppInstance, AppTaskRun, AppTaskConfig, AppRendererPref, AppPermission
   assert AppInstance.__tablename__ == 'app_instances'
   assert AppTaskRun.__tablename__ == 'app_task_runs'
   assert AppTaskConfig.__tablename__ == 'app_task_config'
   assert AppRendererPref.__tablename__ == 'app_renderer_prefs'
   assert AppPermission.__tablename__ == 'app_permissions'
   print('All models OK')
   "
   ```
2. **Expected:** Output `All models OK`

### 6. Alembic migration 013 is syntactically valid

1. Run: `.venv/bin/python -c "import ast; ast.parse(open('migrations/versions/013_app_tables.py').read()); print('OK')"`
2. **Expected:** Output `OK`

### 7. AppRegistry CRUD operations

1. Run:
   ```python
   .venv/bin/python -c "
   from app.apps.registry import AppRegistry
   from app.apps.manifest import AppManifestSchema
   r = AppRegistry()
   m = AppManifestSchema(appId='test', version='1.0.0', name='T', backend={'entrypoint': 'x'})
   r.register('test', m)
   assert r.get_manifest('test') == m
   assert 'test' in [a['app_id'] for a in r.list_apps()]
   r.unregister('test')
   assert r.get_manifest('test') is None
   print('Registry OK')
   "
   ```
2. **Expected:** Output `Registry OK`

### 8. AppManager importable and constructible

1. Run: `.venv/bin/python -c "from app.apps.manager import AppManager; print('OK')"`
2. **Expected:** Output `OK`

### 9. Contract test: real subprocess health check on UDS

1. Run: `.venv/bin/python -m pytest tests/test_app_lifecycle_contract.py::TestAppLifecycleContract::test_health_check_passes -v`
2. **Expected:** PASSED — the test spawns a real subprocess, connects to its UDS, and verifies `/_health` returns `200 OK` with `{"status":"ok"}`

### 10. Contract test: crash recovery restarts the process

1. Run: `.venv/bin/python -m pytest tests/test_app_lifecycle_contract.py::TestAppLifecycleContract::test_crash_recovery -v`
2. **Expected:** PASSED — the test SIGKILLs a running app process, then verifies the crash watcher restarts it with a new PID and increments `restart_count`

### 11. Contract test: crash exhaustion marks error state

1. Run: `.venv/bin/python -m pytest tests/test_app_lifecycle_contract.py::TestAppLifecycleContract::test_crash_recovery_exhaustion -v`
2. **Expected:** PASSED — after 4 kills (initial + 3 retries), app status is `'error'` with a non-null `error_message`

### 12. AppManager wired into platform lifespan

1. Run: `grep -n "app_manager" app/main.py`
2. **Expected:** Lines showing AppManager creation, `auto_start()` call, and `shutdown_all()` call in the lifespan function

## Edge Cases

### Manifest interval boundary enforcement

1. Run: `.venv/bin/python -m pytest tests/test_app_manifest.py::TestIntervalParsing -v`
2. **Expected:** All interval tests pass — 30s minimum enforced, 24h maximum enforced, shorthand (5m, 1h, 30s) and ISO 8601 (PT5M) both accepted

### Crash recovery exhaustion boundary

1. Run: `.venv/bin/python -m pytest tests/test_app_manager.py::TestAppManagerCrashRecovery -v`
2. **Expected:** 4 tests pass — restart on unexpected exit, stop after max retries (3), ignore intentional stop, exponential backoff timing

### Auto-start skips stopped apps

1. Run: `.venv/bin/python -m pytest tests/test_app_lifecycle_contract.py::TestAutoStart::test_auto_start_skips_stopped_apps -v`
2. **Expected:** PASSED — apps with status='stopped' are not started on platform boot

## Failure Signals

- `ImportError` on any `from app.apps.*` import → package structure broken
- Contract tests timing out (>60s) → health server not starting, socket path conflict, or httpx UDS transport issue
- `RuntimeError: App test-app health check failed after 30s` → stale socket file or subprocess not starting
- `test_crash_recovery` timing out → watcher task not detecting process exit or backoff too long
- Migration file syntax error → `ast.parse()` will fail

## Requirements Proved By This UAT

- APP-01 (manifest validation) — test cases 1-4 prove field validators and cross-field validators
- APP-02 (subprocess lifecycle) — test cases 9-11 prove start/health/crash-recovery/exhaustion on real subprocess
- APP-13 (DB tables + migrations) — test cases 5-6 prove models and migration are valid

## Not Proven By This UAT

- Docker stack integration (venv creation via `uv` inside container) — deferred to S03/S07
- Admin UI for app management — deferred to S03
- SDK runner as the actual subprocess — contract tests use a test fixture; real SDK is S02
- Migration applied to real SQLite/PostgreSQL database — migration file is valid syntax but `alembic upgrade` not exercised without Docker

## Notes for Tester

- Contract tests spawn real subprocesses and take ~21s — this is expected, not a performance issue.
- The 4 RuntimeWarnings in `test_app_manager.py` about unawaited coroutines are known harmless mock artifacts — ignore them.
- If `/tmp/sempkm-app-test-app.sock` is stale from a crashed test run, delete it before re-running contract tests.
- The `packaging` pin at ~=25.0 may show a downgrade warning if your venv had 26.x — this is intentional per the design spec.
