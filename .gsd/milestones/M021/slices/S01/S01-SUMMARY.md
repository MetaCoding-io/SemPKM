---
id: S01
parent: M021
milestone: M021
provides:
  - CalDAV auth module with HTTP Basic credential storage, connection test, auth header generation
  - CalDAVClient with WebDAV XML protocol (PROPFIND/REPORT/PUT/DELETE) and multistatus response parser
  - Full discovery chain (well-known → principal → calendar-home → calendar-list) handling both Fastmail and Nextcloud server variants
  - Installable app with manifest, 6 route handlers, credential form, calendar selection UI, sync config controls
  - 62 unit tests covering all XML generation, response parsing, discovery chain, auth helpers, and error handling
requires:
  - slice: none
    provides: first slice — no dependencies
affects:
  - S02
  - S03
  - S04
key_files:
  - apps/caldav-calendar/services/caldav_client.py
  - apps/caldav-calendar/services/auth.py
  - apps/caldav-calendar/app.py
  - apps/caldav-calendar/manifest.yaml
  - apps/caldav-calendar/requirements.txt
  - apps/caldav-calendar/frontend/templates/connect.html
  - apps/caldav-calendar/frontend/templates/connect_status.html
  - apps/caldav-calendar/frontend/static/styles.css
  - backend/tests/test_caldav_auth.py
  - backend/tests/test_caldav_client.py
key_decisions:
  - Renamed auth.test_connection → auth.check_connection to prevent pytest from collecting it as a test function
  - Home collection filtered by urljoin-resolving relative hrefs before comparison (Nextcloud compatibility)
patterns_established:
  - CalDAV XML builders use stdlib xml.etree.ElementTree with registered namespace prefixes (d/c/cs) per D224
  - _parse_multistatus handles both propstat-based and direct-status responses (for sync-collection deleted resources)
  - CalDAVClient uses http_client.request("PROPFIND", ...) for WebDAV methods not in standard HTTP verb set
  - CalDAV app follows identical route/template/CSS structure to Google Calendar app, adapted for HTTP Basic (no OAuth redirect dance)
observability_surfaces:
  - caldav.auth logger — connection test results, credential storage events
  - caldav.client logger — PROPFIND/REPORT/GET/PUT/DELETE request URLs and response status codes, discovery chain progress
  - CalDAVError exception hierarchy with status_code and response_body on every error
  - get_connection_status() returns {connected, auth_method, server_url, username} — password never exposed
drill_down_paths:
  - .gsd/milestones/M021/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M021/slices/S01/tasks/T02-SUMMARY.md
duration: 55m
verification_result: passed
completed_at: 2026-03-19
---

# S01: Auth + CalDAV Client + Calendar Discovery

**CalDAV protocol layer with HTTP Basic auth, WebDAV XML client (PROPFIND/REPORT/PUT/DELETE), full discovery chain, and installable app with credential form + calendar selection — all proven by 62 unit tests.**

## What Happened

T01 built the core protocol layer in two modules:

**`auth.py`** (~130 lines) provides HTTP Basic credential management: `get_auth_headers()` returns base64-encoded Authorization header, `store_credentials()` persists server URL/username/password via StateClient (with trailing-slash stripping), `check_connection()` probes the server with a PROPFIND request, `get_connection_status()` returns a safe dict that never exposes the password, and `clear_auth_state()` wipes all stored credentials.

**`caldav_client.py`** (~400 lines) implements the WebDAV XML protocol. Three XML builder functions generate namespace-aware PROPFIND and REPORT request bodies using stdlib `xml.etree.ElementTree` with DAV:, caldav:, and calendarserver namespace prefixes. The multistatus XML parser handles both standard propstat-based responses and the simpler direct-status format used for deleted resources in sync-collection REPORT results. CalDAVClient provides: the full discovery chain (`discover_principal` → `discover_calendar_home` → `discover_calendars`), event operations (`get_events` via sync-collection REPORT, `get_event`, `put_event` with If-Match/If-None-Match ETag handling, `delete_event`), and a custom exception hierarchy (CalDAVError → CalDAVAuthError/NotFound/Conflict) carrying status_code and response_body.

A key fix during T01: Nextcloud returns relative hrefs in its PROPFIND Depth:1 responses, while Fastmail returns absolute URLs. The discovery chain needed `urljoin()` to resolve relative hrefs before comparing against the home collection URL. Both variants are covered by unit tests with canned XML.

T02 wired everything into an installable app: manifest with `network: ["*"]` wildcard (D225), `icalendar` in requirements.txt for S02, 6 route handlers in `app.py` (connect fragment, save credentials + PROPFIND test, disconnect, save calendars, sync config, sync-now stub), 2 task handler stubs (poll-events, push-changes), and two templates — `connect.html` with server URL/username/password form, and `connect_status.html` with connection badge, calendar checkboxes, sync direction/interval controls, sync stats section, and disconnect button. CSS adapted from Google Calendar app with CalDAV-specific scope.

## Verification

- **62 unit tests pass** — 20 auth (base64 encoding, credential CRUD, connection test success/failure/exception, password redaction, state clearing) + 42 client (XML builders, multistatus parser variants, full discovery chain with Fastmail/Nextcloud canned XML, event CRUD with ETag, error handling for 401/403/404/500, missing credentials)
- **htmx prefix audit clean** — `grep -r "hx-post|hx-get" apps/caldav-calendar/frontend/templates/ | grep -v "/app/caldav-calendar/"` returns zero matches
- **Valid manifest** — `yaml.safe_load()` succeeds on manifest.yaml

## Requirements Advanced

- CDAV-01 (CalDAV auth) — HTTP Basic credential storage, connection test, auth headers implemented and unit-tested. Not yet validated (needs live runtime proof in S04 E2E).
- CDAV-02 (Calendar discovery) — Full well-known → principal → calendar-home → calendar-list chain implemented with Fastmail and Nextcloud variant coverage. Not yet validated (needs live runtime proof).
- CDAV-03 (CalDAV client protocol) — PROPFIND/REPORT/PUT/DELETE with XML generation and parsing, ETag concurrency. Not yet validated (needs sync engine integration in S02/S03).

## Requirements Validated

- none (contract-level proof only — runtime validation deferred to S04 E2E)

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- Renamed `test_connection()` → `check_connection()` in auth.py to prevent pytest from collecting it as a test function. Behavior is identical; only the name changed.

## Known Limitations

- `get_events()` returns `new_sync_token=None` — the sync-token for incremental sync lives in the multistatus root element, outside the per-response entries. The parser currently only extracts per-response data. S02 will need to extract the root-level `<sync-token>` from sync-collection responses.
- `sync-now` route handler returns a stub result — sync engine doesn't exist yet (S02).
- Task handlers (poll-events, push-changes) are stubs that log and return — wired in S02/S03.

## Follow-ups

- S02 must extract sync-token from multistatus root element in `get_events()` for incremental sync support.
- S02 will need to handle the `icalendar` library's typed return values (vDate, vDatetime, vCalAddress, vRecur) with careful single-vs-list detection.

## Files Created/Modified

- `apps/caldav-calendar/services/__init__.py` — empty package init
- `apps/caldav-calendar/services/auth.py` — HTTP Basic auth helpers (~130 lines)
- `apps/caldav-calendar/services/caldav_client.py` — CalDAVClient with WebDAV XML protocol (~400 lines)
- `apps/caldav-calendar/manifest.yaml` — app manifest with network wildcard, tasks, UI page
- `apps/caldav-calendar/requirements.txt` — icalendar dependency for S02
- `apps/caldav-calendar/app.py` — 6 route handlers + 2 task stubs + lifecycle hooks (~275 lines)
- `apps/caldav-calendar/frontend/templates/connect.html` — credential entry form (~65 lines)
- `apps/caldav-calendar/frontend/templates/connect_status.html` — connected status with calendar list, sync config, stats (~165 lines)
- `apps/caldav-calendar/frontend/static/styles.css` — scoped styles adapted from Google Calendar (~330 lines)
- `backend/tests/test_caldav_auth.py` — 20 auth unit tests
- `backend/tests/test_caldav_client.py` — 42 client unit tests with canned XML for Fastmail/Nextcloud variants

## Forward Intelligence

### What the next slice should know
- CalDAVClient.get_events() returns a list of dicts with keys: `href`, `status`, `props` (dict with `getetag`, `calendar-data`). The `calendar-data` value is raw iCalendar text that S02 will parse with the `icalendar` library.
- The discovery chain returns calendars as dicts: `{href, name, color, ctag, supported_components}`. The `href` is the calendar collection URL used for event operations.
- `put_event()` takes `calendar_url`, `event_uid`, `ical_data`, and optional `etag`. Pass `etag=None` for creates (sends If-None-Match: *), pass the current etag for updates (sends If-Match).

### What's fragile
- `get_events()` doesn't extract the root-level sync-token — S02's sync engine needs this for incremental sync. Either extend the parser or do a second parse of the raw XML response.
- The multistatus parser assumes `{DAV:}href` is a direct child of `{DAV:}response`. Some servers may nest it differently — the unit tests only cover Fastmail and Nextcloud variants.

### Authoritative diagnostics
- `backend/tests/test_caldav_client.py` — the canned XML strings are the reference for what server responses look like. Start here when debugging parsing issues.
- `caldav.client` logger at DEBUG level shows every request URL and response status — first place to look when discovery chain fails.

### What assumptions changed
- Originally assumed `test_connection` was a safe function name — pytest's collection phase imports all files matching the test path pattern, so app-level functions named `test_*` get collected. Renamed to `check_connection`.
