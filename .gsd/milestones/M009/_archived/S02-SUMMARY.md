---
id: S02
parent: M009
milestone: M009
provides:
  - sempkm-app-sdk Python package with App class, decorator-based handler registration, AppContext with 5 client stubs
  - CLI runner starting uvicorn on UDS with system endpoints (/_health, /_lifecycle/*, /_tasks/*)
  - JWT token generation/validation utility with grace period support for token renewal
  - AppProxy UDS forwarding with per-app connection pooling and token injection
  - Proxy router at /app/{app_id}/{path:path} with 502/503 error semantics
  - Token renewal endpoint at POST /api/apps/{app_id}/token/renew with 300s grace
  - AppManager updates: JWT on start, SDK install on install, token store with cleanup
requires:
  - slice: S01
    provides: AppManager (socket path, process lifecycle), AppRegistry (manifest lookup), AppManifestSchema (entrypoint field), SQLAlchemy models, app.auth.tokens._get_secret_key()
affects:
  - S03
  - S04
  - S05
key_files:
  - backend/app/apps/tokens.py
  - backend/app/apps/proxy.py
  - backend/app/apps/router.py
  - backend/app/apps/manager.py
  - backend/app/main.py
  - backend/sdk/pyproject.toml
  - backend/sdk/sempkm_app_sdk/app.py
  - backend/sdk/sempkm_app_sdk/context.py
  - backend/sdk/sempkm_app_sdk/runner.py
  - backend/sdk/sempkm_app_sdk/clients/commands.py
  - backend/sdk/sempkm_app_sdk/clients/graph.py
  - backend/sdk/sempkm_app_sdk/clients/state.py
  - backend/sdk/sempkm_app_sdk/clients/http.py
  - backend/sdk/sempkm_app_sdk/clients/settings.py
  - backend/tests/test_app_tokens.py
  - backend/tests/test_sdk_app.py
  - backend/tests/test_app_proxy.py
  - backend/tests/test_sdk_integration.py
  - backend/tests/fixtures/test_sdk_app/app.py
  - backend/tests/fixtures/test_sdk_app/manifest.yaml
key_decisions:
  - D157: SDK token validation via string comparison, not PyJWT decode — simpler, no key management in SDK
  - D158: SDK client stubs use loose dependency pins to avoid conflicts in per-app venvs
  - D159: AppProxy connection pooling per app_id, not per request — matches app lifecycle
  - D160: Proxy uses non-streaming response for v1 — fragments are small, streaming adds complexity
patterns_established:
  - App decorator pattern: @app.route(), @app.task(), @app.on_startup/shutdown/install/uninstall register handlers; build_asgi_app() wires them into FastAPI
  - AppContext lazy-init pattern: client properties create instances on first access, all platform clients share one httpx.AsyncClient with Bearer auth
  - System endpoint auth: /_lifecycle/* and /_tasks/* require X-SemPKM-App-Token header; /_health is exempt
  - Proxy connection pool: one httpx.AsyncClient per app_id, created lazily, closed on app stop or platform shutdown
  - Router retrieves manager/proxy from request.app.state — singleton pattern, no FastAPI Depends() DI
observability_surfaces:
  - JWT generation/validation logged at DEBUG (app_id + expiry, sub claim); invalid tokens at WARNING (exception type, never the token value)
  - Proxy errors (socket missing, connection refused) logged at WARNING with app_id context
  - HTTP 502 with {"detail":"App {app_id} not reachable"} on socket/connection failure; 503 when app not running
  - AppManager.get_token(app_id) returns current JWT for runtime inspection
  - AppProxy._clients dict shows which apps have active httpx connections
  - SDK App class logs lifecycle hook and task dispatch at INFO; token validation failures at WARNING with method+path
drill_down_paths:
  - .gsd/milestones/M009/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M009/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M009/slices/S02/tasks/T03-SUMMARY.md
  - .gsd/milestones/M009/slices/S02/tasks/T04-SUMMARY.md
duration: 1h25m
verification_result: passed
completed_at: 2026-03-16
---

# S02: App SDK & IPC Proxy

**Built the `sempkm-app-sdk` Python package, JWT auth layer, UDS proxy forwarding, and proved the full round-trip with a real subprocess serving HTML fragments through the platform proxy.**

## What Happened

**T01 — JWT tokens (15m):** Created `backend/app/apps/tokens.py` with `generate_app_token()` (HS256 JWT with sub/permissions/iat/exp claims), `validate_app_token()` (two-pass decode with grace period for renewal), and `get_secret()` delegating to the auth module. 17 tests.

**T02 — SDK package (25m):** Built the full `sempkm-app-sdk` package at `backend/sdk/` with hatchling build system. The `App` class provides decorator-based handler registration (`@app.route`, `@app.task`, lifecycle decorators) and `build_asgi_app()` wiring handlers into FastAPI with system endpoints for health, lifecycle, and task dispatch. `AppContext` provides lazy-initialized clients (CommandClient, GraphClient, StateClient, HttpClient, SettingsClient) sharing one httpx.AsyncClient for platform API calls. Runner parses CLI args, reads manifest, imports entrypoint via `module:attribute` format, and runs uvicorn on UDS. 30 tests.

**T03 — Proxy, router, manager updates (25m):** Created `AppProxy` forwarding HTTP to app UDS via httpx `AsyncHTTPTransport(uds=...)` with per-app connection pooling and token injection. Created `app_proxy_router` with catch-all `/app/{app_id}/{path:path}` (502 on unreachable, 503 on not running) and token renewal endpoint with 300s grace. Modified `AppManager` to generate JWT on start, install SDK into app venv on install, and maintain a token store. Wired proxy router into `main.py` before `browser_router`. 23 tests.

**T04 — Integration proof (15m):** Created a minimal SDK test app fixture and integration tests proving the full S02 contract: real subprocess on UDS serves `/_health`, `/_fragments/main`, `/_lifecycle/startup`, and `/_tasks/test-task` — all with correct JWT auth enforcement. 7 tests proving the round-trip.

## Verification

All four slice verification checks pass — 77 tests total:

- `pytest tests/test_app_tokens.py -v` — **17 passed** (JWT generation, validation, grace period, secret delegation)
- `pytest tests/test_sdk_app.py -v` — **30 passed** (decorator registration, ASGI building, token validation, AppContext, clients, runner)
- `pytest tests/test_app_proxy.py -v` — **23 passed** (proxy forwarding, router 502/503, token renewal, manager tokens, SDK install)
- `pytest tests/test_sdk_integration.py -v` — **7 passed** (real subprocess round-trip on UDS)
- Existing `test_app_manager.py` — **31 passed** (updated install assertion for SDK install step)

No user-visible features in this slice (pure backend infrastructure) — no E2E or docs tasks required.

## Requirements Advanced

- APP-03 (App SDK) — SDK package built with App class, AppContext, 5 client stubs, and CLI runner. Permission enforcement deferred to S05.
- APP-04 (IPC via HTTP/UDS) — Platform proxies to app subprocess UDS via httpx transport with JWT auth. Token renewal endpoint with grace period. Hourly rotation deferred to S05 (scheduler triggers renewal).
- APP-02 (Subprocess lifecycle) — AppManager extended with JWT generation on start, SDK install on install, token cleanup on stop.

## Requirements Validated

- None — S02 advances APP-03 and APP-04 but full validation requires downstream slices (S03 admin visibility, S04 frontend fragment loading, S05 permission enforcement).

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- `render_template()` parameter renamed from `name` to `template_name` — avoids collision when template context includes a `name` variable.
- `pyyaml>=6.0` added to SDK dependencies — runner needs it to read `manifest.yaml`, was missing from plan.
- Proxy uses non-streaming `client.request()` instead of `client.send(stream=True)` — simpler for v1, fragments are small.
- Integration tests use sync `httpx.Client` instead of async — sufficient since subprocess management is synchronous.

## Known Limitations

- SDK client stubs have no permission enforcement — commands, graph queries, HTTP requests are unconstrained. S05 adds whitelists, IRI prefix enforcement, and domain restrictions.
- Token rotation is not automatic — renewal endpoint exists but nothing triggers it periodically. S05's scheduler will handle this.
- Proxy is non-streaming — large responses from apps would be buffered entirely in memory. Sufficient for HTML fragments but may need streaming if apps serve large payloads.
- PyJWT warns about short HMAC keys in dev mode (test secret < 32 bytes) — not a production issue.

## Follow-ups

- None — all deferred work is already planned in S03–S06.

## Files Created/Modified

- `backend/app/apps/tokens.py` — JWT generation, validation, grace period, secret delegation
- `backend/app/apps/proxy.py` — AppProxy with UDS forwarding, per-app connection pooling, AppNotReachableError
- `backend/app/apps/router.py` — app_proxy_router with catch-all proxy route + token renewal endpoint
- `backend/app/apps/manager.py` — modified: token store, get_token(), JWT on start, SDK install on install, token cleanup
- `backend/app/main.py` — modified: AppProxy creation in lifespan, proxy router before browser_router, proxy cleanup
- `backend/sdk/pyproject.toml` — SDK package metadata with hatchling build backend
- `backend/sdk/sempkm_app_sdk/__init__.py` — package exports (App, AppContext)
- `backend/sdk/sempkm_app_sdk/__main__.py` — `python -m sempkm_app_sdk` entry point
- `backend/sdk/sempkm_app_sdk/app.py` — App class with decorator registry and ASGI builder
- `backend/sdk/sempkm_app_sdk/context.py` — AppContext with lazy clients and Jinja2 template rendering
- `backend/sdk/sempkm_app_sdk/runner.py` — CLI runner with argparse, entrypoint import, uvicorn on UDS
- `backend/sdk/sempkm_app_sdk/clients/__init__.py` — clients package exports
- `backend/sdk/sempkm_app_sdk/clients/commands.py` — CommandClient (POST /api/commands)
- `backend/sdk/sempkm_app_sdk/clients/graph.py` — GraphClient (POST /api/sparql)
- `backend/sdk/sempkm_app_sdk/clients/state.py` — StateClient (SPARQL-based key/value in app named graph)
- `backend/sdk/sempkm_app_sdk/clients/http.py` — HttpClient (external HTTP wrapper)
- `backend/sdk/sempkm_app_sdk/clients/settings.py` — SettingsClient (settings: prefix over StateClient)
- `backend/tests/test_app_tokens.py` — 17 JWT unit tests
- `backend/tests/test_sdk_app.py` — 30 SDK unit tests
- `backend/tests/test_app_proxy.py` — 23 proxy/router/manager token tests
- `backend/tests/test_sdk_integration.py` — 7 integration contract tests (real subprocess round-trip)
- `backend/tests/fixtures/test_sdk_app/manifest.yaml` — minimal valid app manifest for test fixture
- `backend/tests/fixtures/test_sdk_app/app.py` — SDK test app with route, task, and startup hook
- `backend/tests/fixtures/test_sdk_app/requirements.txt` — empty (SDK injected by platform)

## Forward Intelligence

### What the next slice should know
- The SDK package is at `backend/sdk/` and installs via `uv pip install /app/backend/sdk`. The `AppManager.install()` method already handles this as the third `uv` subprocess call (after venv create and app deps install).
- `app_proxy_router` is included in `main.py` **before** `browser_router` — this is critical because the browser router has an `{iri:path}` catch-all that would consume `/app/` URLs otherwise. S03's admin router should also be included before browser_router.
- Token renewal endpoint at `POST /api/apps/{app_id}/token/renew` validates the old token with 300s grace. S05's scheduler should trigger this periodically.
- `AppProxy` is stored on `app.state.app_proxy` — S03's admin routes can access it for status verification.

### What's fragile
- SDK token validation is string comparison (`header == app_token`) — if the platform ever changes the token without restarting the app, the app will reject all requests until restarted. Token renewal must update both sides atomically.
- The integration test fixture uses a module-scoped subprocess — if a test mutates app state (not just reads), it could affect subsequent tests. Currently all 7 tests are read-only.

### Authoritative diagnostics
- `backend/tests/test_sdk_integration.py` — the integration tests are the single best signal that the S02 contract works. If they pass, the round-trip is proven.
- `AppProxy._clients` dict — inspect this at runtime to see which apps have active httpx connections.
- `AppManager._tokens` dict — inspect to see which apps have current JWT tokens.

### What assumptions changed
- Plan assumed SDK would validate JWT tokens via PyJWT decode — actual implementation uses simple string comparison (D157). This is simpler but means apps can't inspect token claims. Acceptable because the platform controls both sides.
- Plan assumed streaming proxy responses — actual implementation buffers full response (D160). Fragments are small enough that this is fine.
