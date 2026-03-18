---
id: S02
parent: M009
milestone: M009
provides:
  - sempkm-app-sdk Python package at backend/sdk/ with App class, AppContext, 5 client stubs, CLI runner
  - JWT token generation/validation utility with grace period for token renewal
  - AppProxy forwarding HTTP to app UDS sockets via httpx AsyncHTTPTransport with token injection
  - FastAPI router at /app/{app_id}/{path} for proxy forwarding and POST /api/apps/{app_id}/token/renew
  - AppManager updates: JWT generation on start, SDK install on install, token cleanup on stop
  - Integration proof: real SDK subprocess serves health/fragments/lifecycle/tasks over UDS
requires:
  - slice: S01
    provides: AppManager (socket path, process lifecycle), AppRegistry (manifest lookup), AppManifestSchema (entrypoint field), SQLAlchemy models, app.auth.tokens._get_secret_key() (secret resolution)
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
  - backend/sdk/sempkm_app_sdk/clients/
  - backend/tests/test_app_tokens.py
  - backend/tests/test_sdk_app.py
  - backend/tests/test_app_proxy.py
  - backend/tests/test_sdk_integration.py
  - backend/tests/fixtures/test_sdk_app/
key_decisions:
  - D173: SDK uses shared-secret string comparison (not JWT decode) — simpler model, apps don't need PyJWT or secret key access
  - D174: Non-streaming proxy (v1) — httpx client.request() not stream=True, sufficient for KB-range fragment responses
  - Token renewal uses 300s grace period — expired tokens within 5 minutes accepted for renewal endpoint only
  - Lifecycle decorators as properties returning decorator functions — @app.on_startup syntax cleaner than @app.lifecycle("startup")
  - AppContext uses lazy-init properties — avoids creating HTTP clients until first access
patterns_established:
  - SDK decorator pattern: @app.route(path, methods), @app.task(task_id), @app.on_{lifecycle}
  - System endpoint pattern: /_health (no auth), /_lifecycle/{hook} (auth), /_tasks/{task_id} (auth)
  - Client stub pattern: thin async wrappers around httpx.AsyncClient with platform base_url
  - State graph IRI pattern: urn:sempkm:app:{app_id}:state for app-scoped key-value storage
  - Proxy connection pooling: one httpx.AsyncClient per app_id with UDS transport, cleaned on stop
  - Proxy error code pattern: 502 (socket missing), 503 (app not running), 404 (app not found)
  - Token claims structure: {sub: "app:{app_id}", permissions: {...}, iat, exp}
observability_surfaces:
  - /_health endpoint returns {"status": "ok"} — platform uses for liveness probing
  - Proxy returns HTTP 502 {"detail": "App {app_id} not reachable"} on socket/connection failure
  - Proxy returns HTTP 503 {"detail": "App {app_id} is not running"} on stopped app
  - System endpoints return 403 {"detail": "Invalid or missing app token"} on auth failure
  - AppManager.get_token(app_id) returns current JWT for inspection
  - AppProxy._clients dict shows which apps have active httpx connections
  - DEBUG-level logs for token generation/validation, lifecycle/task dispatch, client creation
  - WARNING-level logs for invalid tokens, socket missing, connection failures
drill_down_paths:
  - .gsd/milestones/M009/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M009/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M009/slices/S02/tasks/T03-SUMMARY.md
  - .gsd/milestones/M009/slices/S02/tasks/T04-SUMMARY.md
duration: 70m
verification_result: passed
completed_at: 2026-03-18
---

# S02: App SDK & IPC Proxy

**Built the sempkm-app-sdk package and IPC proxy layer — apps built with the SDK start on unix sockets, the platform proxies HTTP to them with JWT auth, and real subprocess integration tests prove the full round-trip**

## What Happened

This slice delivered three interlocking components that form the developer-facing contract and communication channel for the app platform:

**T01 — JWT Token Utility** (10m): Created `backend/app/apps/tokens.py` with `generate_app_token()` (HS256 JWT with sub/permissions/iat/exp claims), `validate_app_token()` (returns claims dict or None, supports grace period for renewal), and `get_secret()` (delegates to existing platform secret resolution). 18 unit tests covering round-trip, expiry, tampering, wrong secret/algorithm, grace period boundaries.

**T02 — SDK Package** (25m): Built the `sempkm-app-sdk` package at `backend/sdk/` with hatchling build backend. The `App` class provides a decorator registry — `@app.route(path, methods)`, `@app.task(task_id)`, and lifecycle decorators (`@app.on_startup`, `@app.on_shutdown`, `@app.on_install`, `@app.on_uninstall`). `build_asgi_app(ctx)` produces a FastAPI instance with three system endpoint families: `/_health` (no auth, liveness), `/_lifecycle/{hook}` (auth required), and `/_tasks/{task_id}` (auth required). `AppContext` is a dataclass with lazy-init properties for 5 client stubs (CommandClient, GraphClient, StateClient, HttpClient, SettingsClient) sharing one platform httpx.AsyncClient, plus Jinja2 template rendering. The CLI runner (`python -m sempkm_app_sdk`) accepts `--app-dir`, `--socket`, `--platform-url`, `--app-token`, reads the app manifest, imports the entrypoint, and starts uvicorn on UDS. 45 unit tests.

**T03 — Platform Proxy & Manager Updates** (20m): Created `AppProxy` class that routes HTTP to app UDS sockets via `httpx.AsyncHTTPTransport(uds=...)`, maintaining a connection pool per app_id and injecting the `X-SemPKM-App-Token` header. Created `app_proxy_router` with catch-all `ANY /app/{app_id}/{path:path}` (checks app status first) and `POST /api/apps/{app_id}/token/renew` (validates old token with 300s grace, issues fresh JWT). Modified `AppManager` to generate JWTs on `start()`, store them in `_tokens` dict, install SDK into app venvs during `install()`, and clean up on `stop()`. Wired `app_proxy_router` into `main.py` before `browser_router` (critical ordering — browser router has `{iri:path}` catch-all). 21 unit tests.

**T04 — Integration Proof** (15m): Created a minimal SDK test app fixture at `backend/tests/fixtures/test_sdk_app/` and 8 integration tests that start a real subprocess on UDS, wait for the socket file, then exercise all endpoint types through httpx async client with UDS transport. Tests cover: health (200, no auth), fragment route (HTML response), lifecycle dispatch (startup hook fires), task dispatch (handler called), and token enforcement (missing/wrong → 401/403). Discovered that FastAPI route handlers must type-annotate `request: Request` to avoid 422 — added to KNOWLEDGE.md.

## Verification

All 4 verification commands from the slice plan pass:

| # | Command | Tests | Verdict |
|---|---------|-------|---------|
| 1 | `pytest tests/test_app_tokens.py -v` | 18/18 | ✅ pass |
| 2 | `pytest tests/test_sdk_app.py -v` | 45/45 | ✅ pass |
| 3 | `pytest tests/test_app_proxy.py -v` | 21/21 | ✅ pass |
| 4 | `pytest tests/test_sdk_integration.py -v` | 8/8 | ✅ pass |

**Total: 92 tests pass in ~2.3s**

The S02 demo scenario is proven: a real SDK-based app subprocess starts on UDS, serves health and fragment responses, dispatches lifecycle hooks and task handlers, and enforces token authentication — all exercised through the proxy round-trip.

## Requirements Advanced

- APP-02 — S02 completed the end-to-end proof: SDK runner starts on UDS, platform proxies to it, lifecycle hooks and tasks dispatch correctly. The subprocess lifecycle engine from S01 is now validated with a real app.

## Requirements Validated

- APP-02 — Full lifecycle proven end-to-end: S01 engine + S02 SDK runner + 8 integration tests on real subprocess
- APP-03 — SDK package delivered with all acceptance criteria: App class with decorators, AppContext with 5 client stubs, task/route/lifecycle registration, template rendering, CLI runner on UDS. 45 unit + 8 integration tests.
- APP-04 — IPC via HTTP/UDS delivered: AppProxy forwards requests through UDS transport with JWT injection, token renewal with grace period, structured error responses. 21 proxy + 8 integration tests.

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- **Token validation in SDK uses shared-secret comparison, not JWT decode** — the plan mentioned JWT validation via `validate_app_token()` in the SDK, but the implementation uses simpler string comparison (platform passes token at startup, SDK compares `X-SemPKM-App-Token` header to stored value). This is simpler and avoids SDK needing PyJWT or secret key access. Recorded as D173.
- **FastAPI route handlers require `request: Request` type annotation** — discovered during T04 integration testing. Without it, FastAPI treats `request` as a query parameter and returns 422. Added to KNOWLEDGE.md for future SDK app developers.
- **Token renewal same-second identity** — when both old and new tokens are generated within the same second, JWT claims are identical, producing identical tokens. Assertion changed to validate claims structure rather than string inequality.

## Known Limitations

- **No permission enforcement on SDK clients** — all client stubs (CommandClient, GraphClient, etc.) make unrestricted calls to the platform API. Permission whitelisting, IRI prefix enforcement, and network domain restrictions are deferred to S05.
- **Non-streaming proxy** — `AppProxy` buffers full responses before forwarding. Adequate for HTML fragments but won't support SSE or large file downloads. Streaming upgrade planned if needed (D174).
- **No automatic token rotation** — tokens are generated on `start()` with 1-hour TTL, and the renewal endpoint exists, but the SDK does not yet auto-renew before expiry. Apps calling platform APIs beyond 1 hour would need manual renewal or SDK-side renewal logic (S05 scope).

## Follow-ups

- S05 must add permission enforcement to SDK client stubs (command whitelist, IRI prefix, network domain restriction)
- S03 should verify that admin portal UI can communicate with apps through the proxy (status verification)
- S04 will load app fragment content through the proxy into workspace — the `/_fragments/{page}` pattern is ready

## Files Created/Modified

- `backend/app/apps/tokens.py` — new: JWT generation, validation with grace period, secret delegation
- `backend/app/apps/proxy.py` — new: AppProxy class with UDS forwarding, connection pooling, error handling
- `backend/app/apps/router.py` — new: app_proxy_router with catch-all proxy route and token renewal endpoint
- `backend/app/apps/manager.py` — modified: added _tokens dict, JWT generation on start, SDK install on install, token cleanup
- `backend/app/main.py` — modified: imports AppProxy and app_proxy_router, wires proxy lifecycle, includes router before browser_router
- `backend/sdk/pyproject.toml` — new: SDK package metadata with hatchling build system
- `backend/sdk/sempkm_app_sdk/__init__.py` — new: package exports (App, AppContext, __version__)
- `backend/sdk/sempkm_app_sdk/__main__.py` — new: python -m entry point
- `backend/sdk/sempkm_app_sdk/app.py` — new: App class with decorator registry and ASGI app builder
- `backend/sdk/sempkm_app_sdk/context.py` — new: AppContext dataclass with lazy-init clients and template rendering
- `backend/sdk/sempkm_app_sdk/runner.py` — new: CLI runner with argparse, manifest reading, entrypoint import, uvicorn UDS
- `backend/sdk/sempkm_app_sdk/clients/__init__.py` — new: exports all 5 client classes
- `backend/sdk/sempkm_app_sdk/clients/commands.py` — new: CommandClient (POST /api/commands)
- `backend/sdk/sempkm_app_sdk/clients/graph.py` — new: GraphClient (POST /api/sparql)
- `backend/sdk/sempkm_app_sdk/clients/state.py` — new: StateClient (SPARQL-backed key-value)
- `backend/sdk/sempkm_app_sdk/clients/http.py` — new: HttpClient (external HTTP, separate client)
- `backend/sdk/sempkm_app_sdk/clients/settings.py` — new: SettingsClient (delegates to StateClient with prefix)
- `backend/tests/test_app_tokens.py` — new: 18 JWT unit tests
- `backend/tests/test_sdk_app.py` — new: 45 SDK unit tests
- `backend/tests/test_app_proxy.py` — new: 21 proxy/router unit tests
- `backend/tests/test_sdk_integration.py` — new: 8 integration tests on real subprocess
- `backend/tests/fixtures/test_sdk_app/manifest.yaml` — new: minimal valid manifest for integration tests
- `backend/tests/fixtures/test_sdk_app/app.py` — new: SDK test app with route, task, lifecycle handlers
- `backend/tests/fixtures/test_sdk_app/requirements.txt` — new: empty (SDK injected by platform)
- `backend/tests/test_app_manager.py` — modified: updated install test to expect 3 uv calls (includes SDK install)

## Forward Intelligence

### What the next slice should know
- The proxy routes `/app/{app_id}/{path}` are wired in `main.py` **before** `browser_router` — this ordering is load-bearing because browser_router has a `{iri:path}` catch-all that would swallow app routes. Any new router insertions must respect this ordering.
- SDK system endpoints (`/_health`, `/_lifecycle/*`, `/_tasks/*`) use `X-SemPKM-App-Token` header for auth. User-registered routes (like `/_fragments/*`) do NOT require token auth — they're public endpoints proxied through the platform.
- The `AppManager._tokens` dict stores JWT strings keyed by app_id. `get_token(app_id)` is the accessor for injecting tokens into proxy requests.
- SDK install happens during `AppManager.install()` via `uv pip install /app/backend/sdk --python {venv_python}`. The Docker path `/app/backend/sdk` assumes the standard volume mount layout.

### What's fragile
- **Router ordering in main.py** — `app_proxy_router` MUST come before `browser_router`. Moving it after will silently break all app proxy routes because `{iri:path}` catches everything.
- **Token store is in-memory only** — if the platform process restarts, all app tokens are lost. `auto_start()` regenerates tokens for previously-running apps, but any in-flight app requests during the restart window will fail with 401.
- **SDK package path in Docker** — `install()` hardcodes `/app/backend/sdk` as the SDK install path, which depends on the Docker volume mount at `./backend:/app`.

### Authoritative diagnostics
- `GET /app/{app_id}/_health` → if this returns 200 with `{"status":"ok"}`, the full chain works (proxy → UDS → SDK → response)
- `AppManager.get_token(app_id)` → returns None if app hasn't started or token was cleared
- `AppProxy._clients` dict → shows which apps have active httpx connections with UDS transport

### What assumptions changed
- **Plan assumed JWT decode in SDK** — actual implementation uses simpler shared-secret string comparison (D173). This means apps don't parse JWT claims, which simplifies the SDK but means apps can't inspect their own permissions from the token. S05 may need to revisit this when adding permission enforcement.
- **Plan assumed streaming proxy** — actual implementation uses buffered responses (D174). This is fine for HTML fragments but would need upgrade for SSE or large file proxying.
