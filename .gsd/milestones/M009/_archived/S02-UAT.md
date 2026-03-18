# S02: App SDK & IPC Proxy — UAT

**Milestone:** M009
**Written:** 2026-03-16

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S02 is pure backend infrastructure with no user-visible UI. All verification is through automated tests exercising real subprocesses on Unix Domain Sockets. The 77 pytest tests cover the full contract including a real subprocess round-trip.

## Preconditions

- Backend virtualenv exists at `backend/.venv` with SDK installed (`uv pip install -e sdk/`)
- No other process occupying `/tmp/sempkm-app-test-sdk-*.sock` paths
- `SECRET_KEY` or `SEMPKM_SECRET_KEY` environment variable set (or default dev secret available)

## Smoke Test

Run all four S02 test suites in one command:
```bash
cd backend && .venv/bin/pytest tests/test_app_tokens.py tests/test_sdk_app.py tests/test_app_proxy.py tests/test_sdk_integration.py -v
```
**Expected:** 77 tests pass. No failures, no errors. Integration tests complete in <5s.

## Test Cases

### 1. JWT Token Round-Trip

1. Run `cd backend && .venv/bin/pytest tests/test_app_tokens.py -v`
2. **Expected:** 17 tests pass covering: valid token generation, claims structure (sub, permissions, iat, exp), custom TTL, expired token returns None, wrong secret returns None, tampered token returns None, wrong algorithm returns None, grace period acceptance/rejection.

### 2. SDK App Class and Decorator Registration

1. Run `cd backend && .venv/bin/pytest tests/test_sdk_app.py -v`
2. **Expected:** 30 tests pass covering:
   - `@app.on_install`, `@app.on_startup`, `@app.on_shutdown`, `@app.on_uninstall` register handlers
   - `@app.route()` registers with default and custom HTTP methods
   - `@app.task()` registers task handlers by ID
   - `build_asgi_app()` returns FastAPI with `/_health`, `/_lifecycle/{hook}`, `/_tasks/{task_id}`
   - System endpoints reject requests without valid `X-SemPKM-App-Token`
   - AppContext creates lazy-initialized clients (CommandClient, GraphClient, StateClient, HttpClient, SettingsClient)
   - `render_template()` renders Jinja2 templates from app directory
   - Runner module imports and parses args

### 3. Proxy Forwarding and Router Wiring

1. Run `cd backend && .venv/bin/pytest tests/test_app_proxy.py -v`
2. **Expected:** 23 tests pass covering:
   - AppProxy forwards requests with correct method/path/headers/body
   - AppProxy injects `X-SemPKM-App-Token` header
   - AppProxy strips hop-by-hop headers (host, connection, transfer-encoding)
   - Socket-not-found raises AppNotReachableError → HTTP 502
   - Connection refused raises AppNotReachableError → HTTP 502
   - App not in 'running' status → HTTP 503
   - Token renewal: valid token → new JWT, expired-within-grace → new JWT, expired-beyond-grace → 401, missing auth → 401, wrong app_id → 403
   - AppManager generates token on start, clears on stop, stores in _tokens dict
   - AppManager install step includes SDK install (`uv pip install /app/backend/sdk`)

### 4. Integration — Real Subprocess Round-Trip on UDS

1. Run `cd backend && .venv/bin/pytest tests/test_sdk_integration.py -v`
2. **Expected:** 7 tests pass proving the full S02 contract:
   - `/_health` returns 200 with `{"status":"ok"}` — no token required
   - `/_health` accessible without token (exempt from auth)
   - `/_fragments/main` returns HTML content from app route handler
   - `POST /_lifecycle/startup` dispatches on_startup hook, returns 200 — with valid token
   - `POST /_lifecycle/startup` returns 403 without token
   - `POST /_tasks/test-task` dispatches task handler, returns 200 — with valid token
   - `POST /_tasks/test-task` returns 403 without token

### 5. Existing Manager Tests Still Pass

1. Run `cd backend && .venv/bin/pytest tests/test_app_manager.py -v`
2. **Expected:** 31 tests pass. The install test expects 3 `uv` subprocess calls (venv create, app deps install, SDK install) instead of the previous 2.

## Edge Cases

### Token Grace Period Boundary

1. Generate a token with `ttl_seconds=1`
2. Wait 2 seconds
3. Validate with `grace_seconds=300`
4. **Expected:** Token accepted (expired by 2s, within 300s grace)

### Token Grace Period Exceeded

1. Generate a token with `ttl_seconds=1`
2. Wait 2 seconds
3. Validate with `grace_seconds=0`
4. **Expected:** Token rejected (no grace, expired)

### Token Renewal Cross-App Prevention

1. Generate token for app_id "app-a"
2. Attempt renewal at `POST /api/apps/app-b/token/renew` with app-a's token
3. **Expected:** HTTP 403 — sub claim doesn't match target app_id

### Proxy to Non-Existent App

1. Send `GET /app/nonexistent/anything` when no app "nonexistent" is registered
2. **Expected:** HTTP 503 with `{"detail": "App nonexistent is not running"}`

### Proxy to Stopped App

1. Register an app but leave it in 'stopped' status
2. Send `GET /app/{app_id}/anything`
3. **Expected:** HTTP 503 with `{"detail": "App {app_id} is not running"}`

### Proxy to App with Missing Socket

1. Set app status to 'running' but delete/don't create the socket file
2. Send `GET /app/{app_id}/anything`
3. **Expected:** HTTP 502 with `{"detail": "App {app_id} not reachable"}`

### SDK System Endpoint Without Token

1. Start SDK app subprocess
2. Send `POST /_lifecycle/startup` without `X-SemPKM-App-Token` header
3. **Expected:** HTTP 403
4. Send `POST /_tasks/test-task` without token
5. **Expected:** HTTP 403
6. Send `GET /_health` without token
7. **Expected:** HTTP 200 (health is exempt)

## Failure Signals

- Integration tests fail to start subprocess → check if SDK is installed in backend venv (`pip show sempkm-app-sdk`)
- Socket timeout in integration tests → check `/tmp/sempkm-app-test-sdk-*.sock` for stale socket files
- Import errors in test_sdk_app → check `backend/sdk/` package structure and `__init__.py` exports
- Token tests fail → check PyJWT version (`pip show PyJWT`) and `SECRET_KEY` availability
- Proxy tests show RuntimeWarning about unawaited coroutines → expected from mocked async methods in sync test teardown, not a failure

## Requirements Proved By This UAT

- APP-03 (App SDK) — partially: SDK package built and functional, clients shape correct HTTP requests, decorators register handlers. Full validation requires permission enforcement (S05).
- APP-04 (IPC via HTTP/UDS) — partially: platform proxies to app UDS with JWT auth, real subprocess round-trip proven. Full validation requires admin visibility (S03) and frontend fragment loading (S04).

## Not Proven By This UAT

- Permission enforcement on SDK clients (S05)
- Automatic token rotation (S05 scheduler)
- Admin portal visibility of app status/tokens (S03)
- Frontend fragment loading through the proxy chain (S04)
- Docker/nginx integration for `/app/{appId}/` routing (S03)
- Large response streaming through proxy (deferred, non-streaming v1)

## Notes for Tester

- PyJWT warnings about HMAC key length < 32 bytes are expected in dev/test environments — the dev-mode secret is shorter than recommended. Not a security issue in production where `SECRET_KEY` should be a proper random string.
- The integration tests use a module-scoped subprocess — all 7 tests share one app process. This is intentional for speed (~1.5s total).
- `RuntimeWarning: coroutine was never awaited` in proxy tests is a test artifact from mocking async methods — not a real issue.
