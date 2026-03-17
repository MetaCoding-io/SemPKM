---
estimated_steps: 8
estimated_files: 4
---

# T03: AppRegistry + AppManager lifecycle engine

**Slice:** S01 — Manifest, DB Schema & Subprocess Lifecycle
**Milestone:** M009

## Description

Build the core subprocess lifecycle management engine. `AppRegistry` is the in-memory manifest cache. `AppManager` orchestrates all lifecycle operations (install, start, stop, restart, uninstall) with crash recovery, health checking, and log capture. This is the critical-path deliverable of S01 and the highest-risk component in M009.

## Steps

1. Create `backend/app/apps/registry.py` — `AppRegistry` class:
   - `_apps: dict[str, AppManifestSchema]` keyed by app_id
   - `register(app_id: str, manifest: AppManifestSchema) → None`
   - `unregister(app_id: str) → None`
   - `get_manifest(app_id: str) → AppManifestSchema | None`
   - `list_apps() → list[str]` returns registered app_ids
   - `get_app(app_id: str) → dict | None` returns manifest summary dict (id, name, version)

2. Create `backend/app/apps/manager.py` — `AppManager` class constructor:
   - Parameters: `session_factory` (async session maker), `triplestore_client` (TriplestoreClient), `apps_dir` (Path — where app source dirs live, e.g. `/app/apps`), `data_dir` (Path — where venvs/runtime data live, e.g. `/app/data/apps`), `platform_url` (str)
   - Internal state: `_processes: dict[str, asyncio.subprocess.Process]`, `_watchers: dict[str, asyncio.Task]`, `_log_buffers: dict[str, collections.deque]`, `_registry: AppRegistry`, `_stop_flags: set[str]` (to distinguish intentional stop from crash), `_install_lock: asyncio.Lock` (per research: prevent concurrent install races)

3. Implement `AppManager.install(app_dir: Path) → dict`:
   - Parse manifest via `parse_app_manifest(app_dir / "manifest.yaml")`
   - Check `dependencies.platform` against `settings.app_version` using `packaging.specifiers.SpecifierSet`
   - Compute manifest_hash via `hashlib.sha256` of manifest file bytes
   - Acquire `_install_lock`
   - Create data dir: `self.data_dir / app_id`
   - Create venv: `await _run_uv(["venv", str(venv_path)])` where venv_path = `data_dir / app_id / "venv"`
   - Install deps: `await _run_uv(["pip", "install", "-r", str(app_dir / manifest.backend.requirements), "--python", str(venv_path / "bin" / "python")])`
   - Note: `_run_uv()` is a private async method that runs `/bin/uv` via `asyncio.create_subprocess_exec` and raises on non-zero exit
   - Insert `AppInstance` row into DB (status='installing', manifest_hash, installed_at=now)
   - Register manifest in `_registry`
   - Call `await self.start(app_id)`
   - Return status dict

4. Implement `AppManager.start(app_id: str) → None`:
   - Get manifest from registry
   - Clean up stale socket: `socket_path = Path(f"/tmp/sempkm-app-{app_id}.sock")`; if exists, `os.unlink()`
   - Build command: `[str(venv_python), "-m", "sempkm_app_sdk.runner", "--app-dir", str(app_dir), "--socket", str(socket_path), "--platform-url", self.platform_url]`
   - Note: `--app-token` will be added in S02 when JWT exists — for now, pass a placeholder or omit
   - Start process: `asyncio.create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)`
   - Store process in `_processes[app_id]`
   - Start log capture tasks: `_capture_output(app_id, proc.stdout)` and `_capture_output(app_id, proc.stderr)` — both append to `_log_buffers[app_id]` (a `collections.deque(maxlen=100)`)
   - Start watcher task: `_watchers[app_id] = asyncio.create_task(_watch_process(app_id))`
   - Wait for health: `await _wait_for_health(app_id, socket_path, timeout=30)`
   - Update DB: status='running', pid=proc.pid, socket_path=str(socket_path), started_at=now, restart_count=0

5. Implement `AppManager.stop(app_id: str) → None`, `restart(app_id)`, `uninstall(app_id)`:
   - `stop`: Add app_id to `_stop_flags`, send SIGTERM to process, wait up to 5s (`asyncio.wait_for(proc.wait(), timeout=5)`), SIGKILL if still alive, clean up `_processes`/`_watchers`/`_log_buffers`, update DB status='stopped', reset restart_count=0
   - `restart`: `await stop(app_id)`, then `await start(app_id)`
   - `uninstall`: `await stop(app_id)`, delete socket file, `shutil.rmtree(data_dir / app_id)` (removes venv), delete `AppInstance` row from DB, `_registry.unregister(app_id)`
   - `get_status(app_id) → dict`: query DB for current row, add uptime calc from started_at, return {app_id, status, pid, uptime_seconds, restart_count, error_message, version}
   - `get_logs(app_id) → list[str]`: return list(self._log_buffers.get(app_id, []))

6. Implement crash recovery — `async _watch_process(app_id: str)`:
   - `await proc.wait()` — blocks until process exits
   - If `app_id in _stop_flags`: remove from flags, return (intentional stop)
   - Else: unexpected crash. Log at WARNING with exit code.
   - Read current restart_count from `_processes` tracking or DB
   - If restart_count < 3: increment, compute backoff = `2 ** restart_count` seconds (1s, 2s, 4s), `await asyncio.sleep(backoff)`, call `await start(app_id)` (which resets restart_count on success — actually, preserve the count), update DB restart_count
   - If restart_count >= 3: mark status='error' in DB, set error_message = f"Crashed {restart_count + 1} times, last exit code: {returncode}", log at ERROR
   - Important: restart_count must persist across restart attempts but reset to 0 on manual start/restart

7. Implement health check — `async _wait_for_health(app_id: str, socket_path: Path, timeout: int = 30)`:
   - Poll loop: every 1 second for `timeout` seconds
   - Use `httpx.AsyncClient(transport=httpx.AsyncHTTPTransport(uds=str(socket_path)))` 
   - `GET http://localhost/_health` (host doesn't matter for UDS, but httpx requires it)
   - On 200 response: return
   - On connection error: continue polling (process still starting)
   - On timeout: raise `RuntimeError(f"App {app_id} health check failed after {timeout}s")`
   - Close the httpx client after use

8. Write `backend/tests/test_app_manager.py` with unit tests using mocked subprocess:
   - Test `install()` calls uv venv + uv pip install in correct order
   - Test `start()` builds correct command, starts process, calls health check
   - Test `stop()` sends SIGTERM, then SIGKILL on timeout
   - Test `restart()` calls stop then start
   - Test crash recovery: mock process exiting unexpectedly, verify restart with backoff delay
   - Test crash recovery stops after 3 failures and marks error
   - Test `get_status()` returns correct dict
   - Test `get_logs()` returns buffer contents
   - Test socket cleanup on start (mock `os.path.exists` + `os.unlink`)
   - Test install lock prevents concurrent installs
   - Mock `asyncio.create_subprocess_exec`, `httpx.AsyncClient`, DB session

## Must-Haves

- [ ] `AppRegistry` provides manifest cache with register/unregister/get/list
- [ ] `AppManager.install()` creates venv via `/bin/uv`, installs deps, registers, starts
- [ ] `AppManager.start()` cleans socket, starts subprocess, captures output, waits for health
- [ ] `AppManager.stop()` sends SIGTERM→SIGKILL with 5s timeout
- [ ] `AppManager.uninstall()` stops, removes venv dir, deletes DB row
- [ ] Crash recovery restarts up to 3x with exponential backoff (1s, 2s, 4s)
- [ ] Log capture via ring buffer (deque maxlen=100)
- [ ] Health check polls `/_health` on UDS via httpx
- [ ] Unit tests with mocked subprocess cover all state transitions

## Verification

- `cd backend && python -m pytest tests/test_app_manager.py -v` — all tests pass
- `cd backend && python -c "from app.apps.manager import AppManager; from app.apps.registry import AppRegistry; print('OK')"` — importable

## Observability Impact

- Signals added: `app_instances.status` transitions logged at INFO, crash recovery at WARNING, max-retry at ERROR
- How a future agent inspects this: `AppManager.get_status(app_id)` returns status/pid/uptime/restart_count/error_message dict; `AppManager.get_logs(app_id)` returns last 100 stdout/stderr lines
- Failure state exposed: `app_instances.error_message` + `app_instances.restart_count` persisted to DB on crash exhaustion

## Inputs

- `backend/app/apps/manifest.py` — `AppManifestSchema`, `parse_app_manifest` from T01
- `backend/app/apps/models.py` — `AppInstance` SQLAlchemy model from T02
- `backend/app/apps/__init__.py` — package from T01
- `.gsd/design/APP-PLATFORM-DESIGN.md` §5 (Process Architecture), §10 (Lifecycle Management) — subprocess model, startup command, supervision table
- Existing pattern: `backend/app/services/models.py` `ModelService.install()/remove()` — lifecycle reference

## Expected Output

- `backend/app/apps/registry.py` — `AppRegistry` class
- `backend/app/apps/manager.py` — `AppManager` class with full lifecycle methods
- `backend/tests/test_app_manager.py` — 15+ unit tests with mocked subprocess
