---
estimated_steps: 7
estimated_files: 1
---

# T02: E2E Playwright test for full demo flow

**Slice:** S04 — Cloud deployment config + E2E + docs
**Milestone:** M025

## Description

Write a Playwright E2E test that exercises the complete demo experience against the live Docker demo stack — anonymous access, tour auto-start and completion, CTA banner visibility, and dashboard rendering. This is the milestone's primary verification artifact, proving DEMO-03 (sample data visible), DEMO-04 (tour completes), DEMO-05 (dashboard renders), and DEMO-06 (CTA visible).

The test runs in the existing `demo` Playwright project (configured in `e2e/playwright.config.ts`) which targets `http://localhost:3902` with no authentication. It must use the `demo` project, not the default project. The demo stack must be running with seed data loaded before tests execute.

**Critical pitfalls from S04-RESEARCH and S03 Forward Intelligence:**
- Do NOT step through tour steps individually — trigger via `window.startDemoTour()` and verify outcome via localStorage flag
- Tour has hardcoded 500ms delays per step × 7 steps = ~3.5s minimum. Use generous timeout (~60s) for `waitForFunction` on localStorage
- CTA banner appears via `sempkm:demo-tour-done` custom event or on page load if localStorage flag is set — verify after localStorage is confirmed
- Dashboard UUID is `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` — shared constant between seed script and tour JS

**Existing test pattern to follow:** See `e2e/tests/50-demo/demo-read-only.spec.ts` for the demo test structure (serial mode, DEMO_URL constant, `@playwright/test` imports, no auth fixtures).

## Steps

1. Create `e2e/tests/50-demo/demo-full-flow.spec.ts` with imports and constants:
   ```typescript
   import { test, expect } from '@playwright/test';
   const DEMO_URL = 'http://localhost:3902';
   ```
   Use `test.describe.configure({ mode: 'serial' })` to run tests in order.

2. **Test 1: Anonymous workspace loads with sample data visible** — Navigate to `${DEMO_URL}/browser/`, verify HTTP 200, URL contains `/browser` (no login redirect), workspace container is visible. Then verify sample data is present: check that the explorer/nav tree has at least one item visible (e.g., a list item or tree node in the sidebar). This proves DEMO-01 (already validated in S01, but this is the starting state for subsequent tests) and DEMO-03 (sample data visible in browser).

3. **Test 2: Demo tour completes via startDemoTour()** — First clear any existing localStorage keys to simulate a fresh visitor: `page.evaluate(() => { localStorage.removeItem('sempkm_demo_tour_done'); localStorage.removeItem('sempkm_demo_cta_dismissed'); })`. Then trigger the tour: `page.evaluate('window.startDemoTour()')`. Wait for localStorage completion flag: `page.waitForFunction(() => localStorage.getItem('sempkm_demo_tour_done') === '1', null, { timeout: 60_000 })`. Verify no JS errors during the tour by checking `page.evaluate(() => !document.querySelector('.driver-popover-close-btn'))` or simply that the localStorage flag was set (the flag proves all 7 steps completed since it's only set in the `onDestroyStarted` callback). This proves DEMO-04.

4. **Test 3: CTA banner visible after tour completion** — After the tour completes (previous test set localStorage), verify the CTA banner is visible. The banner shows either via the `sempkm:demo-tour-done` event (during tour) or on page load when localStorage flag is set. Use `page.locator('#demo-cta-banner')` or `page.locator('.demo-cta-banner')` — check which selector matches the workspace.html markup. Assert the banner is visible with `toBeVisible()`. If the banner is shown via animation, give it a moment with a short timeout. Also verify the banner contains a link/button with text about "Get Started" or "Try SemPKM" or similar. This proves DEMO-06.

5. **Test 4: Demo dashboard renders with content** — Open the demo dashboard via `page.evaluate(() => { if (typeof openDashboardTab === 'function') openDashboardTab('aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee', 'Demo Dashboard'); })`. Wait for the dashboard tab to appear — look for a tab header or panel containing "Demo Dashboard" text, or wait for an iframe/content area to load. Verify the dashboard has content (not an empty page) — check for the presence of dashboard blocks or embedded view content. This proves DEMO-05.

6. **Test 5 (optional): Verify no console errors during full flow** — Check `page.on('pageerror')` listener captured no unhandled exceptions during the entire test run. This is a quality gate — tour steps that reference missing DOM elements would produce errors here.

7. Add file-level JSDoc comment explaining the test's purpose, prerequisites (demo stack running with seed data), and which requirements it validates (DEMO-03, DEMO-04, DEMO-05, DEMO-06).

## Must-Haves

- [ ] Test file exists at `e2e/tests/50-demo/demo-full-flow.spec.ts`
- [ ] Tests run in the `demo` Playwright project (matches `50-demo/*.spec.ts` pattern)
- [ ] Test proves anonymous workspace access with sample data visible (DEMO-03)
- [ ] Test proves tour triggers and completes via localStorage flag (DEMO-04)
- [ ] Test proves CTA banner is visible after tour (DEMO-06)
- [ ] Test proves demo dashboard renders with content (DEMO-05)

## Verification

- `npx playwright test tests/50-demo/demo-full-flow.spec.ts --project=demo` — all tests pass against the live demo Docker stack (prerequisite: `docker compose -f docker-compose.demo.yml up -d` with seed data loaded via `deploy-demo.sh`)
- The test must pass on a fresh run (no pre-existing localStorage state)

## Inputs

- `e2e/tests/50-demo/demo-read-only.spec.ts` — existing demo test file to follow as pattern (serial mode, DEMO_URL const, no auth)
- `e2e/playwright.config.ts` — has `demo` project targeting `http://localhost:3902`
- S03 Forward Intelligence: localStorage keys are `sempkm_demo_tour_done` and `sempkm_demo_cta_dismissed`; dashboard UUID is `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee`; tour function is `window.startDemoTour()`
- S03: CTA banner element uses class `.demo-cta-banner` in workspace.html
- S03: tour completion dispatches `sempkm:demo-tour-done` custom event and sets localStorage

## Expected Output

- `e2e/tests/50-demo/demo-full-flow.spec.ts` — new: ~100-150 lines, 4-5 serial Playwright tests proving the full demo flow

## Observability Impact

- **Test reporter output:** Playwright `list` reporter shows pass/fail for each of the 5 serial tests (DEMO-03, DEMO-04, DEMO-05, DEMO-06, JS-errors). HTML reporter at `e2e/playwright-report/` shows detailed traces on failure.
- **Console error capture:** The `pageerror` listener in the final test surfaces any unhandled JS exceptions from the entire flow — acts as a canary for broken tour steps, missing DOM elements, or failed dashboard loading.
- **Failure diagnostics:** On test failure, Playwright captures screenshot (`screenshot: 'only-on-failure'`) and trace (`trace: 'on-first-retry'`) automatically per the `demo` project config. These go to `e2e/test-results/`.
- **Tour completion signal:** The `sempkm_demo_tour_done` localStorage flag is the primary observable — if the tour test fails, check whether Driver.js loaded (`window.driver.js.driver` defined), whether the popover appeared (`.driver-popover` in DOM), and which step stalled.
- **How to inspect:** Run `npx playwright test tests/50-demo/demo-full-flow.spec.ts --project=demo --reporter=list` for live output. Add `--debug` for step-through mode. Check `e2e/test-results/` for failure artifacts.
