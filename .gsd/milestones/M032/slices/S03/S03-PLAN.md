# S03: E2E Tests and User Guide

**Goal:** Browser-level E2E tests verify new dashboard block types render with live data, and the user guide documents all block types and the GridStack builder.
**Demo:** Playwright E2E test creates a dashboard with stat-card, chart, and heading blocks via the API, opens it in the workspace, and asserts that each block renders its expected content. Chapter 28 of the user guide describes all 10 block types with configuration instructions.

## Must-Haves

- Playwright E2E spec that exercises at least stat-card (live SPARQL count) and chart (Chart.js canvas) rendering
- Heading block rendering verified in E2E
- Dashboard selectors added to `e2e/helpers/selectors.ts`
- User guide chapter 28 updated with all 4 new block types (stat-card, chart, heading, form-group)
- Guide updated to describe GridStack builder replacing CSS Grid layout templates
- Guide describes markdown (now full marked.js rendering) and sparql-result (now executes queries) improvements

## Verification

- `cd e2e && npx playwright test tests/45-dashboard-blocks/dashboard-blocks.spec.ts --project=chromium` — all test cases pass
- `test -f docs/guide/28-dashboards-and-workflows.md` and guide contains all 10 block types
- `grep -c 'stat-card\|chart\|heading\|form-group' docs/guide/28-dashboards-and-workflows.md` returns ≥ 4

## Tasks

- [ ] **T01: E2E Playwright test for dashboard block rendering** `est:1h30m`
  - Why: Milestone requires E2E verification of stat-card and chart blocks rendering with live SPARQL data. Backend unit tests exist (1,547 lines across 3 files) but no browser-level test exercises the full rendering pipeline including htmx lazy-load → SPARQL fetch → DOM update → Chart.js initialization.
  - Files: `e2e/tests/45-dashboard-blocks/dashboard-blocks.spec.ts`, `e2e/helpers/selectors.ts`, `e2e/helpers/dockview.ts`
  - Do: Add dashboard selectors to selectors.ts. Add `openDashboardTab` helper to dockview.ts. Write spec that: (1) creates a dashboard via POST /api/dashboard with stat-card, chart, and heading blocks, (2) opens it via `window.openDashboardTab()`, (3) waits for htmx block loading + SPARQL widget execution, (4) asserts stat-card shows a numeric count, chart has a canvas element with Chart.js instance, heading renders correct text/level. Use `ownerPage` + `ownerSessionToken` fixtures. SPARQL queries target seed data (11 objects). Chart.js loads from CDN — test needs network access.
  - Verify: `cd e2e && npx playwright test tests/45-dashboard-blocks/dashboard-blocks.spec.ts --project=chromium` passes
  - Done when: All E2E test cases pass against Docker test stack with stat-card showing a numeric value, chart canvas rendered, heading text visible

- [ ] **T02: Update user guide chapter 28 with new block types and GridStack builder** `est:45m`
  - Why: Milestone requires user-facing documentation of all new block types and the modernized dashboard builder.
  - Files: `docs/guide/28-dashboards-and-workflows.md`
  - Do: Rewrite the Block Types table to cover all 10 types (add stat-card, chart, heading, form-group; update markdown and sparql-result descriptions). Replace the Layout Templates section with GridStack drag-drop description. Update "Creating a Dashboard" section for the GridStack palette workflow. Add a "Data Widgets" subsection covering stat-card and chart SPARQL configuration. Add a "Form Groups" subsection explaining multi-object creation with slots and edges. Update the Dashboard vs. Workflow comparison table to reflect 10 block types.
  - Verify: `test -f docs/guide/28-dashboards-and-workflows.md && grep -q 'stat-card' docs/guide/28-dashboards-and-workflows.md && grep -q 'form-group' docs/guide/28-dashboards-and-workflows.md && grep -q 'chart' docs/guide/28-dashboards-and-workflows.md`
  - Done when: Chapter 28 documents all 10 block types with configuration instructions, GridStack builder workflow, form-group slot/edge concepts, and data widget SPARQL patterns

## Files Likely Touched

- `e2e/tests/45-dashboard-blocks/dashboard-blocks.spec.ts`
- `e2e/helpers/selectors.ts`
- `e2e/helpers/dockview.ts`
- `docs/guide/28-dashboards-and-workflows.md`
