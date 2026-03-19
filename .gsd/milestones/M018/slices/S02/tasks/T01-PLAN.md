---
estimated_steps: 6
estimated_files: 4
---

# T01: Fix app proxy query-param forwarding and HttpClient domain enforcement

**Slice:** S02 — Google OAuth 2.0 + Calendar List
**Milestone:** M018

## Description

Two platform bugs block OAuth and external HTTP for all sync apps. The app proxy at `backend/app/apps/proxy.py` constructs the target URL without appending the request's query string, so an OAuth callback like `?code=xxx&state=yyy` arrives at the app subprocess with no parameters. The SDK's `HttpClient` domain enforcement in `backend/sdk/sempkm_app_sdk/context.py` treats a manifest's `network` list (e.g., `["api.linear.app"]`) as a dict due to an `isinstance` check, resulting in `allowed_domains=[]` which blocks all external HTTP.

Both are one-line fixes with regression tests. These must land first because every subsequent task depends on working query param forwarding (OAuth callback) and external HTTP (Google API calls).

## Steps

1. Read `backend/app/apps/proxy.py` and fix the `target_url` construction on ~line 63. When `request.url.query` is non-empty, append `?{request.url.query}` to the target URL. The fix should handle the case where query is empty (no `?` appended).
2. Read `backend/sdk/sempkm_app_sdk/context.py` ~line 136. Change `else []` to `else network` so that when the manifest's `network` value is already a list (not a dict), it's used directly as `allowed_domains`.
3. Write `backend/tests/test_app_proxy_query_params.py` — regression test that constructs a mock `Request` with query parameters, calls `AppProxy.forward()`, and asserts the query string arrives in the target URL sent to the upstream. Use httpx mock or monkeypatch the client's `request()` method to capture the URL. Test both with and without query params.
4. Write `backend/tests/test_sdk_network_permissions.py` — test that `AppContext.http` with a list-type `network` permission (matching real manifests like `["api.linear.app"]`) produces an `HttpClient` with the correct `allowed_domains`. Also test that dict-type `network: {domains: [...]}` still works.
5. Run all existing tests to verify no regressions: `cd backend && python -m pytest tests/ -x -q`.
6. Verify the proxy fix doesn't break existing Linear/GitHub sync apps by checking that the change only *adds* query params that were previously dropped — backward compatible.

## Must-Haves

- [ ] `proxy.py` appends query string to target_url when present
- [ ] `context.py` passes list-type network permissions through to HttpClient
- [ ] Regression test for proxy query param forwarding passes
- [ ] Regression test for SDK network permission parsing passes
- [ ] All existing backend tests pass (no regressions)

## Verification

- `cd backend && python -m pytest tests/test_app_proxy_query_params.py -v` — all tests pass
- `cd backend && python -m pytest tests/test_sdk_network_permissions.py -v` — all tests pass
- `cd backend && python -m pytest tests/ -x -q` — full suite passes

## Inputs

- `backend/app/apps/proxy.py` — current proxy implementation, bug at line ~63 (`target_url = f"http://localhost/{path}"` drops query string)
- `backend/sdk/sempkm_app_sdk/context.py` — current SDK context, bug at line ~136 (`else []` discards list-type network permissions)
- `backend/tests/test_linear_auth.py` — reference test pattern (importlib module loading, MockHttpClient, MockStateClient)

## Expected Output

- `backend/app/apps/proxy.py` — one-line fix appending query string
- `backend/sdk/sempkm_app_sdk/context.py` — one-line fix for network permission parsing
- `backend/tests/test_app_proxy_query_params.py` — new regression test file (~3-5 tests)
- `backend/tests/test_sdk_network_permissions.py` — new regression test file (~3-4 tests)

## Observability Impact

- **Proxy query forwarding:** No new logging — the existing `logger.warning` on connection failures covers the error path. The fix is transparent: query params now arrive at the app subprocess, observable via the app's own request logging.
- **SDK network permissions:** No new logging — the existing `PermissionError` raised by `HttpClient._check_domain()` provides domain enforcement visibility. A future agent can verify correct domain enforcement by inspecting `ctx.http._allowed_domains` in tests or via the `PermissionError` message which lists allowed domains.
- **Failure state:** Misconfigured network permissions surface as `PermissionError: HTTP request to domain 'X' is not permitted. Allowed domains: [...]` — the domains list in the error message confirms whether list-type parsing worked.
