---
estimated_steps: 4
estimated_files: 4
---

# T04: Integration proof — real subprocess round-trip

**Slice:** S02 — App SDK & IPC Proxy
**Milestone:** M009

## Description

Prove the full S02 contract with real subprocesses: platform → proxy → UDS → SDK app → response. Creates a minimal SDK-based test app fixture and contract tests that start a real subprocess running the SDK runner, then exercise health, fragment, lifecycle, and task endpoints through the UDS connection. This replaces the test_health_server.py fixture approach for SDK-level integration testing.

## Steps

1. **Create test app fixture at `backend/tests/fixtures/test_sdk_app/`**:
   - `manifest.yaml`: minimal valid manifest matching `AppManifestSchema`. Fields: `appId: "test-sdk"`, `name: "Test SDK App"`, `version: "1.0.0"`, `description: "Minimal app for SDK contract tests"`, `author: "SemPKM Tests"`, `dependencies: {platform: ">=0.1.0"}`, `backend: {entrypoint: "app:test_app"}`, `permissions: {commands: []}`, `tasks: []`, `frontend: {pages: [{id: "main", title: "Main", route: "/_fragments/main"}]}`.
   - `app.py`: Import `from sempkm_app_sdk import App, AppContext`. Create `test_app = App("test-sdk")`. Register one route: `@test_app.route("/_fragments/main")` returning `<div>Hello from test-sdk</div>`. Register one task: `@test_app.task("test-task")` returning `{"result": "ok"}`. Register `@test_app.on_startup` that logs "test-sdk started".
   - `requirements.txt`: empty file (SDK injected by platform, no additional deps).

2. **Create `backend/tests/test_sdk_integration.py`** — contract tests:
   - **Setup**: Determine paths — `sdk_path = Path(__file__).parent.parent / "sdk"`, `fixture_path = Path(__file__).parent / "fixtures" / "test_sdk_app"`. Install SDK into current venv if not already installed: `subprocess.run([sys.executable, "-m", "pip", "install", str(sdk_path)], check=True)`. Generate a JWT for testing: `from app.apps.tokens import generate_app_token, get_secret; token = generate_app_token("test-sdk", {}, get_secret())`.
   - **Fixture**: `pytest` fixture that starts the subprocess: `socket_path = f"/tmp/sempkm-app-test-sdk-{uuid4().hex[:8]}.sock"` (unique per test run to avoid collisions). Start: `proc = subprocess.Popen([sys.executable, "-m", "sempkm_app_sdk.runner", "--app-dir", str(fixture_path), "--socket", socket_path, "--platform-url", "http://localhost:8000", "--app-token", token], stdout=subprocess.PIPE, stderr=subprocess.PIPE)`. Wait for socket file to appear (poll with 0.2s intervals, 15s timeout). Yield `(proc, socket_path, token)`. Teardown: `proc.terminate(); proc.wait(timeout=5)`. Clean up socket.
   - **Test: `/_health`**: Create `httpx.AsyncClient(transport=httpx.AsyncHTTPTransport(uds=socket_path))`. `GET http://localhost/_health` → 200, body `{"status": "ok"}`.
   - **Test: `/_fragments/main`**: `GET http://localhost/_fragments/main` → 200, body contains `Hello from test-sdk`.
   - **Test: `/_lifecycle/startup`**: `POST http://localhost/_lifecycle/startup` with `X-SemPKM-App-Token: {token}` → 200.
   - **Test: `/_tasks/test-task`**: `POST http://localhost/_tasks/test-task` with `X-SemPKM-App-Token: {token}` → 200, body contains `result`.
   - **Test: token required on system endpoints**: `POST http://localhost/_lifecycle/startup` without token → 403.
   - **Test: health exempt from token**: `GET http://localhost/_health` without token → 200 (health is always public for liveness checks).
   - Use `pytest-asyncio` for async tests with `httpx.AsyncClient`.

3. **Handle test environment concerns**:
   - The tests use `subprocess.Popen` (not `asyncio.create_subprocess_exec`) for simplicity in pytest fixtures. Sync subprocess is fine — the runner internally is async.
   - Socket path uses random suffix to allow parallel test runs.
   - If SDK not installed, the setup fixture installs it — this adds ~5s on first run.

4. **Verify all S02 tests together**:
   - `cd backend && .venv/bin/pytest tests/test_app_tokens.py tests/test_sdk_app.py tests/test_app_proxy.py tests/test_sdk_integration.py -v`

## Must-Haves

- [ ] Test fixture app uses real `sempkm_app_sdk` imports (App, AppContext)
- [ ] Real subprocess starts and serves on UDS
- [ ] `/_health` returns 200 OK
- [ ] Fragment route returns expected HTML content
- [ ] Lifecycle endpoint dispatches to registered handler
- [ ] Task endpoint dispatches to registered handler
- [ ] Token validation enforced on system endpoints (except health)
- [ ] All tests pass, including prior S02 tests

## Verification

- `cd backend && .venv/bin/pytest tests/test_sdk_integration.py -v` — all integration tests pass
- `cd backend && .venv/bin/pytest tests/test_app_tokens.py tests/test_sdk_app.py tests/test_app_proxy.py tests/test_sdk_integration.py -v` — full S02 test suite passes

## Observability Impact

- **New test signals**: Integration tests exercise the real subprocess and UDS path — failures surface as pytest failures with captured stdout/stderr from the runner process
- **Runtime inspection**: Test fixture subprocess emits uvicorn access logs and SDK-level logs (lifecycle dispatch, token validation) to stderr, captured by pytest on failure
- **Failure visibility**: If the subprocess crashes during test, the fixture captures stdout/stderr and includes them in the pytest.fail() message — no silent failures
- **Socket cleanup**: Stale sockets are cleaned up in fixture teardown; unique per-run suffixes prevent cross-run collisions

## Inputs

- `backend/sdk/` (T02) — complete SDK package with App, AppContext, runner
- `backend/app/apps/tokens.py` (T01) — `generate_app_token()`, `get_secret()` for creating test tokens
- `backend/tests/fixtures/test_health_server.py` (S01) — existing pattern for UDS test fixtures (reference only, not modified)

## Expected Output

- `backend/tests/fixtures/test_sdk_app/manifest.yaml` — minimal valid app manifest
- `backend/tests/fixtures/test_sdk_app/app.py` — SDK-based test app with route, task, lifecycle handlers
- `backend/tests/fixtures/test_sdk_app/requirements.txt` — empty requirements
- `backend/tests/test_sdk_integration.py` — ~8 contract tests proving the full SDK round-trip on real UDS
