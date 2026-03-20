---
id: S04
parent: M021
milestone: M021
provides:
  - Mock CalDAV server with PROPFIND/REPORT/GET/PUT/DELETE and 12-check selftest
  - 7-phase Playwright E2E test for full CalDAV sync lifecycle
  - CalDAV selectors in shared e2e helpers
  - Chapter 39 user guide with field mapping tables and server-specific notes
  - README TOC, glossary, and navigation chain updates
requires:
  - slice: S01
    provides: CalDAVClient, auth module, app routes, templates
  - slice: S02
    provides: Field mapper, sync engine pull, person matcher, settings UI
  - slice: S03
    provides: Push sync, bpkm_to_ical_event reverse mapping, ETag concurrency
affects: []
key_files:
  - e2e/mock-caldav-api/server.py
  - docker-compose.test.yml
  - e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts
  - e2e/helpers/selectors.ts
  - docs/guide/39-caldav-calendar-sync.md
  - docs/guide/README.md
  - docs/guide/appendix-d-glossary.md
  - docs/guide/38-outlook-calendar-sync.md
key_decisions:
  - Hand-crafted XML string responses in mock server (matches mock-outlook pattern, avoids ET namespace complexity)
  - accountUsername selector instead of accountEmail (CalDAV uses username-based auth, not email)
  - No Appendix A update needed — CalDAV has no environment variable overrides (server URL is user-entered)
patterns_established:
  - CalDAV mock follows BaseHTTPRequestHandler + selftest pattern from prior sync apps, with custom do_PROPFIND/do_REPORT methods for WebDAV
  - CalDAV E2E test follows Outlook 7-phase structure but with simplified Phase 3 (direct form fill instead of OAuth redirect)
  - CalDAV user guide follows Ch 38 Outlook structure but replaces OAuth section with HTTP Basic credentials section
observability_surfaces:
  - GET /health → JSON health check consumed by Docker healthcheck
  - All mock requests logged to stderr as [mock-caldav] METHOD /path → STATUS
  - python server.py --selftest exercises all endpoints with per-check pass/fail (12 checks)
  - E2E test phase labels and SPARQL verification in Phase 5
drill_down_paths:
  - .gsd/milestones/M021/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M021/slices/S04/tasks/T02-SUMMARY.md
  - .gsd/milestones/M021/slices/S04/tasks/T03-SUMMARY.md
duration: 47m
verification_result: passed
completed_at: 2026-03-19
---

# S04: E2E Tests + User Guide + Docs

**Mock CalDAV server with 12-check selftest, 304-line Playwright E2E test covering full sync lifecycle, Chapter 39 user guide with field mapping tables and server-specific notes, README/glossary/nav-chain updated**

## What Happened

Three tasks assembled the final deliverables for the CalDAV Calendar Sync milestone.

**T01 — Mock CalDAV Server:** Built a ~500-line Python HTTP server speaking the full CalDAV WebDAV XML protocol. It handles the discovery chain (PROPFIND for principal → calendar-home → calendar-list), sync-collection REPORT with sync-token for initial and incremental sync, and individual event CRUD with ETag-based concurrency. Three canned iCalendar events cover the field mapping surface: a timed event with attendees/VALARM/location/categories, an all-day event with DATE and CLASS:PRIVATE, and a recurring event with RRULE WEEKLY/BYDAY/UNTIL. XML responses use the exact namespace URIs the CalDAVClient parser expects. The selftest exercises all 12 check points including the 412 Precondition Failed path for wrong ETags. Added `mock-caldav` service to `docker-compose.test.yml` with healthcheck and wired it into the api service's `depends_on`.

**T02 — Playwright E2E Test:** Created a 304-line test following the Outlook test's 7-phase structure. Phase 3 is simplified — CalDAV uses HTTP Basic auth, so it fills 3 form fields and submits directly instead of simulating an OAuth redirect. All other phases mirror the Outlook pattern. Added 13 CalDAV-specific selectors to the shared helpers file, all verified against actual template HTML. SPARQL verification in Phase 5 checks for "Team Standup" and "Company Holiday" labels from the mock server's canned events.

**T03 — Chapter 39 User Guide:** Wrote a 368-line chapter following the Ch 38 Outlook pattern but adapted for CalDAV's simpler auth model. Key sections: HTTP Basic credentials with PROPFIND discovery chain explanation, two field mapping table groups (Core Properties + Attendees/Recurrence), RSVP push-back with ETag concurrency, native RRULE passthrough, server-specific URL notes (Fastmail/Nextcloud/Synology/Radicale), and troubleshooting. Updated README TOC, glossary (alphabetically positioned), and Ch 38 nav footer. Confirmed no Appendix A update needed — no `CALDAV_*` env vars.

## Verification

| # | Check | Result |
|---|-------|--------|
| 1 | `python3 server.py --selftest` — 12/12 checks pass | ✅ |
| 2 | E2E test exists (304 lines) | ✅ |
| 3 | TypeScript compiles clean (`npx tsc --noEmit`) | ✅ |
| 4 | `caldavCalendarSync` selectors in `e2e/helpers/selectors.ts` | ✅ |
| 5 | Chapter 39 exists (368 lines) with field mapping tables | ✅ |
| 6 | README TOC has Ch 39 entry | ✅ |
| 7 | Glossary has CalDAV entry | ✅ |
| 8 | Nav chain: Ch 38 → Ch 39 | ✅ |
| 9 | Nav chain: Ch 39 → Appendix A | ✅ |
| 10 | htmx prefix audit: 0 violations | ✅ |
| 11 | Full unit test suite: 229 tests pass in 0.34s | ✅ |
| 12 | Mock server includes PUT wrong ETag → 412 (failure path) | ✅ |

## Requirements Advanced

- CDAV requirements (CDAV-01 through CDAV-10) referenced in roadmap were never registered in REQUIREMENTS.md. This slice completes the milestone's DoD items: mock server selftest, E2E test, Chapter 39 guide, README/glossary/nav-chain updates.

## Requirements Validated

- none (CDAV requirements not registered — milestone roadmap references CDAV-01 through CDAV-10 but they were not added to REQUIREMENTS.md during planning)

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

None — all three tasks executed per plan.

## Known Limitations

- E2E test is structurally complete but not runtime-verified against Docker stack (consistent with prior sync app milestones — blocked by pre-existing app subprocess startup issue)
- Mock server ignores authentication headers entirely (by design — no real credentials flow through the mock)

## Follow-ups

- none — this is the terminal slice

## Files Created/Modified

- `e2e/mock-caldav-api/server.py` — Created: ~500-line mock CalDAV server with PROPFIND/REPORT/GET/PUT/DELETE, 3 canned iCalendar events, 12-check selftest
- `docker-compose.test.yml` — Modified: Added mock-caldav service with healthcheck, added to api depends_on
- `e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts` — Created: 304-line Playwright E2E test with 7 phases
- `e2e/helpers/selectors.ts` — Modified: Added caldavCalendarSync selector block with 13 selectors
- `docs/guide/39-caldav-calendar-sync.md` — Created: 368-line Chapter 39 user guide
- `docs/guide/README.md` — Modified: Added Ch 39 TOC entry
- `docs/guide/appendix-d-glossary.md` — Modified: Added "CalDAV Calendar Sync" glossary entry
- `docs/guide/38-outlook-calendar-sync.md` — Modified: Updated nav footer Next link to Chapter 39

## Forward Intelligence

### What the next slice should know
- This is the terminal slice — no downstream work within this milestone. The CalDAV app is complete.

### What's fragile
- Mock server XML responses are hand-crafted strings with exact namespace URIs matching CalDAVClient's parser constants. If CalDAVClient's namespace constants change, the mock responses will fail silently (200 but empty parse results).

### Authoritative diagnostics
- `python3 e2e/mock-caldav-api/server.py --selftest` — exercises every mock endpoint in 2s, trustworthy because it uses the same HTTP request patterns the E2E test will use
- `pytest tests/test_caldav_*.py -v` — 229 tests in 0.34s covering all modules

### What assumptions changed
- No assumptions changed — this was a straightforward assembly slice with low risk, executed per plan.
