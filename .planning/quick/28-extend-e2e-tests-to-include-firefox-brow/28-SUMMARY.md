---
phase: quick-28
plan: 01
subsystem: testing
tags: [playwright, firefox, cross-browser, e2e]

requires:
  - phase: e2e-test-suite
    provides: Chromium-based Playwright test suite
provides:
  - Firefox browser project in Playwright config
  - Firefox convenience scripts in package.json
  - Firefox baseline test results (174/208 pass)
affects: [e2e, ci]

tech-stack:
  added: []
  patterns: [multi-browser Playwright projects]

key-files:
  created: []
  modified:
    - e2e/playwright.config.ts
    - e2e/package.json

key-decisions:
  - "Default 'test' script unchanged (chromium only) to keep fast path"
  - "test:all runs both chromium and firefox projects"

patterns-established:
  - "Browser-specific npm scripts follow test:{browser} naming convention"

requirements-completed: [QUICK-28]

duration: 52min
completed: 2026-03-07
---

# Quick Task 28: Extend E2E Tests to Include Firefox Summary

**Firefox project added to Playwright with convenience scripts; baseline established at 174/208 passing (83.7%)**

## Performance

- **Duration:** 52 min (mostly test execution time)
- **Started:** 2026-03-07T19:28:30Z
- **Completed:** 2026-03-07T20:20:22Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added Firefox project to Playwright config (Desktop Firefox device preset)
- Added 4 convenience scripts: test:firefox, test:firefox:headed, test:firefox:debug, test:all
- Ran full Firefox test suite establishing baseline: 174 passed, 33 failed, 1 flaky

## Task Commits

1. **Task 1: Add Firefox convenience scripts to package.json** - `c2de078` (feat)
2. **Task 2: Add Firefox project to Playwright config** - `13512e7` (feat)

## Files Created/Modified
- `e2e/playwright.config.ts` - Added firefox project with Desktop Firefox device
- `e2e/package.json` - Added test:firefox, test:firefox:headed, test:firefox:debug, test:all scripts

## Firefox Test Baseline (174/208 = 83.7%)

### Failure Categories (33 failures)

| Category | Count | Root Cause | Same as Chromium? |
|----------|-------|-----------|-------------------|
| Setup wizard (00-setup/01) | 5 | Non-fresh stack (expected) | Yes |
| Magic link auth (00-setup/02) | 2 | Session/cookie handling | Partial |
| Edit mode / flip (01-objects) | 7 | CSS crossfade/flip timing in Firefox | No - Firefox-specific |
| Admin pages (05-admin) | 12 | Session cookie not forwarded to admin routes | No - Firefox-specific |
| Bottom panel (03-navigation) | 1 | Dockview panel detection timing | No - Firefox-specific |
| Helptext (11-helptext) | 4 | Edit mode entry fails (same root as flip) | No - Firefox-specific |
| Lint dashboard (10-lint) | 1 | Validation result timing | No - Firefox-specific |
| Bug-fix regression (12) | 1 | Concept search/linking timing | No - Firefox-specific |

### Key Observations
- **26 Firefox-specific failures** (excluding 7 setup tests that fail on both browsers)
- **Common root causes:** (1) Edit mode entry/CSS flip timing, (2) Admin page session cookie handling, (3) htmx swap timing differences
- **Chromium baseline for comparison:** 124/129 pass (5 setup failures)

## Decisions Made
- Default "test" script kept as chromium-only for fast development iteration
- test:all script added for running both browsers in CI or pre-release verification

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- Background test process output was buffered through pipe, requiring direct execution instead
- Full test suite takes ~20 minutes for Firefox (sequential, single worker)

## User Setup Required
None - no external service configuration required.

## Next Steps
- Investigate Firefox-specific edit mode failures (CSS crossfade timing)
- Investigate Firefox admin page session cookie handling (12 failures share same root cause)
- Consider adding Firefox to CI pipeline once pass rate improves

---
*Quick Task: 28-extend-e2e-tests-to-include-firefox-brow*
*Completed: 2026-03-07*

## Self-Check: PASSED
