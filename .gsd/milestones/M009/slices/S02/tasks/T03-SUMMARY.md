---
id: T03
parent: S02
milestone: M009
provides:
  - AppProxy class forwarding HTTP to app subprocesses via UDS with token injection
  - FastAPI router at /app/{app_id}/{path} and POST /api/apps/{app_id}/token/renew
  - AppManager token store with JWT generation on start, cleanup on stop
  - SDK install step in AppManager.install()
  - app_proxy_router included before browser_router in main.py
key_files:
  - backend/app/apps/proxy.py
  - backend/app/apps/router.py
  - backend/app/apps/manager.py
  - backend/app/main.py
  - backend/tests/test_app_proxy.py
key_decisions:
  - Non-streaming proxy (v1) — uses client.request() instead of stream=True for simplicity; streaming can be added later if large responses become a problem
  - Token renewal uses 300s grace period matching plan spec — expired tokens within 5 minutes are accepted for renewal
patterns_established:
  - Proxy connection pooling pattern — one httpx.AsyncClient per app_id with UDS transport, created on first forward, cleaned up on app stop or platform shutdown
  - Error code pattern for proxy — 502 (socket missing/connection failed), 503 (app not running), 404 (app not found)
observability_surfaces:
  - AppProxy logs WARNING on socket missing or connection failure with app_id context
  - HTTP 502 responses carry structured JSON {"detail": "App {app_id} not reachable"}
  - HTTP 503 responses carry structured JSON {"detail": "App {app_id} is not running"}
  - AppManager.get_token(app_id) returns current JWT for inspection
  - AppProxy._clients dict shows which apps have active httpx connections
duration: 20m
verification_result: passed
blocker_discovered: false
---

# T03: Platform proxy, router, and manager updates

**Wired platform-side IPC: AppProxy forwards HTTP to app UDS sockets with JWT injection, proxy router at /app/{app_id}/{path} with token renewal endpoint, and AppManager generates/stores JWTs on start and installs SDK into app venvs**

## What Happened

Created `AppProxy` class that routes HTTP requests to app subprocesses over Unix domain sockets using httpx `AsyncHTTPTransport(uds=...)`. The proxy maintains a connection pool (`_clients` dict) with one `httpx.AsyncClient` per app_id, injects the `X-SemPKM-App-Token` header from the manager's token store, and propagates method/path/headers/body to the upstream app.

Created `app_proxy_router` with two endpoints: a catch-all `ANY /app/{app_id}/{path:path}` that checks app status before forwarding, and `POST /api/apps/{app_id}/token/renew` that validates the old token with 300s grace period before issuing a fresh JWT.

Modified `AppManager` to: (1) maintain a `_tokens` dict for JWT storage, (2) generate JWT via `generate_app_token()` and append `--app-token` to subprocess cmd in `start()`, (3) install the SDK package (`/app/backend/sdk`) into app venvs during `install()`, (4) clean up tokens in `stop()` and `shutdown_all()`.

Modified `main.py` to import and wire `AppProxy` on `app.state.app_proxy`, include `app_proxy_router` before `browser_router` (critical — `browser_router` has `{iri:path}` catch-all), and close proxy connections during shutdown.

Updated existing `test_app_manager.py` to expect 3 uv calls in install (venv + requirements + SDK) instead of 2.

## Verification

- `backend/.venv/bin/pytest tests/test_app_proxy.py -v` — 21 tests pass (7 proxy, 4 router, 5 token renewal, 5 manager token)
- `backend/.venv/bin/pytest tests/test_app_manager.py -v` — 30 tests pass (existing manager tests updated for SDK install step)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_app_proxy.py -v` | 0 | ✅ pass | 1.0s |
| 2 | `pytest tests/test_app_manager.py -v` | 0 | ✅ pass | 1.0s |
| 3 | `pytest tests/test_app_tokens.py -v` | 0 | ✅ pass | 0.04s |
| 4 | `pytest tests/test_sdk_app.py -v` | 0 | ✅ pass | 0.34s |
| 5 | `pytest tests/test_sdk_integration.py -v` | — | ⏳ T04 | — |

## Diagnostics

- **Proxy errors:** Socket missing → HTTP 502 with `{"detail": "App {app_id} not reachable"}`, logged at WARNING. App not running → HTTP 503 with `{"detail": "App {app_id} is not running"}`.
- **Token inspection:** `AppManager.get_token(app_id)` returns current JWT string or None.
- **Connection pool:** `AppProxy._clients` dict keys show which apps have active httpx connections.
- **Token renewal failures:** 401 response with detail indicating "expired beyond grace" or "invalid" — check WARNING-level logs for token validation specifics.

## Deviations

- Plan mentioned `_cleanup_runtime_state()` method for token cleanup, but this method doesn't exist in the manager. Token cleanup is handled in `stop()` and `shutdown_all()` which are the actual cleanup paths.
- Removed assertion that renewed token differs from old token — when both are generated within the same second, JWT claims (including `iat`) are identical, producing identical tokens. Replaced with validation that the returned token decodes to correct claims.

## Known Issues

None.

## Files Created/Modified

- `backend/app/apps/proxy.py` — new: AppProxy class with UDS forwarding, connection pooling, AppNotReachableError exception
- `backend/app/apps/router.py` — new: app_proxy_router with catch-all proxy route and token renewal endpoint
- `backend/app/apps/manager.py` — modified: added _tokens dict, get_token() accessor, JWT generation in start(), SDK install in install(), token cleanup in stop()/shutdown_all()
- `backend/app/main.py` — modified: imports AppProxy and app_proxy_router, wires proxy lifecycle in lifespan, includes router before browser_router
- `backend/tests/test_app_proxy.py` — new: 21 unit tests for proxy, router, and manager token handling
- `backend/tests/test_app_manager.py` — modified: updated install test to expect 3 uv calls (includes SDK install)
