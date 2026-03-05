---
phase: 40-e2e-test-coverage-v24
plan: 02
subsystem: testing
tags: [playwright, e2e, helptext, bug-fix, regression, ninja-keys, dockview, card-view]

# Dependency graph
requires:
  - phase: 39-verification
    provides: Bug fixes for BUG-04 through BUG-09, helptext feature
provides:
  - Edit form helptext E2E tests (4 tests)
  - Bug fix regression E2E tests for BUG-04 through BUG-09 (6 tests)
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ninja-keys opened attribute check instead of toBeVisible (shadow DOM web component)"
    - "Properties toggle expand before interacting with form helptext"
    - "keyboard.type for ninja-keys search (shadow DOM intercepts keyboard input)"

key-files:
  created:
    - e2e/tests/11-helptext/helptext.spec.ts
    - e2e/tests/12-bug-fixes/bug-fixes.spec.ts
  modified: []

key-decisions:
  - "Used attribute check for ninja-keys opened state instead of toBeVisible (shadow DOM hides internals from Playwright visibility)"
  - "Checked border on .flip-card-front not [data-testid=card-item] (border is on inner face element)"

patterns-established:
  - "ninja-keys: use toHaveAttribute('opened') not toBeVisible() for shadow DOM web components"
  - "Expand properties-toggle-badge before checking form helptext in edit mode"

requirements-completed: [TEST-05]

# Metrics
duration: 18min
completed: 2026-03-05
---

# Phase 40 Plan 02: Helptext and Bug Fix E2E Tests Summary

**10 Playwright E2E tests covering edit form helptext toggles and BUG-04 through BUG-09 regression verification**

## Performance

- **Duration:** 18 min
- **Started:** 2026-03-05T07:27:59Z
- **Completed:** 2026-03-05T07:45:55Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- 4 helptext E2E tests: toggle presence, form-level expand/collapse, field-level toggle, markdown rendering
- 6 bug fix regression tests: tab accent colors, card borders, Ctrl+K palette, inactive tab bleed, chevron icons, concept search
- All 10 tests pass; no regressions in existing 179-test suite

## Task Commits

Each task was committed atomically:

1. **Task 1: Edit form helptext E2E tests** - `74383c0` (feat)
2. **Task 2: Bug fix regression E2E tests** - `3a1990f` (feat)

## Files Created/Modified
- `e2e/tests/11-helptext/helptext.spec.ts` - 4 tests for form/field helptext toggle, expand/collapse, markdown rendering
- `e2e/tests/12-bug-fixes/bug-fixes.spec.ts` - 6 tests for BUG-04 through BUG-09 regression coverage

## Decisions Made
- Used `toHaveAttribute('opened')` instead of `toBeVisible()` for ninja-keys web component (shadow DOM blocks Playwright visibility detection)
- Checked `.flip-card-front` border instead of `[data-testid="card-item"]` (CSS border is on inner face, not outer wrapper)
- Used `keyboard.type()` for ninja-keys search input (shadow DOM intercepts keyboard events directly)
- Properties section must be expanded before helptext is accessible (collapsed by default when object has body text)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed form visibility in edit mode**
- **Found during:** Task 1 (helptext tests)
- **Issue:** Opening object in edit mode via `openTab(iri, label, 'edit')` leaves form behind flip card (not visible)
- **Fix:** Changed to open in read mode first, then click mode-toggle to switch to edit (matching existing test patterns)
- **Files modified:** e2e/tests/11-helptext/helptext.spec.ts
- **Verification:** All 4 helptext tests pass

**2. [Rule 1 - Bug] Fixed properties section expansion for helptext access**
- **Found during:** Task 1 (helptext tests)
- **Issue:** Form helptext summary not visible because properties-collapsible section is collapsed by default
- **Fix:** Added properties-toggle-badge click before helptext assertions
- **Files modified:** e2e/tests/11-helptext/helptext.spec.ts
- **Verification:** All 4 helptext tests pass

**3. [Rule 1 - Bug] Fixed card border assertion targeting wrong element**
- **Found during:** Task 2 (BUG-05 test)
- **Issue:** Border CSS is on `.flip-card-front` child, not on `[data-testid="card-item"]` wrapper
- **Fix:** Changed locator to `.flip-card-front` for border assertion
- **Files modified:** e2e/tests/12-bug-fixes/bug-fixes.spec.ts
- **Verification:** BUG-05 test passes

**4. [Rule 1 - Bug] Fixed ninja-keys visibility detection for shadow DOM**
- **Found during:** Task 2 (BUG-06 and BUG-09 tests)
- **Issue:** Playwright `toBeVisible()` reports hidden for shadow DOM web components even when visually open
- **Fix:** Used `toHaveAttribute('opened')` and `keyboard.type()` for shadow DOM interaction
- **Files modified:** e2e/tests/12-bug-fixes/bug-fixes.spec.ts
- **Verification:** BUG-06 and BUG-09 tests pass

---

**Total deviations:** 4 auto-fixed (4 bugs in test assertions)
**Impact on plan:** All auto-fixes necessary for test correctness. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 40 E2E test coverage complete (plan 01 inference/lint + plan 02 helptext/bug-fixes)
- Full suite: 179 passing + 10 new = 189 passing tests

---
*Phase: 40-e2e-test-coverage-v24*
*Completed: 2026-03-05*

## Self-Check: PASSED
