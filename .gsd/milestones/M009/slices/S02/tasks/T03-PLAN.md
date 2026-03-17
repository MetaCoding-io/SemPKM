---
estimated_steps: 6
estimated_files: 5
---

# T03: Platform proxy, router, and manager updates

**Slice:** S02 — App SDK & IPC Proxy
**Milestone:** M009

## Description

Wire the platform side of the IPC channel. `AppProxy` forwards HTTP requests to app subprocesses over UDS. A new FastAPI router exposes `/app/{app_id}/{path:path}` and a token renewal endpoint. `AppManager` gains JWT generation on start, SDK install on install, and a token store. The proxy router is included in `main.py` before `browser_router` to avoid the catch-all `{iri:path}` consuming `/app/` URLs.

## Steps

1. **Create `backend/app/apps/proxy.py`** — `AppProxy` class:
   - `__init__(self, manager: AppManager)` — stores manager reference, creates `_clients: dict[str, httpx.AsyncClient]` for connection pooling per app.
   - `async forward(self, app_id: str, path: str, request: Request) -> Response`:
     1. Get socket path: `/tmp/sempkm-app-{app_id}.sock`
     2. Check socket file exists — if not, raise `AppNotReachableError` (custom exception)
     3. Get or create `httpx.AsyncClient` with `transport=httpx.AsyncHTTPTransport(uds=str(socket_path))` for this app_id. Base URL: `http://localhost` (required by httpx but ignored for UDS).
     4. Build target URL: `http://localhost/{path}`
     5. Copy headers from incoming request, add/replace `X-SemPKM-App-Token` with token from `manager.get_token(app_id)`
     6. Forward via `client.send(client.build_request(method, url, headers=headers, content=await request.body()))` with `stream=True` — actually, for simplicity in v1, use `client.request(method, url, headers=..., content=...)` without streaming. Streaming can be added later if large responses are a problem.
     7. Return `Response(content=response.content, status_code=response.status_code, headers=dict(response.headers))`
   - `async close_client(self, app_id: str)` — pop and `await client.aclose()` for cleanup on app stop.
   - `async close_all(self)` — close all clients (platform shutdown).

2. **Create `backend/app/apps/router.py`** — FastAPI router:
   - `app_proxy_router = APIRouter()` — no prefix (routes define full paths).
   - `ANY /app/{app_id}/{path:path}` — catch-all for all HTTP methods. Use `@router.api_route("/app/{app_id}/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE","HEAD","OPTIONS"])`. Check app status via `manager.get_status(app_id)` — if not 'running', return 503 with `{"detail": f"App {app_id} is not running"}`. Call `proxy.forward(app_id, path, request)`. Catch `AppNotReachableError` → return 502 with `{"detail": f"App {app_id} not reachable"}`.
   - `POST /api/apps/{app_id}/token/renew` — validate the old token from `Authorization: Bearer {token}` header using `validate_app_token(token, secret, grace_seconds=300)`. If invalid even with grace → 401. Generate new token, store in manager's `_tokens`, return `{"token": new_token}`.
   - Both endpoints get `manager` and `proxy` from `request.app.state.app_manager` and `request.app.state.app_proxy`.

3. **Modify `backend/app/apps/manager.py`**:
   - Add `from app.apps.tokens import generate_app_token, get_secret` import.
   - Add `self._tokens: dict[str, str] = {}` to `__init__`.
   - Add `def get_token(self, app_id: str) -> str | None` accessor returning `self._tokens.get(app_id)`.
   - In `start()`: before building cmd list, generate token: `token = generate_app_token(app_id, {}, get_secret())`. Store: `self._tokens[app_id] = token`. Append to cmd: `"--app-token", token`.
   - In `install()`: after `_run_uv(["venv", ...])` and before installing requirements, add SDK install step: `await self._run_uv(["pip", "install", "/app/backend/sdk", "--python", str(venv_python)])`. Use the container-absolute path `/app/backend/sdk` since this runs inside Docker. Note: for local dev/tests, the path would be different — but the contract tests (T04) handle this.
   - In `stop()`: add `self._tokens.pop(app_id, None)` to clean up token.
   - In `_cleanup_runtime_state()`: add `self._tokens.pop(app_id, None)`.

4. **Modify `backend/app/main.py`**:
   - Add import: `from app.apps.router import app_proxy_router`
   - Add import: `from app.apps.proxy import AppProxy`
   - In lifespan, after creating `app_manager` and storing on `app.state.app_manager`: create `app_proxy = AppProxy(app_manager)` and store on `app.state.app_proxy = app_proxy`.
   - In lifespan shutdown: add `await app_proxy.close_all()` before `await app_manager.shutdown_all()`.
   - Add `app.include_router(app_proxy_router)` **before** `app.include_router(browser_router)` at line 547. This is critical — browser_router has `{iri:path}` catch-all that would consume `/app/` URLs.

5. **Create `backend/tests/test_app_proxy.py`** — unit tests (~15 tests):
   - **Proxy tests** (mock httpx transport): `forward()` sends correct method, path, headers, body to UDS. `forward()` injects `X-SemPKM-App-Token` header. Socket missing → `AppNotReachableError`.
   - **Router tests** (TestClient with mocked manager/proxy): `/app/test-app/some/path` calls proxy.forward. App not running → 503. App not reachable → 502. Token renewal with valid token → new token returned. Token renewal with expired-within-grace → new token. Token renewal with expired-beyond-grace → 401.
   - **Manager token tests**: `start()` generates token and appends to cmd. `get_token()` returns stored token. `stop()` clears token.

6. **Verify** the full test suite:
   - `cd backend && .venv/bin/pytest tests/test_app_proxy.py -v`
   - Also re-run `tests/test_app_manager.py` to verify manager changes don't break existing tests.

## Must-Haves

- [ ] `AppProxy.forward()` routes HTTP to UDS with token injection
- [ ] Socket-not-found returns 502, app-not-running returns 503
- [ ] Token renewal endpoint with grace period
- [ ] `AppManager.start()` generates JWT and passes `--app-token` to subprocess
- [ ] `AppManager.install()` installs SDK into app venv
- [ ] `app_proxy_router` included before `browser_router` in main.py
- [ ] All tests pass (new + existing manager tests)

## Verification

- `cd backend && .venv/bin/pytest tests/test_app_proxy.py -v` — all proxy/router tests pass
- `cd backend && .venv/bin/pytest tests/test_app_manager.py -v` — existing manager tests still pass

## Observability Impact

- Signals added/changed: proxy logs WARNING on socket missing/connection refused with app_id context. 502/503 responses carry structured JSON error detail.
- How a future agent inspects this: `AppManager.get_token(app_id)` returns current JWT for an app. `AppProxy._clients` dict shows which apps have active httpx connections.
- Failure state exposed: HTTP 502 means socket/connection failure (app crashed), 503 means app not in running state (stopped or installing).

## Inputs

- `backend/app/apps/tokens.py` (T01) — `generate_app_token()`, `validate_app_token()`, `get_secret()`
- `backend/app/apps/manager.py` (S01) — `AppManager` with `start()`, `install()`, `stop()`, `_processes`, `_cleanup_runtime_state()`
- `backend/app/apps/registry.py` (S01) — `AppRegistry` with `get_manifest()`
- `backend/app/main.py` (S01) — lifespan with `app_manager`, router include order

## Expected Output

- `backend/app/apps/proxy.py` — AppProxy with UDS forwarding and connection pooling
- `backend/app/apps/router.py` — proxy catch-all route + token renewal endpoint
- `backend/app/apps/manager.py` — modified with token generation, SDK install, token store
- `backend/app/main.py` — modified with proxy router include and AppProxy lifecycle
- `backend/tests/test_app_proxy.py` — ~15 unit tests for proxy, router, and manager token handling
