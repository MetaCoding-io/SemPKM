# S01: Microsoft OAuth + Graph API Client

**Goal:** App scaffold with Microsoft Identity Platform OAuth 2.0, Graph API REST client, and calendar list/selection UI.
**Demo:** User installs Outlook Calendar Sync from Admin > Applications, enters Azure AD credentials, completes OAuth consent flow, and sees their calendar list with selection checkboxes.

## Must-Haves

- App manifest with correct identity, permissions (graph.microsoft.com, login.microsoftonline.com), and task declarations
- Microsoft OAuth 2.0 authorize URL builder, code exchange, token refresh, store/clear via StateClient
- OutlookClient REST wrapper for Graph API with authenticated requests, 401→refresh→retry, pagination via @odata.nextLink
- Calendar list endpoint (GET /me/calendars) with selection UI and state persistence
- Connect/disconnect flow through app proxy OAuth callback
- 50+ unit tests covering auth module and client module

## Verification

- `cd backend && python -m pytest tests/test_outlook_auth.py tests/test_outlook_client.py -v` — all pass
- App manifest validates: `python -c "from app.apps.manifest import AppManifestSchema; ..."` or equivalent
- grep for hardcoded htmx URLs: `grep -rn 'hx-\(get\|post\|put\|delete\)="/' apps/outlook-calendar/ | grep -v '/app/outlook-calendar/'` returns empty
- Auth module failure paths: token exchange and refresh errors include status code + response body in exception; `get_connection_status()` returns structured dict with connected flag and token_preview for runtime inspection

## Observability / Diagnostics

- Runtime signals: `outlook.sync.auth` logger — INFO on token store/verify/clear, WARNING on verification/refresh failures
- Runtime signals: `outlook.sync.client` logger — DEBUG for each REST request (method + URL)
- Inspection surfaces: `get_connection_status()` returns connected flag, auth_method, calendars_count, token_preview
- Failure visibility: auth module logs token refresh errors with status code and response body

## Tasks

- [x] **T01: App scaffold + manifest + auth module** `est:45m`
  - Why: Foundation for all Outlook sync work — app identity, OAuth helpers, credential storage
  - Files: `apps/outlook-calendar/manifest.yaml`, `apps/outlook-calendar/services/__init__.py`, `apps/outlook-calendar/services/auth.py`, `backend/tests/test_outlook_auth.py`
  - Do: Clone from `apps/google-calendar/`, adapt manifest (appId: "outlook-calendar", name, network permissions to graph.microsoft.com + login.microsoftonline.com, icon to "calendar-clock"). Build auth module with Microsoft Identity Platform OAuth 2.0: authorize URL builder using `https://login.microsoftonline.com/common/oauth2/v2.0/authorize` with scope `Calendars.ReadWrite offline_access`, code exchange via `/token` endpoint, token refresh, store tokens as ISO 8601 via StateClient, connection status with masked token preview, clear/disconnect. Add OUTLOOK_API_URL env var override for mock server testability. Write 20+ unit tests.
  - Verify: `cd backend && python -m pytest tests/test_outlook_auth.py -v`
  - Done when: All auth tests pass, manifest validates

- [x] **T02: Graph API REST client** `est:35m`
  - Why: HTTP layer for all Microsoft Graph API interactions — calendar list, events, patches
  - Files: `apps/outlook-calendar/services/outlook_client.py`, `backend/tests/test_outlook_client.py`
  - Do: Build OutlookClient with: authenticated requests (Bearer token header), get_calendar_list() with @odata.nextLink pagination, get_events_delta() with deltaLink/nextLink handling, patch_event() for RSVP updates. 401→refresh→retry pattern (matching M018 GCalClient). OUTLOOK_API_URL env var for base URL override. Rate limit awareness (log warning at 80% of 10,000 req/10min). Write 15+ unit tests covering single-page, paginated, empty, auth header, 401→retry, error handling, delta token flow.
  - Verify: `cd backend && python -m pytest tests/test_outlook_client.py -v`
  - Done when: All client tests pass, delta query pagination works correctly

- [x] **T03: App routes + OAuth flow + calendar selection UI** `est:40m`
  - Why: Wires auth + client into user-facing OAuth flow and calendar selection
  - Files: `apps/outlook-calendar/app.py`, `apps/outlook-calendar/frontend/templates/connect.html`, `apps/outlook-calendar/frontend/templates/connect_status.html`, `apps/outlook-calendar/frontend/templates/calendars.html`, `apps/outlook-calendar/frontend/static/styles.css`
  - Do: Build app.py with route handlers: connect form (client ID + client secret input), OAuth redirect (authorize URL with state CSRF), OAuth callback (code exchange, token storage, redirect to status), disconnect (clear tokens), calendar list with checkboxes (GET /me/calendars via client), calendar selection save (persist as JSON state). All htmx URLs prefixed with `/app/outlook-calendar/`. Templates cloned from M018 and adapted for Microsoft terminology (Application ID, Client Secret, Azure AD).
  - Verify: grep for unprefixed htmx URLs: `grep -rn 'hx-\(get\|post\|put\|delete\)="/' apps/outlook-calendar/ | grep -v '/app/outlook-calendar/'` returns empty. All template files exist and have correct prefix.
  - Done when: Full OAuth flow is implemented, templates render correctly, calendar selection persists

## Files Likely Touched

- `apps/outlook-calendar/manifest.yaml`
- `apps/outlook-calendar/app.py`
- `apps/outlook-calendar/services/__init__.py`
- `apps/outlook-calendar/services/auth.py`
- `apps/outlook-calendar/services/outlook_client.py`
- `apps/outlook-calendar/frontend/templates/connect.html`
- `apps/outlook-calendar/frontend/templates/connect_status.html`
- `apps/outlook-calendar/frontend/templates/calendars.html`
- `apps/outlook-calendar/frontend/static/styles.css`
- `backend/tests/test_outlook_auth.py`
- `backend/tests/test_outlook_client.py`
