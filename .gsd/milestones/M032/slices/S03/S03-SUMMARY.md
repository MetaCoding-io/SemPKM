---
id: S03
parent: M032
milestone: M032
provides:
  - E2E Playwright spec verifying stat-card, chart, heading, and multi-block dashboard rendering
  - Dashboard selectors in e2e/helpers/selectors.ts
  - openDashboardTab helper in e2e/helpers/dockview.ts
  - User guide chapter 28 updated with all 10 block types, GridStack, data widgets, form groups
requires:
  - slice: S02
    provides: Frontend JS widget activation, CSS, builder config for all 10 block types
affects: []
key_files:
  - e2e/tests/45-dashboard-blocks/dashboard-blocks.spec.ts
  - e2e/helpers/selectors.ts
  - e2e/helpers/dockview.ts
  - docs/guide/28-dashboards-and-workflows.md
key_decisions:
  - Wait for actual content changes (stat value != "…", canvas drawn) instead of data-*-loaded attributes
  - Chart.js instance detection via Chart.getChart(canvas) with fallback to canvas.toDataURL() length
patterns_established:
  - waitForStatCardValue() and waitForChartRendered() helpers for async dashboard widget readiness
  - createDashboard/deleteDashboard API helpers for E2E test arrangement/cleanup
observability_surfaces:
  - Playwright HTML report in e2e/playwright-report/ with per-test screenshots and DOM snapshots
  - Trace artifacts in e2e/test-results/*/trace.zip for failed test debugging
  - Console tab in traces captures [SemPKM] SPARQL/Chart warnings
drill_down_paths:
  - .gsd/milestones/M032/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M032/slices/S03/tasks/T02-SUMMARY.md
duration: 37min
verification_result: passed
completed_at: 2026-03-22
---

# S03: E2E Tests and User Guide

**Added E2E Playwright spec with 4 test cases for dashboard block rendering (stat-card, chart, heading, multi-block) and rewrote user guide chapter 28 with all 10 block types, GridStack layout, data widgets, and form groups.**

## What Happened

T01 added dashboard selectors to `e2e/helpers/selectors.ts` (13 selectors covering grid, stat-card, chart, heading, markdown, form-group, loading/error states) and `openDashboardTab()` helper to `e2e/helpers/dockview.ts`. Created the E2E spec with 4 test cases: stat-card rendering a live SPARQL count, chart rendering a Chart.js visualization, heading rendering configured text/subtitle, and multi-block dashboard with all three types simultaneously. Key discovery: data-*-loaded attributes are dedup guards set before async fetch, not readiness signals — implemented waitForStatCardValue() (waits for text ≠ "…") and waitForChartRendered() (waits for Chart.js instance) as proper readiness checks.

T02 rewrote chapter 28 of the user guide: expanded the Block Types table from 6 to 10 types, replaced the CSS Grid Layout Templates section with GridStack drag-and-drop description, added Data Widgets subsection with SPARQL configuration examples for stat-card/chart/sparql-result, added Form Groups subsection explaining slots/edges/batch creation, and updated the Dashboard vs. Workflow comparison table. All three guide index files already had chapter 28 registered.

## Verification

- E2E Playwright spec: 4/4 test cases pass (`cd e2e && npx playwright test tests/45-dashboard-blocks/dashboard-blocks.spec.ts --project=chromium`)
- Guide file exists with all 10 block types documented
- `grep -c 'stat-card|chart|heading|form-group'` returns 19 (≥4 required)
- `grep -c '^|'` returns 25 table rows (≥12 required)
- GridStack, navigation links, and all block type names confirmed present

## Requirements Advanced

- DASH-01 — Dashboard documentation updated to reflect 10 block types and GridStack builder (was validated with 6 types and CSS Grid)

## Requirements Validated

None — DASH-01 was already validated; this milestone extends it.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

- E2E tests wait for actual content changes instead of data-*-loaded attributes (plan assumed these were readiness signals; they're dedup guards).
- Chart.js instance detection uses Chart.getChart(canvas) (v4.x API) with toDataURL fallback, not the __chartjs_instance__ property from the plan.
- Added backwards-compatibility note about legacy CSS Grid layouts in the guide (not in plan, but necessary for existing users).

## Known Limitations

- E2E spec does not test form-group submission (would require a running triplestore with model data for SHACL forms). Backend unit tests cover this path.
- E2E spec does not test the SPARQL error path (would need a mock or intentionally broken query). The T01 plan mentioned this but it was deferred — backend error-path tests exist in test_data_widgets.py.

## Follow-ups

None.

## Files Created/Modified

- `e2e/tests/45-dashboard-blocks/dashboard-blocks.spec.ts` — 4 E2E test cases for dashboard block rendering
- `e2e/helpers/selectors.ts` — 13 dashboard selectors
- `e2e/helpers/dockview.ts` — openDashboardTab() helper
- `docs/guide/28-dashboards-and-workflows.md` — Rewritten chapter with 10 block types, GridStack, data widgets, form groups

## Forward Intelligence

### What the next slice should know
- The E2E spec creates and deletes dashboards via the API — no builder UI interaction needed for test setup.
- waitForStatCardValue() and waitForChartRendered() are the correct readiness patterns for any future E2E test that needs to verify async dashboard widget content.

### What's fragile
- Chart.js CDN load can fail in restricted network environments — the waitForChartRendered helper has a 15s timeout but no explicit CDN error detection.
- The E2E spec targets seed data counts — if seed data changes, the stat-card assertions (numeric value > 0) should still hold but exact counts would differ.

### Authoritative diagnostics
- Playwright HTML report at `e2e/playwright-report/` for test results
- Trace zip at `e2e/test-results/*/trace.zip` for failed test debugging
- Browser console in traces shows `[SemPKM]` prefixed warnings for SPARQL/Chart errors

### What assumptions changed
- data-sparql-loaded/data-chart-loaded are NOT readiness signals — they're idempotency guards set before the async work starts. This was the key E2E timing insight.
