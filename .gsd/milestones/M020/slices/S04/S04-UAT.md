# S04: E2E Tests + User Guide — UAT

**Milestone:** M020
**Written:** 2026-03-19

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S04 deliverables are a mock API server (selftest-verified), a Playwright E2E test (structurally verified via TypeScript), and documentation files (grep-verified). No new runtime behavior to verify beyond the mock server's selftest.

## Preconditions

- Working directory is the M018 worktree (`/home/james/Code/SemPKM/.gsd/worktrees/M018`)
- Python 3.12+ available for mock server selftest
- Node.js/npm available for TypeScript checking
- No Docker stack required for UAT (artifact-level checks only)

## Smoke Test

Run `cd e2e/mock-outlook-api && python3 server.py --selftest` — should print `[selftest] 13/13 passed, 0 failed` and exit 0.

## Test Cases

### 1. Mock server selftest passes with all 13 checks

1. `cd e2e/mock-outlook-api && python3 server.py --selftest`
2. **Expected:** Output shows 13 ✓ lines covering: health, token, calendars, delta initial, delta incremental, timed event fields, all-day event, recurring event pattern, PATCH RSVP, PATCH unknown → 404, user profile, deltaLink format, unknown path → 404. Exit code 0.

### 2. Mock server error-path check works

1. In the selftest output, find the `PATCH unknown event → 404` check
2. **Expected:** Returns 404 status with `ErrorItemNotFound` error code in JSON body

### 3. Docker Compose wiring complete

1. `grep "mock-outlook" docker-compose.test.yml`
2. **Expected:** At least 5 matches — service definition, depends_on, volume mount, and env var references
3. `grep "OUTLOOK_API_URL" docker-compose.test.yml`
4. **Expected:** Shows `http://mock-outlook:8080/v1.0`
5. `grep "OUTLOOK_TOKEN_URL" docker-compose.test.yml`
6. **Expected:** Shows `http://mock-outlook:8080/common/oauth2/v2.0/token`
7. `grep "OUTLOOK_AUTH_URL" docker-compose.test.yml`
8. **Expected:** Shows `http://mock-outlook:8080/common/oauth2/v2.0/authorize`

### 4. E2E test file has all 7 phases

1. `grep -n "Phase" e2e/tests/38-outlook-sync/outlook-calendar-sync.spec.ts`
2. **Expected:** 8 phase markers (Phase 0 through Phase 6, including Phase 5b)
3. `wc -l e2e/tests/38-outlook-sync/outlook-calendar-sync.spec.ts`
4. **Expected:** ~394 lines

### 5. E2E test selectors registered

1. `grep -A 15 "outlookCalendarSync" e2e/helpers/selectors.ts`
2. **Expected:** Block with 13 selectors including `clientId`, `clientSecret`, `connectBtn`, `calendarCheckbox`, `syncNowBtn`

### 6. E2E test OAuth simulation follows established pattern

1. Open `e2e/tests/38-outlook-sync/outlook-calendar-sync.spec.ts`
2. Find Phase 3 — should use `ownerRequest.post(...)` with `maxRedirects: 0`, extract `state` from redirect Location header, navigate browser to callback URL with mock auth code
3. **Expected:** Same pattern as Google Calendar E2E test — no hardcoded state values

### 7. Chapter 38 exists with required sections

1. `test -f docs/guide/38-outlook-calendar-sync.md`
2. **Expected:** File exists
3. `grep -c "##" docs/guide/38-outlook-calendar-sync.md`
4. **Expected:** 15+ section headings
5. `grep "Azure" docs/guide/38-outlook-calendar-sync.md | head -3`
6. **Expected:** Azure AD app registration section present
7. `grep "showAs" docs/guide/38-outlook-calendar-sync.md`
8. **Expected:** showAs enum mapping table present
9. `grep "Recurrence" docs/guide/38-outlook-calendar-sync.md`
10. **Expected:** Recurrence pattern type × range type matrix present

### 8. README TOC updated

1. `grep "38.*Outlook" docs/guide/README.md`
2. **Expected:** `38. [Outlook Calendar Sync](38-outlook-calendar-sync.md)`

### 9. Glossary updated

1. `grep "Outlook Calendar Sync" docs/guide/appendix-d-glossary.md`
2. **Expected:** Definition entry present, alphabetically before "Todoist Sync"

### 10. Appendix A env vars added

1. `grep -c "OUTLOOK_" docs/guide/appendix-a-environment-variables.md`
2. **Expected:** 3 (OUTLOOK_API_URL, OUTLOOK_TOKEN_URL, OUTLOOK_AUTH_URL)

### 11. Navigation chain correct

1. `grep "Chapter 38" docs/guide/37-todoist-sync.md`
2. **Expected:** Ch 37 footer has "Next: Chapter 38: Outlook Calendar Sync"
3. `grep "Chapter 37" docs/guide/38-outlook-calendar-sync.md`
4. **Expected:** Ch 38 footer has "Previous: Chapter 37: Todoist Sync"
5. `grep "Appendix A" docs/guide/38-outlook-calendar-sync.md | tail -1`
6. **Expected:** Ch 38 footer has "Next: Appendix A"

### 12. htmx prefix audit clean

1. `grep -rn "hx-\(get\|post\|put\|delete\|patch\)" apps/outlook-calendar/ | grep -v "/app/outlook-calendar/" | wc -l`
2. **Expected:** 0

## Edge Cases

### Mock server canned data completeness

1. Run selftest and check timed event has: attendees array, categories array, showAs value, sensitivity value, onlineMeetingUrl
2. Check all-day event has: `isAllDay: true` (or equivalent flag)
3. Check recurring event has: structured `recurrence` object with `pattern.type: "weekly"` and `range.type: "endDate"`
4. **Expected:** All three event types have expected field richness per the mock data contract

### Mock deltaLink format

1. In selftest output, verify deltaLink check passes
2. **Expected:** deltaLink is a full URL containing `$deltatoken=` parameter (not just the token value)

## Failure Signals

- Mock selftest reports any FAIL line → mock server endpoint is broken
- `grep "mock-outlook" docker-compose.test.yml` returns <5 matches → Docker wiring incomplete
- `grep "OUTLOOK_" docs/guide/appendix-a-environment-variables.md` returns <3 → env vars not fully documented
- Ch 37 navigation still points to Appendix A instead of Ch 38 → navigation chain broken
- `grep -rn "hx-(get|post)" apps/outlook-calendar/ | grep -v "/app/outlook-calendar/"` returns >0 → htmx URLs bypass proxy

## Requirements Proved By This UAT

- OL-09 — Mock server selftest, E2E test structure, Chapter 38 docs, and docs infrastructure updates

## Not Proven By This UAT

- Full E2E test execution against Docker test stack (blocked by pre-existing app subprocess startup timing issue)
- Runtime behavior of the mock server under Docker networking (healthcheck configuration verified structurally, not at runtime)
- Chapter 38 content accuracy against a real Azure AD app registration (documented from Microsoft docs, not from a live walkthrough)

## Notes for Tester

- The mock server selftest is the single most useful verification command — it exercises all 6 endpoints in <1s
- The E2E test has not been run against a live Docker stack — structural correctness is verified via TypeScript parsing and phase count
- The htmx prefix audit distinguishes between URL-bearing attributes (hx-get, hx-post — must use proxy prefix) and non-URL attributes (hx-target, hx-swap — don't need prefix). Only URL-bearing violations matter.
