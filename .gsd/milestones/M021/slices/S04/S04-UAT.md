# S04: E2E Tests + User Guide + Docs — UAT

**Milestone:** M021
**Written:** 2026-03-19

## UAT Type

- UAT mode: mixed (artifact-driven for docs, live-runtime for mock server and unit tests)
- Why this mode is sufficient: Mock server selftest exercises all WebDAV endpoints standalone. E2E test is structurally verified via TypeScript compilation. Docs are artifact-verified via grep checks. Unit tests provide runtime proof of all CalDAV modules.

## Preconditions

- Working directory is the M018 worktree (or main tree with CalDAV app code)
- Python 3.11+ available for mock server selftest
- Node.js 18+ available for TypeScript compilation check
- `uv` available in `backend/` for running pytest
- Docker Compose available if running the E2E test against the full stack

## Smoke Test

Run `cd e2e/mock-caldav-api && python3 server.py --selftest` — should output 12/12 passed with 0 failed.

## Test Cases

### 1. Mock CalDAV server selftest passes

1. `cd e2e/mock-caldav-api`
2. `python3 server.py --selftest`
3. **Expected:** All 12 checks pass:
   - GET /health → 200
   - PROPFIND / → 207 with current-user-principal
   - PROPFIND /principals/user/ → 207 with calendar-home-set
   - PROPFIND /calendars/user/ → 207 with Work + Personal calendars
   - REPORT initial sync → 207 with Team Standup event + sync-token
   - REPORT incremental sync → 207 with new sync-token, no events
   - GET team-standup-001.ics → 200 with ETag and VCALENDAR content
   - PUT with matching ETag → 204
   - PUT with wrong ETag → 412 Precondition Failed
   - DELETE → 204
   - GET deleted event → 404
   - GET unknown event → 404

### 2. Docker service wired correctly

1. `grep -A5 "mock-caldav:" docker-compose.test.yml`
2. `grep -A20 "depends_on:" docker-compose.test.yml | grep mock-caldav`
3. **Expected:** mock-caldav service defined with port 8080, healthcheck on /health, and present in api service depends_on

### 3. E2E test file compiles

1. `cd e2e && npx tsc --noEmit tests/39-caldav-calendar/caldav-calendar-sync.spec.ts`
2. **Expected:** Exit 0, no TypeScript errors

### 4. E2E selectors match template HTML

1. `grep -A20 "caldavCalendarSync" e2e/helpers/selectors.ts`
2. Cross-reference selector IDs with `apps/caldav-calendar/frontend/templates/connect.html` and `connect_status.html`
3. **Expected:** All 13 selectors match actual HTML IDs/classes:
   - `#caldav-server-url`, `#caldav-username`, `#caldav-password` in connect.html
   - `#sync-now-btn`, `.connection-status`, `.account-username`, `.calendar-checkbox-item`, `.sync-stats`, `.credentials-form`, `.calendars-section`, `.sync-config-form` in connect_status.html

### 5. Full unit test suite passes

1. `cd backend && uv run pytest tests/test_caldav_*.py -v`
2. **Expected:** 229 tests pass in <2s across 5 test files (auth, client, field_mapper, person_matcher, sync_engine)

### 6. Chapter 39 exists with field mapping tables

1. `head -20 docs/guide/39-caldav-calendar-sync.md`
2. `grep -c "|" docs/guide/39-caldav-calendar-sync.md` (markdown table rows)
3. **Expected:** Chapter title "CalDAV Calendar Sync", multiple field mapping tables (Core Properties, Attendees/Recurrence, STATUS, CLASS, TRANSP mapping tables)

### 7. README TOC has Chapter 39

1. `grep "39.*[Cc]al[Dd][Aa][Vv]" docs/guide/README.md`
2. **Expected:** Entry like `39. [CalDAV Calendar Sync](39-caldav-calendar-sync.md)`

### 8. Glossary has CalDAV entry

1. `grep -i "caldav calendar sync" docs/guide/appendix-d-glossary.md`
2. **Expected:** Bold glossary entry with CalDAV description mentioning PROPFIND, REPORT, PUT, HTTP Basic

### 9. Navigation chain intact

1. `grep "Chapter 39" docs/guide/38-outlook-calendar-sync.md`
2. `grep "Chapter 38" docs/guide/39-caldav-calendar-sync.md`
3. `grep "Appendix A" docs/guide/39-caldav-calendar-sync.md`
4. **Expected:** Ch 38 Next → Ch 39, Ch 39 Previous → Ch 38, Ch 39 Next → Appendix A

### 10. htmx prefix audit clean

1. `grep -rE "hx-post|hx-get" apps/caldav-calendar/frontend/templates/ | grep -v "/app/caldav-calendar/" | wc -l`
2. **Expected:** 0 (all htmx URLs use the `/app/caldav-calendar/` proxy prefix)

## Edge Cases

### Mock server handles malformed requests

1. `curl -X PROPFIND http://localhost:8080/nonexistent` (when server is running)
2. **Expected:** 404 or appropriate error, not a crash. Server continues serving.

### Mock server ETag concurrency enforcement

1. Run selftest — checks 8 and 9 specifically test matching vs wrong ETag
2. **Expected:** Matching ETag → 204, wrong ETag → 412. This proves the mock exercises CalDAVClient's If-Match header handling.

### Canned events cover all field types

1. Inspect `e2e/mock-caldav-api/server.py` CANNED_EVENTS
2. **Expected:** Three events covering: timed event (DTSTART/DTEND with TZID, ATTENDEE list, VALARM, LOCATION, CATEGORIES), all-day event (DATE not DATETIME, CLASS:PRIVATE), recurring event (RRULE with FREQ/BYDAY/UNTIL)

## Failure Signals

- Selftest exits non-zero or reports any FAIL — mock server is broken
- TypeScript compilation fails — E2E test has syntax errors or import issues
- pytest returns failures — CalDAV module code has regressions
- `grep -v "/app/caldav-calendar/"` returns >0 lines — htmx prefix violation present
- Navigation grep returns empty — nav chain is broken
- README/glossary grep returns empty — cross-references missing

## Requirements Proved By This UAT

- Milestone DoD items: mock server selftest, E2E test structure, Chapter 39, README/glossary/nav-chain
- 229 unit tests prove all CalDAV modules (auth, client, field mapper, sync engine, person matcher)

## Not Proven By This UAT

- Runtime E2E execution against Docker stack (structurally verified only — consistent with prior sync app milestones)
- Real CalDAV server compatibility (mock server only — by design, no real CalDAV server in test infrastructure)

## Notes for Tester

- The mock server runs standalone (`python3 server.py --selftest`) — no Docker needed for the selftest
- The E2E test requires the full Docker test stack with mock-caldav service. If running manually, ensure `docker compose -f docker-compose.test.yml up -d` includes the mock-caldav service
- The E2E test may be blocked by the pre-existing app subprocess startup issue (500 error on first app page load) — this is a platform bug, not a CalDAV-specific issue
