---
id: T03
parent: S02
milestone: M009
provides:
  - AppProxy UDS forwarding with connection pooling and token injection
  - Proxy catch-all router at /app/{app_id}/{path:path} with 502/503 error semantics
  - Token renewal endpoint at POST /api/apps/{app_id}/token/renew with 300s grace
  - AppManager JWT generation on start, SDK install on install, token store with cleanup
key_files:
  - backend/app/apps/proxy.py
  - backend/app/apps/router.py
  - backend/app/apps/manager.py
  - backend/app/main.py
  - backend/tests/test_app_proxy.py
key_decisions:
  - Token renewal validates sub claim matches app_id to prevent cross-app token reuse
  - Proxy uses non-streaming httpx.request() for v1 simplicity — streaming can be added later if large responses are a problem
  - Proxy strips hop-by-hop headers (host, connection, transfer-encoding) from both directions
patterns_established:
  - AppProxy connection pool pattern — one httpx.AsyncClient per app_id, created lazily, closed on app stop or platform shutdown
  - Router retrieves manager/proxy from request.app.state — no FastAPI Depends() DI since these are singleton app-level objects
observability_surfaces:
  - WARNING logs on socket missing / connection refused with app_id context
  - HTTP 502 with {"detail": "App {app_id} not reachable"} on socket/connection failure
  - HTTP 503 with {"detail": "App {app_id} is not running"} on stopped/unknown app
  - AppManager.get_token(app_id) returns current JWT for runtime inspection
  - AppProxy._clients dict shows which apps have active httpx connections
duration: 25m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T03: Platform proxy, router, and manager updates

**Built AppProxy UDS forwarding, proxy router with 502/503 semantics, token renewal endpoint, and wired JWT generation + SDK install into AppManager.**

## What Happened

Created `AppProxy` class that forwards HTTP requests to app subprocesses via Unix Domain Sockets using httpx's `AsyncHTTPTransport(uds=...)`. The proxy maintains a connection pool (one `AsyncClient` per app), injects `X-SemPKM-App-Token` headers, and strips hop-by-hop headers in both directions. Socket-not-found and connection failures raise `AppNotReachableError`.

Created `app_proxy_router` with two endpoints: a catch-all `ANY /app/{app_id}/{path:path}` that checks app status before forwarding (503 if not running, 502 if unreachable), and `POST /api/apps/{app_id}/token/renew` that validates the old token with 300s grace period and returns a fresh JWT.

Modified `AppManager`: added `_tokens` dict and `get_token()` accessor, `start()` now generates JWT via `generate_app_token()` and passes `--app-token` to the subprocess command, `install()` now installs the SDK package into the app venv, and `stop()` / `_cleanup_process_state()` clean up tokens.

Modified `main.py`: `AppProxy` created in lifespan and stored on `app.state.app_proxy`, `app_proxy_router` included before `browser_router` to prevent the `{iri:path}` catch-all from consuming `/app/` URLs, and proxy cleanup added to shutdown sequence.

## Verification

- `pytest tests/test_app_proxy.py -v` — **23 tests pass**: 7 proxy unit tests, 4 router tests, 6 token renewal tests, 5 manager token tests, 1 SDK install test
- `pytest tests/test_app_manager.py -v` — **31 tests pass**: existing manager tests all pass (updated install test assertion for 3 uv calls instead of 2)
- Slice-level checks:
  - ✅ `pytest tests/test_app_tokens.py -v` — 17 pass
  - ✅ `pytest tests/test_sdk_app.py -v` — 30 pass
  - ✅ `pytest tests/test_app_proxy.py -v` — 23 pass
  - ⏳ `pytest tests/test_sdk_integration.py -v` — T04 (not yet created)

## Diagnostics

- Proxy errors: `grep "socket not found\|connection failed" <logfile>` — WARNING-level with app_id
- Token lifecycle: `AppManager.get_token(app_id)` returns current JWT; None after stop
- Connection pool: `AppProxy._clients` dict keys show which apps have active httpx connections
- Error responses carry structured JSON: `{"detail": "App {app_id} not reachable"}` (502) or `{"detail": "App {app_id} is not running"}` (503)

## Deviations

- Plan referenced `_cleanup_runtime_state()` but actual method is `_cleanup_process_state()` — used correct name
- Plan said `get_status()` returns a status string — it actually returns a dict; router checks `status_info.get("status") != "running"`
- Used non-streaming `client.request()` instead of `client.send()` with `stream=True` as plan suggested for v1 simplicity
- Updated existing `test_app_manager.py::test_install_creates_venv_and_starts` to expect 3 uv calls (was 2) due to SDK install step

## Known Issues

None.

## Files Created/Modified

- `backend/app/apps/proxy.py` — new: AppProxy with UDS forwarding, connection pooling, AppNotReachableError
- `backend/app/apps/router.py` — new: app_proxy_router with catch-all proxy route + token renewal endpoint
- `backend/app/apps/manager.py` — modified: added token store, get_token(), JWT generation in start(), SDK install in install(), token cleanup in stop()/_cleanup_process_state()
- `backend/app/main.py` — modified: added AppProxy creation in lifespan, proxy router include before browser_router, proxy cleanup on shutdown
- `backend/tests/test_app_proxy.py` — new: 23 unit tests for proxy, router, and manager token handling
- `backend/tests/test_app_manager.py` — modified: updated install test assertion for 3 uv calls
