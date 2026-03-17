# S02: App SDK & IPC Proxy — Research

**Date:** 2026-03-16
**Researcher:** GSD auto-mode

## Summary

S02 builds the developer-facing SDK package (`backend/sdk/sempkm_app_sdk/`) and the platform-side IPC proxy that connects the platform to app subprocesses. This is the second high-risk slice — it introduces a new Python package, a uvicorn-on-UDS runner, JWT token auth, and an httpx UDS proxy. All of these are new to the codebase but use well-understood libraries already pinned in `pyproject.toml` (httpx~=0.28.1, PyJWT~=2.10, uvicorn~=0.41.0).

S01 proved subprocess lifecycle works: install, start, health check, crash recovery. S02 replaces the `test_health_server.py` stub with a real SDK runner and adds the proxy layer so the platform can route HTTP requests to app subprocesses and apps can call back to the platform API.

The SDK clients (`CommandClient`, `GraphClient`, `StateClient`, `HttpClient`, `SettingsClient`) are stubs in this slice — they make HTTP calls to the platform API without permission enforcement (S05 adds enforcement). The key deliverable is proving the round-trip: platform → proxy → UDS → app → SDK client → platform API → response back.

## Recommendation

**4 tasks, bottom-up, proving the round-trip last.**

1. **JWT tokens** — Platform-side generation + validation. Independent of everything else, unblocks both proxy and SDK.
2. **SDK package** — `App` class, `AppContext`, client stubs, runner. The bulk of new code. Can be unit-tested without a running platform.
3. **Platform proxy + router** — `AppProxy` httpx UDS forwarding, API routes, manager integration (pass `--app-token` on start, install SDK into venv).
4. **Integration test** — Real subprocess running SDK runner, proxied request, callback to platform API mock. Proves the full chain.

This ordering works because: tokens are a pure utility (no deps); the SDK can be tested in isolation; the proxy needs to know the token format; the integration test ties everything together.

## Implementation Landscape

### Key Files — Existing (to modify)

| File | What Changes |
|------|-------------|
| `backend/app/apps/manager.py` | (1) Pass `--app-token {jwt}` to subprocess start command. (2) Install SDK package into app venv during `install()`: `uv pip install /app/backend/sdk --python {venv}/bin/python`. (3) Store token in memory dict `_tokens[app_id]` for proxy use. (4) Generate token via `tokens.generate_app_token()` before start. |
| `backend/app/main.py` | Include `app_proxy_router` — register BEFORE `browser_router` since browser has catch-all `{iri:path}`. |
| `backend/tests/fixtures/test_health_server.py` | Not modified — S02 adds a separate SDK-based test fixture alongside it. |

### Key Files — New (to create)

| File | Purpose |
|------|---------|
| **`backend/app/apps/tokens.py`** | `generate_app_token(app_id, permissions, secret) -> str` and `validate_app_token(token, secret) -> dict|None`. Uses PyJWT HS256. 1-hour expiry. Claims: `sub`, `permissions`, `iat`, `exp`. |
| **`backend/app/apps/proxy.py`** | `AppProxy` class: creates per-app `httpx.AsyncClient` with `AsyncHTTPTransport(uds=socket_path)`. Method `forward(app_id, request) -> Response` copies method, path, headers, body, streams response back. Injects `X-SemPKM-App-Token` header. |
| **`backend/app/apps/router.py`** | FastAPI router with: `ANY /app/{app_id}/{path:path}` → proxy to subprocess. `POST /api/apps/{app_id}/token/renew` → generate new token, return to SDK. |
| **`backend/sdk/pyproject.toml`** | SDK package metadata. Dependencies: `fastapi`, `uvicorn`, `httpx`, `PyJWT`, `jinja2`. Minimal — apps bring their own deps. |
| **`backend/sdk/sempkm_app_sdk/__init__.py`** | Exports `App`, `AppContext`. |
| **`backend/sdk/sempkm_app_sdk/app.py`** | `App` class with decorators: `@app.on_install`, `@app.on_startup`, `@app.on_shutdown`, `@app.on_uninstall`, `@app.task("id")`, `@app.route("/_fragments/...")`. Stores handlers in dicts. Builds a FastAPI app with registered routes + `/_health` + `/_lifecycle/*` + `/_tasks/*`. |
| **`backend/sdk/sempkm_app_sdk/context.py`** | `AppContext` dataclass: `app_id`, `commands` (CommandClient), `graph` (GraphClient), `state` (StateClient), `http` (HttpClient), `settings` (SettingsClient), `render_template()` method, `logger` property. |
| **`backend/sdk/sempkm_app_sdk/runner.py`** | `__main__`-compatible runner. Parses args: `--app-dir`, `--socket`, `--platform-url`, `--app-token`. Imports app entrypoint from manifest. Builds FastAPI app. Installs SIGTERM handler calling `on_shutdown`. Runs `uvicorn.run(app, uds=socket)`. |
| **`backend/sdk/sempkm_app_sdk/clients/__init__.py`** | Package init. |
| **`backend/sdk/sempkm_app_sdk/clients/commands.py`** | `CommandClient` — wraps `httpx.AsyncClient` calling `POST {platform_url}/api/commands` with JWT in header. No permission enforcement yet (S05). |
| **`backend/sdk/sempkm_app_sdk/clients/graph.py`** | `GraphClient` — wraps `POST {platform_url}/api/sparql` with JWT. Returns parsed results. |
| **`backend/sdk/sempkm_app_sdk/clients/state.py`** | `StateClient` — `get(key)`, `set(key, val)` via SPARQL on `urn:sempkm:app:{appId}:state`. Uses platform SPARQL endpoint. |
| **`backend/sdk/sempkm_app_sdk/clients/http.py`** | `HttpClient` — thin wrapper around `httpx.AsyncClient`. No domain enforcement yet (S05). |
| **`backend/sdk/sempkm_app_sdk/clients/settings.py`** | `SettingsClient` — `get(key)`, `set(key, val)`. Stub that stores in state graph. |
| **`backend/tests/test_app_tokens.py`** | Unit tests for JWT generation/validation: valid token, expired token, tampered token, claim structure. |
| **`backend/tests/test_app_proxy.py`** | Unit tests for `AppProxy.forward()` with mocked httpx transport. |
| **`backend/tests/test_sdk_app.py`** | Unit tests for `App` class: decorator registration, FastAPI app building, route wiring. |
| **`backend/tests/test_sdk_integration.py`** | Contract-level test: real subprocess running SDK runner on UDS, proxy a request, get response. Replaces the `test_health_server.py` fixture with real SDK for this test. |

### Build Order

**Task 1: JWT Tokens** (`backend/app/apps/tokens.py` + tests)
- Pure utility, zero deps on other S02 work
- `generate_app_token(app_id: str, permissions: dict, secret: str, ttl_seconds: int = 3600) -> str`
- `validate_app_token(token: str, secret: str) -> dict | None` — returns decoded claims or None
- Uses `jwt.encode()` / `jwt.decode()` with HS256
- Claims: `{"sub": f"app:{app_id}", "permissions": {...}, "iat": now, "exp": now+ttl}`
- Secret key: reuse `_get_secret_key()` from `app.auth.tokens` (same secret, different salt/claims)
- ~10 unit tests: valid token, expired, tampered, missing claims, wrong algorithm

**Task 2: SDK Package** (`backend/sdk/` tree)
- `App` class with decorator registry pattern:
  - `_lifecycle_handlers: dict[str, Callable]` — `on_install`, `on_startup`, `on_shutdown`, `on_uninstall`
  - `_task_handlers: dict[str, Callable]` — keyed by task ID
  - `_route_handlers: list[tuple[str, str, Callable]]` — (method, path, handler)
  - `build_asgi_app() -> FastAPI` — constructs the internal FastAPI app with all registered routes + system endpoints
- System endpoints wired by `build_asgi_app()`:
  - `GET /_health` → `{"status": "ok"}`
  - `POST /_lifecycle/{hook}` → dispatches to lifecycle handler
  - `POST /_tasks/{task_id}` → dispatches to task handler (validates `X-SemPKM-Task-Run` header)
- `AppContext` constructed from CLI args:
  - `platform_url` and `app_token` drive the httpx base client for all SDK clients
  - All clients share the same `httpx.AsyncClient` with `base_url=platform_url` and `Authorization: Bearer {token}` header
  - `render_template()` uses Jinja2 with `FileSystemLoader` on `{app_dir}/frontend/templates/`
- Runner (`runner.py`):
  - `argparse` for `--app-dir`, `--socket`, `--platform-url`, `--app-token`
  - Reads manifest from `{app_dir}/manifest.yaml` to get `backend.entrypoint`
  - Imports entrypoint module, resolves the `App` instance
  - Calls `app.build_asgi_app()` to get the ASGI app
  - `uvicorn.run(asgi_app, uds=socket, log_level="info")`
  - SIGTERM handler: run `on_shutdown` hook, then exit
- Client stubs (all use shared httpx client, all have no permission enforcement):
  - `CommandClient.execute(command_type, params)` → `POST /api/commands`
  - `GraphClient.query(sparql)` → `POST /api/sparql`
  - `StateClient.get(key)` / `.set(key, value)` → SPARQL on state graph via platform
  - `HttpClient.get(url)` / `.post(url, ...)` → direct httpx (no domain checking)
  - `SettingsClient.get(key)` / `.set(key, value)` → store in state graph
- ~20 unit tests: decorator registration, ASGI app building, route dispatch, context creation, client HTTP call shaping

**Task 3: Platform Proxy + Router + Manager Updates**
- `AppProxy`:
  - `__init__(manager: AppManager)` — gets socket paths from manager/registry
  - `forward(app_id: str, request: Request) -> Response`:
    1. Look up socket path from `manager._processes` or DB
    2. Create `httpx.AsyncClient(transport=AsyncHTTPTransport(uds=socket_path))`
    3. Forward method, path suffix, headers, body
    4. Inject `X-SemPKM-App-Token: {token}` header
    5. Stream response back as `StreamingResponse`
  - Connection pooling: keep a dict of `httpx.AsyncClient` per app_id, reuse across requests
- Router (`backend/app/apps/router.py`):
  - `ANY /app/{app_id}/{path:path}` → `proxy.forward(app_id, request)`
  - `POST /api/apps/{app_id}/token/renew` → generate new token, return JWT to SDK
  - Both require the app to be in `running` status
- Manager updates:
  - `start()` generates JWT via `tokens.generate_app_token()`, passes as `--app-token` CLI arg
  - `install()` adds `uv pip install {sdk_path} --python {venv}/bin/python` step
  - Store `_tokens[app_id]` for proxy access
  - Add `get_token(app_id) -> str | None` accessor for proxy
- `main.py`: import and include `app_proxy_router` before `browser_router`
- ~15 unit tests: proxy forward with mocked transport, router wiring, token renewal

**Task 4: Integration Proof**
- Create a minimal test app at `backend/tests/fixtures/test_sdk_app/`:
  - `manifest.yaml` with minimal valid config
  - `app.py` with `App("test-sdk")`, one route returning HTML fragment, one task handler
  - `requirements.txt` (empty — SDK injected by platform)
- Test: start subprocess with real SDK runner, proxy a request via httpx UDS, verify response
- Test: verify `/_health` returns 200
- Test: verify `/_lifecycle/startup` calls the hook
- Test: verify `/_tasks/test-task` dispatches to handler
- ~8 contract tests

### Verification Approach

**Unit tests (no Docker, <5s each):**
```bash
cd backend && .venv/bin/pytest tests/test_app_tokens.py -v
cd backend && .venv/bin/pytest tests/test_app_proxy.py -v
cd backend && .venv/bin/pytest tests/test_sdk_app.py -v
```

**Integration tests (real subprocess, ~20s):**
```bash
cd backend && .venv/bin/pytest tests/test_sdk_integration.py -v
```

**Observable behaviors:**
- SDK runner starts on UDS, `/_health` returns `{"status": "ok"}`
- Proxy forwards `GET /app/test-sdk/_fragments/main` → gets HTML fragment back
- JWT token validates on both platform and SDK side
- Token renewal endpoint returns a fresh JWT
- App entrypoint imported from `manifest.backend.entrypoint`

## Constraints

- **SDK installed via `uv pip install /app/backend/sdk`** — path must be a valid pip-installable package (needs `pyproject.toml` with `[build-system]`). `uv` handles editable installs differently than pip — use direct install, not `-e`.
- **SDK dependencies must not conflict with app deps** — keep SDK deps minimal: `fastapi`, `uvicorn`, `httpx`, `PyJWT`, `jinja2`. All are common and unlikely to conflict.
- **Runner must accept the exact CLI args from `AppManager.start()`** — current command: `{venv}/bin/python -m sempkm_app_sdk.runner --app-dir {dir} --socket {sock} --platform-url {url}`. S02 adds `--app-token {jwt}`.
- **`entrypoint` format is `module:attribute`** — e.g. `backend.app:app` or `app:my_app`. The runner must `importlib` the module and `getattr` the attribute. The app directory must be on `sys.path`.
- **No token persistence needed** — tokens are ephemeral, generated at start time, held in manager's `_tokens` dict. If platform restarts, `auto_start()` regenerates tokens.
- **Proxy must handle both GET and POST** (and any other HTTP method) — use FastAPI's `api_route` with all methods, or a catch-all approach.
- **httpx UDS transport requires the socket file to exist** — proxy must handle the case where the app crashed and the socket is gone (return 502 or 503).
- **Secret key for JWT** — reuse the platform's secret key from `app.auth.tokens._get_secret_key()`. No separate key management.

## Common Pitfalls

- **`importlib.import_module` requires the module to be on `sys.path`** — the runner must insert `app_dir` into `sys.path[0]` before importing the entrypoint. If the entrypoint is `app:my_app`, the runner does `sys.path.insert(0, app_dir); mod = importlib.import_module("app"); obj = getattr(mod, "my_app")`.
- **uvicorn.run() blocks** — the runner must be the last thing called. All setup (signal handlers, context creation) happens before `uvicorn.run()`. Use `uvicorn.Config` + `uvicorn.Server` if we need async setup before serving.
- **httpx proxy must not buffer large responses** — use `httpx.AsyncClient.send()` with `stream=True` and return `StreamingResponse` to avoid memory issues with large fragments.
- **JWT `exp` claim is seconds since epoch, not a datetime** — PyJWT handles this if you pass `datetime` to `exp`, but verify the convention.
- **FastAPI catch-all `{path:path}` for proxy** — must be registered at the right level. If registered under `/app/{app_id}/{path:path}`, it must not collide with other `/app/` routes (there are none currently, but future slices add admin routes at `/admin/apps/`).
- **SDK package `pyproject.toml` needs `[build-system]`** — without it, `uv pip install` will fail. Use `hatchling` as the build backend (same as the platform's `pyproject.toml`).
- **Token renewal race** — if the SDK makes a request with an expired token, the platform returns 401, the SDK calls `/api/apps/{app_id}/token/renew`, gets a new token, retries. The renewal endpoint must itself be authenticated — use the old (expired) token with a grace period, or use a separate renewal mechanism. Simplest: platform accepts tokens up to 5 minutes past expiry for renewal only.

## Open Risks

- **SDK test isolation** — contract tests need a real subprocess running the SDK runner. This requires either (a) installing the SDK package into a temp venv (slow, ~10s), or (b) running the test fixture with `sys.path` manipulation (fast but fragile). Best approach: the contract tests use the platform's `.venv` with the SDK installed there during test setup, running the fixture via `python -m sempkm_app_sdk.runner` directly.
- **Entrypoint import failures at runtime** — if an app's entrypoint has an import error, the runner will crash immediately. The SDK runner should catch `ImportError` and exit with a clear error message (which the crash watcher will capture in the log buffer).
- **httpx client lifecycle in proxy** — creating a new `httpx.AsyncClient` per request is wasteful; keeping one per app is efficient but needs cleanup when apps stop. The `AppProxy` should track clients and close them on app stop.

## Sources

- `backend/app/apps/manager.py` — subprocess start command template, health check pattern, UDS transport usage
- `backend/app/apps/registry.py` — manifest lookup interface
- `backend/app/apps/manifest.py` — `AppBackend.entrypoint` field, task/route schemas
- `backend/app/auth/tokens.py` — `_get_secret_key()` pattern for secret resolution
- `backend/app/main.py` — router include order, lifespan wiring, `app.state.app_manager`
- `backend/app/commands/router.py` — `POST /api/commands` endpoint (SDK CommandClient target)
- `backend/app/sparql/router.py` — `POST /api/sparql` endpoint (SDK GraphClient target)
- `.gsd/design/APP-PLATFORM-DESIGN.md` §5 (process architecture), §6 (SDK), §9 (JWT), §10 (lifecycle)
- `backend/pyproject.toml` — httpx~=0.28.1, PyJWT~=2.10, uvicorn~=0.41.0 already pinned
- `backend/tests/fixtures/test_health_server.py` — existing UDS test fixture pattern
