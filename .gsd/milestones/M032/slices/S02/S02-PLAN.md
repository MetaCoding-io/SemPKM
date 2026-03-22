# S02: Data-Driven Widgets (stat-card, chart, heading) + Block Fixes

**Goal:** Dashboard blocks for stat-card (live SPARQL count), chart (Chart.js visualization), heading (styled title/subtitle), plus fixed markdown (real rendering via marked.js) and sparql-result (executable query with table output) — all configurable through the builder.
**Demo:** A dashboard displays a stat-card with a live count from SPARQL, a Chart.js bar chart visualizing query results, a styled heading, working markdown with full rendering, and an executable sparql-result table — all configured through the builder.

## Must-Haves

- `stat-card`, `chart`, `heading` registered in BlockRegistry with correct config schemas and defaults
- `render_block()` returns proper HTML with `data-*` attributes for all 3 new types
- `render_block()` markdown branch emits raw content in a `<script type="text/plain">` tag for client-side marked.js rendering
- `render_block()` sparql-result branch emits `data-sparql-query` and `data-sparql-table` attributes for frontend JS pickup
- Frontend JS `_executeSparqlWidgets()` finds `[data-sparql-query]` elements after htmx settle, fetches `/api/sparql`, populates stat-card values and sparql-result tables
- Frontend JS `_initChartBlocks()` lazy-loads Chart.js from CDN on first chart block, then creates Chart instance from SPARQL results
- Frontend JS `_renderMarkdownBlocks()` finds `[data-md-block]` elements, reads `<script type="text/plain">` content, renders via `marked.parse()` + `DOMPurify.sanitize()`
- CSS styles for `.dashboard-block-stat-card`, `.dashboard-block-chart`, `.dashboard-block-heading`
- Builder `getTypeConfigHTML()` has config forms for stat-card (query, label, icon, color), chart (query, chart_type, label), heading (text, level, subtitle, align)
- All existing dashboard tests (27 + 9) pass without changes
- New tests cover registry count (10 types), new type specs, and render_block output for each new/fixed type

## Proof Level

- This slice proves: contract (block registration + render output) + integration (frontend JS executing SPARQL and rendering charts)
- Real runtime required: yes (Chart.js rendering requires browser; SPARQL execution requires running API)
- Human/UAT required: yes (visual check of chart rendering, stat-card styling)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_block_registry.py -v` — 10 types registered, new types have correct specs
- `cd backend && .venv/bin/python -m pytest tests/test_data_widgets.py -v` — render_block output for stat-card, chart, heading, fixed markdown, fixed sparql-result
- `cd backend && .venv/bin/python -m pytest tests/test_dashboard.py tests/test_dashboard_builder.py -v` — existing tests pass (regression guard)
- `grep -c 'data-sparql-query\|data-chart-query\|data-md-block' frontend/static/js/workspace.js` returns ≥ 3 (frontend hooks present)
- `grep -c 'stat-card\|chart\|heading' backend/app/templates/browser/dashboard_builder.html` returns ≥ 6 (builder config cases present)
- `cd backend && .venv/bin/python -m pytest tests/test_data_widgets.py::TestStatCardRender::test_no_query_returns_error tests/test_data_widgets.py::TestChartRender::test_no_query_returns_error tests/test_data_widgets.py::TestSparqlResultRender::test_no_query_returns_error -v` — error-path blocks render with diagnostic message (failure visibility)

## Observability / Diagnostics

- Runtime signals: SPARQL widget errors logged to browser console with block context (query text, response status). Chart.js load failures logged with CDN URL.
- Inspection surfaces: `[data-sparql-query]` and `[data-chart-query]` DOM attributes visible in DevTools. Chart.js load state tracked by `_chartJsLoaded` / `_chartJsLoading` globals.
- Failure visibility: failed SPARQL fetches render error message in the block DOM. Chart.js load timeout shows "Chart library unavailable" in block. Markdown parse failures show raw content (graceful degradation).

## Integration Closure

- Upstream surfaces consumed: `backend/app/dashboard/registry.py` (BlockRegistry pattern), `backend/app/dashboard/router.py` (render_block dispatch), `backend/app/templates/browser/dashboard_builder.html` (getTypeConfigHTML switch), `frontend/static/js/workspace.js` (htmx:afterSettle hook), `/api/sparql` endpoint
- New wiring introduced: 3 new JS functions hooked into htmx:afterSettle, Chart.js CDN lazy loader, 3 new builder config form cases
- What remains before the milestone is truly usable end-to-end: S03 (E2E Playwright tests, user guide docs)

## Tasks

- [x] **T01: Register stat-card, chart, heading blocks and fix markdown/sparql-result render handlers** `est:1h`
  - Why: Backend foundation — all 3 new block types need registry entries for palette visibility and validation, and the render_block function needs HTML output with correct data attributes for frontend JS pickup. Markdown and sparql-result are already registered but their render handlers are broken (html.escape instead of marked.js, no SPARQL execution).
  - Files: `backend/app/dashboard/registry.py`, `backend/app/dashboard/router.py`, `backend/tests/test_block_registry.py`, `backend/tests/test_data_widgets.py`
  - Do: (1) Add 3 BlockTypeSpec registrations to registry.py (stat-card: category=data, icon=hash, config={query:str,label:str,icon:str,color:str}, 3×2; chart: category=data, icon=bar-chart-3, config={query:str,chart_type:str,label:str}, 6×4; heading: category=content, icon=heading, config={text:str,level:str,subtitle:str,align:str}, 12×2). (2) Add render_block elif branches for stat-card (div with data-sparql-query, stat-card-label, stat-card-icon, stat-card-value[data-stat-target]), chart (div with data-chart-query, data-chart-type, canvas.chart-canvas), heading (div with configurable h1-h4 + subtitle p). (3) Fix markdown branch: replace html.escape+paragraph split with `<script type="text/plain" class="md-source">` containing raw content inside a `<div data-md-block>` wrapper. (4) Fix sparql-result branch: change data-query to data-sparql-query, add data-sparql-table attribute, emit proper table container. (5) SPARQL query text in data attributes must be HTML-escaped via html.escape(query, quote=True). (6) Update test_block_registry.py EXPECTED_TYPES to include new types, count to 10. (7) Create test_data_widgets.py with render_block output tests for all 5 block types (3 new + 2 fixed).
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_block_registry.py tests/test_data_widgets.py -v` — all pass
  - Done when: 10 block types registered, render_block returns correct HTML with data attributes for all 5 types, all existing dashboard tests pass

- [x] **T02: Frontend JS (SPARQL widgets, Chart.js, markdown) + CSS + builder config forms** `est:1.5h`
  - Why: The backend now emits HTML with data attributes, but nothing happens until frontend JS activates the widgets. This task adds the JS execution layer, visual styling, and builder config forms so users can create and configure all new block types.
  - Files: `frontend/static/js/workspace.js`, `frontend/static/css/workspace.css`, `backend/app/templates/browser/dashboard_builder.html`
  - Do: (1) In workspace.js, add `_executeSparqlWidgets(root)` — finds `[data-sparql-query]` elements within root, POSTs each query to `/api/sparql` as JSON, populates `[data-stat-target]` textContent for stat-cards (first binding's first value), builds `<table>` with thead/tbody for `[data-sparql-table]` elements. Mark processed elements with a data attribute to prevent re-execution (idempotency). (2) Add `_initChartBlocks(root)` — finds `[data-chart-query]` elements, calls `_ensureChartJs(callback)` for lazy CDN load (`https://cdn.jsdelivr.net/npm/chart.js@4.4/dist/chart.umd.min.js`), executes SPARQL query, maps `?label`→labels and `?value`→data arrays, creates `new Chart(canvas, {type, data, options:{responsive:true, maintainAspectRatio:false}})`. (3) Add `_renderMarkdownBlocks(root)` — finds `[data-md-block]` elements, reads sibling `<script type="text/plain" class="md-source">` textContent, renders via `globalThis.marked.parse()` + `DOMPurify.sanitize()` if available, falls back to textContent. (4) Hook all 3 functions into the existing `htmx:afterSettle` handler at line 3194 of workspace.js, scoped to `e.detail.elt`. (5) Add CSS for stat-card (flex column, large value 1.8em bold accent, small label uppercase muted, icon with flex-shrink:0 + stroke:currentColor per CLAUDE.md rules), chart (canvas fills block, min-height:0), heading (configurable align, h1-h4 sizes, muted subtitle). Add `.dashboard-page` scoped overrides for overflow. (6) Add 3 cases to `getTypeConfigHTML()` switch in dashboard_builder.html: stat-card (textarea[data-key=query], input[data-key=label], input[data-key=icon], input[data-key=color]), chart (textarea[data-key=query], select[data-key=chart_type] with bar/line/pie options, input[data-key=label]), heading (input[data-key=text], select[data-key=level] with h1-h4, input[data-key=subtitle], select[data-key=align] with left/center/right). Error handling: show error message in block DOM on SPARQL fetch failure (400 or network error). Console.warn with query text on failure for debugging.
  - Verify: `grep -c '_executeSparqlWidgets\|_initChartBlocks\|_renderMarkdownBlocks' frontend/static/js/workspace.js` returns 3+. `grep -c "case 'stat-card'\|case 'chart'\|case 'heading'" backend/app/templates/browser/dashboard_builder.html` returns 3. `cd backend && .venv/bin/python -m pytest tests/test_dashboard.py tests/test_dashboard_builder.py -v` — existing tests pass.
  - Done when: All 3 new JS widget functions exist and are hooked into htmx:afterSettle. CSS styles render stat-card, chart, heading blocks. Builder has config forms for all 3 types. Existing tests pass.

## Files Likely Touched

- `backend/app/dashboard/registry.py`
- `backend/app/dashboard/router.py`
- `backend/tests/test_block_registry.py`
- `backend/tests/test_data_widgets.py` (new)
- `frontend/static/js/workspace.js`
- `frontend/static/css/workspace.css`
- `backend/app/templates/browser/dashboard_builder.html`
