---
estimated_steps: 6
estimated_files: 5
---

# T03: App routes + OAuth flow + calendar selection UI

**Slice:** S01 — Microsoft OAuth + Graph API Client
**Milestone:** M020

## Description

Wire auth + client into user-facing OAuth flow and calendar selection. Build app.py route handlers and frontend templates with all htmx URLs prefixed with `/app/outlook-calendar/`.

## Steps

1. Build `app.py` with route handlers: connect form, OAuth redirect, OAuth callback, disconnect, calendar list, calendar selection save, sync-now, sync-config stubs
2. Create `frontend/templates/connect.html` — Azure AD credential form (Application ID + Client Secret)
3. Create `frontend/templates/connect_status.html` — connected status with calendar checkboxes, sync config stubs
4. Create `frontend/templates/calendars.html` — calendar checkbox partial
5. Create `frontend/static/styles.css` — copy from M018
6. Verify all htmx URLs prefixed with `/app/outlook-calendar/`

## Must-Haves

- [ ] All htmx URLs use /app/outlook-calendar/ prefix
- [ ] OAuth redirect/callback flow is complete
- [ ] Calendar selection persists via StateClient

## Verification

- `grep -rn 'hx-\(get\|post\|put\|delete\)="/' apps/outlook-calendar/ | grep -v '/app/outlook-calendar/'` returns empty
- All template files exist

## Observability Impact

- **Logger:** `outlook_calendar.app` at INFO for OAuth flow events (credential save, OAuth redirect, callback success/failure, disconnect, calendar save, sync trigger)
- **Logger:** `outlook.sync.auth` and `outlook.sync.client` (from T01/T02) log token lifecycle and API requests
- **Inspection surface:** `get_connection_status()` returns `connected`, `auth_method`, `microsoft_email`, `token_expiry`, `token_preview` — called on every connect fragment render
- **Failure visibility:** OAuth callback renders error page with message; connect fragment falls back to connect.html on GCalAPIError/auth errors; all form validation errors rendered inline
- **State keys:** `client_id`, `client_secret`, `oauth_state`, `access_token`, `refresh_token`, `auth_method`, `microsoft_email`, `token_expiry`, `selected_calendars`, `sync_direction`, `poll_interval`, `last_sync_at`, `last_pull_result`, `last_push_result`

## Inputs

- `apps/outlook-calendar/services/auth.py` — from T01
- `apps/outlook-calendar/services/outlook_client.py` — from T02
- `apps/google-calendar/app.py` — reference to adapt

## Expected Output

- `apps/outlook-calendar/app.py`
- `apps/outlook-calendar/frontend/templates/connect.html`
- `apps/outlook-calendar/frontend/templates/connect_status.html`
- `apps/outlook-calendar/frontend/templates/calendars.html`
- `apps/outlook-calendar/frontend/static/styles.css`
