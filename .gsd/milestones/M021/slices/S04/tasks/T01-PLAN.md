---
estimated_steps: 8
estimated_files: 2
---

# T01: Mock CalDAV server with WebDAV XML endpoints and selftest

**Slice:** S04 — E2E Tests + User Guide + Docs
**Milestone:** M021

## Description

Build a standalone Python HTTP server at `e2e/mock-caldav-api/server.py` that speaks CalDAV's WebDAV XML protocol. Unlike the JSON REST mocks for Google/Outlook, this mock must handle custom HTTP methods (PROPFIND, REPORT) and return XML multistatus responses with correct namespace URIs plus raw iCalendar text for event resources.

The CalDAV app's client (`apps/caldav-calendar/services/caldav_client.py`) builds XML request bodies and parses responses using specific namespace URIs (`{DAV:}`, `{urn:ietf:params:xml:ns:caldav}`, `{http://calendarserver.org/ns/}`). The mock must emit responses that match what the client parser expects — the unit tests in `backend/tests/test_caldav_client.py` contain the authoritative canned XML.

Also adds the `mock-caldav` Docker service to `docker-compose.test.yml` and wires it into the api service's `depends_on`.

## Steps

1. **Create `e2e/mock-caldav-api/server.py`** with `BaseHTTPRequestHandler`. Override `do_GET`, `do_PUT`, `do_DELETE`, and add `do_PROPFIND` and `do_REPORT` methods (Python's BaseHTTPRequestHandler dispatches custom methods via `do_METHODNAME()` — case-sensitive).

2. **Define canned iCalendar data** (embedded as Python string constants):
   - **Timed event** "Team Standup" — UID `team-standup-001`, DTSTART/DTEND with timezone, LOCATION "Conference Room B", 2 ATTENDEEs (with PARTSTAT=ACCEPTED and PARTSTAT=NEEDS-ACTION), VALARM (15min before), CATEGORIES "work,standup"
   - **All-day event** "Company Holiday" — UID `company-holiday-002`, DTSTART as DATE (not DATETIME), CLASS:PRIVATE
   - **Recurring event** "Weekly Review" — UID `weekly-review-003`, RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR;UNTIL=20261231T000000Z

   Each event must be wrapped in a full VCALENDAR/VEVENT structure. Keep each property on one line (no RFC 5545 line folding — the library handles unfolding but cleaner to avoid it).

3. **Implement PROPFIND endpoints** (check the `Depth` header):
   - `PROPFIND /` (Depth:0) → 207 multistatus with `<d:current-user-principal>` pointing to `/principals/user/`
   - `PROPFIND /principals/user/` (Depth:0) → 207 multistatus with `<c:calendar-home-set>` pointing to `/calendars/user/`
   - `PROPFIND /calendars/user/` (Depth:1) → 207 multistatus listing 2 calendars: "Work" at `/calendars/user/work/` and "Personal" at `/calendars/user/personal/` with displayname, ctag, supported-calendar-component-set (VEVENT). Include the home collection `/calendars/user/` as first entry (client filters it out by comparing against the home URL).

   XML namespace URIs that the client parser expects:
   - `DAV:` (prefix `d`)
   - `urn:ietf:params:xml:ns:caldav` (prefix `c`)
   - `http://calendarserver.org/ns/` (prefix `cs`)

4. **Implement REPORT endpoint** for sync-collection:
   - `REPORT /calendars/user/work/` — parse request body XML. If no `<d:sync-token>` in request (initial sync): return 207 multistatus with 3 events (calendar-data containing the canned .ics), plus `<d:sync-token>` at the multistatus root level (`sync-token-initial-001`). If request has sync-token: return empty multistatus with new sync-token (`sync-token-incremental-002`) — simulates "no changes since last sync".

   The `<c:calendar-data>` element contains the full VCALENDAR text. The client extracts it as `{urn:ietf:params:xml:ns:caldav}calendar-data`.

5. **Implement GET/PUT/DELETE for individual events:**
   - `GET /calendars/user/work/{uid}.ics` → 200 with `Content-Type: text/calendar`, body = full VCALENDAR text, ETag header (e.g., `"etag-{uid}-v1"`)
   - `PUT /calendars/user/work/{uid}.ics` → Check `If-Match` header against stored ETag. If match or no If-Match: 204 with new ETag. If mismatch: 412 Precondition Failed.
   - `DELETE /calendars/user/work/{uid}.ics` → 204 No Content

   Store a mutable `ETAGS` dict mapping uid → current etag for concurrency simulation.

6. **Implement GET /health** → 200 JSON `{"status": "ok", "service": "mock-caldav"}`.

7. **Add selftest function** (`--selftest` CLI flag). Use `urllib.request` (no external deps) to exercise all endpoints against a locally-started server. Selftest checks (target 10-12):
   - GET /health → 200
   - PROPFIND / (Depth:0) → 207, body contains `current-user-principal`
   - PROPFIND /principals/user/ (Depth:0) → 207, body contains `calendar-home-set`
   - PROPFIND /calendars/user/ (Depth:1) → 207, body contains "Work" and "Personal"
   - REPORT /calendars/user/work/ (initial) → 207, body contains "Team Standup" and sync-token
   - REPORT /calendars/user/work/ (incremental with sync-token) → 207, body contains new sync-token, no calendar-data
   - GET /calendars/user/work/team-standup-001.ics → 200, has ETag header, body contains VCALENDAR
   - PUT /calendars/user/work/team-standup-001.ics (with matching ETag) → 204
   - PUT /calendars/user/work/team-standup-001.ics (with wrong ETag) → 412
   - DELETE /calendars/user/work/team-standup-001.ics → 204

   For PROPFIND/REPORT requests, use `urllib.request.Request` with `method='PROPFIND'` and `method='REPORT'` — Python's urllib supports custom method strings.

8. **Add `mock-caldav` service to `docker-compose.test.yml`:**
   - Image: `python:3.12-slim`
   - Volume: `./e2e/mock-caldav-api:/app:ro`
   - Working dir: `/app`
   - Command: `python server.py`
   - Health check: `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"`
   - Network: `sempkm-test`
   - Add `mock-caldav: condition: service_healthy` to `api` service's `depends_on`

   No env vars needed on the api container — CalDAV server URL is user-entered in the credential form, not env-var overridden.

## Must-Haves

- [ ] `do_PROPFIND` and `do_REPORT` custom method handlers (case-sensitive)
- [ ] XML responses use correct namespace URIs: `DAV:`, `urn:ietf:params:xml:ns:caldav`, `http://calendarserver.org/ns/`
- [ ] Canned iCalendar events: timed with attendees/VALARM/location, all-day with DATE, recurring with RRULE
- [ ] Sync-token in multistatus root element (not per-response)
- [ ] ETag quoting with double quotes (`"etag-value"`)
- [ ] PUT checks If-Match header for ETag concurrency (412 on mismatch)
- [ ] Selftest exercises all endpoints (10+ checks)
- [ ] Docker service added to docker-compose.test.yml with health check

## Verification

- `cd e2e/mock-caldav-api && python server.py --selftest` — all checks pass, exits 0
- `grep "mock-caldav" docker-compose.test.yml` — service defined
- `grep "mock-caldav" docker-compose.test.yml | grep "depends_on" -A5` — api depends_on includes mock-caldav

## Observability Impact

- **New health endpoint:** `GET /health` returns JSON `{"status": "ok", "service": "mock-caldav"}` — consumed by Docker healthcheck and available for manual probing
- **Request logging:** Every request logs `[mock-caldav] METHOD /path → STATUS` to stderr — visible via `docker compose logs mock-caldav` or direct stderr when running standalone
- **Selftest diagnostic:** `python server.py --selftest` provides a built-in diagnostic surface — run it anytime to verify all endpoints work correctly (10+ checks with per-check pass/fail)
- **Error paths visible:** 400 for bad XML, 404 for unknown events, 412 for ETag mismatch — all return descriptive status codes a future agent or E2E test can assert on
- **Failure state:** No persistent state — the mock resets on restart. ETag concurrency simulation uses in-memory dict only.

## Inputs

- `e2e/mock-outlook-api/server.py` — Reference pattern for mock server structure (BaseHTTPRequestHandler, selftest pattern, Docker service)
- `backend/tests/test_caldav_client.py` — Authoritative canned XML responses showing exactly what namespace URIs and element structures the client parser expects
- `apps/caldav-calendar/services/caldav_client.py` — The client that will talk to this mock, showing what XML it sends and what it parses from responses

## Expected Output

- `e2e/mock-caldav-api/server.py` — ~450-550 line mock server with PROPFIND/REPORT/GET/PUT/DELETE handlers, 3 canned events, selftest with 10+ checks
- `docker-compose.test.yml` — Modified with `mock-caldav` service and api depends_on entry
