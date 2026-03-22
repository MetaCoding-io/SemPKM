# S03 Research: E2E Tests and User Guide

## Summary

This is straightforward work: one E2E Playwright spec and updating the existing user guide chapter. Both follow well-established patterns already in the codebase. S01 and S02 have shipped all 10 block types (including the 4 new ones) with full backend unit test coverage (1,286 lines across 3 test files). What's left is browser-level verification and documentation.

## Requirement Coverage

| Req | Description | Role |
|-----|-------------|------|
| BLK-10 | E2E Playwright tests for new block types | Primary owner |
| BLK-11 | User guide documentation for new block types and form groups | Primary owner |

## Recommendation

Two tasks — one for the E2E spec, one for the user guide update. Independent, no ordering dependency. The E2E test should create a dashboard via the API, open it, and assert on rendered block content. The guide update extends existing chapter 28 with new block types and the GridStack builder.

## Implementation Landscape

### E2E Test

**Pattern to follow:** `e2e/tests/10-lint-dashboard/lint-dashboard.spec.ts` — creates test data via API, navigates to workspace, opens a panel, asserts on DOM content. Uses `ownerPage` + `ownerSessionToken` fixtures from `e2e/fixtures/auth.ts`.

**Dashboard API (for test setup):**
- `POST /api/dashboard` — JSON body: `{name, description, layout, blocks}` where `blocks` is an array of `{type, config, x, y, w, h}`
- Requires auth cookie: `Cookie: sempkm_session=${token}`
- Returns `{id, name}` with status 201

**Opening a dashboard in the workspace:**
```javascript
await page.evaluate(({ id, name }) => {
  window.openDashboardTab(id, name);
}, { id: dashboardId, name: 'Test Dashboard' });
```

**Block selectors for assertions:**

| Block Type | Container Selector | Data Attribute | Value Selector |
|------------|-------------------|----------------|----------------|
| stat-card | `.dashboard-block-stat-card` | `data-sparql-query` | `[data-stat-target]` (textContent = query result) |
| chart | `.dashboard-block-chart` | `data-chart-query`, `data-chart-type` | `canvas.chart-canvas` |
| heading | `.dashboard-block-heading` | — | `h1`–`h4` element with configured text |
| markdown | `[data-md-block]` | — | `.markdown-rendered` container |
| sparql-result | `[data-sparql-table]` | `data-sparql-query` | `table` element after query execution |
| form-group | `.dashboard-block-form-group` | — | `.form-group-slot` containers |

**Stat-card query execution flow:**
1. Block loads via htmx `hx-get` → returns HTML with `data-sparql-query="SELECT ..."`
2. `_executeSparqlWidgets()` fires on htmx `afterSettle` event
3. Fetches `/api/sparql` with the query
4. Writes result into `[data-stat-target]` element's textContent

**Chart block execution flow:**
1. Block loads → HTML with `data-chart-query` and `data-chart-type`
2. `_initChartBlocks()` fires on htmx `afterSettle`
3. `_ensureChartJs()` lazy-loads Chart.js CDN script
4. Fetches `/api/sparql`, parses bindings into labels/values
5. Creates `new Chart()` on the `canvas.chart-canvas` element

**Key timing considerations:**
- Blocks load lazily via htmx `hx-trigger="load"` — need to wait for htmx settle
- SPARQL fetch is async after block HTML loads — need to wait for `[data-sparql-loaded]` attribute
- Chart.js lazy load adds another async layer — wait for canvas to have Chart instance
- Use `waitForIdle(page)` + targeted `page.waitForSelector` / `page.waitForFunction`

**Recommended test cases (minimum viable per roadmap: stat-card + chart):**

1. **Stat-card renders live SPARQL count** — Create dashboard with stat-card block configured with `SELECT (COUNT(*) AS ?count) WHERE { ?s a ?type }`, open dashboard, assert `[data-stat-target]` shows a numeric value ≥ 11 (seed data count).

2. **Chart block renders Chart.js visualization** — Create dashboard with chart block configured with `SELECT ?label (COUNT(*) AS ?value) WHERE { ?s a ?type . BIND(STRAFTER(STR(?type), "#") AS ?label) } GROUP BY ?type`, open dashboard, assert `canvas.chart-canvas` exists and Chart.js instance is attached.

3. **Heading block renders configured text** — Create dashboard with heading block, assert the correct heading level and text content appear.

4. **Multiple block types in one dashboard** — Create dashboard with stat-card + heading + chart, verify all render without interference.

**Test file location:** `e2e/tests/11-dashboard-blocks/dashboard-blocks.spec.ts` (follows the `NN-feature/` naming convention).

**SEL.dashboard selectors to add to `e2e/helpers/selectors.ts`:**
```typescript
dashboard: {
  page: '.dashboard-page',
  grid: '.grid-stack',
  statCard: '.dashboard-block-stat-card',
  statValue: '[data-stat-target]',
  chart: '.dashboard-block-chart',
  chartCanvas: 'canvas.chart-canvas',
  heading: '.dashboard-block-heading',
  markdown: '[data-md-block]',
  formGroup: '.dashboard-block-form-group',
  sparqlResult: '[data-sparql-table]',
  blockError: '.dashboard-block-error',
  blockLoading: '.dashboard-block-loading',
}
```

### User Guide Update

**Three files must be updated** (per KNOWLEDGE.md rule):
1. `docs/guide/28-dashboards-and-workflows.md` — main content
2. `docs/guide/index.html` — static HTML sidebar (already has ch28 entry — no change needed unless renaming)
3. `backend/app/templates/guide.html` — in-app docs page (already has ch28 entry — no change needed unless renaming)

Since we're updating an existing chapter (not adding a new one), only file 1 needs content changes. Files 2 and 3 already link to chapter 28.

**Content to add to chapter 28:**

The existing Block Types table lists 6 types. It needs to grow to 10:

| New Block Type | Description for Guide |
|----------------|----------------------|
| **stat-card** | Displays a single numeric value from a SPARQL query (e.g., a count or sum) with a label and icon. Config: SPARQL query, label text, Lucide icon name, optional accent color. |
| **chart** | Renders a Chart.js visualization (bar, line, or pie) from SPARQL query results. The query must return `?label` and `?value` columns. Config: SPARQL query, chart type, optional label. |
| **heading** | Displays a title and optional subtitle at a configurable heading level (h1–h4) with alignment. Config: text, level, subtitle, alignment. |
| **form-group** | Creates multiple linked objects in one submission. Contains two or more SHACL sub-forms (slots), with edges automatically created between the resulting objects. Config: slot definitions (name + target class) and edge definitions (source slot → target slot + predicate). |

**Sections to update:**
- Block Types table — add 4 new types, update markdown description (now uses marked.js for full rendering), update sparql-result description (now actually executes queries)
- Layout section — update from CSS Grid templates to GridStack drag-drop builder description (blocks are positioned freely, no named slots)
- Creating a Dashboard section — update to describe GridStack palette drag-in and click-to-add
- Add a new "Form Group" subsection explaining multi-object creation workflows with slot/edge concepts
- Add a "Data Widgets" subsection covering stat-card and chart SPARQL configuration patterns

**No screenshots needed** per the roadmap — the roadmap says "screenshots and configuration instructions" but screenshots require a running instance which the planner/executor agents can't capture. Configuration instructions are the actionable deliverable.

### Constraints and Gotchas

1. **Chart.js CDN dependency in E2E:** The chart block lazy-loads Chart.js from CDN. The Docker test stack needs outbound internet access (or Chart.js needs to be vendored). Check if `_ensureChartJs()` uses a CDN URL or a local path.

2. **SPARQL query in E2E must work with seed data:** The basic-pkm model installs 11 seed objects (2 projects, 3 people, 3 notes, 3 concepts). Queries should target these known counts.

3. **htmx block loading timing:** Each block is a separate htmx request. Tests need to wait for all blocks to load, not just the first one. Use `page.waitForFunction(() => document.querySelectorAll('.dashboard-block-loading').length === 0)` or similar.

4. **The guide chapter 28 is 210 lines and significantly outdated.** The layout templates section describes 5 CSS Grid templates (single, sidebar-main, grid-2x2, grid-3, top-bottom) which may have been replaced by GridStack free positioning. The planner should verify whether the old layout template system still exists or was fully replaced before rewriting.
