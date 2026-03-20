---
id: T01
parent: S04
milestone: M021
provides:
  - Mock CalDAV server with PROPFIND/REPORT/GET/PUT/DELETE handlers
  - Canned iCalendar events (timed, all-day, recurring)
  - Docker mock-caldav service for E2E test infrastructure
key_files:
  - e2e/mock-caldav-api/server.py
  - docker-compose.test.yml
key_decisions:
  - Hand-crafted XML string responses rather than ET builder — matches the pattern from mock-outlook and avoids namespace registration complexity
patterns_established:
  - CalDAV mock follows same BaseHTTPRequestHandler + selftest pattern as mock-outlook but with custom do_PROPFIND/do_REPORT methods
observability_surfaces:
  - GET /health → JSON health check consumed by Docker healthcheck
  - All requests logged to stderr as [mock-caldav] METHOD /path → STATUS
  - python server.py --selftest exercises all endpoints with per-check pass/fail
duration: 20m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T01: Mock CalDAV server with WebDAV XML endpoints and selftest

**Built standalone mock CalDAV server with PROPFIND/REPORT/GET/PUT/DELETE handlers, 3 canned iCalendar events, 12-check selftest, and Docker service wiring**

## What Happened

Created `e2e/mock-caldav-api/server.py` — a ~500-line Python HTTP server that speaks the CalDAV WebDAV XML protocol. The server handles the full discovery chain (PROPFIND for principal → calendar-home → calendar-list), sync-collection REPORT with sync-token for initial and incremental sync, and individual event CRUD with ETag-based optimistic concurrency.

Three canned iCalendar events cover the field mapping surface: a timed event with attendees/VALARM/location/categories, an all-day event with DATE (not DATETIME) and CLASS:PRIVATE, and a recurring event with RRULE WEEKLY/BYDAY/UNTIL.

XML responses use the exact namespace URIs the CalDAVClient parser expects: `DAV:`, `urn:ietf:params:xml:ns:caldav`, `http://calendarserver.org/ns/`. The sync-token lives at the multistatus root level (not per-response), matching what `_extract_sync_token()` looks for.

Added the `mock-caldav` Docker service to `docker-compose.test.yml` and wired it into the api service's `depends_on`.

## Verification

- Selftest: `python3 server.py --selftest` → 12/12 passed, exit 0
- Docker Compose: `grep "mock-caldav" docker-compose.test.yml` confirms service defined and api depends_on includes mock-caldav
- Namespace URIs verified against `caldav_client.py` constants and `test_caldav_client.py` canned XML

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd e2e/mock-caldav-api && python3 server.py --selftest` | 0 | ✅ pass | 2s |
| 2 | `grep "mock-caldav" docker-compose.test.yml` | 0 | ✅ pass | <1s |
| 3 | `grep -A20 "depends_on:" docker-compose.test.yml` (mock-caldav present) | 0 | ✅ pass | <1s |

## Diagnostics

- **Health probe:** `curl http://mock-caldav:8080/health` (or localhost:8080 when running standalone)
- **Request log:** `docker compose -f docker-compose.test.yml logs mock-caldav` — shows every request with method, path, status
- **Quick smoke test:** `python3 e2e/mock-caldav-api/server.py --selftest` — exercises all endpoints standalone

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `e2e/mock-caldav-api/server.py` — Created: Mock CalDAV server with PROPFIND/REPORT/GET/PUT/DELETE, 3 canned iCalendar events, 12-check selftest
- `docker-compose.test.yml` — Modified: Added mock-caldav service with health check, added to api depends_on
- `.gsd/milestones/M021/slices/S04/S04-PLAN.md` — Modified: Added Observability/Diagnostics section, failure-path verification check
- `.gsd/milestones/M021/slices/S04/tasks/T01-PLAN.md` — Modified: Added Observability Impact section
