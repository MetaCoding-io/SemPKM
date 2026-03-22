---
id: T02
parent: S02
milestone: M032
provides:
  - _executeSparqlWidgets() JS function — fetches SPARQL queries, populates stat-card values and sparql-result tables
  - _initChartBlocks() JS function — lazy-loads Chart.js from CDN, renders Chart.js visualizations from SPARQL data
  - _renderMarkdownBlocks() JS function — renders markdown via marked.parse() + DOMPurify.sanitize()
  - All 3 functions hooked into htmx:afterSettle handler, scoped to settled element
  - CSS styles for stat-card, chart, heading, sparql-result table, and inline error blocks
  - Builder config forms for stat-card, chart, heading in getTypeConfigHTML()
key_files:
  - frontend/static/js/workspace.js
  - frontend/static/css/workspace.css
  - backend/app/templates/browser/dashboard_builder.html
key_decisions:
  - Chart.js loaded from jsdelivr CDN (chart.js@4.4 UMD build) with lazy singleton pattern — only loads when first chart block appears
  - Chart color palette for pie charts uses 7 hardcoded accent colors matching the app's dark theme; bar/line uses single accent with 0.6 opacity
  - Stat-card scalar extraction uses first binding's first variable — simple and generic
  - Markdown gracefully degrades to raw text when marked.js is unavailable (no hard dependency)
patterns_established:
  - Dashboard widget activation uses data-*-loaded attribute for idempotency — prevents re-execution on htmx re-settle
  - Console warnings prefixed with [SemPKM] and include query excerpt (first 120 chars) for debugging
  - Chart.js lazy loader uses callback queue pattern (_chartJsCallbacks) to handle concurrent chart blocks
  - Builder config forms use existing data-key + escapeAttr/escapeHtml pattern — auto-collected by _builderSave()
observability_surfaces:
  - console.warn with [SemPKM] prefix for SPARQL widget, chart, and markdown errors
  - data-sparql-loaded, data-chart-loaded, data-md-rendered attributes on processed blocks (DevTools inspection)
  - _chartJsLoaded / _chartJsLoading globals track CDN load state
  - .dashboard-block-error-inline elements visible in DOM on fetch or render failures
duration: 20m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T02: Frontend JS (SPARQL widgets, Chart.js, markdown) + CSS + builder config forms

**Added 3 dashboard widget activation functions (SPARQL fetch, Chart.js lazy load, markdown render), CSS for all new block types, and builder config forms for stat-card/chart/heading**

## What Happened

Added three JS functions to workspace.js that activate the data-* attributes emitted by T01's render_block:

1. **`_executeSparqlWidgets(root)`** — finds `[data-sparql-query]` elements, POSTs each query to `/api/sparql`, extracts scalar values for stat-cards (`[data-stat-target]`) and builds `<table>` HTML for sparql-result blocks (`[data-sparql-table]`). Error handling shows inline error messages + console.warn.

2. **`_initChartBlocks(root)`** — finds `[data-chart-query]` elements, lazy-loads Chart.js from CDN via `_ensureChartJs()` callback queue, executes SPARQL query, maps `?label`/`?value` columns to Chart.js dataset, creates `new Chart()` with responsive options. Supports bar, line, and pie chart types.

3. **`_renderMarkdownBlocks(root)`** — finds `[data-md-block]` elements, reads raw content from `<script type="text/plain" class="md-source">`, renders via `marked.parse()` + `DOMPurify.sanitize()`. Falls back to raw text when libraries aren't available.

All three are hooked into the existing `htmx:afterSettle` handler, scoped to `e.detail.elt`. Each uses a `data-*-loaded`/`data-*-rendered` attribute for idempotency.

Added CSS for `.dashboard-block-stat-card` (flex column, large accent-colored value, uppercase muted label, icon with flex-shrink:0 + stroke:currentColor per CLAUDE.md), `.dashboard-block-chart` (flex column filling height, canvas with min-height:0), `.dashboard-block-heading` (configurable alignment, h1-h4 with zero margin, muted subtitle), `.sparql-table-container table` (collapse styling matching existing tables), `.dashboard-block-error-inline` (warning-colored italic message). Added `.dashboard-page` scoped overrides for stat-card, chart, and heading.

Added three new cases to `getTypeConfigHTML()` in the builder template: stat-card (query textarea, label, icon, color inputs), chart (query textarea, chart_type select with bar/line/pie, label input), heading (text input, level select with h1-h4, subtitle input, align select with left/center/right). All use `data-key` attributes auto-collected by `_builderSave()`.

## Verification

- `grep -c` for JS functions: 6 (≥3 ✅)
- `grep -c` for builder cases: 3 (=3 ✅)
- `grep -c` for CSS classes: 10 (≥3 ✅)
- `grep -c` for frontend hooks (data-sparql-query|data-chart-query|data-md-block): 10 (≥3 ✅)
- `grep -c` for builder coverage (stat-card|chart|heading): 7 (≥6 ✅)
- test_block_registry.py: 38/38 passed
- test_data_widgets.py: 28/28 passed
- test_dashboard.py: 27/27 passed
- test_dashboard_builder.py: 6/9 passed (3 pre-existing failures from S01 GridStack migration)
- Error-path tests (3 specific): 3/3 passed

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -c '_executeSparqlWidgets\|_initChartBlocks\|_renderMarkdownBlocks' frontend/static/js/workspace.js` | 0 | ✅ pass (6) | <1s |
| 2 | `grep -c "case 'stat-card'\|case 'chart'\|case 'heading'" backend/app/templates/browser/dashboard_builder.html` | 0 | ✅ pass (3) | <1s |
| 3 | `grep -c 'dashboard-block-stat-card\|dashboard-block-chart\|dashboard-block-heading' frontend/static/css/workspace.css` | 0 | ✅ pass (10) | <1s |
| 4 | `cd backend && .venv/bin/python -m pytest tests/test_dashboard.py tests/test_dashboard_builder.py -v` | 1 | ⚠️ partial (3 pre-existing failures) | 13.1s |
| 5 | `cd backend && .venv/bin/python -m pytest tests/test_block_registry.py -v` | 0 | ✅ pass (38/38) | 4.3s |
| 6 | `cd backend && .venv/bin/python -m pytest tests/test_data_widgets.py -v` | 0 | ✅ pass (28/28) | 4.3s |
| 7 | `cd backend && .venv/bin/python -m pytest tests/test_data_widgets.py::TestStatCardRender::test_no_query_returns_error tests/test_data_widgets.py::TestChartRender::test_no_query_returns_error tests/test_data_widgets.py::TestSparqlResultRender::test_no_query_returns_error -v` | 0 | ✅ pass (3/3) | 4.3s |
| 8 | `grep -c 'data-sparql-query\|data-chart-query\|data-md-block' frontend/static/js/workspace.js` | 0 | ✅ pass (10) | <1s |
| 9 | `grep -c 'stat-card\|chart\|heading' backend/app/templates/browser/dashboard_builder.html` | 0 | ✅ pass (7) | <1s |

## Diagnostics

- **SPARQL widget errors**: Look for `[SemPKM] SPARQL widget error:` in browser console — includes error message and first 120 chars of query
- **Chart errors**: `[SemPKM] Chart block error:` in console for query failures; `[SemPKM] Chart.js failed to load` for CDN issues
- **Markdown errors**: `[SemPKM] Markdown render error:` in console with parse exception
- **Processing state**: Check `data-sparql-loaded`, `data-chart-loaded`, `data-md-rendered` attributes in DevTools — "1" means processed
- **CDN state**: `window._chartJsLoaded` and `window._chartJsLoading` in console show Chart.js load state
- **Inline errors**: `.dashboard-block-error-inline` elements appear in the DOM when SPARQL fetch or chart render fails

## Deviations

- Chart label element is read from `.chart-label` span in the rendered HTML, using its textContent as the dataset label — slightly different from plan which suggested a separate variable, but simpler since the backend already renders the label span.
- Added root-element self-match checks (`root.matches && root.matches(...)`) in all three functions — handles the case where the settled element itself is a widget block, not just a container of widget blocks.

## Known Issues

- 3 pre-existing test failures in `test_dashboard_builder.py` (layout radio button checks removed during GridStack migration in S01). Not caused by this task — confirmed same failures in T01.
- Chart.js CDN dependency means charts won't render offline. Could be addressed later with a local bundle if needed.
- `marked.js` and `DOMPurify` must be loaded separately by the page for markdown rendering to work — if they aren't present, blocks show raw text.

## Files Created/Modified

- `frontend/static/js/workspace.js` — added _executeSparqlWidgets(), _initChartBlocks(), _renderMarkdownBlocks(), _ensureChartJs(), Chart.js state variables, and htmx:afterSettle hooks
- `frontend/static/css/workspace.css` — added styles for stat-card, chart, heading, sparql-result table, inline error, and dashboard-page scoped overrides
- `backend/app/templates/browser/dashboard_builder.html` — added 3 new getTypeConfigHTML() cases for stat-card, chart, heading
- `.gsd/milestones/M032/slices/S02/tasks/T02-PLAN.md` — added Observability Impact section (pre-flight fix)
