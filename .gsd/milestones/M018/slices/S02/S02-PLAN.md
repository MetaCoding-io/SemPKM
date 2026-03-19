# S02: Google OAuth 2.0 + Calendar List

**Goal:** User installs the google-calendar app, completes an OAuth consent flow through the app proxy, and sees their Google Calendar list with selection checkboxes. Auth tokens stored via StateClient with automatic refresh.
**Demo:** Install google-calendar app → enter client ID/secret → click "Connect with Google" → OAuth redirect → callback returns authorization code → tokens exchanged and stored → calendar list displayed with checkboxes → disconnect clears state.

## Must-Haves

- App proxy forwards query parameters on OAuth callback (platform bug fix)
- HttpClient domain enforcement correctly parses list-type network permissions (platform bug fix)
- `apps/google-calendar/` directory with valid manifest, app.py, services, templates
- OAuth helpers: authorize URL builder, code exchange, token storage, refresh, connection status, clear
- GCal REST client: calendar list fetch with pagination, auth header injection, 401→refresh→retry
- Connect flow: client ID/secret form → OAuth redirect → callback → token exchange → calendar list
- Calendar list UI with checkboxes for selection, persisted via StateClient
- Disconnect button clears all auth state
- ≥25 unit tests covering auth helpers, gcal client, and platform regression

## Proof Level

- This slice proves: integration (OAuth code exchange through real app proxy path, token storage/refresh, calendar list fetch)
- Real runtime required: no (all verified via unit tests with mocked HTTP + state clients)
- Human/UAT required: no

## Verification

- `cd backend && python -m pytest tests/test_app_proxy_query_params.py -v` — proxy query param forwarding regression test passes
- `cd backend && python -m pytest tests/test_gcal_auth.py -v` — ≥15 auth helper tests pass (URL construction, code exchange, token storage, refresh, connection status, clear)
- `cd backend && python -m pytest tests/test_gcal_client.py -v` — ≥10 gcal client tests pass (calendar list, auth header, 401 retry, error handling)
- All existing tests still pass: `cd backend && python -m pytest tests/ -x -q`
- OAuth diagnostic: `get_connection_status()` returns `connected: True/False` with `auth_method`, `google_email`, and `token_expiry` — inspectable via state client

## Observability / Diagnostics

- Runtime signals: `google_calendar.auth` logger with INFO on token exchange/refresh/clear, WARNING on failures
- Inspection surfaces: `get_connection_status()` returns structured dict with connected flag, auth method, google email, token expiry timestamp
- Failure visibility: `GCalAuthError` / `GCalAPIError` exceptions with status_code + response_body; token_expiry stored as ISO 8601 for easy comparison
- Redaction constraints: access_token, refresh_token, client_secret never logged — only auth_method and google_email

## Integration Closure

- Upstream surfaces consumed: `backend/app/apps/proxy.py` (query param fix), `backend/sdk/sempkm_app_sdk/context.py` (domain enforcement fix), SDK StateClient/HttpClient/App class
- New wiring introduced: `apps/google-calendar/` app directory registered via manifest, proxy query param forwarding
- What remains before the milestone is truly usable end-to-end: S03 (pull sync + field mapping), S04 (RSVP push + recurrence), S05 (E2E tests + guide)

## Tasks

- [x] **T01: Fix app proxy query-param forwarding and HttpClient domain enforcement** `est:45m`
  - Why: Two platform bugs block all OAuth callback flows and external HTTP from sync apps. The proxy drops query parameters (authorization code lost on callback), and the HttpClient domain parser discards list-type network permissions (blocks all external API calls). Both are one-line fixes but need regression tests.
  - Files: `backend/app/apps/proxy.py`, `backend/sdk/sempkm_app_sdk/context.py`, `backend/tests/test_app_proxy_query_params.py`, `backend/tests/test_sdk_network_permissions.py`
  - Do: (1) Fix proxy.py line ~63 to append `request.url.query` to target_url when present. (2) Fix context.py line ~136 to use `else network` instead of `else []` for list-type network permissions. (3) Write regression tests for both fixes. (4) Run all existing tests to confirm no regressions.
  - Verify: `cd backend && python -m pytest tests/test_app_proxy_query_params.py tests/test_sdk_network_permissions.py -v` passes; `cd backend && python -m pytest tests/ -x -q` shows no regressions
  - Done when: Both bug fixes committed with regression tests, all existing tests pass

- [x] **T02: Build google-calendar app scaffold, auth module, and gcal client with full unit tests** `est:2h`
  - Why: Creates the core app structure and all backend logic needed for OAuth and calendar list fetching. The auth module and gcal client are pure-function modules testable entirely with mocks — no runtime needed. Following the linear-sync/github-sync pattern closely.
  - Files: `apps/google-calendar/manifest.yaml`, `apps/google-calendar/requirements.txt`, `apps/google-calendar/services/__init__.py`, `apps/google-calendar/services/auth.py`, `apps/google-calendar/services/gcal_client.py`, `backend/tests/test_gcal_auth.py`, `backend/tests/test_gcal_client.py`
  - Do: (1) Create manifest.yaml following linear-sync pattern with `appId: "google-calendar"`, network permissions for `googleapis.com`/`accounts.google.com` domains, tasks for `poll-events`/`push-changes`, settings page with `calendar` Lucide icon. (2) Create `services/auth.py` with: `build_google_authorize_url()` (includes `access_type=offline`, `prompt=consent`, `scope=calendar.events`), `exchange_code()`, `refresh_access_token()`, `refresh_if_expired()` (checks token_expiry with 5-min buffer), `store_auth_tokens()` (stores access_token, refresh_token, token_expiry as ISO 8601, auth_method, google_email), `get_connection_status()`, `clear_auth_state()`. (3) Create `services/gcal_client.py` with `GCalClient` class: `get_calendar_list()` with pagination via `nextPageToken`, auth header injection via `_get_headers()`, 401→refresh→retry, exception classes (`GCalAPIError`, `GCalAuthError`, `GCalRateLimitError`). Base URL from env var `GCAL_API_URL` for testing. (4) Write `test_gcal_auth.py` (~15 tests) following test_linear_auth.py pattern with importlib loading, MockHttpClient, MockStateClient. (5) Write `test_gcal_client.py` (~10 tests) following test_linear_client.py pattern.
  - Verify: `cd backend && python -m pytest tests/test_gcal_auth.py tests/test_gcal_client.py -v` — all ≥25 tests pass
  - Done when: Auth module and gcal client fully tested; manifest validates; all pure-function OAuth helpers work with mock clients

- [x] **T03: Build app routes, templates, and connect flow** `est:1h30m`
  - Why: Wires auth module and gcal client into HTTP route handlers and user-facing templates. Completes the full connect → OAuth → calendar list → select → disconnect flow. This is the integration layer that makes S02 demoable.
  - Files: `apps/google-calendar/app.py`, `apps/google-calendar/frontend/templates/connect.html`, `apps/google-calendar/frontend/templates/connect_status.html`, `apps/google-calendar/frontend/static/styles.css`
  - Do: (1) Create `app.py` with route handlers following linear-sync pattern: `/_fragments/connect` (GET — render connect form or status), `/_fragments/connect/google` (POST — build authorize URL with state param, redirect), `/_fragments/oauth-callback` (GET — exchange code, store tokens, fetch email via userinfo or calendarList, redirect to connect), `/_fragments/connect/disconnect` (POST — clear auth state, re-render connect form), `/_fragments/settings/calendars` (POST — save selected calendar IDs to state). (2) Create `connect.html` with client ID/secret inputs and "Connect with Google" button. Include instructions for Google Cloud Console setup. All htmx URLs use `/app/google-calendar/` prefix (per KNOWLEDGE.md). (3) Create `connect_status.html` showing connected Google email, calendar list with checkboxes (loaded from gcal client), save button for selection, disconnect button. (4) Create `styles.css` adapted from linear-sync styles. (5) Ensure state param is generated, stored, and verified on callback for CSRF protection. (6) Redirect URI is `http://localhost:3000/app/google-calendar/_fragments/oauth-callback`.
  - Verify: All existing tests still pass: `cd backend && python -m pytest tests/ -x -q`. Template files render without Jinja2 syntax errors (verified by importing and calling render_template in a test or manually).
  - Done when: Complete connect flow implemented with CSRF-safe OAuth, calendar list display with checkboxes, disconnect, and styling. All htmx URLs properly prefixed.

## Files Likely Touched

- `backend/app/apps/proxy.py` — query param forwarding fix
- `backend/sdk/sempkm_app_sdk/context.py` — domain enforcement fix
- `backend/tests/test_app_proxy_query_params.py` — proxy regression test (new)
- `backend/tests/test_sdk_network_permissions.py` — SDK regression test (new)
- `apps/google-calendar/manifest.yaml` — app manifest (new)
- `apps/google-calendar/requirements.txt` — dependencies (new)
- `apps/google-calendar/services/__init__.py` — package init (new)
- `apps/google-calendar/services/auth.py` — OAuth helpers (new)
- `apps/google-calendar/services/gcal_client.py` — REST client (new)
- `apps/google-calendar/app.py` — route handlers (new)
- `apps/google-calendar/frontend/templates/connect.html` — connect form (new)
- `apps/google-calendar/frontend/templates/connect_status.html` — status page (new)
- `apps/google-calendar/frontend/static/styles.css` — app CSS (new)
- `backend/tests/test_gcal_auth.py` — auth unit tests (new)
- `backend/tests/test_gcal_client.py` — client unit tests (new)
