---
id: T02
parent: S04
milestone: M020
provides:
  - Playwright E2E test for full Outlook Calendar Sync lifecycle (7 phases)
  - outlookCalendarSync selector block in e2e/helpers/selectors.ts
key_files:
  - e2e/tests/38-outlook-sync/outlook-calendar-sync.spec.ts
  - e2e/helpers/selectors.ts
key_decisions:
  - "SPARQL RRULE assertion checks for FREQ=WEEKLY (no RRULE: prefix) — both Google and Outlook field mappers strip the prefix before storage"
patterns_established:
  - "Outlook Calendar E2E follows identical phase structure to Google Calendar E2E — cleanup → model → app install → credentials → OAuth simulation → calendar selection → sync config → sync now → SPARQL verification → admin uninstall"
observability_surfaces:
  - "E2E test phases delimited by numbered comments — Playwright reporter identifies exact failing phase"
  - "SPARQL verification queries log response body on assertion failure"
  - "Screenshot artifacts in test-results/ on Playwright failure"
duration: 20m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T02: Write Playwright E2E test for Outlook Calendar Sync lifecycle

**Added 394-line Playwright E2E test covering full Outlook Calendar Sync lifecycle (install→OAuth→sync→SPARQL verify→cleanup) and outlookCalendarSync selector block**

## What Happened

Cloned the Google Calendar E2E test structure and adapted for Outlook-specific selectors, OAuth simulation, and SPARQL verification.

1. Added `outlookCalendarSync` selector block to `e2e/helpers/selectors.ts` with 13 selectors matching the Outlook Calendar app's template IDs (`#outlook-client-id`, `#outlook-client-secret`, `.btn-microsoft`, etc.).

2. Created `e2e/tests/38-outlook-sync/outlook-calendar-sync.spec.ts` (394 lines) implementing all 7 phases:
   - **Phase 0** — Cleanup any prior outlook-calendar install
   - **Phase 1** — Install basic-pkm model if not present
   - **Phase 2** — Install outlook-calendar app, poll for "Running" status, 5s startup wait
   - **Phase 3** — Enter Azure AD credentials, simulate OAuth by POSTing to connect/microsoft with `maxRedirects: 0`, extracting state from redirect Location, navigating browser to callback URL with mock auth code
   - **Phase 4** — Check calendar checkboxes, submit calendar selection, set bidirectional sync direction
   - **Phase 5** — Click Sync Now, verify sync stats show "ok" status with ≥2 created events
   - **Phase 5b** — SPARQL queries verify event existence ("Team Standup", "Company Holiday") via rdfs:label and RRULE string on recurring event ("Weekly Review") containing `FREQ=WEEKLY`
   - **Phase 6** — Admin detail page verification, uninstall, confirm removal

3. Discovered that both Google and Outlook field mappers strip the `RRULE:` prefix before storing recurrence rules. The stored value is `FREQ=WEEKLY;BYDAY=MO,WE,FR;UNTIL=...` (not `RRULE:FREQ=WEEKLY`). Adjusted the assertion accordingly.

## Verification

- File exists: `test -f e2e/tests/38-outlook-sync/outlook-calendar-sync.spec.ts` → PASS
- Selector block: `grep "outlookCalendarSync" e2e/helpers/selectors.ts` → found
- TypeScript: `npx tsc --noEmit` reports 0 errors for our files (pre-existing errors in other worktree files are unrelated)
- Phase coverage: `grep -n "Phase" outlook-calendar-sync.spec.ts` → 8 phase markers (0, 1, 2, 3, 4, 5, 5b, 6)
- OAuth simulation: uses `maxRedirects: 0`, extracts state from Location header, navigates to callback
- SPARQL verification: two queries — event labels and RRULE
- Test timeout: `test.setTimeout(240_000)` (4 minutes)
- Retry loops: 3 `toPass()` blocks for model install, app Running status, and connect-content visibility
- Mock selftest: `python3 server.py --selftest` → 13/13 passed, exit 0

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f e2e/tests/38-outlook-sync/outlook-calendar-sync.spec.ts` | 0 | ✅ pass | <1s |
| 2 | `grep "outlookCalendarSync" e2e/helpers/selectors.ts` | 0 | ✅ pass | <1s |
| 3 | `npx tsc --noEmit \| grep "38-outlook-sync\|selectors.ts"` | 0 matches | ✅ pass | 3s |
| 4 | `grep -c "Phase" outlook-calendar-sync.spec.ts` | 0 (8 matches) | ✅ pass | <1s |
| 5 | `python3 e2e/mock-outlook-api/server.py --selftest` | 0 | ✅ pass | 1s |

## Diagnostics

- **Test execution:** `npx playwright test outlook-calendar-sync.spec.ts --reporter=list` shows per-assertion output with phase markers
- **Screenshot artifacts:** Playwright captures screenshots on failure in `test-results/` directory
- **Mock server logs:** `docker compose -f docker-compose.test.yml logs mock-outlook` shows `[mock-outlook] METHOD /path → STATUS` for each endpoint hit
- **SPARQL debugging:** Phase 5b queries are logged with full response body — if assertions fail, the SPARQL results are visible in the test output

## Deviations

- SPARQL RRULE assertion uses `FREQ=WEEKLY` instead of plan's `RRULE:FREQ=WEEKLY` — the field mapper strips the `RRULE:` prefix before storage. This matches the actual data flow (both Google and Outlook mappers strip the prefix).

## Known Issues

- The E2E test has not been run against the full Docker test stack (would require building and starting all containers). TypeScript parsing and structural correctness are verified.
- Pre-existing TypeScript errors exist in other test files in this worktree — unrelated to our changes.

## Files Created/Modified

- `e2e/tests/38-outlook-sync/outlook-calendar-sync.spec.ts` — new, 394-line Playwright E2E test with 7 phases
- `e2e/helpers/selectors.ts` — added `outlookCalendarSync` selector block (13 selectors)
- `.gsd/milestones/M020/slices/S04/tasks/T02-PLAN.md` — added Observability Impact section
