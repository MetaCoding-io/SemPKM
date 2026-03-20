---
id: T02
parent: S04
milestone: M025
provides:
  - E2E Playwright test proving full demo flow (DEMO-03, DEMO-04, DEMO-05, DEMO-06)
key_files:
  - e2e/tests/50-demo/demo-full-flow.spec.ts
key_decisions:
  - Used shared page with pageerror listener across serial tests to catch JS errors from the entire flow
  - Click-through loop for Driver.js tour steps (startDemoTour triggers, but user clicks needed to advance) rather than programmatic auto-complete
patterns_established:
  - Serial demo E2E tests share a single page context via beforeAll/afterAll to preserve localStorage state across tests
observability_surfaces:
  - Playwright list/HTML reporter shows pass/fail per DEMO requirement; pageerror listener in final test surfaces unhandled JS exceptions from the full flow; failure artifacts (screenshot, trace) captured automatically by demo project config
duration: 15m
verification_result: partial
completed_at: 2026-03-20
blocker_discovered: false
---

# T02: E2E Playwright test for full demo flow

**Created serial Playwright test exercising anonymous access → sample data → tour completion → CTA banner → dashboard rendering against the live demo Docker stack**

## What Happened

Created `e2e/tests/50-demo/demo-full-flow.spec.ts` with 5 serial tests in the existing `demo` Playwright project:

1. **Anonymous workspace with sample data** (DEMO-03) — Navigates to `/browser/`, verifies HTTP 200 with no login redirect, workspace container visible, and explorer sidebar has at least one item (proving seed data loaded).

2. **Tour completion** (DEMO-04) — Clears localStorage, triggers `window.startDemoTour()`, then clicks through Driver.js Next/Done buttons in a loop until `sempkm_demo_tour_done` localStorage flag is set. The flag is only set in the `onDestroyStarted` callback, proving all 7 tour steps completed.

3. **CTA banner visibility** (DEMO-06) — After tour completion (previous test set localStorage), verifies `#demo-cta-banner` is visible, contains "SemPKM" text, a "Get Started" link pointing to GitHub.

4. **Dashboard renders** (DEMO-05) — Opens demo dashboard via `openDashboardTab('aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee', 'Demo Dashboard')`, waits for iframe or dashboard container to appear, verifies content rendered.

5. **No JS errors** — Quality gate checking the `pageerror` listener captured no unhandled exceptions during the entire serial flow (filters out ResizeObserver noise).

Key design decision: Used `test.beforeAll` with a shared page context so localStorage state persists across serial tests (e.g., tour sets flag in test 2, CTA test 3 reads it). This matches how a real user session works.

Updated T02-PLAN.md with the required Observability Impact section.

## Verification

- ✅ Test file exists at `e2e/tests/50-demo/demo-full-flow.spec.ts`
- ✅ File matches `50-demo/*.spec.ts` pattern → runs in `demo` Playwright project
- ✅ TypeScript compiles with zero errors (verified via `npx tsc --noEmit`)
- ✅ Test covers DEMO-03 (sample data visible in browser)
- ✅ Test covers DEMO-04 (tour triggers and completes via localStorage flag)
- ✅ Test covers DEMO-05 (demo dashboard renders with content)
- ✅ Test covers DEMO-06 (CTA banner visible after tour completion)
- ⏳ Cannot run tests live — demo Docker stack not running on localhost:3902

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f e2e/tests/50-demo/demo-full-flow.spec.ts` | 0 | ✅ pass | <1s |
| 2 | `grep -q "50-demo" e2e/playwright.config.ts` | 0 | ✅ pass | <1s |
| 3 | `grep -q "DEMO-03" e2e/tests/50-demo/demo-full-flow.spec.ts` | 0 | ✅ pass | <1s |
| 4 | `grep -q "DEMO-04" e2e/tests/50-demo/demo-full-flow.spec.ts` | 0 | ✅ pass | <1s |
| 5 | `grep -q "DEMO-05" e2e/tests/50-demo/demo-full-flow.spec.ts` | 0 | ✅ pass | <1s |
| 6 | `grep -q "DEMO-06" e2e/tests/50-demo/demo-full-flow.spec.ts` | 0 | ✅ pass | <1s |
| 7 | `npx tsc --noEmit \| grep demo-full-flow` | 0 | ✅ pass (0 errors) | 5s |
| 8 | `bash -n scripts/reset-demo.sh` | 0 | ✅ pass (T01) | <1s |
| 9 | `bash -n scripts/deploy-demo.sh` | 0 | ✅ pass (T01) | <1s |
| 10 | `grep -q "set -euo pipefail" scripts/reset-demo.sh` | 0 | ✅ pass (T01) | <1s |
| 11 | `npx playwright test --project=demo` | — | ⏳ skipped (demo stack not running) | — |
| 12 | `grep "38" docs/guide/README.md` | — | ⏳ pending (T03) | — |
| 13 | `grep "38" docs/guide/index.html` | — | ⏳ pending (T03) | — |
| 14 | `grep "DEMO_MODE" docs/guide/appendix-a-*.md` | — | ⏳ pending (T03) | — |

## Diagnostics

- **Run the test:** `cd e2e && npx playwright test tests/50-demo/demo-full-flow.spec.ts --project=demo --reporter=list`
- **Debug mode:** Add `--debug` flag for step-through execution
- **Failure artifacts:** Screenshots and traces in `e2e/test-results/` (per demo project config)
- **Tour stall diagnosis:** If tour test hangs, check: (1) Driver.js loaded (`window.driver.js.driver`), (2) popover visible (`.driver-popover`), (3) which step stalled (check console for `[SemPKM] Demo tour` log messages)
- **Prerequisites:** Demo stack must be running with seed data: `docker compose -f docker-compose.demo.yml up -d --build` then `scripts/deploy-demo.sh` (or seed manually)

## Deviations

- **Tour click-through:** The plan suggested verifying tour outcome solely via `waitForFunction` on localStorage after calling `startDemoTour()`. However, Driver.js requires user interaction (clicking Next/Done buttons) to advance steps — the `onDestroyStarted` callback only fires when the user clicks Done on the final step. Added a click-through loop that finds and clicks `.driver-popover-next-btn` / `.driver-popover-done-btn` with 1s delays between steps. This still uses `startDemoTour()` as the entry point and verifies via localStorage flag as planned.

## Known Issues

- Tests cannot be verified live in this environment since the demo Docker stack is not running on localhost:3902. Full verification requires the stack running with seed data.

## Files Created/Modified

- `e2e/tests/50-demo/demo-full-flow.spec.ts` — new: 5 serial Playwright tests proving DEMO-03, DEMO-04, DEMO-05, DEMO-06
- `.gsd/milestones/M025/slices/S04/tasks/T02-PLAN.md` — modified: added Observability Impact section
- `.gsd/milestones/M025/slices/S04/S04-PLAN.md` — modified: marked T02 as done
