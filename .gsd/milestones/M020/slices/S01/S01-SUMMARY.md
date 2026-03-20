---
id: S01
parent: M020
milestone: M020
provides:
  - Outlook Calendar Sync app scaffold with Microsoft Identity Platform OAuth 2.0 auth, Graph API REST client, OAuth connect/disconnect flow, and calendar list/selection UI
requires: []
affects:
  - S02
key_files:
  - apps/outlook-calendar/manifest.yaml
  - apps/outlook-calendar/app.py
  - apps/outlook-calendar/services/__init__.py
  - apps/outlook-calendar/services/auth.py
  - apps/outlook-calendar/services/outlook_client.py
  - apps/outlook-calendar/frontend/templates/connect.html
  - apps/outlook-calendar/frontend/templates/connect_status.html
  - apps/outlook-calendar/frontend/templates/calendars.html
  - apps/outlook-calendar/frontend/static/styles.css
  - backend/tests/test_outlook_auth.py
  - backend/tests/test_outlook_client.py
key_decisions:
  - Microsoft Identity Platform OAuth 2.0 with /common/ tenant for multi-tenant support (D217)
  - Token refresh delegation to auth.py rather than inline in client — single module owns token lifecycle
  - Microsoft Graph @odata.nextLink pagination uses full URLs (not query params like Google's nextPageToken)
  - Default calendar name used as display identity since Graph doesn't expose email without User.Read scope
patterns_established:
  - Microsoft OAuth 2.0 flow requiring scope in both authorize and token exchange requests (unlike Google)
  - Refresh token rotation detection — store new refresh_token only when it differs from the old one
  - Env var overrides (OUTLOOK_TOKEN_URL, OUTLOOK_AUTH_URL, OUTLOOK_API_URL) for mock server testability
  - OutlookClient exception hierarchy: OutlookAPIError → OutlookAuthError (401/403) + OutlookRateLimitError (429)
  - Delta query pattern: get_events_delta() returns (events, delta_link) tuple for incremental sync
observability_surfaces:
  - "outlook.sync.auth" logger — INFO on token store/clear, WARNING on exchange/refresh failures with status code + body
  - "outlook.sync.client" logger — DEBUG for each REST request (method + URL), INFO on token refresh
  - get_connection_status() returns connected, auth_method, microsoft_email, token_expiry, token_preview
  - OutlookAuthError / OutlookRateLimitError carry status_code and response_body for structured diagnosis
drill_down_paths:
  - .gsd/milestones/M020/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M020/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M020/slices/S01/tasks/T03-SUMMARY.md
duration: 39m
verification_result: passed
completed_at: 2026-03-19
---

# S01: Microsoft OAuth + Graph API Client

**Outlook Calendar Sync app scaffold with Microsoft OAuth 2.0 auth module, Graph API REST client with delta query support, and calendar list/selection UI — 65 unit tests, all htmx URLs properly prefixed**

## What Happened

Built the Outlook Calendar Sync app foundation across three tasks, adapting the Google Calendar app (M018) for Microsoft Identity Platform conventions.

**T01 — Auth module (41 tests):** Created `services/auth.py` with Microsoft OAuth 2.0 helpers: authorize URL builder using `login.microsoftonline.com/common/oauth2/v2.0` endpoints, code exchange, token refresh with rotation detection (Microsoft may return a new refresh_token on each refresh), `refresh_if_expired` with 5-minute buffer, ISO 8601 token storage via StateClient, connection status with masked token preview, and state clearing. Key difference from Google: Microsoft requires `scope` in both authorize and token exchange requests.

**T02 — Graph API client (24 tests):** Created `services/outlook_client.py` wrapping Microsoft Graph API calls. `get_calendar_list()` follows `@odata.nextLink` (full URLs, not query params). `get_events_delta()` implements delta queries returning `(events, delta_link)` tuples for incremental sync. `patch_event()` for future RSVP push-back. 401→refresh→retry delegates to auth module's `refresh_if_expired` instead of duplicating token endpoint calls. Exception hierarchy: `OutlookAPIError` → `OutlookAuthError` (401/403) and `OutlookRateLimitError` (429 with `retry_after`).

**T03 — Routes + templates:** Created `app.py` with 10 route handlers covering full OAuth lifecycle: credential save, Microsoft OAuth redirect with CSRF state, callback with code exchange and error page, disconnect, calendar list with checkboxes, calendar selection save, sync config, and manual sync trigger. Five template files with all htmx URLs prefixed with `/app/outlook-calendar/`. Scoped CSS with Microsoft brand blue (#0078d4).

## Verification

- `cd backend && python -m pytest tests/test_outlook_auth.py tests/test_outlook_client.py -v` — 65/65 passed (0.08s)
- Manifest validates against `AppManifestSchema` (appId=outlook-calendar, version=0.1.0)
- `grep -rn 'hx-\(get\|post\|put\|delete\)="/' apps/outlook-calendar/ | grep -v '/app/outlook-calendar/'` — empty (no unprefixed htmx URLs)
- `python3 -c "import ast; ast.parse(...)"` on app.py — syntax valid
- Auth error carries status_code + response_body (verified by unit tests)
- get_connection_status returns structured dict with connected, auth_method, microsoft_email, token_expiry, token_preview (verified by unit tests)

## Requirements Advanced

- No new requirements registered yet for M020 — will be registered during S02 when pull sync proves end-to-end functionality

## Requirements Validated

- None — S01 establishes foundation; validation requires end-to-end sync (S02+)

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

None — all three tasks followed their plans as written.

## Known Limitations

- `sync_now` and task handlers in app.py import `services.sync_engine` which doesn't exist yet — these are skeleton handlers that will raise ImportError until S02 builds the sync engine
- Microsoft Graph's calendar list doesn't expose the user's email address — the app uses the default calendar's `name` as display identity. A future enhancement could add `User.Read` scope to call `/me`
- `OutlookAuthError` is defined locally in auth.py as a fallback; the canonical version in outlook_client.py supersedes it at runtime

## Follow-ups

- None — S02 consumes all S01 outputs as planned

## Files Created/Modified

- `apps/outlook-calendar/manifest.yaml` — App manifest with identity, permissions (graph.microsoft.com, login.microsoftonline.com), two background tasks, calendar-clock icon
- `apps/outlook-calendar/services/__init__.py` — Empty package init
- `apps/outlook-calendar/services/auth.py` — Microsoft OAuth 2.0 auth helpers (7 functions + error class + constants)
- `apps/outlook-calendar/services/outlook_client.py` — Graph API REST client (get_calendar_list, get_events_delta, patch_event, 401→refresh→retry)
- `apps/outlook-calendar/app.py` — 10 route handlers for OAuth flow, calendar selection, sync config, disconnect, task stubs
- `apps/outlook-calendar/frontend/templates/connect.html` — Azure AD credential form with Application ID + Client Secret inputs
- `apps/outlook-calendar/frontend/templates/connect_status.html` — Connected status with calendar checkboxes, sync config, sync stats
- `apps/outlook-calendar/frontend/templates/calendars.html` — Calendar checkbox partial for htmx swap
- `apps/outlook-calendar/frontend/static/styles.css` — Scoped CSS with Microsoft brand colors
- `backend/tests/test_outlook_auth.py` — 41 unit tests covering all auth functions
- `backend/tests/test_outlook_client.py` — 24 unit tests covering client operations, pagination, delta queries, error handling

## Forward Intelligence

### What the next slice should know
- The auth module stores tokens via StateClient with keys defined in `AUTH_STATE_KEYS` dict — use the same keys when checking connection status in sync engine
- `get_events_delta()` returns `(events, delta_link)` — the delta_link must be stored (via StateClient) and passed back on subsequent calls for incremental sync
- Deleted events in delta responses pass through with `@removed` key intact — the sync engine must detect and handle these
- The `OUTLOOK_API_URL` env var defaults to `https://graph.microsoft.com/v1.0` and can be overridden for mock server testing

### What's fragile
- `sync_now` handler imports `services.sync_engine` which doesn't exist yet — first import in S02 context will crash until the module is created
- OutlookAuthError is defined in both auth.py (local fallback) and outlook_client.py (canonical) — the import in `_handle_token_refresh` uses a deferred import to avoid circular dependency

### Authoritative diagnostics
- `backend/tests/test_outlook_auth.py` — 41 tests covering every auth function including edge cases (rotation, buffer expiry, missing fields)
- `backend/tests/test_outlook_client.py` — 24 tests covering pagination, delta queries, 401→retry, error hierarchy
- `outlook.sync.auth` logger at WARNING level shows token exchange/refresh failures with HTTP status and response body

### What assumptions changed
- No assumptions changed — Microsoft OAuth and Graph API behaved as expected from research docs
