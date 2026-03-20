# S04: E2E Tests + User Guide + Docs — Research

**Date:** 2026-03-19

## Summary

Terminal slice producing the mock CalDAV server, Playwright E2E test, Chapter 39 user guide, and README/glossary/appendix updates. This is the third calendar sync E2E/docs slice — M018/S05 (Google) and M020/S04 (Outlook) establish the pattern exactly. CalDAV is slightly simpler in some areas (HTTP Basic auth → no OAuth dance) and slightly different in one key way: the mock server must speak WebDAV/XML and return iCalendar text instead of JSON. The server URL is entered in the credential form (not env-var overridden like Google/Outlook), so the mock URL (`http://mock-caldav:8080/`) goes directly into the form field.

Three independent deliverables (mock server, E2E test, docs) — natural three-task decomposition.

## Recommendation

**T01: Mock CalDAV server + selftest** — Standalone Python HTTP server at `e2e/mock-caldav-api/server.py` handling PROPFIND, REPORT, GET, PUT, DELETE with canned XML/iCalendar responses. Docker service `mock-caldav` in `docker-compose.test.yml`. Selftest validates all endpoints.

**T02: Playwright E2E test** — `e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts` following the Outlook test's 7-phase structure. Simpler auth phase (just fill form fields, no OAuth redirect simulation). Add CalDAV selectors to `e2e/helpers/selectors.ts`.

**T03: Chapter 39 user guide + README/glossary/appendix** — Follow the Ch 38 Outlook guide structure adapted for CalDAV (simpler auth section — HTTP Basic instead of Azure AD). Update README TOC, appendix-d-glossary, nav chain (Ch 38 → Ch 39 → Appendix A).

**Build order:** T01 first (mock server is the E2E dependency), T02 second (E2E depends on mock), T03 independent of T01/T02 (pure docs).

## Implementation Landscape

### Key Files

**Mock server (create):**
- `e2e/mock-caldav-api/server.py` — Mock CalDAV server (~450-550 lines). Must handle:
  - `GET /health` → 200 JSON health check
  - `PROPFIND /` (Depth:0) → 207 multistatus with `DAV:current-user-principal` pointing to `/principals/user/`
  - `PROPFIND /principals/user/` (Depth:0) → 207 multistatus with `caldav:calendar-home-set` pointing to `/calendars/user/`
  - `PROPFIND /calendars/user/` (Depth:1) → 207 multistatus listing 2 calendars (Work, Personal) with displayname, ctag, supported-components (VEVENT)
  - `REPORT /calendars/user/work/` (sync-collection) → 207 multistatus with 3 events (.ics in calendar-data), sync-token
  - `REPORT /calendars/user/work/` (with sync-token) → 207 multistatus with empty value list + new sync-token (incremental)
  - `GET /calendars/user/work/{uid}.ics` → 200 with full VCALENDAR text + ETag header (for push fetch)
  - `PUT /calendars/user/work/{uid}.ics` → 204 with If-Match ETag check (for push write-back)
  - `DELETE /calendars/user/work/{uid}.ics` → 204
  - `--selftest` mode exercising all endpoints

**Canned iCalendar data (embedded in server.py):**
- Timed event: "Team Standup" with DTSTART/DTEND, LOCATION, 2 ATTENDEE (with PARTSTAT), VALARM, CATEGORIES
- All-day event: "Company Holiday" with DATE (not DATETIME), CLASS:PRIVATE
- Recurring event: "Weekly Review" with RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR;UNTIL=...

**E2E test (create):**
- `e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts` — ~350-400 lines, 7 phases:
  - Phase 0: Cleanup (remove caldav-calendar if installed from prior run)
  - Phase 1: Prerequisite (install basic-pkm model)
  - Phase 2: Install caldav-calendar app, wait for Running
  - Phase 3: Enter credentials (server URL `http://mock-caldav:8080/`, username, password) — no OAuth, just form fill + submit
  - Phase 4: Select calendars + configure sync (bidirectional)
  - Phase 5: Sync Now + verify events via SPARQL (check "Team Standup", "Company Holiday" labels + RRULE)
  - Phase 6: Admin detail + cleanup (uninstall)

**Selectors (modify):**
- `e2e/helpers/selectors.ts` — Add `caldavCalendarSync` section:
  - `serverUrlInput: '#caldav-server-url'`
  - `usernameInput: '#caldav-username'`
  - `passwordInput: '#caldav-password'`
  - `credentialsSubmitBtn: '.credentials-form button[type="submit"]'`
  - `connectStatus: '.connection-status'`
  - `accountUsername: '.account-username'`
  - `calendarCheckbox: '.calendar-checkbox-item input[type="checkbox"]'`
  - `saveCalendarsBtn: '.calendars-section button[type="submit"]'`
  - `syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]'`
  - `saveConfigBtn: '.sync-config-form button[type="submit"]'`
  - `syncNowBtn: '#sync-now-btn'`
  - `syncStats: '.sync-stats'`

**Docker compose (modify):**
- `docker-compose.test.yml` — Add `mock-caldav` service (same pattern as mock-outlook: `python:3.12-slim`, mount `./e2e/mock-caldav-api:/app:ro`, port 8080, health check on `/health`). No env vars needed on the API container (CalDAV URL is user-entered, not env-overridden).

**Docs (create/modify):**
- `docs/guide/39-caldav-calendar-sync.md` — Chapter 39 (~350-400 lines). Sections:
  - Prerequisites (basic-pkm v2.1+)
  - Installing the App
  - Connecting Your Server (HTTP Basic: server URL, username, password — no OAuth setup section)
  - Selecting Calendars
  - Sync Configuration (direction, poll interval)
  - Running a Sync (sync-collection REPORT with sync-token)
  - Field Mapping tables (Core Properties, Status/Visibility, Recurrence, Attendees, Reminders, Tags, Sync Metadata)
  - RSVP Push-Back (fetch-modify-PUT pattern, ETag concurrency)
  - Recurrence Handling (native RRULE passthrough — simpler than Outlook)
  - Server-Specific Notes (Fastmail, Nextcloud, Synology, Radicale URLs and quirks)
  - Troubleshooting
- `docs/guide/README.md` — Add Ch 39 entry after Ch 38
- `docs/guide/appendix-d-glossary.md` — Add "CalDAV Calendar Sync" entry
- `docs/guide/38-outlook-calendar-sync.md` — Update nav chain: Next → Ch 39
- `docs/guide/39-caldav-calendar-sync.md` — Nav: Prev → Ch 38, Next → Appendix A

**No appendix-a env vars needed** — CalDAV doesn't use env var overrides (URL is user-entered). The mock is reached directly by entering `http://mock-caldav:8080/` in the credential form.

### Key Patterns to Follow

**Mock server pattern:** Clone from `e2e/mock-outlook-api/server.py` structure (BaseHTTPRequestHandler, `_json_response` helper, `selftest()` function). Key differences:
- Override `do_PROPFIND`, `do_REPORT`, `do_PUT`, `do_DELETE` instead of `do_GET`, `do_POST`, `do_PATCH`
- Return XML (`Content-Type: application/xml; charset=utf-8`) with `text/xml` for multistatus responses
- Return iCalendar text (`Content-Type: text/calendar`) for GET .ics
- Return ETags in response headers
- Parse `Depth` header for PROPFIND depth
- Parse `If-Match` header for PUT concurrency check

**E2E test pattern:** Clone from `e2e/tests/38-outlook-sync/outlook-calendar-sync.spec.ts`. Phase 3 is simpler — no OAuth redirect simulation, just fill 3 form fields and submit. The `connect_status.html` template for CalDAV shows `account-username` (not `account-email` like Google/Outlook).

**Docs pattern:** Clone from `docs/guide/38-outlook-calendar-sync.md`. Omit the "Setting Up Azure AD" section entirely. Replace with simpler "Connecting Your Server" section (enter URL + username + password). Add "Server-Specific Notes" section with known server URL patterns.

### Build Order

**T01: Mock CalDAV server** (est: 45-60min)
- Creates `e2e/mock-caldav-api/server.py` with WebDAV XML responses
- Modifies `docker-compose.test.yml` to add `mock-caldav` service
- Selftest validates all endpoints
- **Must complete before T02** (E2E depends on mock)

**T02: Playwright E2E test** (est: 30-45min)
- Creates `e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts`
- Modifies `e2e/helpers/selectors.ts` (add CalDAV selectors)
- **Depends on T01** (mock server must exist)

**T03: Chapter 39 + docs updates** (est: 30-40min)
- Creates `docs/guide/39-caldav-calendar-sync.md`
- Modifies README TOC, glossary, nav chain
- **Independent of T01/T02** — pure docs, can run in parallel with T02

### Verification Approach

**T01:** `cd e2e/mock-caldav-api && python server.py --selftest` — all checks pass (target: 10-12 selftest checks)

**T02:** Not runnable without Docker stack — verify structurally: TypeScript compiles, selectors match template HTML IDs/classes, SPARQL queries syntactically valid, phase structure matches Outlook test

**T03:** Files exist with correct structure, README TOC has Ch 39 entry, glossary has CalDAV entry, nav chain Ch 38 → Ch 39 → Appendix A verified via grep

**Full milestone verification:**
- `pytest tests/test_caldav_*.py -v` — all 229+ unit tests pass
- `python e2e/mock-caldav-api/server.py --selftest` — all selftest checks pass
- `grep -r "hx-post\|hx-get" apps/caldav-calendar/frontend/templates/ | grep -v "/app/caldav-calendar/"` → 0 matches (htmx prefix audit)
- Ch 39 exists with field mapping tables, glossary entry present, README TOC updated

## Constraints

- CalDAV mock must handle custom HTTP methods (PROPFIND, REPORT) — Python's `BaseHTTPRequestHandler` dispatches via `do_PROPFIND()`, `do_REPORT()` method naming
- CalDAV mock returns XML (multistatus) not JSON — XML namespace handling must be correct for the client parser
- Canned iCalendar text must be valid RFC 5545 — the `icalendar` library in the CalDAV app parses it; malformed .ics causes parse failures
- No env var override for CalDAV server URL — the mock URL goes in the credential form. The mock must be reachable from the API container at `http://mock-caldav:8080/`
- CalDAV auth check sends PROPFIND (not GET) — mock must respond to `PROPFIND /` with 207 to pass connection test

## Common Pitfalls

- **BaseHTTPRequestHandler method naming:** Custom methods need `do_PROPFIND`, `do_REPORT`, etc. Case-sensitive. If the method name doesn't match exactly, the server returns 501 Not Implemented.
- **XML namespace in multistatus responses:** Client parser uses `{DAV:}multistatus`, `{DAV:}response`, `{urn:ietf:params:xml:ns:caldav}calendar-data}` etc. Mock must emit XML with correct namespace URIs.
- **Sync-token in multistatus root:** The `_extract_sync_token()` method looks for `<d:sync-token>` as a child of `<d:multistatus>`. Mock must include this element in REPORT responses.
- **ETag quoting:** ETags must be enclosed in double quotes in HTTP headers (`"etag-value-1"`, not `etag-value-1`). CalDAV client passes these directly to If-Match headers.
- **iCalendar line folding:** RFC 5545 allows long lines to be folded (continuation on next line starts with space). The `icalendar` library handles unfolding, but canned .ics data should be syntactically correct. Safest to keep each property on one line for mock data.
- **Calendar list PROPFIND Depth:1:** The client compares resolved href against the home collection URL to skip the home entry. Mock must return the home collection as the first entry (which gets filtered out) plus child calendar entries.
