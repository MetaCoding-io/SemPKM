---
estimated_steps: 8
estimated_files: 12
---

# T02: SDK package — App class, context, clients, runner

**Slice:** S02 — App SDK & IPC Proxy
**Milestone:** M009

## Description

Build the `sempkm-app-sdk` Python package at `backend/sdk/`. This is the developer-facing SDK that apps import to build their backends. The package provides: `App` class with decorator-based handler registration, `AppContext` with scoped HTTP clients, 5 client stubs (commands, graph, state, http, settings), and a CLI runner that starts uvicorn on a unix domain socket. The runner accepts CLI args matching the command template in `AppManager.start()`.

Client stubs make HTTP calls to the platform API but have no permission enforcement — that's deferred to S05.

## Steps

1. **Create `backend/sdk/pyproject.toml`** — package metadata with hatchling build backend (same as platform's pyproject.toml). Name: `sempkm-app-sdk`. Version: `0.1.0`. Dependencies: `fastapi>=0.100`, `uvicorn[standard]>=0.20`, `httpx>=0.24`, `PyJWT>=2.0`, `jinja2>=3.1`. Use loose pins — the SDK shouldn't constrain app dependency choices tightly. Include `[build-system]` section with `requires = ["hatchling"]` and `build-backend = "hatchling.build"`.

2. **Create `backend/sdk/sempkm_app_sdk/app.py`** — the `App` class:
   - Constructor: `App(app_id: str)`. Stores `app_id` and handler registries.
   - Decorator registry dicts: `_lifecycle_handlers: dict[str, Callable]` (keys: `install`, `startup`, `shutdown`, `uninstall`), `_task_handlers: dict[str, Callable]` (keyed by task_id), `_routes: list[tuple[list[str], str, Callable]]` (methods, path, handler).
   - Decorators: `@app.on_install`, `@app.on_startup`, `@app.on_shutdown`, `@app.on_uninstall` — register lifecycle handlers. `@app.task(task_id)` — register task handler. `@app.route(path, methods=["GET"])` — register route handler.
   - `build_asgi_app(ctx: AppContext) -> FastAPI`: Create a FastAPI instance. Store `ctx` on `app.state.ctx`. Wire system endpoints:
     - `GET /_health` → `{"status": "ok"}`
     - `POST /_lifecycle/{hook}` → dispatch to lifecycle handler, validate `X-SemPKM-App-Token` header
     - `POST /_tasks/{task_id}` → dispatch to task handler, validate token
   - Wire user routes from `_routes` list — each gets `ctx` injected via `request.app.state.ctx`.
   - Token validation: read `X-SemPKM-App-Token` header, call `validate_app_token(token, ctx.app_token_secret)`. If invalid, return 403. Health endpoint is exempt (no token needed — platform uses it for liveness).

3. **Create `backend/sdk/sempkm_app_sdk/context.py`** — `AppContext` dataclass:
   - Fields: `app_id: str`, `app_dir: Path`, `platform_url: str`, `app_token: str`, `app_token_secret: str` (for validation on incoming requests — this is the same token value, SDK uses it to validate the platform is calling it with the right token).
   - Lazy-init properties for clients: `commands` → `CommandClient`, `graph` → `GraphClient`, `state` → `StateClient`, `http` → `HttpClient`, `settings` → `SettingsClient`.
   - All clients share one `httpx.AsyncClient` instance with `base_url=platform_url` and `headers={"Authorization": f"Bearer {app_token}"}`. Create this client lazily and store it.
   - `render_template(name: str, **context) -> str` — Jinja2 `Environment(loader=FileSystemLoader(app_dir / "frontend" / "templates"))`. Lazy-init the Jinja env.
   - `async close()` — close the shared httpx client.

   **Important for token validation:** The SDK validates incoming requests by checking the `X-SemPKM-App-Token` header matches the token it was started with (simple string comparison). This is a shared-secret model — the platform and app both know the token. The app doesn't need the signing secret for validation; it just compares the header value to its own `app_token`.

4. **Create client stubs** in `backend/sdk/sempkm_app_sdk/clients/`:
   - `__init__.py` — exports all 5 clients
   - `commands.py` — `CommandClient(client: httpx.AsyncClient)`. Method: `async execute(command_type: str, params: dict) -> dict` → `POST /api/commands` with JSON body `{"commands": [{"type": command_type, **params}]}`. Returns response JSON.
   - `graph.py` — `GraphClient(client: httpx.AsyncClient)`. Method: `async query(sparql: str) -> dict` → `POST /api/sparql` with form data `{"query": sparql}`. Returns response JSON.
   - `state.py` — `StateClient(client: httpx.AsyncClient, app_id: str)`. State graph IRI: `urn:sempkm:app:{app_id}:state`. Methods: `async get(key: str) -> str | None` (SPARQL SELECT), `async set(key: str, value: str) -> None` (SPARQL UPDATE via platform). Both use GraphClient internally.
   - `http.py` — `HttpClient(client: httpx.AsyncClient | None = None)`. Thin wrapper around a fresh `httpx.AsyncClient()` (NOT the platform client — this is for external HTTP calls). Methods: `async get(url, **kwargs)`, `async post(url, **kwargs)`. No domain enforcement yet (S05).
   - `settings.py` — `SettingsClient(state: StateClient)`. Delegates to StateClient using `settings:` key prefix. Methods: `async get(key: str) -> str | None`, `async set(key: str, value: str) -> None`.

5. **Create `backend/sdk/sempkm_app_sdk/runner.py`** — the `__main__`-compatible entry point:
   - `argparse` with: `--app-dir` (required), `--socket` (required), `--platform-url` (required), `--app-token` (required).
   - Read `manifest.yaml` from `app_dir` to get `backend.entrypoint` field (format: `module:attribute`).
   - Insert `app_dir` at `sys.path[0]` before import.
   - `importlib.import_module(module)` + `getattr(mod, attribute)` to get the `App` instance.
   - Construct `AppContext` from CLI args.
   - Call `app.build_asgi_app(ctx)` to get the ASGI app.
   - Install SIGTERM handler: set a shutdown event, run `on_shutdown` hook.
   - `uvicorn.run(asgi_app, uds=str(socket), log_level="info")`.
   - Wrap entrypoint import in try/except `ImportError` — log clear error and `sys.exit(1)`.
   - Make module runnable via `if __name__ == "__main__"` and also via `python -m sempkm_app_sdk.runner` (add `__main__.py` that imports and calls runner).

6. **Create `backend/sdk/sempkm_app_sdk/__init__.py`** — export `App`, `AppContext`.

7. **Create `backend/sdk/sempkm_app_sdk/__main__.py`** — `from sempkm_app_sdk.runner import main; main()` for `python -m sempkm_app_sdk` support.

8. **Create `backend/tests/test_sdk_app.py`** — unit tests (~20 tests):
   - `App` decorator registration: `@app.route` adds to `_routes`, `@app.task` adds to `_task_handlers`, lifecycle decorators add to `_lifecycle_handlers`.
   - `build_asgi_app()`: returns FastAPI instance, `/_health` returns 200 `{"status":"ok"}`, lifecycle endpoint dispatches to registered handler, task endpoint dispatches, unregistered lifecycle hook returns 404, unregistered task returns 404.
   - Token validation: requests to `/_lifecycle/*` and `/_tasks/*` without valid token header return 403. Health endpoint works without token.
   - Route registration: user routes callable via TestClient.
   - AppContext: `render_template` uses Jinja2 with correct loader path. Client properties return correct types.
   - Use `fastapi.testclient.TestClient` for synchronous ASGI testing (no real server needed).
   - For client HTTP call shaping: mock httpx client, verify CommandClient sends correct URL/body/headers, GraphClient sends correct form data.

## Must-Haves

- [ ] SDK package installable via `uv pip install backend/sdk/`
- [ ] `App` class registers route, task, and lifecycle handlers via decorators
- [ ] `build_asgi_app()` produces working FastAPI with `/_health`, `/_lifecycle/{hook}`, `/_tasks/{task_id}`
- [ ] Token validation on system endpoints (except `/_health`)
- [ ] `AppContext` provides all 5 client stubs with shared httpx client
- [ ] Runner parses correct CLI args and imports entrypoint via `module:attribute`
- [ ] All unit tests pass

## Verification

- `cd backend && .venv/bin/pytest tests/test_sdk_app.py -v` — all tests pass
- `cd backend && pip install -e sdk/ && python -c "from sempkm_app_sdk import App, AppContext; print('OK')"` — package imports cleanly

## Inputs

- `backend/app/apps/tokens.py` (T01) — `validate_app_token()` for token checking in system endpoints
- `backend/app/apps/manifest.py` — `AppManifestSchema` with `backend.entrypoint` field format: `module:attribute`
- PyJWT, httpx, FastAPI, uvicorn, Jinja2 all available in platform venv

## Expected Output

- `backend/sdk/pyproject.toml` — package metadata with hatchling build system
- `backend/sdk/sempkm_app_sdk/__init__.py` — exports App, AppContext
- `backend/sdk/sempkm_app_sdk/__main__.py` — `python -m` entry point
- `backend/sdk/sempkm_app_sdk/app.py` — App class with decorator registry and ASGI app builder
- `backend/sdk/sempkm_app_sdk/context.py` — AppContext with client wiring and template rendering
- `backend/sdk/sempkm_app_sdk/runner.py` — CLI runner with argparse, entrypoint import, uvicorn launch
- `backend/sdk/sempkm_app_sdk/clients/__init__.py` — package exports
- `backend/sdk/sempkm_app_sdk/clients/commands.py` — CommandClient stub
- `backend/sdk/sempkm_app_sdk/clients/graph.py` — GraphClient stub
- `backend/sdk/sempkm_app_sdk/clients/state.py` — StateClient stub
- `backend/sdk/sempkm_app_sdk/clients/http.py` — HttpClient stub
- `backend/sdk/sempkm_app_sdk/clients/settings.py` — SettingsClient stub
- `backend/tests/test_sdk_app.py` — ~20 unit tests
