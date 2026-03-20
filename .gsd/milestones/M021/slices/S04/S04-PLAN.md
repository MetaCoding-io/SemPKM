# S04: E2E Tests + User Guide + Docs

**Goal:** Mock CalDAV server passes selftest, Playwright E2E test proves full install → configure → sync → verify → push lifecycle, Chapter 39 user guide documents CalDAV setup and field mapping, README/glossary/appendix updated.
**Demo:** `python e2e/mock-caldav-api/server.py --selftest` passes all checks. `e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts` structurally complete with correct selectors and SPARQL queries. Chapter 39 exists with field mapping tables and server-specific notes. Navigation chain intact from Ch 38 → Ch 39 → Appendix A.

## Must-Haves

- Mock CalDAV server at `e2e/mock-caldav-api/server.py` handling PROPFIND, REPORT, GET, PUT, DELETE with canned XML/iCalendar responses
- Mock server selftest exercising all endpoints
- `mock-caldav` Docker service in `docker-compose.test.yml`
- Playwright E2E test at `e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts` with 7-phase lifecycle
- CalDAV selectors in `e2e/helpers/selectors.ts`
- Chapter 39 user guide at `docs/guide/39-caldav-calendar-sync.md`
- README TOC entry for Ch 39
- Glossary entry for "CalDAV Calendar Sync"
- Navigation chain: Ch 38 → Ch 39 → Appendix A

## Proof Level

- This slice proves: final-assembly
- Real runtime required: yes (Docker stack for E2E, selftest for mock)
- Human/UAT required: no

## Verification

- `cd e2e/mock-caldav-api && python server.py --selftest` — all checks pass (10+ selftest checks)
- E2E test file exists and TypeScript is syntactically valid: `npx tsc --noEmit e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts` (or equivalent check)
- Selectors in `e2e/helpers/selectors.ts` include `caldavCalendarSync` section matching template IDs/classes
- `docs/guide/39-caldav-calendar-sync.md` exists with field mapping tables
- `grep "39-caldav" docs/guide/README.md` returns Ch 39 entry
- `grep -i "caldav" docs/guide/appendix-d-glossary.md` returns glossary entry
- Nav chain verified: `grep "Chapter 39" docs/guide/38-outlook-calendar-sync.md` and `grep "Appendix A" docs/guide/39-caldav-calendar-sync.md`
- htmx prefix audit: `grep -rE "hx-post|hx-get" apps/caldav-calendar/frontend/templates/ | grep -v "/app/caldav-calendar/"` returns 0 matches
- Full unit test suite: `pytest tests/test_caldav_*.py -v` — 229+ tests pass
- Mock server error path: selftest includes PUT with wrong ETag → 412 (failure-path coverage)

## Observability / Diagnostics

- **Mock CalDAV health:** `GET http://mock-caldav:8080/health` returns `{"status": "ok", "service": "mock-caldav"}` — visible in Docker healthcheck logs
- **Selftest as diagnostic surface:** `python server.py --selftest` exercises all endpoints with per-check pass/fail output and exits non-zero on any failure — usable as a quick smoke test at any time
- **Server request logging:** All requests logged to stderr as `[mock-caldav] METHOD /path → STATUS` — visible via `docker compose logs mock-caldav`
- **Failure visibility:** PROPFIND/REPORT return 400 with plain-text error for malformed XML. GET returns 404 for unknown event UIDs. PUT returns 412 for ETag mismatch. All error paths include status code and human-readable body.
- **Redaction:** No real credentials flow through the mock — it ignores auth headers entirely. No secrets to redact.

## Integration Closure

- Upstream surfaces consumed: Complete CalDAV app from S01–S03 (auth, client, field mapper, sync engine, person matcher, app routes, templates)
- New wiring introduced: `mock-caldav` Docker service, `api` container `depends_on` mock-caldav
- What remains before the milestone is truly usable end-to-end: nothing — this is the terminal slice

## Tasks

- [x] **T01: Mock CalDAV server with WebDAV XML endpoints and selftest** `est:45m`
  - Why: The mock server is the E2E test's infrastructure dependency — it provides canned WebDAV XML and iCalendar responses that the CalDAV app talks to during testing. Must complete before T02.
  - Files: `e2e/mock-caldav-api/server.py`, `docker-compose.test.yml`
  - Do: Build a Python HTTP server handling PROPFIND (discovery chain), REPORT (sync-collection with sync-token), GET (.ics with ETag), PUT (If-Match concurrency), DELETE. Canned iCalendar data includes a timed event with attendees/VALARM/location, an all-day event, and a recurring event with RRULE. Add `mock-caldav` service to Docker Compose. Selftest exercises all endpoints.
  - Verify: `cd e2e/mock-caldav-api && python server.py --selftest` — all checks pass
  - Done when: Selftest passes with 10+ checks covering PROPFIND/REPORT/GET/PUT/DELETE and health

- [x] **T02: Playwright E2E test and selectors for CalDAV sync lifecycle** `est:40m`
  - Why: Proves the complete install → configure → sync → verify → push lifecycle against the mock server. Adds CalDAV selectors to the shared helpers file.
  - Files: `e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts`, `e2e/helpers/selectors.ts`
  - Do: Follow the Outlook test's 7-phase structure. Phase 3 is simpler — no OAuth redirect simulation, just fill 3 form fields (server URL `http://mock-caldav:8080/`, username, password) and submit. Phase 5 verifies synced events via SPARQL. Add `caldavCalendarSync` selector block matching template IDs.
  - Verify: TypeScript compiles (`npx tsc --noEmit` or `node -e "..."`), selectors match template HTML, SPARQL queries syntactically valid
  - Done when: E2E test file exists with 7 phases, selectors added, structurally mirrors Outlook test

- [x] **T03: Chapter 39 user guide and README/glossary/nav-chain updates** `est:35m`
  - Why: Documents CalDAV setup, field mapping, and troubleshooting for end users. Completes the docs deliverable and updates all cross-references.
  - Files: `docs/guide/39-caldav-calendar-sync.md`, `docs/guide/README.md`, `docs/guide/appendix-d-glossary.md`, `docs/guide/38-outlook-calendar-sync.md`
  - Do: Follow Ch 38 Outlook guide structure. Replace Azure AD OAuth section with simpler HTTP Basic "Connecting Your Server" section. Add field mapping tables, recurrence handling (native RRULE), server-specific notes (Fastmail/Nextcloud/Synology/Radicale URLs), troubleshooting. Update README TOC, glossary, and nav chain.
  - Verify: `grep "39-caldav" docs/guide/README.md` finds entry; `grep -i "caldav" docs/guide/appendix-d-glossary.md` finds glossary entry; nav chain Ch 38 → Ch 39 → Appendix A verified
  - Done when: Chapter 39 exists with field mapping tables, README has TOC entry, glossary has CalDAV entry, nav chain connects Ch 38 → Ch 39 → Appendix A

## Files Likely Touched

- `e2e/mock-caldav-api/server.py` (create)
- `docker-compose.test.yml` (modify — add mock-caldav service + api depends_on)
- `e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts` (create)
- `e2e/helpers/selectors.ts` (modify — add caldavCalendarSync section)
- `docs/guide/39-caldav-calendar-sync.md` (create)
- `docs/guide/README.md` (modify — add Ch 39 TOC entry)
- `docs/guide/appendix-d-glossary.md` (modify — add CalDAV glossary entry)
- `docs/guide/38-outlook-calendar-sync.md` (modify — update nav chain Next → Ch 39)
