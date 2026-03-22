---
id: T01
parent: S03
milestone: M032
provides:
  - E2E Playwright spec for dashboard block rendering (stat-card, chart, heading)
  - Dashboard selectors in e2e/helpers/selectors.ts
  - openDashboardTab helper in e2e/helpers/dockview.ts
key_files:
  - e2e/tests/45-dashboard-blocks/dashboard-blocks.spec.ts
  - e2e/helpers/selectors.ts
  - e2e/helpers/dockview.ts
key_decisions:
  - Wait for actual content changes (stat value != "…", canvas drawn) instead of data-sparql-loaded/data-chart-loaded attributes, since those are dedup guards set before the async fetch starts
patterns_established:
  - waitForStatCardValue() and waitForChartRendered() helpers for async dashboard widget readiness
  - createDashboard/deleteDashboard API helpers for E2E test arrangement/cleanup
observability_surfaces:
  - Playwright trace captures [SemPKM] SPARQL/Chart console warnings on fetch failures
  - Test timeouts on waitForStatCardValue/waitForChartRendered directly indicate which rendering stage stalled
duration: 25m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T01: E2E Playwright test for dashboard block rendering

**Added E2E Playwright spec with 4 test cases verifying stat-card (live SPARQL count), chart (Chart.js canvas), heading (configured text/subtitle), and multi-block dashboard rendering.**

## What Happened

Added dashboard selectors to `e2e/helpers/selectors.ts` covering grid, stat-card, chart, heading, markdown, form-group, sparql-result, and loading/error states. Added `openDashboardTab()` helper to `e2e/helpers/dockview.ts` that calls `window.openDashboardTab()` and waits for the GridStack container.

Created the E2E spec at `e2e/tests/45-dashboard-blocks/dashboard-blocks.spec.ts` with 4 test cases:
1. **stat-card renders live SPARQL count** — creates dashboard with COUNT query, verifies numeric value > 0
2. **chart block renders Chart.js visualization** — creates dashboard with bar chart, verifies Chart.js instance on canvas
3. **heading block renders configured text** — verifies h2 text and subtitle
4. **multiple block types render in one dashboard** — all three types at different grid positions

Key timing insight: `data-sparql-loaded` and `data-chart-loaded` attributes are deduplication guards set *before* the async fetch, not readiness signals. The first test run failed because it read the "…" placeholder before the SPARQL response arrived. Fixed by implementing `waitForStatCardValue()` (waits for text ≠ "…") and `waitForChartRendered()` (waits for Chart.js instance or drawn canvas).

## Verification

All 4 test cases pass consistently (ran twice to confirm stability):
```
cd e2e && npx playwright test tests/45-dashboard-blocks/dashboard-blocks.spec.ts --project=chromium
```
- stat-card: confirms numeric value > 0 from live SPARQL query against seed data
- chart: confirms Chart.js instance on canvas via `Chart.getChart()` or non-blank canvas data URL
- heading: confirms h2 text "E2E Test Dashboard" and subtitle "Automated verification"
- multi-block: all three types present simultaneously with correct content

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd e2e && npx playwright test tests/45-dashboard-blocks/dashboard-blocks.spec.ts --project=chromium` | 0 | ✅ pass | 6.4s |
| 2 | `test -f docs/guide/28-dashboards-and-workflows.md` | 0 | ✅ pass (file exists) | <1s |
| 3 | `grep -c 'stat-card\|chart\|heading\|form-group' docs/guide/28-dashboards-and-workflows.md` | 0 | ⏳ partial (returns 1, needs ≥4 — T02 will update guide) | <1s |

## Diagnostics

- **Failed test debugging:** Check Playwright HTML report in `e2e/playwright-report/`. On retry, traces are saved at `e2e/test-results/*/trace.zip` — open with `npx playwright show-trace <path>`.
- **SPARQL widget failures:** Console tab in trace shows `[SemPKM] SPARQL widget error:` warnings with query substring when /api/sparql returns errors.
- **Chart.js failures:** Console tab shows `[SemPKM] Chart block error:` with query info. The chart block renders an error div instead of the canvas.
- **Timing issues:** If `waitForStatCardValue()` or `waitForChartRendered()` times out, the async pipeline stalled — check network tab in trace for pending /api/sparql requests.

## Deviations

- **data-sparql-loaded is not a readiness signal:** Plan assumed `[data-sparql-loaded]` indicates SPARQL fetch completed. In reality, it's a dedup guard set immediately before `fetch()`. Replaced with `waitForStatCardValue()` that checks for actual content change (text ≠ "…"). Similarly for `[data-chart-loaded]`.
- **Chart.js instance detection:** Plan suggested checking `__chartjs_instance__` property. Actual Chart.js 4.x uses `Chart.getChart(canvas)`. Added fallback via `canvas.toDataURL()` length check for robustness.
- **Chart SPARQL query fix:** Plan's query used `GROUP BY ?type` but the chart renderer expects `?label` column. Fixed to `GROUP BY ?label` to match the frontend's binding loop.

## Known Issues

None.

## Files Created/Modified

- `e2e/tests/45-dashboard-blocks/dashboard-blocks.spec.ts` — New E2E spec with 4 test cases for dashboard block rendering
- `e2e/helpers/selectors.ts` — Added `dashboard` selector group with 13 selectors for dashboard block testing
- `e2e/helpers/dockview.ts` — Added `openDashboardTab()` helper for opening dashboard tabs in E2E tests
- `.gsd/milestones/M032/slices/S03/S03-PLAN.md` — Added Observability / Diagnostics section and diagnostic verification step
- `.gsd/milestones/M032/slices/S03/tasks/T01-PLAN.md` — Added Observability Impact section
