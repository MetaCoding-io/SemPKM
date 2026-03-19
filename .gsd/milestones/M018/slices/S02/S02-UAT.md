# S02: Google OAuth 2.0 + Calendar List — UAT

**Milestone:** M018
**Written:** 2026-03-18

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All OAuth logic, token management, and calendar list fetching are pure functions testable with mocks. No live Google API or Docker runtime needed — 47 unit tests cover the complete auth and client surface. Route handlers and templates are validated via Jinja2 parse checks and code review.

## Preconditions

- Backend venv exists: `backend/.venv/bin/python` is functional
- All test dependencies installed in venv
- Working directory is project root `/home/james/Code/SemPKM`

## Smoke Test

```bash
cd backend && .venv/bin/python -m pytest tests/test_gcal_auth.py tests/test_gcal_client.py tests/test_app_proxy_query_params.py tests/test_sdk_network_permissions.py -v
```

All 47 tests pass (23 auth + 12 client + 5 proxy + 7 SDK).

## Test Cases

### 1. App proxy forwards query parameters on OAuth callback

1. Run `cd backend && .venv/bin/python -m pytest tests/test_app_proxy_query_params.py -v`
2. Verify `test_query_params_forwarded` passes — confirms `?code=abc&state=xyz` arrives at app subprocess
3. Verify `test_encoded_query_params_preserved` passes — confirms `redirect_uri=http%3A%2F%2Flocalhost` survives forwarding
4. **Expected:** 5/5 tests pass

### 2. SDK correctly parses list-type network permissions

1. Run `cd backend && .venv/bin/python -m pytest tests/test_sdk_network_permissions.py -v`
2. Verify `test_list_type_network_permissions_parsed` passes — `["api.google.com"]` becomes `allowed_domains = ["api.google.com"]`
3. Verify `test_domain_enforcement_end_to_end` passes — request to permitted domain succeeds, non-permitted raises PermissionError
4. **Expected:** 7/7 tests pass

### 3. OAuth authorize URL construction

1. Run `cd backend && .venv/bin/python -m pytest tests/test_gcal_auth.py::TestBuildGoogleAuthorizeUrl -v`
2. Verify URL contains `access_type=offline` (gets refresh token)
3. Verify URL contains `prompt=consent` (forces consent screen every time)
4. Verify URL contains `scope=https://www.googleapis.com/auth/calendar.events`
5. Verify redirect_uri is properly URL-encoded
6. **Expected:** 5/5 tests in this class pass

### 4. OAuth code exchange and token storage

1. Run `cd backend && .venv/bin/python -m pytest tests/test_gcal_auth.py::TestExchangeCode tests/test_gcal_auth.py::TestStoreAuthTokens -v`
2. Verify `test_success_returns_token_dict` — mock 200 response returns access_token, refresh_token, expires_in
3. Verify `test_failure_raises_auth_error` — mock 400 response raises GCalAuthError with status_code
4. Verify `test_stores_all_fields` — all 5 auth keys stored in MockStateClient
5. Verify `test_computes_token_expiry_as_iso8601` — expires_in (3600) converted to future ISO 8601 timestamp
6. **Expected:** 7/7 tests pass

### 5. Token refresh and expiry handling

1. Run `cd backend && .venv/bin/python -m pytest tests/test_gcal_auth.py::TestRefreshIfExpired -v`
2. Verify `test_not_expired_skips_refresh` — valid token with future expiry makes zero HTTP calls
3. Verify `test_expired_triggers_refresh` — expired token triggers refresh and stores new token
4. Verify `test_within_buffer_triggers_refresh` — token expiring within 5 minutes triggers early refresh
5. Verify `test_no_refresh_token_raises` — missing refresh_token raises GCalAuthError (no silent failure)
6. **Expected:** 4/4 tests pass

### 6. Calendar list pagination and error handling

1. Run `cd backend && .venv/bin/python -m pytest tests/test_gcal_client.py -v`
2. Verify `test_single_page_returns_calendars` — single-page response returns normalized calendar dicts
3. Verify `test_paginated_calendar_list` — follows `nextPageToken` across 2 pages, concatenates results
4. Verify `test_empty_calendar_list` — empty items array returns empty list (no crash)
5. Verify `test_401_triggers_refresh_and_retry` — 401 response → refresh → retry succeeds
6. Verify `test_no_infinite_refresh_loop` — 401 after refresh raises (no retry loop)
7. Verify `test_429_raises_rate_limit_with_retry_after` — GCalRateLimitError carries Retry-After header value
8. **Expected:** 12/12 tests pass

### 7. Connection status and disconnect

1. Run `cd backend && .venv/bin/python -m pytest tests/test_gcal_auth.py::TestGetConnectionStatus tests/test_gcal_auth.py::TestClearAuthState -v`
2. Verify `test_connected_with_full_info` — returns `{connected: True, auth_method: "oauth", google_email: "...", token_expiry: "..."}`
3. Verify `test_disconnected_when_no_auth` — returns `{connected: False}` with no email or expiry
4. Verify `test_clears_all_auth_keys` — all 5 AUTH_STATE_KEYS set to empty string
5. **Expected:** 5/5 tests pass

### 8. Full backend regression

1. Run `cd backend && .venv/bin/python -m pytest tests/ -x -q`
2. **Expected:** 1498 tests pass, 0 failures, <15s

### 9. App manifest validates

1. Run `cd backend && .venv/bin/python -c "import yaml; m = yaml.safe_load(open('../apps/google-calendar/manifest.yaml')); assert m['appId'] == 'google-calendar'; assert 'www.googleapis.com' in [d if isinstance(d,str) else d for d in m['permissions']['network']]; print('OK')"`
2. **Expected:** Prints "OK" — manifest has correct appId and network permissions

### 10. Template syntax valid

1. Run `cd backend && .venv/bin/python -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('../apps/google-calendar/frontend/templates')); env.get_template('connect.html'); env.get_template('connect_status.html'); print('OK')"`
2. **Expected:** Prints "OK" — both templates parse without Jinja2 syntax errors

### 11. htmx URLs properly prefixed

1. Run `grep -n 'hx-\(get\|post\|delete\|put\)=' apps/google-calendar/frontend/templates/*.html apps/google-calendar/app.py | grep -v '/app/google-calendar/' | grep -v '#'`
2. **Expected:** No output — all htmx URLs use the `/app/google-calendar/` proxy prefix

## Edge Cases

### OAuth state mismatch (CSRF protection)

1. In `test_gcal_auth.py`, verify that callback with mismatched state param triggers WARNING log
2. The route handler in app.py checks `stored_state != returned_state` and returns an error page
3. **Expected:** Mismatched state → error response, not silent auth

### Missing refresh token on refresh attempt

1. `test_no_refresh_token_raises` verifies this
2. **Expected:** GCalAuthError raised with clear message, not None dereference

### Empty calendar list from Google

1. `test_empty_calendar_list` verifies GCalClient handles `{"items": []}` 
2. **Expected:** Returns empty list, no crash or index error

### 429 Rate limit without Retry-After header

1. `test_429_defaults_retry_after_to_60` verifies this
2. **Expected:** GCalRateLimitError.retry_after defaults to 60 seconds

## Failure Signals

- Any test failure in `test_gcal_auth.py` or `test_gcal_client.py` → auth module broken
- Any test failure in `test_app_proxy_query_params.py` → OAuth callbacks would fail for all apps
- Any test failure in `test_sdk_network_permissions.py` → external HTTP blocked for all apps with list-type permissions
- Regression in full suite (expected 1498) → platform side-effect from bug fixes
- Jinja2 template parse failure → template will crash at runtime when rendered

## Requirements Proved By This UAT

- GCAL-01 — Google OAuth 2.0 authentication: 23 auth tests prove authorize URL construction, code exchange, token refresh, expiry handling, storage, status, and clear
- GCAL-02 — Calendar list and selection: 12 client tests prove paginated calendar fetch, auth header injection, 401→refresh→retry, error handling; template UI provides selection checkboxes with state persistence

## Not Proven By This UAT

- Live OAuth code exchange against real Google servers (requires deployed instance with Google Cloud Console credentials)
- Calendar list rendering in a browser (templates validated syntactically, not visually)
- Token refresh triggered by actual Google API 401 (tested with mocked responses)
- E2E flow through Docker stack (deferred to S05 with mock Google Calendar API)

## Notes for Tester

- All tests run locally with no Docker dependency — `backend/.venv/bin/python -m pytest` is sufficient
- The proxy and SDK fixes are platform-wide — they affect all apps, not just google-calendar. The regression tests specifically cover the fixed edge cases.
- The `_make_client_with_creds` helper in app.py is the bridge between route handlers and the auth/client modules — it reads credentials from state for token-refresh-capable client construction.
