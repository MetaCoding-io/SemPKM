---
estimated_steps: 7
estimated_files: 6
---

## Observability Impact

- **Logs:** `caldav_calendar.app` logger emits route hits (connect, credentials, disconnect, calendar save, sync config, sync-now), connection test results, credential store events, and task handler fires.
- **Errors:** Connection test failures surface HTTP status + message to the UI via the error alert div. CalDAVError and CalDAVAuthError caught in `_render_connect_status` with fallback to connect.html + error message.
- **State keys:** `server_url`, `username`, `password`, `auth_method` (auth), `selected_calendars` (JSON array of hrefs), `sync_direction`, `poll_interval`, `last_sync_at`, `last_pull_result`, `last_push_result` (all via StateClient).
- **Inspection:** `get_connection_status()` returns `{connected, auth_method, server_url, username}` — password never included. Task handler stubs return `{status: "skipped", message: ...}` for diagnostics.

# T02: App manifest, route handlers, connect UI, and calendar selection

**Slice:** S01 — Auth + CalDAV Client + Calendar Discovery
**Milestone:** M021

## Description

Wire the auth and CalDAV client modules (from T01) into an installable app with the standard connect flow. This follows the well-established pattern from 5 prior sync apps (Google Calendar, Outlook, Linear, GitHub, Todoist) — manifest, route handlers, templates, and styles.

CalDAV auth is simpler than Google/Outlook — HTTP Basic means no OAuth redirect dance, no client_id/secret step, no callback URL. The connect form has 3 fields: server URL, username, password. "Test Connection" calls PROPFIND via CalDAVClient. On success, the calendar discovery chain runs and the calendar list renders with checkboxes.

**Critical constraint:** All htmx URLs in templates must use `/app/caldav-calendar/` prefix per the knowledge base entry about app template proxy routing. The grep audit in S01 verification catches violations.

## Steps

1. **Create `apps/caldav-calendar/manifest.yaml`**:
   ```yaml
   appId: "caldav-calendar"
   name: "CalDAV Calendar Sync"
   version: "0.1.0"
   description: "Sync CalDAV calendar events with SemPKM objects"
   author:
     name: "SemPKM"
   license: "MIT"
   
   dependencies:
     platform: ">=0.1.0"
   
   permissions:
     commands:
       - "object.create"
       - "object.patch"
       - "body.set"
       - "edge.create"
     sparql:
       read: true
     backgroundTasks: true
     network:
       - "*"
   
   backend:
     entrypoint: "app:caldav_calendar_app"
   
   tasks:
     - id: "poll-events"
       description: "Poll CalDAV server for updated events and sync to SemPKM"
       interval: "15m"
       retryPolicy:
         maxRetries: 3
         maxBackoff: "60s"
     - id: "push-changes"
       description: "Push local changes back to CalDAV server"
       interval: "15m"
       retryPolicy:
         maxRetries: 3
         maxBackoff: "60s"
   
   frontend:
     staticDir: "frontend/static"
     css:
       - "styles.css"
   
   ui:
     pages:
       - id: "settings"
         path: "/settings"
         label: "CalDAV Calendar"
         icon: "calendar"
         nav: "apps"
         fragment: "connect"
   ```
   Key difference from Google Calendar: `network: ["*"]` (wildcard — D225) instead of specific domains.

2. **Create `apps/caldav-calendar/requirements.txt`**:
   ```
   icalendar
   ```
   S02 needs the icalendar library for iCalendar parsing. Install it now so the venv is ready.

3. **Create `apps/caldav-calendar/app.py`** — app entry point with route handlers:
   - Import `App`, `AppContext` from `sempkm_app_sdk`
   - Import auth and client modules from services
   - `caldav_calendar_app = App("caldav-calendar")`
   - Route handlers (all using `/app/caldav-calendar/` prefix awareness):
     - `GET /_fragments/connect` — renders connect.html (if disconnected) or connect_status.html (if connected, with calendar list from discovery chain)
     - `POST /_fragments/connect/credentials` — receives form with server_url, username, password. Calls `test_connection()` from auth module. On success: stores credentials via `store_credentials()`, runs `discover_calendars()`, renders connect_status.html with calendar list. On failure: re-renders connect.html with error message.
     - `POST /_fragments/connect/disconnect` — calls `clear_auth_state()`, clears selected_calendars, renders connect.html
     - `POST /_fragments/settings/calendars` — receives `calendar_ids` checkbox values, stores as JSON in state, re-renders connect_status.html
     - `POST /_fragments/settings/sync-config` — receives sync_direction and poll_interval, stores in state, re-renders connect_status.html
     - `POST /_fragments/sync-now` — stub that calls pull_sync (import from sync_engine when available), stores result, re-renders connect_status.html. Initially just stores a placeholder result since sync_engine doesn't exist yet.
   - Task handlers (stubs for S02/S03):
     - `@caldav_calendar_app.task("poll-events")` — stub that logs and returns placeholder
     - `@caldav_calendar_app.task("push-changes")` — stub that logs and returns placeholder
   - Startup/shutdown handlers (logging only)
   - Helper: `_render_connect_status(ctx)` — fetches connection status, runs discover_calendars, reads selected calendars/sync config/stats from state, renders connect_status.html. Catches CalDAVError and falls back to connect.html with error.

4. **Create `apps/caldav-calendar/frontend/templates/connect.html`** — credential entry form:
   - `<div id="connect-content" class="caldav-sync-settings">`
   - Heading: "Connect to CalDAV Calendar"
   - Description: link your CalDAV server
   - Error/success alert divs (conditional on template vars)
   - Form with 3 fields:
     - Server URL (text input, placeholder: `https://caldav.fastmail.com/dav/calendars/user/you@fastmail.com/`)
     - Username (text input)
     - Password (password input)
   - Submit button: "Connect" — `hx-post="/app/caldav-calendar/_fragments/connect/credentials"` `hx-target="#connect-content"` `hx-swap="innerHTML"`
   - Hint text: "Enter your CalDAV server URL, username, and password. SemPKM uses HTTP Basic authentication."

5. **Create `apps/caldav-calendar/frontend/templates/connect_status.html`** — connected state with calendar list:
   - Connection status badge (● Connected) + username display
   - Server URL display (masked or truncated for privacy)
   - Calendar selection section: checkboxes for each calendar from discover_calendars
     - `hx-post="/app/caldav-calendar/_fragments/settings/calendars"`
     - Each checkbox: `name="calendar_ids"` `value="{{ cal.href }}"`
     - Display: calendar displayname
   - Sync Configuration section (same pattern as Google Calendar):
     - Direction radios: pull-only / bidirectional
     - Poll interval dropdown: 5m / 15m / 30m / 1h
     - `hx-post="/app/caldav-calendar/_fragments/settings/sync-config"`
   - Manual Sync section:
     - Sync Now button: `hx-post="/app/caldav-calendar/_fragments/sync-now"`
   - Sync Stats section (last sync time, pull/push result stats)
   - Disconnect button: `hx-post="/app/caldav-calendar/_fragments/connect/disconnect"` with hx-confirm

6. **Create `apps/caldav-calendar/frontend/static/styles.css`** — copy from `apps/google-calendar/frontend/static/styles.css` and update class prefixes from `gcal-` to `caldav-`. The CSS is largely identical — connection status badges, form layout, calendar checkboxes, sync config, alert styles.

7. **Verify**:
   - Grep audit for htmx URL prefix: `grep -r "hx-post\|hx-get" apps/caldav-calendar/frontend/templates/ | grep -v "/app/caldav-calendar/"` — must return empty
   - YAML validation: `python -c "import yaml; yaml.safe_load(open('apps/caldav-calendar/manifest.yaml'))"`
   - All T01 tests still pass: `python -m pytest backend/tests/test_caldav_auth.py backend/tests/test_caldav_client.py -v`

## Must-Haves

- [ ] Manifest has appId "caldav-calendar", network: ["*"], all required command permissions, task definitions, UI page config
- [ ] requirements.txt includes `icalendar`
- [ ] All htmx URLs in templates prefixed with `/app/caldav-calendar/`
- [ ] Connect form has server URL, username, password fields
- [ ] Connect flow: submit credentials → test connection via PROPFIND → store credentials → discover calendars → render calendar list
- [ ] Calendar selection saves selected calendar hrefs as JSON in state
- [ ] Disconnect clears all auth state and selected calendars
- [ ] Sync config (direction, interval) persists via StateClient
- [ ] Task handler stubs exist for poll-events and push-changes

## Verification

- `grep -r "hx-post\|hx-get" apps/caldav-calendar/frontend/templates/ | grep -v "/app/caldav-calendar/"` — returns empty (zero htmx prefix violations)
- `python -c "import yaml; yaml.safe_load(open('apps/caldav-calendar/manifest.yaml'))"` — valid YAML
- `python -m pytest backend/tests/test_caldav_auth.py backend/tests/test_caldav_client.py -v` — all T01 tests still pass
- Manual file review: app.py has all 6 route handlers + 2 task handlers + startup/shutdown

## Inputs

- `apps/caldav-calendar/services/auth.py` — from T01: store_credentials, test_connection, get_connection_status, clear_auth_state, get_auth_headers
- `apps/caldav-calendar/services/caldav_client.py` — from T01: CalDAVClient.discover_calendars(), CalDAVError, CalDAVAuthError
- `apps/google-calendar/app.py` — reference pattern for route handler structure, _render_connect_status helper, task handler stubs
- `apps/google-calendar/manifest.yaml` — reference pattern for manifest structure
- `apps/google-calendar/frontend/templates/connect.html` — reference pattern for credential form
- `apps/google-calendar/frontend/templates/connect_status.html` — reference pattern for calendar list + sync config + stats UI
- `apps/google-calendar/frontend/static/styles.css` — CSS to copy and adapt

## Expected Output

- `apps/caldav-calendar/manifest.yaml` — valid app manifest (~40 lines)
- `apps/caldav-calendar/requirements.txt` — single line: `icalendar`
- `apps/caldav-calendar/app.py` — route handlers + task stubs (~250 lines)
- `apps/caldav-calendar/frontend/templates/connect.html` — credential entry form (~60 lines)
- `apps/caldav-calendar/frontend/templates/connect_status.html` — connected status with calendar list, sync config, stats (~140 lines)
- `apps/caldav-calendar/frontend/static/styles.css` — adapted from Google Calendar (~200 lines)
