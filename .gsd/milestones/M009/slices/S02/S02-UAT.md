# S02: App SDK & IPC Proxy — UAT

**Milestone:** M009
**Written:** 2026-03-18

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S02 delivers backend-only infrastructure (SDK package, proxy, JWT tokens) with no user-visible UI. All contracts are proven through 92 automated tests including 8 real subprocess integration tests. No browser or Docker stack needed — pure Python pytest verification.

## Preconditions

- Working directory: the M009 worktree at `.gsd/worktrees/M009/`
- Backend venv has SDK installed: `cd backend && uv pip install -e sdk/` (already done during task execution)
- No Docker stack needed — all tests use in-process mocks or real subprocesses on localhost

## Smoke Test

Run the full S02 test suite:

```bash
cd backend && .venv/bin/pytest tests/test_app_tokens.py tests/test_sdk_app.py tests/test_app_proxy.py tests/test_sdk_integration.py -v
```

Expected: 92 tests pass, 0 failures, <3 seconds.

## Test Cases

### 1. JWT Token Round-Trip

1. `cd backend && .venv/bin/pytest tests/test_app_tokens.py -v -k "test_produces_valid_jwt or test_valid_token_returns_claims"`
2. **Expected:** Both pass — token generates with correct claims structure (`sub: "app:{id}"`, `permissions`, `iat`, `exp`) and round-trips through validation.

### 2. JWT Grace Period for Token Renewal

1. `cd backend && .venv/bin/pytest tests/test_app_tokens.py -v -k "grace"`
2. **Expected:** 5 tests pass — expired-within-grace returns claims, expired-beyond-grace returns None, no grace by default, grace with tampered/wrong-secret returns None.

### 3. SDK App Class Decorator Registration

1. `cd backend && .venv/bin/pytest tests/test_sdk_app.py -v -k "TestDecoratorRegistration"`
2. **Expected:** 8 tests pass — route, task, and all 4 lifecycle decorators register handlers correctly, multiple routes supported.

### 4. SDK ASGI App with System Endpoints

1. `cd backend && .venv/bin/pytest tests/test_sdk_app.py -v -k "TestBuildAsgiApp"`
2. **Expected:** 10 tests pass — `/_health` returns 200 without auth, `/_lifecycle/{hook}` dispatches registered handlers (sync and async), unregistered hooks return 404, `/_tasks/{task_id}` dispatches handlers, user routes callable.

### 5. SDK Token Validation on System Endpoints

1. `cd backend && .venv/bin/pytest tests/test_sdk_app.py -v -k "TestTokenValidation"`
2. **Expected:** 5 tests pass — lifecycle/task endpoints require token (403 without), reject wrong token (403), accept correct token (200).

### 6. SDK AppContext with Lazy Client Initialization

1. `cd backend && .venv/bin/pytest tests/test_sdk_app.py -v -k "TestAppContext"`
2. **Expected:** 10 tests pass — context has correct fields, 5 client properties return correct types, commands/graph/state/settings share platform client, http client is separate, template rendering works, close shuts down platform client.

### 7. SDK Client Stubs Shape Correct HTTP Requests

1. `cd backend && .venv/bin/pytest tests/test_sdk_app.py -v -k "TestCommandClient or TestGraphClient or TestStateClient or TestSettingsClient"`
2. **Expected:** 8 tests pass — CommandClient POSTs to /api/commands, GraphClient POSTs to /api/sparql, StateClient constructs correct SPARQL for get/set with app-scoped graph IRI, SettingsClient delegates to StateClient with prefix.

### 8. AppProxy Forward and Error Handling

1. `cd backend && .venv/bin/pytest tests/test_app_proxy.py -v -k "TestAppProxy"`
2. **Expected:** 7 tests pass — correct method/path forwarded, token header injected, missing socket raises error, connection error raises error, body copied, client cleanup works.

### 9. Proxy Router Status Checks

1. `cd backend && .venv/bin/pytest tests/test_app_proxy.py -v -k "TestProxyRouter"`
2. **Expected:** 4 tests pass — running app proxied successfully, non-running app returns 503, unknown app returns 404, unreachable app returns 502.

### 10. Token Renewal Endpoint

1. `cd backend && .venv/bin/pytest tests/test_app_proxy.py -v -k "TestTokenRenewalRouter"`
2. **Expected:** 5 tests pass — valid token renews, expired-within-grace (300s) renews, expired-beyond-grace rejected (401), missing auth header rejected, invalid token rejected.

### 11. Manager Token Lifecycle

1. `cd backend && .venv/bin/pytest tests/test_app_proxy.py -v -k "TestManagerTokenHandling"`
2. **Expected:** 5 tests pass — start generates token and appends to subprocess cmd, get_token returns stored token, get_token returns None for unknown app, stop clears token, install includes SDK install step (3 uv calls).

### 12. Real Subprocess Integration Round-Trip

1. `cd backend && .venv/bin/pytest tests/test_sdk_integration.py -v`
2. **Expected:** 8 tests pass — real SDK runner starts on UDS, `/_health` returns 200, fragment route returns HTML, lifecycle startup dispatches, task dispatches, missing token → 401/403, wrong token → 403.

## Edge Cases

### Token Expiry Boundary

1. `cd backend && .venv/bin/pytest tests/test_app_tokens.py -v -k "test_expired_token_returns_none and not grace"`
2. **Expected:** Expired token returns None (not an exception). Validation is fail-safe.

### Garbage Token Input

1. `cd backend && .venv/bin/pytest tests/test_app_tokens.py -v -k "test_completely_garbage_token"`
2. **Expected:** Non-JWT strings return None gracefully. No exceptions leak.

### Runner with Missing Manifest

1. `cd backend && .venv/bin/pytest tests/test_sdk_app.py -v -k "test_main_missing_manifest"`
2. **Expected:** Runner exits code 1 with descriptive error. No crash.

### Runner with Bad Entrypoint

1. `cd backend && .venv/bin/pytest tests/test_sdk_app.py -v -k "test_main_invalid_entrypoint or test_main_import_error"`
2. **Expected:** Both return exit code 1 with descriptive error messages. Invalid format and import failures handled separately.

## Failure Signals

- Any test in `test_sdk_integration.py` failing with "socket file not found" → subprocess didn't start; check stderr capture in the test fixture
- Any proxy test failing with `httpx.ConnectError` → UDS transport not configured correctly
- SDK tests failing with 422 → route handler missing `request: Request` type annotation
- Token tests with `InsecureKeyLengthWarning` → expected for test secrets (30 bytes), not a failure — production keys are 64 bytes

## Requirements Proved By This UAT

- APP-02 — subprocess lifecycle proven end-to-end with SDK runner (integration tests)
- APP-03 — SDK package with App class, 5 clients, lifecycle decorators, runner (unit + integration tests)
- APP-04 — IPC via HTTP/UDS with JWT auth and token renewal (proxy + integration tests)

## Not Proven By This UAT

- Permission enforcement on SDK clients (S05)
- Admin portal showing app proxy status (S03)
- Frontend fragment loading through the proxy (S04)
- Scheduler triggering tasks via the proxy (S05)
- Docker/nginx routing to `/app/{appId}/` (S03)
- Automatic token rotation by the SDK (not yet implemented)

## Notes for Tester

- The `InsecureKeyLengthWarning` from PyJWT is expected in tests (short test secrets). Not a bug.
- Integration tests start a real subprocess and wait for a socket file — on slow machines, the 10-second timeout might need increasing. If `test_sdk_integration.py` times out, check that the backend venv has the SDK installed (`uv pip install -e sdk/`).
- The SDK's shared-secret token validation (string comparison, not JWT decode) is a deliberate simplification (D173). Apps don't inspect their own permissions from the token — that's the platform's responsibility.
