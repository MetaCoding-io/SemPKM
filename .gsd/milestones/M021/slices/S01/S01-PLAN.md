# S01: Auth + CalDAV Client + Calendar Discovery

**Goal:** CalDAVClient speaks WebDAV XML (PROPFIND/REPORT/PUT/DELETE), auth stores HTTP Basic credentials, and the discovery chain resolves calendars — all proven by unit tests.
**Demo:** User installs CalDAV app, enters server URL + credentials, and sees their calendar list with selection checkboxes.

## Must-Haves

- HTTP Basic auth module: store URL/username/password via StateClient, connection test via PROPFIND, get_auth_headers() returning Authorization header
- CalDAVClient with PROPFIND (discovery + calendar list), REPORT (sync-collection for events), PUT (event create/update with ETag), DELETE (event removal with ETag)
- Full discovery chain: well-known → principal → calendar-home → calendar-list, with XML namespace-aware parsing
- XML request generation using stdlib xml.etree.ElementTree (DAV:, urn:ietf:params:xml:ns:caldav, calendarserver namespaces)
- XML response parsing for multistatus/propstat/prop structures
- App manifest with network: ["*"] wildcard, task definitions, UI page
- Route handlers: connect fragment, save credentials, test connection, disconnect, save calendars
- Connect UI: credential form (server URL, username, password) and connected status with calendar checkboxes
- `icalendar` in requirements.txt for S02 dependency
- ≥50 unit tests across auth + client modules covering XML generation, response parsing, discovery chain, error handling, auth helpers

## Proof Level

- This slice proves: contract (WebDAV XML protocol correctness, discovery chain navigability)
- Real runtime required: no (unit tests with mocked HTTP/state)
- Human/UAT required: no

## Verification

- `cd /home/james/Code/SemPKM/.gsd/worktrees/M018 && python -m pytest backend/tests/test_caldav_auth.py backend/tests/test_caldav_client.py -v` — all tests pass
- Auth tests: credential storage/retrieval, connection test success/failure, get_auth_headers, clear state, connection status
- Client tests: PROPFIND request XML generation with correct namespaces, multistatus XML response parsing, discovery chain (well-known redirect, principal, calendar-home, calendar-list), sync-collection REPORT request/response, PUT with If-Match/If-None-Match, DELETE with If-Match, error handling (401, 403, 404, 500)
- Grep audit: `grep -r "hx-post\|hx-get\|hx-delete\|hx-put" apps/caldav-calendar/frontend/templates/ | grep -v "/app/caldav-calendar/"` returns zero results (all htmx URLs use proxy prefix)

## Observability / Diagnostics

- Runtime signals: `caldav.auth` and `caldav.client` loggers with connection test results, discovery chain steps, request/response status codes
- Inspection surfaces: `get_connection_status()` returns connected/server_url/username state dict; CalDAVClient methods log XML request types and response status
- Failure visibility: CalDAVError/CalDAVAuthError exceptions with status_code and response_body; connection test surfaces HTTP error details to UI
- Redaction constraints: password never logged or returned in status dicts; only username and masked URL shown

## Integration Closure

- Upstream surfaces consumed: App Platform SDK (App, AppContext, StateClient, HttpClient), bpkm:Event type (EVENT-01)
- New wiring introduced in this slice: `apps/caldav-calendar/` directory with manifest, app entry point, services, frontend assets
- What remains before the milestone is truly usable end-to-end: S02 (pull sync + field mapping), S03 (push sync), S04 (E2E + docs)

## Tasks

- [x] **T01: Build CalDAV auth module and CalDAVClient with WebDAV XML protocol** `est:2h`
  - Why: The core technical risk — CalDAV uses XML-over-HTTP (PROPFIND/REPORT/PUT/DELETE) unlike the JSON REST APIs of prior sync apps. This task builds the protocol layer and credential management, proving WebDAV XML works through the SDK's HttpClient.
  - Files: `apps/caldav-calendar/services/__init__.py`, `apps/caldav-calendar/services/auth.py`, `apps/caldav-calendar/services/caldav_client.py`, `backend/tests/test_caldav_auth.py`, `backend/tests/test_caldav_client.py`
  - Do: Build auth module with HTTP Basic credential storage (server_url, username, password via StateClient), connection test via PROPFIND on server root, get_auth_headers() returning base64-encoded Authorization header. Build CalDAVClient with: (1) XML request builders for PROPFIND and REPORT bodies using stdlib xml.etree.ElementTree with DAV:, caldav:, and calendarserver namespaces, (2) XML response parser for multistatus/propstat structures, (3) discovery chain methods (discover_principal, discover_calendar_home, discover_calendars combining the full chain), (4) get_events via sync-collection REPORT, (5) get_event/put_event/delete_event with ETag handling. Write comprehensive unit tests for both modules using the importlib loading pattern from test_gcal_auth.py. Use canned XML response strings for all server interactions.
  - Verify: `python -m pytest backend/tests/test_caldav_auth.py backend/tests/test_caldav_client.py -v` — ≥50 tests pass covering all XML generation, response parsing, discovery chain steps, auth helpers, and error handling paths
  - Done when: CalDAVClient can generate correct PROPFIND/REPORT/PUT/DELETE XML, parse multistatus responses, navigate the full discovery chain, and handle all error conditions — all proven by unit tests with zero failures

- [x] **T02: App manifest, route handlers, connect UI, and calendar selection** `est:1h30m`
  - Why: Wires the auth and client modules into an installable app with the standard connect flow — manifest, routes, templates, and styles. This is the integration layer that makes the CalDAV app actually usable from the workspace UI.
  - Files: `apps/caldav-calendar/manifest.yaml`, `apps/caldav-calendar/requirements.txt`, `apps/caldav-calendar/app.py`, `apps/caldav-calendar/frontend/templates/connect.html`, `apps/caldav-calendar/frontend/templates/connect_status.html`, `apps/caldav-calendar/frontend/static/styles.css`
  - Do: Create manifest.yaml (appId: caldav-calendar, network: ["*"], commands: object.create/patch/body.set/edge.create, tasks: poll-events/push-changes, UI page for settings). Create requirements.txt with `icalendar`. Build app.py with route handlers following Google Calendar pattern: connect fragment (GET), save credentials (POST), test connection (POST — calls PROPFIND via CalDAVClient), disconnect (POST), save selected calendars (POST), sync-config (POST), sync-now (POST skeleton), plus task handler stubs for poll-events and push-changes. Build connect.html template with server URL, username, password fields (all htmx URLs prefixed with `/app/caldav-calendar/`). Build connect_status.html with connection status badge, calendar checkbox list, sync config section, sync stats section, disconnect button. Copy and adapt styles.css from Google Calendar app.
  - Verify: (1) `grep -r "hx-post\|hx-get" apps/caldav-calendar/frontend/templates/ | grep -v "/app/caldav-calendar/"` returns empty (htmx prefix audit), (2) `python -c "import yaml; yaml.safe_load(open('apps/caldav-calendar/manifest.yaml'))"` succeeds (valid YAML), (3) All prior tests still pass: `python -m pytest backend/tests/test_caldav_auth.py backend/tests/test_caldav_client.py -v`
  - Done when: App directory has complete manifest, requirements, entry point, routes, templates, and styles — ready for installation via Admin > Applications

## Files Likely Touched

- `apps/caldav-calendar/manifest.yaml`
- `apps/caldav-calendar/requirements.txt`
- `apps/caldav-calendar/app.py`
- `apps/caldav-calendar/services/__init__.py`
- `apps/caldav-calendar/services/auth.py`
- `apps/caldav-calendar/services/caldav_client.py`
- `apps/caldav-calendar/frontend/templates/connect.html`
- `apps/caldav-calendar/frontend/templates/connect_status.html`
- `apps/caldav-calendar/frontend/static/styles.css`
- `backend/tests/test_caldav_auth.py`
- `backend/tests/test_caldav_client.py`
