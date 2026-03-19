---
estimated_steps: 8
estimated_files: 7
---

# T02: Build google-calendar app scaffold, auth module, and gcal client with full unit tests

**Slice:** S02 — Google OAuth 2.0 + Calendar List
**Milestone:** M018

## Description

Creates the complete `apps/google-calendar/` directory structure with manifest, the OAuth auth module (pure functions for URL building, code exchange, token storage/refresh, connection status), and the Google Calendar REST client (calendar list fetch with pagination, auth headers, 401→refresh→retry). All logic is in pure-function modules testable with MockHttpClient/MockStateClient — no runtime needed.

Follows the established pattern from `apps/linear-sync/` closely. The auth module mirrors `linear-sync/services/auth.py` but adapted for Google's OAuth endpoints and token format. The gcal client mirrors `linear-sync/services/linear_client.py` but uses REST (not GraphQL) against Google Calendar API v3.

## Steps

1. **Create `apps/google-calendar/manifest.yaml`** following the linear-sync manifest pattern:
   - `appId: "google-calendar"`, `name: "Google Calendar Sync"`, `version: "0.1.0"`
   - Permissions: commands (`object.create`, `object.patch`, `body.set`, `edge.create`), sparql read, backgroundTasks, network (`www.googleapis.com`, `oauth2.googleapis.com`, `accounts.google.com`)
   - Tasks: `poll-events` (15m interval), `push-changes` (15m interval) — skeleton for S03/S04
   - UI page: `id: "settings"`, `path: "/settings"`, `label: "Google Calendar"`, `icon: "calendar"`, `nav: "apps"`, `fragment: "connect"`
   - Frontend: `staticDir: "frontend/static"`, css: `["styles.css"]`

2. **Create `apps/google-calendar/requirements.txt`** — empty or minimal (SDK provides httpx, yaml).

3. **Create `apps/google-calendar/services/__init__.py`** — empty package init.

4. **Create `apps/google-calendar/services/auth.py`** with these pure helper functions:
   - Constants: `GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"`, `GOOGLE_TOKEN_URL` (env-overridable via `GOOGLE_TOKEN_URL`, default `"https://oauth2.googleapis.com/token"`), `GOOGLE_SCOPES = "https://www.googleapis.com/auth/calendar.events"`, `AUTH_STATE_KEYS` tuple
   - `build_google_authorize_url(client_id, redirect_uri, state)` → URL with params: `client_id`, `redirect_uri`, `response_type=code`, `scope=GOOGLE_SCOPES`, `access_type=offline`, `prompt=consent`, `state`
   - `exchange_code(http_client, code, client_id, client_secret, redirect_uri)` → POST to GOOGLE_TOKEN_URL with form-encoded body, returns dict with `access_token`, `refresh_token`, `expires_in`. Raises `GCalAuthError` on non-200.
   - `refresh_access_token(http_client, refresh_token, client_id, client_secret)` → POST to GOOGLE_TOKEN_URL with `grant_type=refresh_token`, returns dict with `access_token`, `expires_in`. Raises `GCalAuthError` on failure.
   - `refresh_if_expired(http_client, state_client, client_id, client_secret)` → reads `token_expiry` from state, compares against `now + 5min buffer`, calls `refresh_access_token` if expired, stores new token + expiry. Returns current access_token.
   - `store_auth_tokens(state_client, access_token, refresh_token, expires_in, google_email)` → stores all tokens plus computed `token_expiry` as ISO 8601 timestamp (`now + expires_in`), sets `auth_method` to `"oauth"`.
   - `get_connection_status(state_client)` → returns dict with `connected`, `auth_method`, `google_email`, `token_expiry`.
   - `clear_auth_state(state_client)` → sets all AUTH_STATE_KEYS to empty string.
   - Import `GCalAuthError` from `services.gcal_client` with try/except fallback (same pattern as linear auth.py importing LinearAuthError).

5. **Create `apps/google-calendar/services/gcal_client.py`** with:
   - `GCAL_BASE_URL` from env var `GCAL_API_URL` or default `"https://www.googleapis.com/calendar/v3"`
   - Exception classes: `GCalAPIError(message, status_code, response_body)`, `GCalAuthError(GCalAPIError)`, `GCalRateLimitError(GCalAPIError)` with `retry_after`
   - `GCalClient` class with `__init__(http_client, state_client, client_id, client_secret)`:
     - `_get_headers()` → reads `access_token` from state, returns `{"Authorization": "Bearer {token}", "Accept": "application/json"}`
     - `_request(method, url, **kwargs)` → makes request with auth headers, handles 401 (refresh token then retry once), 403, 429 (parse Retry-After), 500
     - `get_calendar_list()` → GET `{base}/users/me/calendarList`, handles pagination via `nextPageToken`, returns list of calendar dicts with `id`, `summary`, `primary`, `accessRole`

6. **Write `backend/tests/test_gcal_auth.py`** (~15 tests) following the `test_linear_auth.py` pattern:
   - Module loading via importlib from `apps/google-calendar/services/`
   - MockHttpClient, MockStateClient (same as linear tests)
   - Test classes: `TestBuildGoogleAuthorizeUrl` (basic URL, params, access_type=offline present, prompt=consent present), `TestExchangeCode` (success, failure, missing fields), `TestRefreshAccessToken` (success, failure), `TestRefreshIfExpired` (not expired skips refresh, expired triggers refresh, stores new token), `TestStoreAuthTokens` (stores all keys, computes token_expiry), `TestGetConnectionStatus` (connected, disconnected), `TestClearAuthState` (all keys cleared)

7. **Write `backend/tests/test_gcal_client.py`** (~10 tests) following `test_linear_client.py` pattern:
   - Module loading via importlib from `apps/google-calendar/services/`
   - Test classes: `TestGCalClient` — calendar list fetch (single page, paginated), auth header injection, 401→refresh→retry, 403 error, 429 rate limit with retry_after, 500 server error, empty calendar list

8. **Run all tests** to confirm everything passes: `cd backend && python -m pytest tests/test_gcal_auth.py tests/test_gcal_client.py -v` and `cd backend && python -m pytest tests/ -x -q`.

## Must-Haves

- [ ] `manifest.yaml` valid with correct appId, permissions, tasks, UI page, icon
- [ ] `auth.py` has all 7 helper functions with correct Google OAuth endpoints
- [ ] `auth.py` includes `access_type=offline` and `prompt=consent` in authorize URL
- [ ] `auth.py` stores `token_expiry` as ISO 8601 timestamp (not raw `expires_in`)
- [ ] `gcal_client.py` fetches calendar list with pagination support
- [ ] `gcal_client.py` handles 401→refresh→retry transparently
- [ ] `test_gcal_auth.py` has ≥15 passing tests
- [ ] `test_gcal_client.py` has ≥10 passing tests
- [ ] All existing backend tests still pass

## Verification

- `cd backend && python -m pytest tests/test_gcal_auth.py -v` — ≥15 tests pass
- `cd backend && python -m pytest tests/test_gcal_client.py -v` — ≥10 tests pass
- `cd backend && python -m pytest tests/ -x -q` — full suite passes, no regressions

## Observability Impact

- Signals added: `google_calendar.auth` logger (INFO on token exchange/refresh/clear, WARNING on failures)
- How a future agent inspects this: `get_connection_status()` returns structured dict; `GCalAuthError`/`GCalAPIError` carry status_code + response_body
- Failure state exposed: token exchange failure status code, refresh failure reason, connection status dict

## Inputs

- T01 completed: proxy query param fix and HttpClient domain enforcement fix landed
- `apps/linear-sync/manifest.yaml` — reference manifest structure
- `apps/linear-sync/services/auth.py` — reference auth module pattern (200 lines)
- `apps/linear-sync/services/linear_client.py` — reference client pattern (395 lines)
- `backend/tests/test_linear_auth.py` — reference test pattern with importlib loading, MockHttpClient, MockStateClient
- `backend/tests/test_linear_client.py` — reference client test pattern
- S02-RESEARCH.md constraints: Google token endpoint `https://oauth2.googleapis.com/token`, authorize endpoint `https://accounts.google.com/o/oauth2/v2/auth`, `access_type=offline` required for refresh token, `prompt=consent` required for re-auth refresh token, calendar list at `GET .../users/me/calendarList`

## Expected Output

- `apps/google-calendar/manifest.yaml` — valid app manifest
- `apps/google-calendar/requirements.txt` — dependency file (minimal)
- `apps/google-calendar/services/__init__.py` — package init
- `apps/google-calendar/services/auth.py` — OAuth helper module (~200 lines)
- `apps/google-calendar/services/gcal_client.py` — REST client module (~200 lines)
- `backend/tests/test_gcal_auth.py` — ≥15 unit tests
- `backend/tests/test_gcal_client.py` — ≥10 unit tests
