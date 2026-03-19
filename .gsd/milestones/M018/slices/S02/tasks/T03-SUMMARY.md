---
id: T03
parent: S02
milestone: M018
provides:
  - Google Calendar app route handlers (connect, credentials, OAuth redirect, callback, disconnect, calendar selection)
  - Jinja2 templates for connect form and connected status with calendar checkboxes
  - CSS styling scoped to .gcal-sync-settings
  - Skeleton task handlers for poll-events and push-changes
key_files:
  - apps/google-calendar/app.py
  - apps/google-calendar/frontend/templates/connect.html
  - apps/google-calendar/frontend/templates/connect_status.html
  - apps/google-calendar/frontend/static/styles.css
key_decisions:
  - OAuth callback fetches calendar list to derive google_email from primary calendar ID before storing tokens
  - Disconnect clears auth state AND selected_calendars but preserves client_id/secret so re-connect doesn't require re-entry
  - OAuth redirect uses 303 status code for POST→GET redirect per HTTP spec
patterns_established:
  - Google Calendar app routes follow linear-sync app.py structure with _make_client_with_creds helper for token-refresh-capable clients
  - connect.html uses two-step flow (credentials → OAuth) vs linear-sync's single API key entry
observability_surfaces:
  - google_calendar.app logger with INFO on credential save, OAuth redirect, callback success, calendar save, disconnect; WARNING on state mismatch, connection errors
  - get_connection_status() returns {connected, auth_method, google_email, token_expiry} from route handlers
  - oauth_state key in StateClient for CSRF verification — mismatch produces WARNING log
duration: 15min
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T03: Build app routes, templates, and connect flow

**Wired auth module and gcal client into HTTP route handlers and Jinja2 templates implementing the full OAuth connect/disconnect flow with calendar list selection.**

## What Happened

Created four files following the linear-sync app.py pattern:

1. **app.py** — 8 route handlers covering the full OAuth lifecycle:
   - `/_fragments/connect` (GET) renders connect form or connected status
   - `/_fragments/connect/credentials` (POST) saves client_id/secret to state
   - `/_fragments/connect/google` (POST) generates CSRF state, builds authorize URL, redirects 303
   - `/_fragments/oauth-callback` (GET) verifies state param, exchanges code for tokens, fetches calendar list for primary email, stores tokens
   - `/_fragments/connect/disconnect` (POST) clears auth + calendar selection
   - `/_fragments/settings/calendars` (POST) saves selected calendar IDs as JSON
   - Skeleton `poll-events` and `push-changes` task handlers

2. **connect.html** — Two-section form: credentials entry (client_id + client_secret) with redirect URI instructions, then "Connect with Google" button (disabled until credentials saved).

3. **connect_status.html** — Connected badge, Google email, token expiry, calendar checkbox list with primary badge, save calendars form, disconnect button with confirmation dialog.

4. **styles.css** — Scoped under `.gcal-sync-settings`, adapted from linear-sync CSS with Google-branded button color, primary badge styling, and calendar checkbox list layout.

Key implementation detail: The OAuth callback temporarily stores the access token before fetching the calendar list to find the user's primary calendar ID (which is their email), then calls `store_auth_tokens()` with all five required parameters. The `_make_client_with_creds` helper reads client_id/secret from state for clients that may need token refresh.

## Verification

- Jinja2 template syntax validated via Docker container parse check — both templates OK
- Full test suite: 1498 passed in 8.14s
- Slice-specific tests: proxy (5/5), auth (23/23), client (12/12) — all green
- Entrypoint `app:google_calendar_app` matches manifest
- All htmx URLs use `/app/google-calendar/` prefix (verified via grep)
- Redirect URI consistent across app.py constant and connect.html template

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `backend/.venv/bin/python -m pytest tests/ -x -q` | 0 | ✅ pass | 8.14s |
| 2 | `backend/.venv/bin/python -m pytest tests/test_app_proxy_query_params.py -v` | 0 | ✅ pass (5/5) | 0.23s |
| 3 | `backend/.venv/bin/python -m pytest tests/test_gcal_auth.py -v` | 0 | ✅ pass (23/23) | 0.04s |
| 4 | `backend/.venv/bin/python -m pytest tests/test_gcal_client.py -v` | 0 | ✅ pass (12/12) | 0.03s |
| 5 | Jinja2 template parse (docker exec) | 0 | ✅ pass | <1s |

## Diagnostics

- **Logging**: `google_calendar.app` logger emits INFO on credential save, OAuth redirect/callback, calendar selection, disconnect. WARNING on OAuth state mismatch and connection errors.
- **State inspection**: `get_connection_status(state_client)` returns structured dict with `connected`, `auth_method`, `google_email`, `token_expiry`.
- **CSRF state**: `oauth_state` key stored in StateClient before redirect, verified on callback. Mismatch produces WARNING log and error page.
- **Template errors**: Jinja2 render failures surface as 500 with traceback in app process stderr.

## Deviations

- Added `_make_client_with_creds` async helper (not in plan) to read client_id/secret from state for GCalClient construction with token refresh capability. The plan's `_make_client` used None for both.
- OAuth callback stores access_token temporarily before fetching calendar list (needed to get primary email for `store_auth_tokens` which requires all 5 params). Plan didn't specify this intermediate step.

## Known Issues

None.

## Files Created/Modified

- `apps/google-calendar/app.py` — Route handlers for full OAuth connect flow + skeleton tasks
- `apps/google-calendar/frontend/templates/connect.html` — Credential entry + OAuth connect form
- `apps/google-calendar/frontend/templates/connect_status.html` — Connected status, calendar list, disconnect
- `apps/google-calendar/frontend/static/styles.css` — Scoped app styling
- `.gsd/milestones/M018/slices/S02/tasks/T03-PLAN.md` — Added Observability Impact section (pre-flight fix)
