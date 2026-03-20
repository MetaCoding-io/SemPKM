---
id: T02
parent: S01
milestone: M021
provides:
  - Installable CalDAV Calendar app with manifest, route handlers, connect/disconnect flow, calendar selection UI, sync config, and task handler stubs
key_files:
  - apps/caldav-calendar/manifest.yaml
  - apps/caldav-calendar/app.py
  - apps/caldav-calendar/requirements.txt
  - apps/caldav-calendar/frontend/templates/connect.html
  - apps/caldav-calendar/frontend/templates/connect_status.html
  - apps/caldav-calendar/frontend/static/styles.css
key_decisions:
  - CalDAV sync-now route returns stub result (sync engine not yet implemented) rather than importing a non-existent module
  - Disconnect clears all state keys (auth + sync config + stats) for clean reconnect
patterns_established:
  - CalDAV app follows identical route/template/CSS structure to Google Calendar app, adapted for HTTP Basic (no OAuth redirect dance)
observability_surfaces:
  - "caldav_calendar.app logger: route hits, connection test results, credential storage, calendar save, task handler fires"
  - "State keys: server_url, username, password, auth_method, selected_calendars, sync_direction, poll_interval, last_sync_at, last_pull_result, last_push_result"
  - "CalDAVError/CalDAVAuthError surfaced to UI via error alert div on connect.html"
duration: 25m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T02: App manifest, route handlers, connect UI, and calendar selection

**Wired CalDAV auth and client modules into installable app with manifest, 6 route handlers, connect/status templates, calendar selection, sync config, and adapted CSS — all htmx URLs correctly prefixed.**

## What Happened

Created 6 files that turn the T01 protocol layer into a usable app:

1. **manifest.yaml** — appId `caldav-calendar`, `network: ["*"]` wildcard (D225), poll-events + push-changes tasks at 15m intervals, UI page config pointing to connect fragment.
2. **requirements.txt** — `icalendar` dependency for S02.
3. **app.py** — 6 route handlers (connect fragment, save credentials with PROPFIND test, disconnect, save calendars, save sync config, sync-now stub) + 2 task handler stubs + startup/shutdown hooks. The `_render_connect_status` helper runs the full discovery chain and assembles all state for the template.
4. **connect.html** — credential form with server URL, username, password fields. All htmx URLs prefixed with `/app/caldav-calendar/`.
5. **connect_status.html** — connected state with status badge, username, server URL, calendar checkbox list using `cal.href` as value, sync config (direction radios + poll interval select), manual sync button, sync stats section, and disconnect button with confirmation.
6. **styles.css** — adapted from Google Calendar CSS with `caldav-` prefix scope. Removed Google-specific rules (OAuth button, redirect URI code block, divider). Added server URL hint styling.

## Verification

- **htmx prefix audit:** `grep -r "hx-post\|hx-get\|hx-delete\|hx-put" apps/caldav-calendar/frontend/templates/ | grep -v "/app/caldav-calendar/"` returned empty — zero violations.
- **YAML validation:** `python -c "import yaml; yaml.safe_load(open('apps/caldav-calendar/manifest.yaml'))"` succeeded.
- **T01 tests:** All 62 tests pass (20 auth + 42 client).
- **File review:** app.py has 6 route handlers + 2 task handlers + startup + shutdown (confirmed via grep).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -r "hx-post\|hx-get\|hx-delete\|hx-put" apps/caldav-calendar/frontend/templates/ \| grep -v "/app/caldav-calendar/"` | 1 (no matches) | ✅ pass | <1s |
| 2 | `python -c "import yaml; yaml.safe_load(open('apps/caldav-calendar/manifest.yaml'))"` | 0 | ✅ pass | <1s |
| 3 | `uv run python -m pytest tests/test_caldav_auth.py tests/test_caldav_client.py -v` | 0 | ✅ pass (62/62) | 5.2s |

## Diagnostics

- **Logs:** `caldav_calendar.app` logger emits route-level events — connection test results, credential storage, calendar save counts, sync config changes, task handler fires.
- **State inspection:** All sync state stored via StateClient under well-known keys. `get_connection_status()` returns `{connected, auth_method, server_url, username}` — password never exposed.
- **Error surfaces:** CalDAVError/CalDAVAuthError caught in `_render_connect_status` with graceful fallback to connect.html + error message. Connection test failures show HTTP status + human-readable message.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `apps/caldav-calendar/manifest.yaml` — app manifest with network wildcard, tasks, UI page config
- `apps/caldav-calendar/requirements.txt` — icalendar dependency for S02
- `apps/caldav-calendar/app.py` — route handlers, task stubs, lifecycle hooks (~275 lines)
- `apps/caldav-calendar/frontend/templates/connect.html` — credential entry form (~65 lines)
- `apps/caldav-calendar/frontend/templates/connect_status.html` — connected status with calendar list, sync config, stats (~165 lines)
- `apps/caldav-calendar/frontend/static/styles.css` — scoped styles adapted from Google Calendar (~330 lines)
- `.gsd/milestones/M021/slices/S01/tasks/T02-PLAN.md` — added Observability Impact section (pre-flight fix)
- `.gsd/milestones/M021/slices/S01/S01-PLAN.md` — marked T02 done
