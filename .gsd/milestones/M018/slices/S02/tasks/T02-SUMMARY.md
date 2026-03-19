---
id: T02
parent: S02
milestone: M018
provides:
  - google-calendar app scaffold with manifest
  - OAuth auth module with all 7 helper functions (authorize URL, code exchange, refresh, refresh_if_expired, store tokens, connection status, clear)
  - GCal REST client with calendar list pagination, auth headers, 401→refresh→retry
  - 23 auth unit tests + 12 client unit tests
key_files:
  - apps/google-calendar/manifest.yaml
  - apps/google-calendar/services/auth.py
  - apps/google-calendar/services/gcal_client.py
  - backend/tests/test_gcal_auth.py
  - backend/tests/test_gcal_client.py
key_decisions:
  - Token expiry stored as ISO 8601 timestamp (computed from expires_in at storage time) rather than raw seconds — enables direct comparison without epoch math
  - GCal client uses REST with URL-appended pageToken (not query params dict) matching Google Calendar API v3 pagination pattern
  - auth.py imports GCalAuthError from gcal_client with try/except fallback chain matching linear-sync pattern for importlib test compatibility
patterns_established:
  - Google OAuth auth module mirrors linear-sync auth.py structure with added refresh_if_expired and token_expiry tracking
  - REST client with _request() method handles all HTTP status codes centrally (vs linear's GraphQL-specific query method)
observability_surfaces:
  - google_calendar.auth logger — INFO on token exchange/refresh/clear, WARNING on failures
  - google_calendar.client logger — INFO on token refresh
  - get_connection_status() returns structured dict with connected, auth_method, google_email, token_expiry
  - GCalAuthError/GCalAPIError carry status_code + response_body for diagnosis
duration: 25m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: Build google-calendar app scaffold, auth module, and gcal client with full unit tests

**Created google-calendar app with OAuth auth module (7 helpers), GCal REST client with paginated calendar list and 401→refresh→retry, plus 35 passing unit tests.**

## What Happened

Built the complete `apps/google-calendar/` directory following the linear-sync reference pattern:

1. **Manifest** — `appId: "google-calendar"` with network permissions for `www.googleapis.com`, `oauth2.googleapis.com`, `accounts.google.com`. Tasks for `poll-events` and `push-changes` (15m interval skeletons for S03/S04). Settings UI page with `calendar` icon.

2. **Auth module** (`services/auth.py`) — 7 pure helper functions:
   - `build_google_authorize_url()` — includes `access_type=offline`, `prompt=consent`, `scope=calendar.events`
   - `exchange_code()` — POST to Google token endpoint with form-encoded body
   - `refresh_access_token()` — POST with `grant_type=refresh_token`
   - `refresh_if_expired()` — reads token_expiry from state, 5-minute buffer, auto-refreshes and stores
   - `store_auth_tokens()` — stores all tokens + computes token_expiry as ISO 8601
   - `get_connection_status()` — returns structured dict
   - `clear_auth_state()` — sets all AUTH_STATE_KEYS to empty string

3. **GCal client** (`services/gcal_client.py`) — REST client with:
   - `GCalClient` class with `_get_headers()`, `_request()`, `_handle_token_refresh()`
   - `get_calendar_list()` — pagination via `nextPageToken`, returns normalized dicts
   - Exception hierarchy: `GCalAPIError` → `GCalAuthError`, `GCalRateLimitError`
   - 401→refresh→retry (single attempt, no infinite loop)
   - Base URL overridable via `GCAL_API_URL` env var for testing

4. **Tests** — 23 auth tests + 12 client tests using importlib loading pattern with MockHttpClient/MockStateClient.

## Verification

- `test_gcal_auth.py` — 23 tests passed (URL construction, code exchange, token refresh, refresh_if_expired with expiry buffer, token storage with ISO 8601, connection status, clear)
- `test_gcal_client.py` — 12 tests passed (calendar list single/paginated/empty, auth header injection, 401→refresh→retry, no infinite loop, 403/429/500 error handling)
- Full backend suite — 1498 tests passed, zero failures

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_gcal_auth.py -v` | 0 | ✅ pass | 7.4s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_gcal_client.py -v` | 0 | ✅ pass | 3.4s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/ -x -q` | 0 | ✅ pass | 10.1s |
| 4 | `cd backend && .venv/bin/python -m pytest tests/test_app_proxy_query_params.py -v` | 0 | ✅ pass | 4.3s |

## Diagnostics

- `get_connection_status(state_client)` — returns `{connected: bool, auth_method, google_email, token_expiry}` for runtime inspection
- `GCalAuthError` / `GCalAPIError` exceptions carry `status_code` and `response_body` for debugging failed API calls
- `google_calendar.auth` and `google_calendar.client` loggers provide INFO/WARNING traces
- Token expiry stored as ISO 8601 — can be compared against `datetime.now(timezone.utc)` directly
- Access tokens, refresh tokens, and client secrets are never logged

## Deviations

- Test count exceeds plan estimates: 23 auth tests (plan: ≥15) and 12 client tests (plan: ≥10) — more thorough coverage of edge cases.

## Known Issues

None.

## Files Created/Modified

- `apps/google-calendar/manifest.yaml` — app manifest with permissions, tasks, UI page
- `apps/google-calendar/requirements.txt` — minimal dependency file
- `apps/google-calendar/services/__init__.py` — package init
- `apps/google-calendar/services/auth.py` — OAuth helper module (7 functions, ~250 lines)
- `apps/google-calendar/services/gcal_client.py` — REST client module (~280 lines)
- `backend/tests/test_gcal_auth.py` — 23 auth unit tests
- `backend/tests/test_gcal_client.py` — 12 client unit tests
