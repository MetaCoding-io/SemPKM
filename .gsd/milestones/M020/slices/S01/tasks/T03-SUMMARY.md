---
id: T03
parent: S01
milestone: M020
provides:
  - Outlook Calendar app route handlers (OAuth flow, calendar selection, sync config, disconnect)
  - Frontend templates (connect form, connected status, calendar checkbox partial)
  - Scoped CSS styles with Microsoft brand colors
key_files:
  - apps/outlook-calendar/app.py
  - apps/outlook-calendar/frontend/templates/connect.html
  - apps/outlook-calendar/frontend/templates/connect_status.html
  - apps/outlook-calendar/frontend/templates/calendars.html
  - apps/outlook-calendar/frontend/static/styles.css
key_decisions:
  - Microsoft Graph does not expose user email in calendar list — use default calendar name as display identity instead of requiring an extra scope for /me endpoint
  - OAuth route is /_fragments/connect/microsoft (not /google) to match provider identity
  - OutlookClient field names (name, isDefaultCalendar, canEdit) used directly in templates instead of aliasing to Google's field names
patterns_established:
  - All htmx URLs prefixed with /app/outlook-calendar/ per proxy routing requirement
  - CSS scoped under .outlook-sync-settings with Microsoft blue (#0078d4) for brand button
observability_surfaces:
  - "Logger: outlook_calendar.app at INFO for OAuth flow events (credential save, redirect, callback, disconnect, calendar save, sync trigger)"
  - "get_connection_status() returns connected, auth_method, microsoft_email, token_expiry, token_preview — called on every connect fragment render"
  - "OAuth callback renders explicit error page with failure message; connect fragment falls back to connect form on API errors"
duration: 15min
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T03: App routes + OAuth flow + calendar selection UI

**Built Outlook Calendar app.py with OAuth connect flow, calendar selection, sync config UI, and all htmx-routed templates**

## What Happened

Adapted the Google Calendar app.py and templates for Outlook Calendar, wiring the T01 auth module and T02 OutlookClient into user-facing route handlers. Created five files:

1. `app.py` — 10 route handlers covering the full OAuth lifecycle: credential save, Microsoft OAuth redirect, callback with CSRF state verification, disconnect, calendar list/selection save, sync config save, sync-now trigger. Plus poll-events and push-changes task stubs for S03/S04.

2. `connect.html` — Azure AD credential form with Application (Client) ID and Client Secret inputs, redirect URI display, and Microsoft OAuth connect button.

3. `connect_status.html` — Connected status panel showing Microsoft account, token expiry, calendar checkbox list (using Outlook field names: `name`, `isDefaultCalendar`, `canEdit`), sync direction/interval config, manual sync trigger, and sync stats.

4. `calendars.html` — Standalone calendar checkbox partial for htmx-swapped calendar list refresh.

5. `styles.css` — Scoped under `.outlook-sync-settings` with Microsoft brand blue (#0078d4) for the connect button, otherwise matching the Google Calendar app's design system.

Key adaptation from Google Calendar: Microsoft Graph's calendar list returns `name` (not `summary`), `isDefaultCalendar` (not `primary`), and `canEdit` (not `accessRole`). The OAuth callback uses the default calendar's name as the display identity since Graph doesn't expose user email in the calendar list without an extra User.Read scope.

## Verification

1. **htmx URL prefix check:** `grep -rn 'hx-\(get\|post\|put\|delete\)="/' apps/outlook-calendar/ | grep -v '/app/outlook-calendar/'` returned empty — all htmx URLs properly prefixed.
2. **All template files exist:** Verified all 5 expected output files present.
3. **Python syntax valid:** `ast.parse(open('apps/outlook-calendar/app.py').read())` passes.
4. **Manifest entrypoint matches:** `app:outlook_calendar_app` verified.
5. **T01/T02 tests pass:** 65/65 tests pass (41 auth + 24 client).
6. **Auth error carries status_code + response_body:** Verified programmatically.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -rn 'hx-\(get\|post\|put\|delete\)="/' apps/outlook-calendar/ \| grep -v '/app/outlook-calendar/'` | 1 (no matches) | ✅ pass | <1s |
| 2 | File existence check (5 files) | 0 | ✅ pass | <1s |
| 3 | `python3 -c "import ast; ast.parse(...)"` on app.py | 0 | ✅ pass | <1s |
| 4 | `python3 -m pytest tests/test_outlook_auth.py tests/test_outlook_client.py -v` | 0 | ✅ pass | 0.08s |
| 5 | Manifest entrypoint validation | 0 | ✅ pass | <1s |
| 6 | Auth error status_code/response_body check | 0 | ✅ pass | <1s |

## Diagnostics

- **Logger `outlook_calendar.app`:** INFO for credential save, OAuth redirect, callback success/failure, disconnect, calendar selection save, sync config save, manual sync trigger
- **Logger `outlook.sync.auth`:** INFO on token store/verify/clear, WARNING on verification/refresh failures with status code + response body
- **State inspection:** Call `get_connection_status(state_client)` to see `connected`, `auth_method`, `microsoft_email`, `token_expiry`, `token_preview`
- **OAuth error visibility:** Callback renders a dedicated error page with human-readable message; connect fragment catches OutlookAPIError/OutlookAuthError and falls back to connect form with inline error display

## Deviations

None.

## Known Issues

- Microsoft Graph's calendar list doesn't expose the user's email address — the app uses the default calendar's `name` as the display identity. A future enhancement could add `User.Read` scope and call `/me` to get the actual email.
- `sync_now` and task handlers import `services.sync_engine` which doesn't exist yet (S03/S04 scope). These are skeleton handlers that will raise ImportError until the sync engine is built.

## Files Created/Modified

- `apps/outlook-calendar/app.py` — Route handlers for OAuth flow, calendar selection, sync config, disconnect, and task stubs
- `apps/outlook-calendar/frontend/templates/connect.html` — Azure AD credential form and Microsoft OAuth connect button
- `apps/outlook-calendar/frontend/templates/connect_status.html` — Connected status with calendar checkboxes, sync config, sync stats
- `apps/outlook-calendar/frontend/templates/calendars.html` — Calendar checkbox partial for htmx swap
- `apps/outlook-calendar/frontend/static/styles.css` — Scoped CSS with Microsoft brand colors
- `.gsd/milestones/M020/slices/S01/tasks/T03-PLAN.md` — Added Observability Impact section
