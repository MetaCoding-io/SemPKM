---
id: T02
parent: S02
milestone: M009
provides:
  - sempkm-app-sdk Python package with App class, AppContext, 5 client stubs, and CLI runner
  - Decorator-based handler registration for routes, tasks, and lifecycle hooks
  - FastAPI ASGI app builder with system endpoints (health, lifecycle, tasks)
  - Shared-secret token validation on system endpoints
key_files:
  - backend/sdk/pyproject.toml
  - backend/sdk/sempkm_app_sdk/app.py
  - backend/sdk/sempkm_app_sdk/context.py
  - backend/sdk/sempkm_app_sdk/runner.py
  - backend/sdk/sempkm_app_sdk/clients/
  - backend/tests/test_sdk_app.py
key_decisions:
  - Token validation uses shared-secret string comparison (not JWT decode) — simpler model where platform and app share the same token string
  - Lifecycle decorators implemented as properties returning decorator functions (not direct decorator methods) for clean @app.on_startup syntax
  - AppContext uses dataclass with lazy-init properties (not __init__-constructed clients) to avoid creating HTTP clients until needed
patterns_established:
  - SDK decorator pattern: @app.route(path, methods), @app.task(task_id), @app.on_{lifecycle} for handler registration
  - System endpoint pattern: /_health (no auth), /_lifecycle/{hook} (auth), /_tasks/{task_id} (auth)
  - Client stub pattern: thin async wrappers around httpx.AsyncClient with platform base_url
  - State graph IRI pattern: urn:sempkm:app:{app_id}:state for app-scoped key-value storage
observability_surfaces:
  - /_health endpoint returns {"status": "ok"} — platform uses for liveness
  - System endpoints return 403 {"detail": "Invalid or missing app token"} on auth failure
  - Unregistered hooks/tasks return 404 {"detail": "No handler for ..."}
  - Runner exits code 1 with logged error on manifest/import failures
  - DEBUG-level logs for lifecycle/task dispatch, token validation, client creation
duration: 25m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: SDK package — App class, context, clients, runner

**Built sempkm-app-sdk package with App decorator registry, AppContext client wiring, 5 client stubs, CLI runner, and 45 passing unit tests**

## What Happened

Created the `sempkm-app-sdk` Python package at `backend/sdk/` with hatchling build backend. The package provides:

1. **`App` class** (`app.py`): Decorator-based handler registration with `@app.route()`, `@app.task()`, and lifecycle decorators (`@app.on_startup`, etc.). `build_asgi_app(ctx)` produces a FastAPI instance with `/_health` (no auth), `/_lifecycle/{hook}` (auth required), `/_tasks/{task_id}` (auth required), plus user-registered routes.

2. **`AppContext`** (`context.py`): Dataclass with lazy-init properties for 5 client stubs sharing one platform httpx.AsyncClient (with Bearer auth header). Includes `render_template()` via Jinja2 FileSystemLoader. `close()` method for cleanup.

3. **5 Client Stubs** (`clients/`): CommandClient (POST /api/commands), GraphClient (POST /api/sparql), StateClient (SPARQL-backed key-value via named graph), HttpClient (external HTTP, separate client), SettingsClient (delegates to StateClient with `settings:` prefix).

4. **CLI Runner** (`runner.py`): argparse for `--app-dir`, `--socket`, `--platform-url`, `--app-token`. Reads manifest.yaml, imports entrypoint via `module:attribute` format, constructs AppContext, builds ASGI app, runs uvicorn on UDS. SIGTERM handler calls shutdown hook.

Token validation uses shared-secret string comparison — the platform passes the token at startup, and the SDK validates incoming requests by comparing the `X-SemPKM-App-Token` header to the stored token.

## Verification

- `cd backend && .venv/bin/pytest tests/test_sdk_app.py -v` — 45/45 tests pass
- `cd backend && uv pip install -e sdk/ && .venv/bin/python -c "from sempkm_app_sdk import App, AppContext; print('OK')"` — package imports cleanly
- `cd backend && .venv/bin/pytest tests/test_app_tokens.py -v` — 18/18 T01 tests still pass

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/pytest tests/test_sdk_app.py -v` | 0 | ✅ pass | 0.38s |
| 2 | `cd backend && .venv/bin/pytest tests/test_app_tokens.py -v` | 0 | ✅ pass | 0.04s |
| 3 | `uv pip install -e sdk/ && python -c "from sempkm_app_sdk import App, AppContext"` | 0 | ✅ pass | <1s |
| 4 | `cd backend && .venv/bin/pytest tests/test_app_proxy.py -v` | 4 | ⬜ skipped (T03) | — |
| 5 | `cd backend && .venv/bin/pytest tests/test_sdk_integration.py -v` | 4 | ⬜ skipped (T04) | — |

## Diagnostics

- **Health check:** `GET /_health` always returns `{"status": "ok"}` — no auth needed, used for liveness
- **Token auth failure:** System endpoints return 403 `{"detail": "Invalid or missing app token"}` — check WARNING-level logs for specifics (missing header vs mismatch)
- **Handler dispatch:** Unregistered lifecycle hooks or tasks return 404 with descriptive detail message
- **Runner errors:** Import failures exit code 1 with ERROR log including module name and ImportError message
- **Client wiring:** Access `ctx._platform_client` to verify shared client exists; `ctx.commands._client is ctx.graph._client` confirms sharing

## Deviations

- `render_template()` parameter renamed from `name` to `template_name` to avoid conflict with the `name` kwarg commonly passed as template context (and Python kwargs collision on the dataclass)
- User route handlers need explicit `request: Request` type annotation for FastAPI to avoid 422 validation errors — test handlers updated accordingly

## Known Issues

None.

## Files Created/Modified

- `backend/sdk/pyproject.toml` — package metadata with hatchling build system, loose dependency pins
- `backend/sdk/sempkm_app_sdk/__init__.py` — exports App, AppContext, __version__
- `backend/sdk/sempkm_app_sdk/__main__.py` — `python -m sempkm_app_sdk` entry point
- `backend/sdk/sempkm_app_sdk/app.py` — App class with decorator registry and ASGI app builder
- `backend/sdk/sempkm_app_sdk/context.py` — AppContext dataclass with lazy-init clients and template rendering
- `backend/sdk/sempkm_app_sdk/runner.py` — CLI runner with argparse, manifest reading, entrypoint import, uvicorn UDS
- `backend/sdk/sempkm_app_sdk/clients/__init__.py` — exports all 5 client classes
- `backend/sdk/sempkm_app_sdk/clients/commands.py` — CommandClient: POST /api/commands
- `backend/sdk/sempkm_app_sdk/clients/graph.py` — GraphClient: POST /api/sparql
- `backend/sdk/sempkm_app_sdk/clients/state.py` — StateClient: SPARQL-backed key-value in named graph
- `backend/sdk/sempkm_app_sdk/clients/http.py` — HttpClient: external HTTP via separate httpx client
- `backend/sdk/sempkm_app_sdk/clients/settings.py` — SettingsClient: delegates to StateClient with prefix
- `backend/tests/test_sdk_app.py` — 45 unit tests covering decorators, ASGI app, auth, context, clients, runner
- `.gsd/milestones/M009/slices/S02/tasks/T02-PLAN.md` — added Observability Impact section
