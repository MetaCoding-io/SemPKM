---
id: T02
parent: S02
milestone: M009
provides:
  - sempkm-app-sdk package with App class, AppContext, 5 client stubs, CLI runner
key_files:
  - backend/sdk/pyproject.toml
  - backend/sdk/sempkm_app_sdk/app.py
  - backend/sdk/sempkm_app_sdk/context.py
  - backend/sdk/sempkm_app_sdk/runner.py
  - backend/sdk/sempkm_app_sdk/clients/commands.py
  - backend/sdk/sempkm_app_sdk/clients/graph.py
  - backend/sdk/sempkm_app_sdk/clients/state.py
  - backend/sdk/sempkm_app_sdk/clients/http.py
  - backend/sdk/sempkm_app_sdk/clients/settings.py
  - backend/tests/test_sdk_app.py
key_decisions:
  - Token validation uses shared-secret string comparison (not JWT verify) — simpler, matches platform→app auth model where both sides have the same token
  - render_template uses template_name (not name) as first param to avoid collision with common template variables like name
  - HttpClient uses a separate httpx.AsyncClient (not the platform client) for external HTTP calls
  - StateClient stores per-app state in a named graph (urn:sempkm:app:{app_id}:state) using SPARQL
patterns_established:
  - App decorator pattern: @app.route(), @app.task(), @app.on_install/startup/shutdown/uninstall register handlers into typed dicts, build_asgi_app() wires them into FastAPI
  - AppContext lazy-init pattern: client properties create instances on first access, all platform clients share one httpx.AsyncClient with auth header
  - System endpoints (/_lifecycle/{hook}, /_tasks/{task_id}) require X-SemPKM-App-Token header; /_health is exempt
observability_surfaces:
  - App class logs lifecycle hook and task dispatch at INFO level
  - Token validation failures logged at WARNING (missing/invalid header) with request method and path
  - AppContext logs platform client creation and cleanup at DEBUG
  - Runner logs entrypoint import at INFO, import failures at ERROR with module name
duration: 25m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: SDK package — App class, context, clients, runner

**Built the `sempkm-app-sdk` Python package with decorator-based App class, lazy-init AppContext with 5 client stubs, and CLI runner — 30 tests passing.**

## What Happened

Created the full SDK package at `backend/sdk/` with hatchling build system. The `App` class provides decorator-based handler registration (`@app.route`, `@app.task`, lifecycle decorators) and `build_asgi_app()` that wires handlers into a FastAPI instance with system endpoints for health, lifecycle dispatch, and task dispatch.

`AppContext` is a dataclass providing lazy-initialized clients (CommandClient, GraphClient, StateClient, HttpClient, SettingsClient) that share one httpx.AsyncClient for platform API calls with Bearer token auth. Template rendering via Jinja2 FileSystemLoader. `close()` cleans up all HTTP clients.

Client stubs are thin wrappers: CommandClient posts to `/api/commands`, GraphClient posts SPARQL to `/api/sparql`, StateClient uses SPARQL for per-app key/value storage in a named graph, HttpClient wraps a standalone httpx client for external calls, SettingsClient delegates to StateClient with `settings:` key prefix.

Runner parses `--app-dir`, `--socket`, `--platform-url`, `--app-token`, reads `manifest.yaml` for `backend.entrypoint` (module:attribute format), imports via importlib, builds ASGI app, runs uvicorn on UDS.

One fix during testing: renamed `render_template(name=...)` to `render_template(template_name=...)` to avoid collision when a template variable is named `name`.

## Verification

- `cd backend && uv pip install -e sdk/ --python .venv/bin/python` — installed successfully
- `python -c "from sempkm_app_sdk import App, AppContext; print('OK')"` — imports clean
- `cd backend && .venv/bin/pytest tests/test_sdk_app.py -v` — **30 passed** (decorator registration ×8, ASGI app ×9, token validation ×4, AppContext ×5, client stubs ×2, runner ×2)
- Slice verification:
  - `test_app_tokens.py` — **17 passed** ✓ (T01)
  - `test_sdk_app.py` — **30 passed** ✓ (T02)
  - `test_app_proxy.py` — not yet created (T03)
  - `test_sdk_integration.py` — not yet created (T04)

## Diagnostics

- App handler dispatch: `grep "Dispatching lifecycle\|Dispatching task" <logfile>` — INFO-level logs on every hook/task invocation
- Token validation: `grep "Invalid app token\|Missing X-SemPKM" <logfile>` — WARNING-level on auth failures with method+path context
- Client creation: `grep "Created platform HTTP client\|Closed AppContext" <logfile>` — DEBUG-level lifecycle tracking
- Import failures: `grep "Failed to import app module" <logfile>` — ERROR-level with module name and app_dir

## Deviations

- Renamed `render_template(name=...)` to `render_template(template_name=...)` — the `name` parameter collides with `**context` kwargs when a template variable is called `name` (hit immediately in tests, trivial fix)
- Added `pyyaml>=6.0` to SDK dependencies — runner needs it to read manifest.yaml, was missing from plan

## Known Issues

None.

## Files Created/Modified

- `backend/sdk/pyproject.toml` — package metadata with hatchling build backend
- `backend/sdk/sempkm_app_sdk/__init__.py` — exports App, AppContext
- `backend/sdk/sempkm_app_sdk/__main__.py` — `python -m sempkm_app_sdk` entry point
- `backend/sdk/sempkm_app_sdk/app.py` — App class with decorator registry and ASGI builder
- `backend/sdk/sempkm_app_sdk/context.py` — AppContext with lazy clients and template rendering
- `backend/sdk/sempkm_app_sdk/runner.py` — CLI runner with argparse, entrypoint import, uvicorn UDS
- `backend/sdk/sempkm_app_sdk/clients/__init__.py` — package exports for all 5 clients
- `backend/sdk/sempkm_app_sdk/clients/commands.py` — CommandClient stub (POST /api/commands)
- `backend/sdk/sempkm_app_sdk/clients/graph.py` — GraphClient stub (POST /api/sparql)
- `backend/sdk/sempkm_app_sdk/clients/state.py` — StateClient stub (SPARQL-based key/value)
- `backend/sdk/sempkm_app_sdk/clients/http.py` — HttpClient stub (external HTTP wrapper)
- `backend/sdk/sempkm_app_sdk/clients/settings.py` — SettingsClient stub (settings: prefix over state)
- `backend/tests/test_sdk_app.py` — 30 unit tests covering all SDK components
