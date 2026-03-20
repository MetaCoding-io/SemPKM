---
id: T02
parent: S04
milestone: M021
provides:
  - Playwright E2E test exercising full CalDAV sync lifecycle (7 phases)
  - caldavCalendarSync selector block in shared selectors file
key_files:
  - e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts
  - e2e/helpers/selectors.ts
key_decisions:
  - Used accountUsername (not accountEmail) in selectors — CalDAV template uses .account-username class unlike OAuth-based apps that show email
patterns_established:
  - CalDAV E2E test follows same 7-phase structure as Outlook but with simplified Phase 3 (direct form fill instead of OAuth simulation)
observability_surfaces:
  - E2E test phases labeled with section comments — Playwright trace/screenshot pinpoints failed phase
  - SPARQL verification in Phase 5 returns concrete event labels — empty results indicate sync engine or field mapper issue
  - Selector registry at e2e/helpers/selectors.ts caldavCalendarSync block — single source of truth for CalDAV CSS selectors
duration: 12m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T02: Playwright E2E test and selectors for CalDAV sync lifecycle

**Added 304-line Playwright E2E test for CalDAV Calendar sync lifecycle with 13 CalDAV-specific selectors matching template IDs/classes**

## What Happened

Created the CalDAV Calendar Sync E2E test following the Outlook test's 7-phase structure. The key simplification is Phase 3 — CalDAV uses HTTP Basic auth, so it fills 3 form fields (server URL, username, password) and submits directly instead of simulating an OAuth redirect dance. All other phases (cleanup, model install, app install, calendar selection, sync+SPARQL verify, admin detail, uninstall) mirror the Outlook pattern.

Added 13 CalDAV-specific selectors to `e2e/helpers/selectors.ts`. Verified all selectors match actual template HTML IDs and classes from `connect.html` and `connect_status.html`. Notable difference from other sync apps: CalDAV uses `.account-username` (not `.account-email`) since CalDAV auth is username-based.

The SPARQL verification query uses `urn:sempkm:model:basic-pkm:Event` as the type IRI and checks for "Team Standup" and "Company Holiday" labels from the mock server's canned events.

## Verification

- Test file exists at `e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts` (304 lines)
- TypeScript compiles clean: `npx tsc --noEmit` produces no errors
- `caldavCalendarSync` block present in `e2e/helpers/selectors.ts` with 13 selectors
- All selector IDs (`#caldav-server-url`, `#caldav-username`, `#caldav-password`, `#sync-now-btn`) match template HTML
- All selector classes (`.connection-status`, `.account-username`, `.calendar-checkbox-item`, `.sync-stats`, `.credentials-form`, `.calendars-section`, `.sync-config-form`) match template HTML
- SPARQL queries are syntactically valid SELECT queries
- Mock server selftest passes (12/12 checks)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts` | 0 | ✅ pass | <1s |
| 2 | `cd e2e && npx tsc --noEmit tests/39-caldav-calendar/caldav-calendar-sync.spec.ts` | 0 | ✅ pass | 3s |
| 3 | `grep -q "caldavCalendarSync" e2e/helpers/selectors.ts` | 0 | ✅ pass | <1s |
| 4 | `python3 e2e/mock-caldav-api/server.py --selftest` | 0 | ✅ pass | 1s |
| 5 | Selector-to-template ID match (manual audit) | — | ✅ pass | — |

## Diagnostics

- **Run E2E test:** `npx playwright test e2e/tests/39-caldav-calendar/` against Docker test stack on port 3901
- **Requires mock-caldav service:** `docker compose -f docker-compose.test.yml up mock-caldav` must be running
- **Debug failed phases:** Playwright trace shows which phase failed; section comments in the test identify each phase boundary
- **SPARQL verification failure:** If Phase 5 SPARQL returns empty, check: (1) mock-caldav is responding, (2) sync engine mapped events correctly, (3) field mapper's BPKM prefix matches query

## Deviations

None — implementation follows the task plan exactly.

## Known Issues

None.

## Files Created/Modified

- `e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts` — 304-line Playwright E2E test with 7 phases (cleanup → prerequisites → install → credentials → calendars → sync+verify → cleanup)
- `e2e/helpers/selectors.ts` — Added `caldavCalendarSync` selector block with 13 CalDAV-specific selectors
- `.gsd/milestones/M021/slices/S04/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
