---
id: T01
parent: S05
milestone: M046
key_files:
  - backend/app/templates/browser/calendar_view.html
  - frontend/static/js/calendar.js
  - e2e/tests/00-setup/01-setup-wizard.spec.ts
key_decisions:
  - Used async isSetupComplete helper per-test rather than beforeAll, since Playwright test.skip must be called inside the test body
duration: 
verification_result: passed
completed_at: 2026-03-29T02:48:49.493Z
blocker_discovered: false
---

# T01: Replaced 8 bare-global references (initCalendar, openTab, showToast) with SemPKM.* namespace in calendar files and added test.skip guards to 5 fresh-stack-only setup wizard tests

**Replaced 8 bare-global references (initCalendar, openTab, showToast) with SemPKM.* namespace in calendar files and added test.skip guards to 5 fresh-stack-only setup wizard tests**

## What Happened

Fixed 8 stale bare-global references across calendar_view.html (3 initCalendar) and calendar.js (1 openTab, 4 showToast) that broke all calendar E2E tests after M044/S03 shim removal. Updated JSDoc header. Added isSetupComplete() helper to setup wizard tests that fetches /api/auth/status, and wired test.skip() into tests 1-5 so they skip gracefully on non-fresh Docker stacks. Tests 6-7 remain unconditional.

## Verification

All 5 verification checks pass: zero bare globals in calendar files, 3 SemPKM.initCalendar refs in template, 2 SemPKM.openTab refs in calendar.js, 4 SemPKM.showToast refs in calendar.js, 5 test.skip calls in setup wizard.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg 'typeof initCalendar[^.]|typeof openTab[^.]|typeof showToast[^.]' frontend/static/js/calendar.js backend/app/templates/browser/calendar_view.html | wc -l` | 0 | ✅ pass (returns 0) | 500ms |
| 2 | `rg 'SemPKM\.initCalendar' backend/app/templates/browser/calendar_view.html | wc -l` | 0 | ✅ pass (returns 3, ≥2) | 500ms |
| 3 | `rg 'SemPKM\.openTab' frontend/static/js/calendar.js | wc -l` | 0 | ✅ pass (returns 2, ≥1) | 500ms |
| 4 | `rg 'SemPKM\.showToast' frontend/static/js/calendar.js | wc -l` | 0 | ✅ pass (returns 4, ≥4) | 500ms |
| 5 | `rg 'test\.skip' e2e/tests/00-setup/01-setup-wizard.spec.ts | wc -l` | 0 | ✅ pass (returns 5, ≥1) | 500ms |

## Deviations

Plan expected 2 SemPKM.initCalendar matches in template; actual is 3 because _boot() body also has a typeof guard + call. All correct.

## Known Issues

None.

## Files Created/Modified

- `backend/app/templates/browser/calendar_view.html`
- `frontend/static/js/calendar.js`
- `e2e/tests/00-setup/01-setup-wizard.spec.ts`
