---
id: T03
parent: S04
milestone: M012
provides:
  - 5 Playwright E2E tests covering persona CRUD, auto-creation, sidebar UI selector, command palette entries, and activation switching
key_files:
  - e2e/tests/29-personas/personas.spec.ts
key_decisions:
  - Used try/finally cleanup pattern for test persona deletion (avoids orphan personas on test failure)
patterns_established:
  - Persona API test pattern: create → assert 201 → list → assert contains → rename → get → assert name → delete → assert gone
  - Popover trigger pattern: click button[popovertarget="user-popover"] then waitForSelector on the hx-get loaded partial
observability_surfaces:
  - Playwright test results: cd e2e && npx playwright test tests/29-personas --project=chromium
  - Playwright HTML report: cd e2e && npx playwright show-report
duration: 12m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T03: E2E Playwright tests for personas

**Added 5 Playwright E2E tests covering persona CRUD API, default auto-creation, sidebar selector UI, command palette entries, and activation switching**

## What Happened

Created `e2e/tests/29-personas/personas.spec.ts` with 5 tests organized in a `Personas` describe block:

1. **persona CRUD via API** — Full lifecycle test: POST create (201), GET list (contains), PUT rename (200), GET single (verify rename), DELETE (204), GET list (verify gone). Uses try/finally for cleanup.

2. **default persona auto-created on first workspace load** — Navigates to workspace (triggers `initPersonas()`), then verifies via API that at least one persona exists with `is_active: true`. Tests PERSONA-05.

3. **persona selector visible in sidebar user popover** — Clicks the popover trigger button, waits for the hx-get loaded `.persona-selector` partial, asserts header text "Personas" and presence of persona items. Tests PERSONA-03.

4. **command palette has persona commands** — Opens palette via Alt+K, evaluates ninja-keys data to verify `persona-switch`, `persona-save`, `persona-create` commands exist in section "Persona". Tests PERSONA-04.

5. **persona activation via API switches active persona** — Creates a second persona (auto-activates), verifies previous becomes inactive, then explicitly activates the other persona and verifies the switch. Uses finally block for cleanup. Tests PERSONA-01/02.

## Verification

All 5 persona tests pass on the Docker test stack:
- `cd e2e && npx playwright test tests/29-personas --project=chromium` — 5 passed
- Combined slice tests (27 + 28 + 29) — 12 tests, all pass (3 flaky from auth rate-limiting, all succeed on retry)
- Backend test suite: 946 passed in 6.27s — no regressions
- Zero conflict markers in backend/frontend source

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd e2e && npx playwright test tests/29-personas --project=chromium` | 0 | ✅ pass | 10.7s |
| 2 | `cd e2e && npx playwright test tests/27-event-log-polish tests/28-body-diff tests/29-personas --project=chromium` | 0 | ✅ pass | 35.3s |
| 3 | `backend/.venv/bin/python -m pytest backend/tests/ --tb=short -q` | 0 | ✅ pass (946) | 6.27s |
| 4 | `curl -s http://localhost:3901/api/health` | 0 | ✅ pass | <1s |
| 5 | `grep -rn "^<<<<<<< " backend/ frontend/ ... \| wc -l` | 0 | ✅ pass (0 markers) | <1s |
| 6 | `cd e2e && npx playwright test --project=chromium` (full suite) | 1 | ⚠️ pre-existing syntax errors in unrelated test files | 22s |

## Diagnostics

- Run persona tests: `cd e2e && npx playwright test tests/29-personas --project=chromium`
- View test report: `cd e2e && npx playwright show-report`
- Verify persona API: `curl -s http://localhost:3901/api/personas` (requires auth cookie)
- Check persona service exists: `test -f backend/app/persona/service.py`

## Deviations

None — implementation followed the task plan exactly.

## Known Issues

- Full E2E suite (`npx playwright test --project=chromium`) has pre-existing syntax errors in ~15 test files from earlier merge conflicts (not introduced by this task). These existed before T03 and affect tests in directories 00-07, 18-19. The T03 persona tests and T02 tests (dirs 27-29) all pass cleanly.
- Auth fixture rate-limiting causes occasional flaky first attempts (test retries succeed) — documented and mitigated in T02 via `RATE_LIMIT_ENABLED` config toggle.

## Files Created/Modified

- `e2e/tests/29-personas/personas.spec.ts` — 5 Playwright E2E tests covering PERSONA-01 through PERSONA-05
- `.gsd/milestones/M012/slices/S04/tasks/T03-PLAN.md` — Added Observability Impact section (pre-flight fix)
