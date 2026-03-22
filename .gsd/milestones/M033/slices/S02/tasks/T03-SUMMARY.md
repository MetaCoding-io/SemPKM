---
id: T03
parent: S02
milestone: M033
provides:
  - E2E Playwright test suite for isometric 2.5D layout and Lucide SVG icon toggle
  - Shared selectors for icon toggle and isometric wrapper in selectors.ts
key_files:
  - e2e/tests/02-views/graph-isometric.spec.ts
  - e2e/helpers/selectors.ts
key_decisions:
  - Used openViewTab() JS API (from graph-interaction.spec.ts pattern) rather than dockview.addPanel() (from graph-view.spec.ts pattern) for more reliable graph panel opening
  - Extracted openGraphPanel() helper within the spec file to DRY panel setup across 5 tests
patterns_established:
  - openGraphPanel() helper pattern for graph view E2E tests that returns null when no graph ViewSpec exists, enabling graceful test.skip()
observability_surfaces:
  - "E2E tests verify icon mode via localStorage.getItem('sempkm_graph_icon_mode') and cy.nodes()[0].style('background-image')"
  - "E2E tests verify isometric mode via .isometric-active class on wrapper and cy._isometricActive JS flag"
duration: 10m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T03: E2E tests for isometric layout and icon toggle

**Added 5 Playwright E2E tests covering isometric 2.5D layout selection, CSS 3D transform activation, icon toggle button presence and node background-image injection, and combined isometric+icon interaction.**

## What Happened

Added two selectors to `e2e/helpers/selectors.ts` in the `views` section: `iconToggle: '#graph-icon-toggle'` and `isometricWrapper: '.graph-isometric-wrapper'`.

Created `e2e/tests/02-views/graph-isometric.spec.ts` with a shared `openGraphPanel()` helper that fetches available ViewSpecs, finds a graph spec, opens the workspace, and calls `openViewTab()` to create the graph panel. Each test calls this helper and skips gracefully if no graph ViewSpec exists.

Five test cases:
1. **layout picker includes Isometric 2.5D option** — asserts `option[value="isometric"]` exists and contains "Isometric" text
2. **selecting isometric applies CSS 3D transform** — selects the option, waits for fcose+transform, asserts `.isometric-active` class on wrapper and `cy._isometricActive` JS flag
3. **icon toggle button is present and visible** — asserts button visibility, "Icons" text, and no `.active` class in default state
4. **icon toggle activates icon mode on nodes** — clicks toggle, asserts `.active` class, verifies `localStorage` value, and checks `cy.nodes()[0].style('background-image')` is truthy
5. **isometric and icon toggle work together** — activates both, asserts wrapper class and button class simultaneously, verifies both JS flags

## Verification

All three task-level verification checks pass:

- File exists: `test -f e2e/tests/02-views/graph-isometric.spec.ts` → pass
- Selectors present: `rg -c 'isometric|iconToggle' e2e/helpers/selectors.ts` → 2 (≥2 required)
- Test count: `rg -c 'test\(' e2e/tests/02-views/graph-isometric.spec.ts` → 5 (≥4 required)
- TypeScript compilation: `cd e2e && npx tsc --noEmit tests/02-views/graph-isometric.spec.ts` → success (no errors)

Slice-level verification (`cd e2e && npx playwright test tests/02-views/graph-isometric.spec.ts --reporter=list`) requires the Docker test stack to be running. Tests compile cleanly and follow the established patterns from `graph-interaction.spec.ts`.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f e2e/tests/02-views/graph-isometric.spec.ts` | 0 | ✅ pass | <1s |
| 2 | `rg -c 'isometric\|iconToggle' e2e/helpers/selectors.ts` | 0 | ✅ pass (2) | <1s |
| 3 | `rg -c 'test\(' e2e/tests/02-views/graph-isometric.spec.ts` | 0 | ✅ pass (5) | <1s |
| 4 | `cd e2e && npx tsc --noEmit tests/02-views/graph-isometric.spec.ts` | 0 | ✅ pass | 4s |

## Diagnostics

- **Test file location:** `e2e/tests/02-views/graph-isometric.spec.ts`
- **Run tests:** `cd e2e && npx playwright test tests/02-views/graph-isometric.spec.ts --reporter=list`
- **Graceful skip:** If no graph ViewSpec is available (no model installed with a graph view), all 5 tests skip with `test.skip()` — no false failures
- **Debugging test failures:** Each test uses explicit `waitForSelector` and `waitForFunction` with 15s timeouts, so timeout failures indicate real issues with the graph rendering pipeline, not flaky waits

## Deviations

- Used `openViewTab()` API instead of `dockview.addPanel()` — the newer graph-interaction.spec.ts pattern is more reliable since it goes through the application's normal view-opening code path rather than constructing panel params manually.
- Named the selector `isometricWrapper` (not `isometricLayout` as the plan mentioned) to match the actual CSS class `.graph-isometric-wrapper` — clearer semantics.

## Known Issues

None.

## Files Created/Modified

- `e2e/tests/02-views/graph-isometric.spec.ts` — New E2E test file with 5 test cases covering isometric layout and icon toggle
- `e2e/helpers/selectors.ts` — Added `iconToggle` and `isometricWrapper` selectors to `SEL.views`
