# S02: App SDK & IPC Proxy

**Goal:** A test app built with the SDK starts on a unix socket, the platform proxies HTTP requests to it via httpx UDS transport with JWT auth, and the app can call back to the platform API through scoped SDK clients.

**Demo:** `GET /app/test-sdk/_fragments/main` returns an HTML fragment served by a real SDK-based app subprocess, proxied through the platform, with valid JWT authentication on both legs.

## Must-Haves

- `sempkm-app-sdk` package at `backend/sdk/` — installable via `uv pip install`
- `App` class with `@app.route()`, `@app.task()`, lifecycle decorators (`on_install`, `on_startup`, `on_shutdown`, `on_uninstall`)
- `AppContext` with `CommandClient`, `GraphClient`, `StateClient`, `HttpClient`, `SettingsClient` stubs (no permission enforcement — S05)
- SDK runner (`sempkm_app_sdk.runner`) starts uvicorn on UDS with `/_health`, `/_lifecycle/*`, `/_tasks/*` system endpoints
- Runner accepts `--app-dir`, `--socket`, `--platform-url`, `--app-token` CLI args
- JWT token generation/validation using PyJWT HS256 with platform secret key
- `AppProxy` routing HTTP to app subprocess UDS via httpx `AsyncHTTPTransport(uds=...)`
- Platform router at `/app/{app_id}/{path:path}` forwarding all HTTP methods through proxy
- Token renewal endpoint at `POST /api/apps/{app_id}/token/renew`
- `AppManager.start()` generates JWT and passes `--app-token` to subprocess
- `AppManager.install()` installs SDK package into app venv

## Proof Level

- This slice proves: contract + integration
- Real runtime required: yes (subprocess on UDS)
- Human/UAT required: no

## Verification

- `cd backend && .venv/bin/pytest tests/test_app_tokens.py -v` — JWT generation/validation unit tests pass
- `cd backend && .venv/bin/pytest tests/test_sdk_app.py -v` — SDK App class decorator registration and ASGI app building tests pass
- `cd backend && .venv/bin/pytest tests/test_app_proxy.py -v` — proxy forwarding and router wiring tests pass
- `cd backend && .venv/bin/pytest tests/test_sdk_integration.py -v` — real subprocess on UDS serves `/_health`, proxied request returns response, lifecycle hooks dispatch

## Observability / Diagnostics

- Runtime signals: JWT claims logged at DEBUG on generation; proxy errors (socket missing, connection refused) logged at WARNING with app_id context
- Inspection surfaces: `AppManager.get_token(app_id)` returns current JWT; `AppProxy` connection pool keyed by app_id
- Failure visibility: proxy returns HTTP 502 with `{"detail": "App {app_id} not reachable"}` when socket missing or connection fails; 503 when app not in 'running' status
- Redaction constraints: JWT tokens logged only at DEBUG level, never in error responses

## Integration Closure

- Upstream surfaces consumed: `AppManager` (socket path, process lifecycle), `AppRegistry` (manifest lookup), `AppManifestSchema` (entrypoint field), `app.auth.tokens._get_secret_key()` (secret key resolution)
- New wiring introduced in this slice: `app_proxy_router` included in `main.py` before `browser_router`; `AppManager.start()` gains `--app-token` arg and SDK install step; `AppProxy` stored on `app.state`
- What remains before the milestone is truly usable end-to-end: admin portal (S03), frontend fragment loading (S04), scheduler + permissions (S05), workspace contributions (S06)

## Tasks

- [ ] **T01: JWT token generation and validation** `est:30m`
  - Why: JWT tokens are the authentication mechanism between platform and app subprocesses. Independent of all other S02 work — unblocks both proxy (needs to inject token) and SDK (needs to validate token).
  - Files: `backend/app/apps/tokens.py`, `backend/tests/test_app_tokens.py`
  - Do: Create `generate_app_token(app_id, permissions, secret, ttl_seconds=3600)` returning HS256 JWT with claims `{sub: "app:{app_id}", permissions: {...}, iat, exp}`. Create `validate_app_token(token, secret)` returning decoded claims dict or None. Reuse secret resolution from `app.auth.tokens._get_secret_key()`. Add grace period support — `validate_app_token` accepts `grace_seconds=300` for token renewal (accepts tokens up to 5min past expiry for renewal endpoint only).
  - Verify: `cd backend && .venv/bin/pytest tests/test_app_tokens.py -v`
  - Done when: Valid token round-trips, expired token returns None, expired-within-grace returns claims, tampered token returns None, wrong algorithm returns None, claims structure correct.

- [ ] **T02: SDK package — App class, context, clients, runner** `est:2h`
  - Why: The developer-facing SDK package is the core deliverable — apps import `sempkm_app_sdk` and use `App` + `AppContext` to build their backend. This is the bulk of new code in S02 but is self-contained (no platform modifications needed).
  - Files: `backend/sdk/pyproject.toml`, `backend/sdk/sempkm_app_sdk/__init__.py`, `backend/sdk/sempkm_app_sdk/app.py`, `backend/sdk/sempkm_app_sdk/context.py`, `backend/sdk/sempkm_app_sdk/runner.py`, `backend/sdk/sempkm_app_sdk/clients/__init__.py`, `backend/sdk/sempkm_app_sdk/clients/commands.py`, `backend/sdk/sempkm_app_sdk/clients/graph.py`, `backend/sdk/sempkm_app_sdk/clients/state.py`, `backend/sdk/sempkm_app_sdk/clients/http.py`, `backend/sdk/sempkm_app_sdk/clients/settings.py`, `backend/tests/test_sdk_app.py`
  - Do: (1) Create `pyproject.toml` with hatchling build backend, deps: `fastapi`, `uvicorn[standard]`, `httpx`, `PyJWT`, `jinja2`. (2) `App` class with decorator registry: `@app.route(path, methods)`, `@app.task(task_id)`, `@app.on_startup` / `on_shutdown` / `on_install` / `on_uninstall`. `build_asgi_app()` returns FastAPI with registered routes + system endpoints (`/_health`, `POST /_lifecycle/{hook}`, `POST /_tasks/{task_id}`). System endpoints validate `X-SemPKM-App-Token` header via `validate_app_token()`. (3) `AppContext` dataclass with all 5 client stubs sharing one httpx.AsyncClient with `base_url=platform_url` and `Authorization: Bearer {token}` header. `render_template(name, **ctx)` via Jinja2 FileSystemLoader on `{app_dir}/frontend/templates/`. (4) Runner: argparse for `--app-dir`, `--socket`, `--platform-url`, `--app-token`. Read manifest, import entrypoint via `importlib` (`module:attribute` format), inject `sys.path[0] = app_dir`, construct `AppContext`, call `app.build_asgi_app(ctx)`, run `uvicorn.run(asgi, uds=socket)`. SIGTERM handler calls `on_shutdown`. (5) Client stubs: `CommandClient.execute()` → `POST /api/commands`, `GraphClient.query()` → `POST /api/sparql`, `StateClient.get/set()` via SPARQL, `HttpClient.get/post()` as thin httpx wrapper, `SettingsClient.get/set()` via state graph. No permission enforcement (S05). (6) Unit tests: decorator registration, ASGI app building, route dispatch, health endpoint, lifecycle dispatch, task dispatch, context creation, client HTTP call shaping.
  - Verify: `cd backend && .venv/bin/pytest tests/test_sdk_app.py -v`
  - Done when: `App` decorators register handlers, `build_asgi_app()` produces working FastAPI app with all system endpoints, runner parses args and imports entrypoint, clients shape correct HTTP requests.

- [ ] **T03: Platform proxy, router, and manager updates** `est:1h`
  - Why: Connects the platform to SDK-based app subprocesses. The proxy forwards HTTP to UDS, the router exposes `/app/{app_id}/*`, and manager updates generate/pass JWT tokens and install the SDK into app venvs.
  - Files: `backend/app/apps/proxy.py`, `backend/app/apps/router.py`, `backend/app/apps/manager.py`, `backend/app/main.py`, `backend/tests/test_app_proxy.py`
  - Do: (1) `AppProxy` class: `__init__(manager)` — builds dict of `httpx.AsyncClient` per app_id with UDS transport. `forward(app_id, request) -> Response`: look up socket path, get/create httpx client with `AsyncHTTPTransport(uds=socket)`, forward method/path/headers/body with `stream=True`, inject `X-SemPKM-App-Token` header, return `StreamingResponse`. Handle socket-not-found as HTTP 502. `close_client(app_id)` for cleanup on app stop. (2) Router: `ANY /app/{app_id}/{path:path}` → proxy forward (requires app in 'running' status, returns 503 otherwise). `POST /api/apps/{app_id}/token/renew` → validate old token (with grace period), generate new token, update manager's token store, return new JWT. (3) Manager updates: add `_tokens: dict[str, str] = {}` dict, `get_token(app_id) -> str | None` accessor. In `start()`: generate JWT via `tokens.generate_app_token()`, store in `_tokens[app_id]`, append `--app-token {jwt}` to subprocess cmd. In `install()`: add `uv pip install /app/backend/sdk --python {venv_python}` step after venv creation. In `stop()`: clear token. (4) `main.py`: import and include `app_proxy_router` before `browser_router` (line 547). Store `AppProxy` on `app.state.app_proxy`. (5) Unit tests: proxy forward with mocked httpx, socket missing → 502, app not running → 503, token renewal with valid/expired/grace tokens, router wiring.
  - Verify: `cd backend && .venv/bin/pytest tests/test_app_proxy.py -v`
  - Done when: Proxy forwards requests through UDS transport, returns 502/503 on failures, token renewal works with grace period, manager passes `--app-token` to subprocess, SDK installed into venv during install.

- [ ] **T04: Integration proof — real subprocess round-trip** `est:45m`
  - Why: Proves the full S02 contract: platform → proxy → UDS → SDK app → response. Without this, individual unit tests don't prove the pieces actually connect. This is the slice's demo verification.
  - Files: `backend/tests/fixtures/test_sdk_app/manifest.yaml`, `backend/tests/fixtures/test_sdk_app/app.py`, `backend/tests/fixtures/test_sdk_app/requirements.txt`, `backend/tests/test_sdk_integration.py`
  - Do: (1) Create minimal SDK test app fixture at `backend/tests/fixtures/test_sdk_app/`: `manifest.yaml` (valid manifest with `backend.entrypoint: "app:test_app"`), `app.py` (imports `sempkm_app_sdk.App`, registers one route `/_fragments/main` returning HTML, one task handler, `on_startup` hook), `requirements.txt` (empty). (2) Integration test: install SDK into platform's `.venv` (or use `sys.path` manipulation), start subprocess with `python -m sempkm_app_sdk.runner --app-dir ... --socket ... --platform-url http://localhost:8000 --app-token {jwt}`, wait for socket file to appear. Test: `/_health` returns 200 with `{"status":"ok"}`. Test: `/_fragments/main` returns HTML. Test: `/_lifecycle/startup` calls hook (returns 200). Test: `/_tasks/test-task` dispatches to handler. Test: token validation on system endpoints (request without token → 401/403). Clean up subprocess on teardown.
  - Verify: `cd backend && .venv/bin/pytest tests/test_sdk_integration.py -v`
  - Done when: Real SDK runner starts on UDS, serves health and fragment responses, lifecycle hooks dispatch correctly, task endpoints dispatch, token validation works. Full S02 round-trip proven.

## Files Likely Touched

- `backend/app/apps/tokens.py` — new: JWT generation/validation
- `backend/app/apps/proxy.py` — new: httpx UDS proxy
- `backend/app/apps/router.py` — new: `/app/{app_id}/*` proxy router + token renewal
- `backend/app/apps/manager.py` — modified: JWT generation on start, SDK install on install, token store
- `backend/app/main.py` — modified: include app_proxy_router, store AppProxy on app.state
- `backend/sdk/pyproject.toml` — new: SDK package metadata
- `backend/sdk/sempkm_app_sdk/__init__.py` — new: package exports
- `backend/sdk/sempkm_app_sdk/app.py` — new: App class with decorators
- `backend/sdk/sempkm_app_sdk/context.py` — new: AppContext + client wiring
- `backend/sdk/sempkm_app_sdk/runner.py` — new: CLI runner with uvicorn on UDS
- `backend/sdk/sempkm_app_sdk/clients/__init__.py` — new: clients package
- `backend/sdk/sempkm_app_sdk/clients/commands.py` — new: CommandClient stub
- `backend/sdk/sempkm_app_sdk/clients/graph.py` — new: GraphClient stub
- `backend/sdk/sempkm_app_sdk/clients/state.py` — new: StateClient stub
- `backend/sdk/sempkm_app_sdk/clients/http.py` — new: HttpClient stub
- `backend/sdk/sempkm_app_sdk/clients/settings.py` — new: SettingsClient stub
- `backend/tests/test_app_tokens.py` — new: JWT unit tests
- `backend/tests/test_sdk_app.py` — new: SDK App class unit tests
- `backend/tests/test_app_proxy.py` — new: proxy + router unit tests
- `backend/tests/test_sdk_integration.py` — new: integration contract tests
- `backend/tests/fixtures/test_sdk_app/` — new: SDK-based test app fixture
