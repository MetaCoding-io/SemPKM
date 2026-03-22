---
estimated_steps: 4
estimated_files: 3
skills_used:
  - best-practices
  - frontend-design
  - make-interfaces-feel-better
---

# T02: Frontend JS (SPARQL widgets, Chart.js, markdown) + CSS + builder config forms

**Slice:** S02 — Data-Driven Widgets (stat-card, chart, heading) + Block Fixes
**Milestone:** M032

## Description

The backend (T01) now emits HTML blocks with `data-sparql-query`, `data-chart-query`, `data-md-block`, and `data-sparql-table` attributes, but nothing activates them. This task adds the frontend JS execution layer (SPARQL fetch, Chart.js lazy load, markdown rendering), CSS styling for all new/fixed block types, and builder config forms so users can configure the new widgets.

Three new JS functions hook into the existing `htmx:afterSettle` event handler at line ~3194 of workspace.js, scoped to the settled element for idempotency.

## Steps

1. **Add SPARQL widget execution JS to `frontend/static/js/workspace.js`:**
   - Add `_executeSparqlWidgets(root)` function. Finds all `[data-sparql-query]` elements within `root` that haven't been processed (check for `data-sparql-loaded` attribute). For each element:
     - Read query from `dataset.sparqlQuery`
     - POST to `/api/sparql` with `Content-Type: application/json`, body `{query: queryText}`
     - On success: if element has `[data-stat-target]`, extract `results.bindings[0][head.vars[0]].value` and set it as textContent on the `[data-stat-target]` child (stat-card scalar). If element has `[data-sparql-table]`, build `<table>` with `<thead>` from `head.vars` and `<tbody>` from `results.bindings`, set innerHTML on `.sparql-table-container` child.
     - On error (400 or network): set error message in the block: `"Query error: " + response.statusText` or `"Network error"`. Log to `console.warn` with the query text.
     - Mark element with `data-sparql-loaded="1"` after processing (idempotency).
   - Add `_renderMarkdownBlocks(root)` function. Finds all `[data-md-block]` elements within `root` without `data-md-rendered`. For each: read content from child `<script type="text/plain" class="md-source">` .textContent. If `globalThis.marked` is available, render via `marked.parse(content)` and sanitize via `DOMPurify.sanitize()` if DOMPurify is available. Set innerHTML on `.md-rendered` child. Mark with `data-md-rendered="1"`.
   - Hook both functions into the existing `htmx:afterSettle` handler at line ~3194, after the lucide.createIcons call: `_executeSparqlWidgets(e.detail.elt); _renderMarkdownBlocks(e.detail.elt);`

2. **Add Chart.js lazy loader and chart block initialization to `frontend/static/js/workspace.js`:**
   - Add module-level variables: `var _chartJsLoaded = false; var _chartJsLoading = false; var _chartJsCallbacks = [];`
   - Add `_ensureChartJs(callback)` function: if loaded, call callback immediately. If loading, push to callbacks array. Otherwise set loading=true, create `<script>` with `src="https://cdn.jsdelivr.net/npm/chart.js@4.4/dist/chart.umd.min.js"`, on load set loaded=true and flush callbacks, on error log warning "Chart.js failed to load" and show error in pending chart blocks. Append to `document.head`.
   - Add `_initChartBlocks(root)` function. Finds `[data-chart-query]` elements within root without `data-chart-loaded`. For each: call `_ensureChartJs(function() { ... })`, inside the callback: POST query to `/api/sparql`, map results to Chart.js format (`results.bindings[*].label.value` → labels array, `results.bindings[*].value.value` → data array as Numbers), create `new Chart(canvas, { type: chartType, data: {labels, datasets: [{data, label}]}, options: {responsive: true, maintainAspectRatio: false, plugins: {legend: {display: chartType === 'pie'}}} })`. Mark with `data-chart-loaded="1"`.
   - Hook `_initChartBlocks(e.detail.elt)` into the htmx:afterSettle handler alongside the other two functions.

3. **Add CSS styles to `frontend/static/css/workspace.css`:**
   - `.dashboard-block-stat-card`: `padding: 16px; display: flex; flex-direction: column; gap: 4px;` (similar to existing `.dashboard-block-sparql` but enhanced)
   - `.stat-card-label`: `font-size: 0.8em; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.05em;`
   - `.stat-card-value`: `font-size: 1.8em; font-weight: 600; color: var(--color-accent, #61afef);`
   - `.stat-card-icon svg`: `width: 20px; height: 20px; flex-shrink: 0; stroke: currentColor;` (per CLAUDE.md Lucide rules)
   - `.stat-card-header`: `display: flex; align-items: center; justify-content: space-between;`
   - `.dashboard-block-chart`: `padding: 12px; display: flex; flex-direction: column; height: 100%;`
   - `.chart-canvas`: `flex: 1; min-height: 0; width: 100%;`
   - `.chart-label`: `font-size: 0.85em; color: var(--color-text-muted); margin-bottom: 8px;`
   - `.dashboard-block-heading`: `padding: 16px; display: flex; flex-direction: column; justify-content: center;`
   - `.dashboard-block-heading h1, h2, h3, h4`: `margin: 0; color: var(--color-text-primary);`
   - `.heading-subtitle`: `margin: 4px 0 0; font-size: 0.85em; color: var(--color-text-muted);`
   - `.dashboard-page` scoped overrides for new types: `overflow: auto; max-height: 100%;`
   - `.sparql-table-container table`: basic table styling matching existing table views
   - `.dashboard-block-error-inline`: inline error display for failed SPARQL queries

4. **Add builder config forms to `backend/app/templates/browser/dashboard_builder.html`:**
   - Add 3 new cases to the `getTypeConfigHTML(blockType, config)` switch:
   - `case 'stat-card'`: textarea[data-key="query"] for SPARQL query, input[data-key="label"] for display label, input[data-key="icon"] for Lucide icon name (placeholder: "e.g. hash, users, folder"), input[data-key="color"] for accent color (placeholder: "e.g. #61afef")
   - `case 'chart'`: textarea[data-key="query"] for SPARQL query (with help text: "Query must return ?label and ?value columns"), select[data-key="chart_type"] with options bar/line/pie, input[data-key="label"] for chart title
   - `case 'heading'`: input[data-key="text"] for heading text, select[data-key="level"] with h1/h2/h3/h4 options (default h2), input[data-key="subtitle"] for subtitle, select[data-key="align"] with left/center/right options (default left)
   - All inputs use `data-key` attributes — the existing `_builderSave()` `querySelectorAll('[data-key]')` collector auto-picks them up. Use `escapeAttr()` and `escapeHtml()` helpers already defined in the template for config value pre-population.

## Must-Haves

- [ ] `_executeSparqlWidgets()` finds and processes `[data-sparql-query]` elements — stat-card scalar + sparql-result table
- [ ] `_initChartBlocks()` lazy-loads Chart.js from CDN and renders Chart.js visualization from SPARQL data
- [ ] `_renderMarkdownBlocks()` renders markdown via marked.parse() + DOMPurify.sanitize()
- [ ] All 3 functions hooked into htmx:afterSettle handler, scoped to settled element
- [ ] All 3 functions are idempotent (mark processed elements to prevent re-execution)
- [ ] Error handling: failed SPARQL fetch shows error in block DOM + console.warn
- [ ] CSS styles for stat-card, chart, heading follow existing dashboard block patterns
- [ ] Lucide icon SVG in stat-card sized via CSS with flex-shrink:0 and stroke:currentColor (CLAUDE.md rule)
- [ ] Builder config forms for stat-card, chart, heading use data-key inputs collected by existing _builderSave()
- [ ] Existing test_dashboard.py and test_dashboard_builder.py pass unchanged

## Verification

- `grep -c '_executeSparqlWidgets\|_initChartBlocks\|_renderMarkdownBlocks' frontend/static/js/workspace.js` returns ≥ 3
- `grep -c "case 'stat-card'\|case 'chart'\|case 'heading'" backend/app/templates/browser/dashboard_builder.html` returns 3
- `grep -c 'dashboard-block-stat-card\|dashboard-block-chart\|dashboard-block-heading' frontend/static/css/workspace.css` returns ≥ 3
- `cd backend && .venv/bin/python -m pytest tests/test_dashboard.py tests/test_dashboard_builder.py -v` — existing tests pass

## Inputs

- `frontend/static/js/workspace.js` — existing htmx:afterSettle handler at ~line 3194 (currently only does lucide.createIcons)
- `frontend/static/css/workspace.css` — existing dashboard block styles (`.dashboard-block-sparql` at ~line 7676, `.dashboard-page` scoped at ~line 7860)
- `backend/app/templates/browser/dashboard_builder.html` — existing `getTypeConfigHTML()` switch at ~line 110 with cases for view-embed, markdown, create-form, object-embed, sparql-result, form-group, divider
- `backend/app/dashboard/registry.py` — T01 output: 10 block types registered (needed to confirm config field names)
- `backend/app/dashboard/router.py` — T01 output: render_block HTML structure (needed to match JS selectors to backend output)

## Expected Output

- `frontend/static/js/workspace.js` — 3 new functions + Chart.js lazy loader + htmx:afterSettle hooks
- `frontend/static/css/workspace.css` — styles for stat-card, chart, heading + dashboard-page scoped overrides
- `backend/app/templates/browser/dashboard_builder.html` — 3 new getTypeConfigHTML cases
