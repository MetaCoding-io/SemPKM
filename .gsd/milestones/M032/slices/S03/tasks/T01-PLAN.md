---
estimated_steps: 5
estimated_files: 3
skills_used:
  - test
---

# T01: E2E Playwright test for dashboard block rendering

**Slice:** S03 — E2E Tests and User Guide
**Milestone:** M032

## Description

Write a Playwright E2E spec that creates a dashboard via the API with stat-card, chart, and heading blocks, opens it in the workspace, and asserts that each block renders its expected content. This covers the milestone's E2E verification requirement (BLK-10): stat-card shows a live SPARQL-derived count, chart renders a Chart.js canvas, heading displays configured text.

The dashboard backend and frontend widget activation code are fully implemented by S01 and S02. The E2E test exercises the full rendering pipeline: API → SQLite → htmx lazy-load → SPARQL fetch → DOM update → Chart.js initialization.

## Steps

1. **Add dashboard selectors to `e2e/helpers/selectors.ts`.**
   Add a `dashboard` object to the `SEL` export with these selectors:
   ```typescript
   dashboard: {
     grid: '.grid-stack',
     statCard: '.dashboard-block-stat-card',
     statValue: '[data-stat-target]',
     chart: '.dashboard-block-chart',
     chartCanvas: 'canvas.chart-canvas',
     heading: '.dashboard-block-heading',
     markdown: '[data-md-block]',
     formGroup: '.dashboard-block-form-group',
     sparqlResult: '[data-sparql-table]',
   },
   ```

2. **Add `openDashboardTab` helper to `e2e/helpers/dockview.ts`.**
   Wrap the `window.openDashboardTab(id, name)` call with a wait for GridStack or dashboard content to appear:
   ```typescript
   export async function openDashboardTab(
     page: Page,
     dashboardId: string,
     dashboardName: string,
     timeoutMs = 15000,
   ) {
     await page.evaluate(
       ({ id, name }) => {
         if (typeof (window as any).openDashboardTab === 'function') {
           (window as any).openDashboardTab(id, name);
         }
       },
       { id: dashboardId, name: dashboardName },
     );
     // Wait for GridStack container to appear in the dockview panel
     await page.waitForSelector('.grid-stack', { timeout: timeoutMs });
   }
   ```

3. **Create `e2e/tests/45-dashboard-blocks/dashboard-blocks.spec.ts`.**
   Use the `ownerPage` and `ownerSessionToken` fixtures from `e2e/fixtures/auth`. Structure:

   - **Test: "stat-card renders live SPARQL count"**
     - Create a dashboard via `POST /api/dashboard` (auth cookie: `sempkm_session=${ownerSessionToken}`) with one stat-card block:
       ```json
       {
         "name": "E2E Stat Test",
         "layout": "gridstack",
         "blocks": [{
           "type": "stat-card",
           "config": {
             "query": "SELECT (COUNT(*) AS ?count) WHERE { GRAPH <urn:sempkm:current> { ?s a ?type } }",
             "label": "Total Objects",
             "icon": "database",
             "color": ""
           },
           "x": 0, "y": 0, "w": 4, "h": 2
         }]
       }
       ```
     - Navigate to `/browser/`, wait for workspace, open dashboard tab via `openDashboardTab(page, id, name)`
     - Wait for `[data-sparql-loaded]` attribute on the stat-card element (indicates SPARQL fetch completed)
     - Assert `[data-stat-target]` textContent is a number > 0 (seed data has 11+ objects)

   - **Test: "chart block renders Chart.js visualization"**
     - Create dashboard with a chart block configured with:
       ```json
       {
         "type": "chart",
         "config": {
           "query": "SELECT ?label (COUNT(*) AS ?value) WHERE { GRAPH <urn:sempkm:current> { ?s a ?type } BIND(STRAFTER(STR(?type), '#') AS ?label) } GROUP BY ?type",
           "chart_type": "bar",
           "label": "Objects by Type"
         },
         "x": 0, "y": 0, "w": 6, "h": 4
       }
       ```
     - Open dashboard, wait for `[data-chart-loaded]` attribute on the chart element
     - Assert `canvas.chart-canvas` exists and has a Chart.js instance: `page.waitForFunction(() => { const c = document.querySelector('canvas.chart-canvas'); return c && (c as any).__chartjs_instance__ !== undefined; })` — or check via `Chart.getChart(canvas)` if available. Fallback: verify canvas element exists and has non-zero dimensions.

   - **Test: "heading block renders configured text"**
     - Create dashboard with a heading block: `{ "type": "heading", "config": { "text": "E2E Test Dashboard", "level": "2", "subtitle": "Automated verification", "align": "left" }, "x": 0, "y": 0, "w": 12, "h": 2 }`
     - Open dashboard, assert `h2` with text "E2E Test Dashboard" exists within `.dashboard-block-heading`
     - Assert subtitle text "Automated verification" is visible

   - **Test: "multiple block types render in one dashboard"**
     - Create dashboard with stat-card + heading + chart blocks at different grid positions
     - Open dashboard, assert all three block types are present simultaneously

4. **Handle timing for async block loading.**
   Dashboard blocks load lazily via htmx `hx-trigger="load"`. After opening the dashboard tab:
   - Wait for `waitForIdle(page)` (no active htmx requests)
   - Then wait for specific data attributes: `[data-sparql-loaded]` on stat-card/sparql-result, `[data-chart-loaded]` on chart
   - Use generous timeouts (15s) since Chart.js CDN load + SPARQL fetch can be slow
   - Import `waitForWorkspace` and `waitForIdle` from `e2e/helpers/wait-for`

5. **Clean up test dashboards after each test.**
   After each test, delete the created dashboard via `DELETE /api/dashboard/{id}` to avoid accumulation. Use `test.afterEach` or handle cleanup inline. Check if DELETE endpoint exists; if not, leave dashboards (they're isolated by user and don't interfere).

## Must-Haves

- [ ] Dashboard selectors in `e2e/helpers/selectors.ts`
- [ ] `openDashboardTab` helper in `e2e/helpers/dockview.ts`
- [ ] E2E spec with stat-card, chart, heading, and multi-block test cases
- [ ] Tests wait for async SPARQL/Chart.js initialization before asserting
- [ ] Tests use `ownerPage`/`ownerSessionToken` auth fixtures

## Verification

- `cd e2e && npx playwright test tests/45-dashboard-blocks/dashboard-blocks.spec.ts --project=chromium` — all tests pass
- Stat-card test confirms a numeric value > 0
- Chart test confirms canvas element exists after Chart.js loads
- Heading test confirms correct heading level and text content

## Inputs

- `e2e/fixtures/auth.ts` — provides `ownerPage`, `ownerSessionToken`, `BASE_URL`
- `e2e/fixtures/seed-data.ts` — provides SEED constants (11+ seed objects for SPARQL counts)
- `e2e/helpers/wait-for.ts` — provides `waitForWorkspace`, `waitForIdle`
- `e2e/helpers/selectors.ts` — existing selector patterns to extend
- `e2e/helpers/dockview.ts` — existing dockview helpers to extend
- `backend/app/dashboard/router.py` — dashboard API (POST /api/dashboard, render_block HTML output)
- `frontend/static/js/workspace.js` — `openDashboardTab()`, `_executeSparqlWidgets()`, `_initChartBlocks()`

## Expected Output

- `e2e/tests/45-dashboard-blocks/dashboard-blocks.spec.ts` — E2E test spec with 4 test cases
- `e2e/helpers/selectors.ts` — extended with `dashboard` selector group
- `e2e/helpers/dockview.ts` — extended with `openDashboardTab` helper

## Observability Impact

- **New diagnostic signals in tests:** Each test waits for `data-sparql-loaded` / `data-chart-loaded` data attributes, which directly surface whether the async rendering pipeline completed. Timeout on these attributes pinpoints which rendering stage failed.
- **Console warnings captured:** Playwright traces capture `[SemPKM] SPARQL widget error:` and `[SemPKM] Chart block error:` console warnings, making fetch failures visible in test reports.
- **Future agent inspection:** To debug a failing dashboard block test, check Playwright trace for: (1) network tab — did `/api/sparql` POST return 200? (2) console tab — any `[SemPKM]` warnings? (3) DOM snapshot — is the `data-sparql-loaded` or `data-chart-loaded` attribute present?
