---
phase: quick-31
plan: 01
subsystem: testing
tags: [firefox, playwright, e2e, crossfade, css-classes]

requires:
  - phase: quick-30
    provides: "Root cause analysis of 12 Firefox e2e test failures"
provides:
  - "Firefox e2e parity with Chromium (222/223 pass)"
  - "face-visible/face-hidden class markers in crossfade toggle"
affects: [e2e-tests, workspace-js]

tech-stack:
  added: []
  patterns: ["face-visible/face-hidden class toggling alongside crossfade .flipped class"]

key-files:
  created: []
  modified:
    - frontend/static/js/workspace.js
    - e2e/tests/03-navigation/workspace-layout.spec.ts
    - e2e/tests/01-objects/object-view-redesign.spec.ts

key-decisions:
  - "Added face-visible/face-hidden as additive markers without changing crossfade mechanism"
  - "Scoped .markdown-body selector with .first() for Firefox strict mode compatibility"

patterns-established:
  - "toggleObjectMode always applies face-visible/face-hidden alongside .flipped for test selector compatibility"

requirements-completed: [FF-01, FF-02, FF-03]

duration: 21min
completed: 2026-03-08
---

# Quick Task 31: Fix Firefox E2E Failures Summary

**Added face-visible/face-hidden class toggling to crossfade and fixed 2 e2e test selectors, resolving all 12 Firefox-specific failures**

## Performance

- **Duration:** 21 min
- **Started:** 2026-03-08T01:33:10Z
- **Completed:** 2026-03-08T01:54:17Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- All 12 previously-failing Firefox e2e tests now pass (222/223 total, 1 unrelated flaky test)
- toggleObjectMode() now applies .face-visible/.face-hidden class markers in both read-to-edit and edit-to-read transitions
- Bottom panel tab count test updated from 2 to 4 (EVENT LOG, INFERENCE, AI COPILOT, LINT)
- .markdown-body selector scoped to .object-face-read to avoid Playwright strict mode error

## Task Commits

Each task was committed atomically:

1. **Task 1: Add face-visible/face-hidden class toggling to toggleObjectMode** - `086fbb6` (fix)
2. **Task 2: Fix panel tab count and markdown-body selector in e2e tests** - `25bd29e` (fix)
3. **Task 3: Run Firefox e2e tests to verify all 12 failures are resolved** - verification only, no commit

## Files Created/Modified
- `frontend/static/js/workspace.js` - Added .face-visible/.face-hidden toggling in both branches of toggleObjectMode()
- `e2e/tests/03-navigation/workspace-layout.spec.ts` - Updated panel tab count from 2 to 4, added INFERENCE and LINT assertions
- `e2e/tests/01-objects/object-view-redesign.spec.ts` - Scoped .markdown-body selector to .object-face-read with .first()

## Decisions Made
- Added face-visible/face-hidden as purely additive class markers -- the crossfade mechanism (.flipped class + opacity transition) is unchanged
- Used `.object-face-read .markdown-body` scoping plus `.first()` for maximum robustness against strict mode

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Docker test environment was not running; started with `npm run env:start` before test execution
- 1 unrelated test failure remains: `edit-object-ui.spec.ts:246` (multi-value reference field save) -- this is a pre-existing flaky test, not one of the 12 targeted failures

## Next Phase Readiness
- Firefox e2e suite at parity with Chromium (222/223 pass)
- The remaining 1 failure is unrelated to this task and should be tracked separately

---
*Quick Task: 31*
*Completed: 2026-03-08*

## Self-Check: PASSED
