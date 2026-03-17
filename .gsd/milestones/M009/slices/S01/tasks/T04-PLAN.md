---
estimated_steps: 5
estimated_files: 4
---

# T04: Lifespan integration + auto-start + contract tests

**Slice:** S01 — Manifest, DB Schema & Subprocess Lifecycle
**Milestone:** M009

## Description

Wire the AppManager into the platform lifespan so apps auto-start on boot and cleanly stop on shutdown. Then prove the entire lifecycle works end-to-end with contract tests that start a real subprocess on a real unix domain socket — not mocked.

## Steps

1. Create `backend/tests/fixtures/test_health_server.py` — a minimal standalone Python script (~35 lines) that:
   - Takes a socket path as `sys.argv[1]`
   - Creates a simple HTTP server on that unix socket (use `http.server.HTTPServer` with a custom server class that binds to the UDS, or use `socketserver.UnixStreamServer` — simplest approach is `aiohttp` or just raw socket + HTTP parsing, but since we want zero external deps: use the stdlib `http.server` approach with a Unix socket override)
   - Actually simplest: use `asyncio` with raw streams: `asyncio.start_unix_server(handler, path=socket_path)`, read HTTP request lines, respond with `HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{"status":"ok"}` for any GET to `/_health`
   - Handle SIGTERM by closing the server and exiting cleanly
   - This is test-only infrastructure — not SDK code (SDK comes in S02)
   - Must be executable: `#!/usr/bin/env python3` and `if __name__ == "__main__"`

2. Modify `backend/app/main.py` lifespan function:
   - Add import: `from app.apps.manager import AppManager`
   - After the `app.state.workflow_service = WorkflowService(async_session_factory)` line (near end of service init, after SQL engine is ready):
     ```python
     # Initialize App Platform manager
     app_manager = AppManager(
         session_factory=async_session_factory,
         triplestore_client=client,
         apps_dir=Path("/app/apps"),
         data_dir=Path("/app/data/apps"),
         platform_url=f"http://localhost:{settings.port}",
     )
     app.state.app_manager = app_manager
     
     # Auto-start apps that were running before platform shutdown
     try:
         await app_manager.auto_start()
     except Exception:
         logger.error("Failed to auto-start apps", exc_info=True)
     ```
   - In shutdown section (before `await sql_engine.dispose()`), add:
     ```python
     # Gracefully shut down all running app subprocesses
     try:
         await app_manager.shutdown_all()
     except Exception:
         logger.error("Error shutting down app processes", exc_info=True)
     ```

3. Add `auto_start()` method to `AppManager`:
   - Query `app_instances` table for rows where status='running' (these were running when platform last shut down)
   - For each, attempt `await self.start(app_id)` 
   - Log each start attempt result (success or failure)
   - Don't raise on individual failures — log and continue to next app

4. Add `shutdown_all()` method to `AppManager`:
   - For each app_id in `_processes`:
     - Send SIGTERM to the process
   - `await asyncio.gather(*[self._wait_process_exit(app_id, timeout=10) for app_id in list(self._processes)])` 
   - For any still alive after 10s, send SIGKILL
   - Update all DB rows to status='stopped' (preserving the 'running' marker so auto_start works next boot — actually, keep status='running' in DB during clean shutdown so auto_start picks them up again; only set 'stopped' on explicit user stop)
   - Design decision: on platform shutdown, leave DB status as 'running' so next boot auto-starts them. On explicit user `stop()`, set status='stopped'.

5. Create `backend/tests/test_app_lifecycle_contract.py` — integration/contract tests using the real test_health_server:
   - **Fixture: `tmp_app_dir`** — creates a temp directory with a minimal `manifest.yaml` (appId: "test-app", version: "0.1.0", name: "Test App", backend.entrypoint: "app:TestApp", minimal required fields only)
   - **Fixture: `app_manager`** — creates an AppManager with temp data dir, mocked session_factory (use in-memory SQLite via `aiosqlite`), mocked triplestore_client, apps_dir = tmp_app_dir.parent
   - **Patch `_create_venv` and `_install_deps`** — skip uv calls (no real venv needed since test_health_server uses system Python)
   - **Override the start command** — instead of `venv/bin/python -m sempkm_app_sdk.runner ...`, use `sys.executable tests/fixtures/test_health_server.py {socket_path}` (patch the command building)
   - **Test: install and start** — call install, assert status is 'running', assert PID is set, assert socket file exists
   - **Test: health check passes** — after start, manually hit the UDS with httpx and verify 200 response
   - **Test: stop** — call stop, assert status is 'stopped', assert process is terminated
   - **Test: restart** — call restart, assert status is 'running' with new PID
   - **Test: crash recovery** — start the app, kill the process directly (proc.kill()), wait a couple seconds for the watcher to detect + restart, assert restart_count incremented and status is 'running' again
   - **Test: crash recovery exhaustion** — start, kill 4 times (exhausting 3 retries), assert final status is 'error' with error_message set
   - Mark these tests with `@pytest.mark.asyncio` and use `pytest.mark.timeout(30)` to prevent hangs

## Must-Haves

- [ ] `AppManager` created in `main.py` lifespan after SQL init
- [ ] `auto_start()` queries DB for previously-running apps and starts them
- [ ] `shutdown_all()` sends SIGTERM to all running apps with 10s timeout
- [ ] Platform shutdown preserves 'running' status in DB for next auto-start
- [ ] Contract tests prove real subprocess lifecycle on UDS
- [ ] Crash recovery verified with real process kill + automatic restart

## Verification

- `cd backend && python -m pytest tests/test_app_lifecycle_contract.py -v` — all contract tests pass
- `cd backend && python -c "from app.apps.manager import AppManager; print('OK')"` — auto_start/shutdown_all exist
- `grep -n "app_manager" backend/app/main.py` — confirms lifespan wiring

## Observability Impact

- Signals added: auto_start logs INFO per app started, WARNING on failures; shutdown_all logs INFO on clean shutdown, WARNING on SIGKILL fallback
- How a future agent inspects this: `app.state.app_manager.get_status(app_id)` from any request handler
- Failure state exposed: auto_start failures logged but don't block platform boot

## Inputs

- `backend/app/apps/manager.py` — `AppManager` from T03
- `backend/app/apps/manifest.py` — `AppManifestSchema` from T01
- `backend/app/apps/models.py` — `AppInstance` model from T02
- `backend/app/main.py` — existing lifespan function (wiring point)
- Pattern: existing lifespan service initialization order (after SQL, before yield)

## Expected Output

- `backend/app/main.py` — modified with AppManager init, auto_start, shutdown_all
- `backend/tests/fixtures/test_health_server.py` — standalone UDS HTTP server for testing
- `backend/tests/test_app_lifecycle_contract.py` — 5-6 contract tests proving real subprocess lifecycle
- `backend/app/apps/manager.py` — updated with `auto_start()` and `shutdown_all()` methods
