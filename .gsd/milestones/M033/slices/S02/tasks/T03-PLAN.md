---
estimated_steps: 3
estimated_files: 2
skills_used: []
---

# T03: E2E tests for isometric layout and icon toggle

**Slice:** S02 — Isometric 2.5D Graph Layout & Icon Toggle
**Milestone:** M033

## Description

Write E2E Playwright tests verifying both features from T01 and T02. Follow the patterns established in `e2e/tests/02-views/graph-view.spec.ts` — use the API to find a graph ViewSpec, open a graph panel via dockview `evaluate`, then assert on DOM state.

The existing `graph-view.spec.ts` already has tests for: container rendering, data endpoint, layout picker (≥3 options), and fit button. The new spec covers the S02 additions: isometric layout option, icon toggle button, and their interaction.

## Steps

1. **Add selectors to `e2e/helpers/selectors.ts`** — In the `views` section, add: `iconToggle: '#graph-icon-toggle'` and `isometricWrapper: '.graph-isometric-wrapper'`. These target the new elements added in T01 and T02.

2. **Write `e2e/tests/02-views/graph-isometric.spec.ts`** — Create the test file with these test cases:
   - **"layout picker includes Isometric 2.5D option"** — Open a graph view panel (same pattern as existing tests), wait for `#layout-picker`, assert that one of the `<option>` elements has `value="isometric"` and text containing "Isometric".
   - **"selecting isometric applies CSS 3D transform"** — Open graph panel, select "isometric" from `#layout-picker` via `selectOption('isometric')`, wait 1.5s for fcose layout + transform to apply, assert that `.graph-isometric-wrapper` has class `.isometric-active` (or check `getComputedStyle` for a non-`none` transform).
   - **"icon toggle button is present"** — Open graph panel, wait for `#graph-icon-toggle`, assert it's visible.
   - **"icon toggle applies background-image to nodes"** — Open graph panel, wait for Cytoscape init (wait for `#cy-container canvas` to appear), click `#graph-icon-toggle`, then evaluate in page: `window._sempkmGraph.nodes()[0].style('background-image')` — assert it's truthy/non-empty (or at minimum assert the button has `.active` class).
   - **"isometric and icon toggle work together"** — Select isometric layout, then toggle icons. Assert both: wrapper has `.isometric-active` AND icon toggle button has `.active` class.

   Each test should skip gracefully with `test.skip()` if no graph ViewSpec exists (same pattern as existing tests).

3. **Verify tests run** — Run `cd e2e && npx playwright test tests/02-views/graph-isometric.spec.ts --reporter=list` against the test stack. If the Docker test stack is not running, verify at minimum that the test file compiles: `cd e2e && npx tsc --noEmit tests/02-views/graph-isometric.spec.ts` (or check syntax via the test runner's dry-run mode).

## Must-Haves

- [ ] Selectors for icon toggle and isometric wrapper added to `selectors.ts`
- [ ] Test file covers layout picker option, CSS transform application, icon toggle presence, icon toggle effect
- [ ] Tests skip gracefully when no graph ViewSpec available
- [ ] Tests follow existing patterns from `graph-view.spec.ts`

## Verification

- `test -f e2e/tests/02-views/graph-isometric.spec.ts` — file exists
- `rg -c 'isometric\|iconToggle' e2e/helpers/selectors.ts` returns ≥ 2
- `rg -c 'test\(' e2e/tests/02-views/graph-isometric.spec.ts` returns ≥ 4 (at least 4 test cases)

## Inputs

- `e2e/tests/02-views/graph-view.spec.ts` — existing patterns for graph view E2E tests
- `e2e/helpers/selectors.ts` — existing selector definitions to extend
- `frontend/static/js/graph.js` — T01 and T02 output: icon toggle + isometric layout implementation (to know what DOM state to assert on)
- `backend/app/templates/browser/graph_view.html` — T01 and T02 output: toolbar HTML with icon toggle button and isometric wrapper

## Expected Output

- `e2e/tests/02-views/graph-isometric.spec.ts` — new E2E test file with 4-5 test cases
- `e2e/helpers/selectors.ts` — modified with `iconToggle` and `isometricWrapper` selectors
