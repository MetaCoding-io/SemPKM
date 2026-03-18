# S01: Manifest, DB Schema & Subprocess Lifecycle — UAT

**Milestone:** M009
**Written:** 2026-03-18

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S01 is a pure backend slice with no UI — all deliverables are Python modules and database schemas verified through automated tests. No browser or Docker stack needed.

## Preconditions

- Working directory: `backend/` within the M009 worktree
- Python venv active (`.venv/bin/python` accessible)
- No stale socket at `/tmp/sempkm-app-test-app.sock`

## Smoke Test

```bash
cd backend && .venv/bin/python -c "from app.apps.manifest import AppManifestSchema; from app.apps.manager import AppManager; from app.apps.models import AppInstance; print('All imports OK')"
```

Expected: prints "All imports OK" with exit code 0.

## Test Cases

### 1. Manifest Validation — All 61 Tests Pass

1. Run `cd backend && .venv/bin/python -m pytest tests/test_app_manifest.py -v`
2. **Expected:** 61 tests pass, 0 failures, <1s runtime
3. Verify test classes cover: valid manifests (minimal + full), appId rejection, semver, dependency ranges, interval bounds, cross-field validators, command palette actions, renderer modes, settings, YAML parsing, edge cases

### 2. AppManager Unit Tests — All 30 Tests Pass

1. Run `cd backend && .venv/bin/python -m pytest tests/test_app_manager.py -v`
2. **Expected:** 30 tests pass, 0 failures, <1s runtime (2 RuntimeWarning about unawaited coroutine are expected — mock artifact)
3. Verify test classes cover: install flow, start (subprocess + health + socket cleanup), stop (SIGTERM + SIGKILL fallback), restart, uninstall, crash recovery (backoff + max retries + intentional stop skips), status reporting, log buffer, health check (success + timeout), uv execution

### 3. Contract Tests — All 8 Tests Pass on Real UDS

1. Run `cd backend && .venv/bin/python -m pytest tests/test_app_lifecycle_contract.py -v`
2. **Expected:** 8 tests pass, 0 failures, ~29s runtime (real backoff waits)
3. Verify these contract points:
   - `test_install_and_start`: Process starts with valid PID, DB status='running', socket file exists
   - `test_health_check_on_uds`: `GET /_health` on UDS returns 200 with `{"status":"ok"}`
   - `test_stop`: Process terminated, DB status='stopped', PID cleared
   - `test_restart`: New PID after restart, DB status='running'
   - `test_crash_recovery`: SIGKILL → automatic restart with new PID, restart_count ≥ 1
   - `test_crash_recovery_exhaustion`: 4 kills → DB status='error', error_message contains "Crashed"
   - `test_auto_start`: Seeds status='running' row → auto_start picks it up and starts process
   - `test_shutdown_all`: Processes stopped but DB status stays 'running' (for next auto_start)

### 4. SQLAlchemy Models Importable with Correct Structure

1. Run `cd backend && .venv/bin/python -c "from app.apps.models import AppInstance, AppTaskRun, AppTaskConfig, AppRendererPref, AppPermission; print('OK')"`
2. **Expected:** prints "OK"
3. Verify model structure: `cd backend && .venv/bin/python -c "
from app.apps.models import AppInstance, AppTaskRun, AppTaskConfig, AppRendererPref, AppPermission
# Check AppInstance columns
cols = [c.name for c in AppInstance.__table__.columns]
assert 'app_id' in cols and 'status' in cols and 'pid' in cols and 'restart_count' in cols
# Check AppTaskRun has composite index
idx_names = [i.name for i in AppTaskRun.__table__.indexes]
assert any('app_id_task_id' in n for n in idx_names)
# Check FK cascade on AppPermission
fks = list(AppPermission.__table__.foreign_keys)
assert len(fks) == 1 and fks[0].ondelete == 'CASCADE'
print('Structure OK')
"`
4. **Expected:** prints "Structure OK"

### 5. Alembic Migration 014 Is Syntactically Valid

1. Run `cd backend && python3 -c "import ast; ast.parse(open('migrations/versions/014_app_tables.py').read()); print('OK')"`
2. **Expected:** prints "OK"
3. Verify revision chain: `grep 'down_revision' migrations/versions/014_app_tables.py`
4. **Expected:** `down_revision = "013"`

### 6. Lifespan Wiring in main.py

1. Run `grep -n "app_manager\|AppManager\|auto_start\|shutdown_all" backend/app/main.py`
2. **Expected:** At least 5 lines showing:
   - `from app.apps.manager import AppManager`
   - `app_manager = AppManager(...)` construction with session_factory, triplestore_client, apps_dir, data_dir, platform_url
   - `app.state.app_manager = app_manager`
   - `await app_manager.auto_start()`
   - `await app_manager.shutdown_all()`

### 7. Dependencies Added to pyproject.toml

1. Run `grep -E "packaging|PyJWT" backend/pyproject.toml`
2. **Expected:** Both lines present: `packaging~=25.0` and `PyJWT~=2.10`

## Edge Cases

### Stale Socket Cleanup

1. Create a stale socket: `touch /tmp/sempkm-app-test-app.sock`
2. Run `cd backend && .venv/bin/python -m pytest tests/test_app_lifecycle_contract.py::test_install_and_start -v`
3. **Expected:** Test passes — start() cleans up the stale socket before spawning the process

### Manifest Cross-Field Validation

1. Run `cd backend && .venv/bin/python -c "
from app.apps.manifest import AppManifestSchema
try:
    AppManifestSchema(appId='test', version='1.0.0', name='Test', backend={'entrypoint':'a:B'}, dependencies={'platform':'>=1.0.0'}, tasks=[{'id':'t1','handler':'h','interval':'5m'}], permissions={})
    print('ERROR: should have raised')
except Exception as e:
    assert 'backgroundTasks' in str(e)
    print('Cross-field validator caught: tasks require backgroundTasks permission')
"`
2. **Expected:** prints the validation message — tasks without backgroundTasks permission rejected

### Interval Bounds

1. Run `cd backend && .venv/bin/python -c "
from app.apps.manifest import AppManifestSchema
# Below 30s floor
try:
    AppManifestSchema(appId='test', version='1.0.0', name='Test', backend={'entrypoint':'a:B'}, dependencies={'platform':'>=1.0.0'}, tasks=[{'id':'t1','handler':'h','interval':'10s'}], permissions={'backgroundTasks':True})
    print('ERROR: should have raised')
except Exception as e:
    assert '30s' in str(e) or '30 seconds' in str(e).lower()
    print('30s floor enforced')
"`
2. **Expected:** prints "30s floor enforced"

## Failure Signals

- Any test failure in the 3 test files indicates a regression
- Import failures from `app.apps.*` indicate missing or broken module structure
- Missing `app_manager` references in `main.py` means lifespan wiring is incomplete
- Contract test hanging >60s indicates a process or socket cleanup issue
- `RuntimeError: App test-app health check failed after 30s` in contract tests indicates the test health server didn't start (check for socket permission issues or port conflicts)

## Requirements Proved By This UAT

- APP-01 — Manifest validation with all design §14 constraints (Test Cases 1, Edge Cases 2–3)
- APP-13 — DB tables with correct schema (Test Cases 4–5)
- APP-02 (partially) — Lifecycle management proven via contract tests (Test Case 3) but pending SDK runner for full validation

## Not Proven By This UAT

- APP-02 full validation — requires real SDK app (S02) to prove end-to-end lifecycle with a real app, not a test fixture
- Docker integration — migration 014 not run against a real DB in Docker (verified syntactically only)
- Admin UI interaction — no UI exists yet (S03)
- Inter-process communication — health check is the only IPC tested; SDK client→platform communication is S02

## Notes for Tester

- Contract tests take ~29s due to real exponential backoff waits (1s+2s+4s in crash recovery tests). This is by design.
- The 2 RuntimeWarnings in manager unit tests are a known mock artifact (session.add() returns a coroutine in mocks). Not a bug.
- If test_install_and_start fails on first run but passes on retry, it's likely a stale socket from a prior crashed test run.
