# S02 Research: Data-Driven Widgets (stat-card, chart, heading) + Block Fixes

## Summary

This is a **targeted research** slice. The patterns are well-established: BlockRegistry registration, `render_block()` dispatch, builder `getTypeConfigHTML()` config forms, and frontend JS hooks. The work is: register 3 new block types (stat-card, chart, heading), fix 2 existing blocks (markdown, sparql-result), add frontend JS to execute SPARQL queries and render Chart.js visualizations, and wire up builder config forms.

No novel architecture. No risky integration. The main technical question is Chart.js lazy loading in the workspace context.

## Recommendation

Five tasks in dependency order:

1. **Register new block types + fix markdown/sparql-result render_block handlers** — Backend-only. Adds stat-card, chart, heading to BlockRegistry. Fixes markdown block to use `marked.js`. Fixes sparql-result to emit proper data attributes for frontend pickup. Tests.
2. **Frontend SPARQL widget execution JS** — The `_executeSparqlWidget()` function that fires after htmx block load, fetches `/api/sparql`, and populates stat-card and sparql-result blocks.
3. **Chart.js lazy loader and chart block rendering** — Lazy-load Chart.js via `<script>` injection on first chart block encounter. Render Chart.js visualization from SPARQL results.
4. **Builder config forms for stat-card, chart, heading** — Add `getTypeConfigHTML()` cases for all three types in `dashboard_builder.html`.
5. **Integration verification** — Run full test suite, verify against Docker stack.

## Implementation Landscape

### Files to Change

**Backend:**

| File | Change | Why |
|------|--------|-----|
| `backend/app/dashboard/registry.py` | Add 3 `BlockTypeSpec` registrations: `stat-card`, `chart`, `heading` | New block types need registry entries for validation + builder palette |
| `backend/app/dashboard/router.py` | Add `elif` branches in `render_block()` for `stat-card`, `chart`, `heading`. Fix `markdown` and `sparql-result` branches. | Render HTML for each new block type; fix broken existing blocks |
| `backend/app/dashboard/models.py` | No change needed | `VALID_BLOCK_TYPES` is derived from `BLOCK_REGISTRY.all_types()` — auto-picks up new registrations |
| `backend/tests/test_block_registry.py` | Update count assertion from 7 → 10. Add parametrized checks for new types. | Regression guard |
| `backend/tests/test_dashboard.py` | Possibly add render tests for new block types via API | Integration coverage |

**Frontend:**

| File | Change | Why |
|------|--------|-----|
| `frontend/static/js/workspace.js` | Add `_executeSparqlWidgets()` function + htmx:afterSettle hook | Picks up `[data-sparql-query]` elements after block load, fetches SPARQL, populates DOM |
| `frontend/static/js/workspace.js` | Add `_initChartBlock()` function with Chart.js lazy loader | Loads Chart.js on demand, creates Chart instance from SPARQL results |
| `frontend/static/css/workspace.css` | Add `.dashboard-block-stat-card`, `.dashboard-block-chart`, `.dashboard-block-heading` styles | Visual presentation of new block types |
| `backend/app/templates/browser/dashboard_builder.html` | Add 3 cases to `getTypeConfigHTML()` switch + config collection in `_builderSave()` | Builder UI for configuring new block types |

### Existing Patterns to Follow

**BlockRegistry registration** (in `registry.py`):
```python
registry.register(BlockTypeSpec(
    type_name="stat-card",
    label="Stat Card",
    icon="hash",           # Lucide icon
    category="data",
    config_schema={"query": str, "label": str, "icon": str, "color": str},
    default_w=3,
    default_h=2,
))
```

**render_block dispatch** (in `router.py`):
Each block type returns `HTMLResponse(...)` with a `<div class="dashboard-block dashboard-block-{type}">` wrapper. Data-driven blocks include `data-*` attributes for frontend JS pickup.

**Builder config form** (in `dashboard_builder.html`):
`getTypeConfigHTML(blockType, config)` switch case returns HTML string with `<input>`/`<textarea>`/`<select>` elements tagged with `data-key="configFieldName"`. The save collector (`querySelectorAll('[data-key]')`) auto-collects values.

**htmx block loading** (in `dashboard_page.html`):
Blocks load via `hx-get="/browser/dashboard/{id}/block/{index}" hx-trigger="load"`. Content arrives as an HTML fragment. Any post-load JS must hook into `htmx:afterSettle` to find and activate new elements.

### Block Type Specifications

#### stat-card
- **Config:** `{query: str, label: str, icon: str, color: str}`
- **Render:** `<div class="dashboard-block dashboard-block-stat-card" data-sparql-query="..."><span class="stat-card-label">Label</span><span class="stat-card-icon"><i data-lucide="icon"></i></span><span class="stat-card-value" data-stat-target>...</span></div>`
- **Frontend:** After htmx load, `_executeSparqlWidgets()` finds `[data-sparql-query]` elements, POSTs to `/api/sparql` with JSON body `{query: "..."}`, extracts first binding's first value, sets `textContent` on `[data-stat-target]`.
- **Config schema:** `query` (SPARQL SELECT returning one row with one value column), `label` (display text), `icon` (Lucide icon name, optional), `color` (CSS color for value, optional).
- **Default size:** 3×2 (quarter-width, short).

#### chart
- **Config:** `{query: str, chart_type: str, label: str}`
- **Render:** `<div class="dashboard-block dashboard-block-chart" data-chart-query="..." data-chart-type="bar"><canvas class="chart-canvas"></canvas></div>`
- **Frontend:** After htmx load, `_initChartBlock()` lazy-loads Chart.js, executes SPARQL query, maps results to Chart.js `{labels, datasets}` format (expects `?label` and `?value` columns), creates `new Chart(canvas, config)`.
- **Chart types:** `bar`, `line`, `pie` (initial set — extensible later).
- **SPARQL result mapping:** `?label` → chart labels array, `?value` → dataset data array. Multiple `?value*` columns could support multi-series later, but v1 is single-series.
- **Default size:** 6×4 (half-width, standard height).

#### heading
- **Config:** `{text: str, level: str, subtitle: str, align: str}`
- **Render:** `<div class="dashboard-block dashboard-block-heading"><h2>Title</h2><p class="heading-subtitle">Subtitle</p></div>` (level configurable h1-h4).
- **Frontend:** Pure HTML — no JS needed.
- **Default size:** 12×2 (full-width, short).

#### markdown (FIX)
- **Current:** `html.escape()` + paragraph split — no real markdown rendering.
- **Fix:** Use `globalThis.marked.parse()` on the content, sanitize with `DOMPurify.sanitize()`, render to innerHTML.
- **Approach:** The backend renders the raw markdown into a `<script type="text/plain">` tag or data attribute, and the frontend uses the existing `marked.js` (already global) to parse and render. OR the backend renders using `marked.js` equivalent on the server — but since `marked.js` is already loaded client-side and the codebase uses client-side rendering elsewhere (markdown-render.js, canvas.js, vfs-browser.js), the client-side approach is consistent.
- **Implementation:** Backend emits `<div class="dashboard-block dashboard-block-markdown" data-md-content="...">Loading...</div>`. Frontend hook in `htmx:afterSettle` finds `[data-md-content]` and renders.
- **Alternative (simpler):** Backend emits the raw content in a `<template>` or `<script type="text/plain">` tag inside the block, frontend reads `.textContent` and calls `marked.parse()` + `DOMPurify.sanitize()`. This avoids escaping issues with `data-*` attributes for multi-line markdown.

#### sparql-result (FIX)
- **Current:** Renders `<span data-query="...">...</span>` but no JS executes the query.
- **Fix:** Change to `data-sparql-query="..."` (same attribute as stat-card for unified handling). Add `data-sparql-table` attribute to distinguish table rendering from scalar stat rendering.
- **Frontend:** `_executeSparqlWidgets()` detects `[data-sparql-table]`, fetches results, renders `<table>` with `<thead>` (from `head.vars`) and `<tbody>` (from `results.bindings`).

### Chart.js Lazy Loading

Chart.js is already vendored in `frontend/build.js` as `chartjs.js` → hashed filename in the manifest. The `asset_url` filter resolves it to `/assets/chartjs-xxx.min.js` in production or `/js/chartjs.js` in dev.

**Problem:** The workspace page doesn't include Chart.js in its `<script>` tags. Only the admin model_detail page loads it.

**Solution:** Lazy-load via a `<script>` tag injection when the first chart block is encountered:

```javascript
var _chartJsLoaded = false;
var _chartJsLoading = false;
var _chartJsCallbacks = [];

function _ensureChartJs(callback) {
    if (_chartJsLoaded) { callback(); return; }
    _chartJsCallbacks.push(callback);
    if (_chartJsLoading) return;
    _chartJsLoading = true;
    var script = document.createElement('script');
    script.src = _chartJsCdnUrl; // or asset_url resolved path
    script.onload = function() {
        _chartJsLoaded = true;
        _chartJsCallbacks.forEach(function(cb) { cb(); });
        _chartJsCallbacks = [];
    };
    document.head.appendChild(script);
}
```

**URL resolution:** The Chart.js URL must be available to the frontend JS. Options:
1. **Data attribute on `<body>` or a config element** — backend injects `data-chartjs-url="{{ 'chartjs.js' | asset_url }}"` somewhere in `base.html`. Frontend reads it.
2. **Hardcode CDN URL** — simpler but doesn't use the vendored build. The admin page already falls back to CDN: `https://cdn.jsdelivr.net/npm/chart.js@4.4/dist/chart.umd.min.js`.
3. **Expose asset manifest to JS** — overkill for one library.

**Recommendation:** Option 1 — add a `<meta>` tag or data attribute in `base.html` that exposes the Chart.js URL. The frontend reads it. This works for both dev (CDN fallback) and production (vendored hash).

Simplest: add `<script id="chartjs-url" type="application/json">"{{ 'chartjs.js' | asset_url }}"</script>` in `base.html`, read it in JS.

Even simpler: since Chart.js is only used on chart dashboard blocks (rare), just use the CDN URL directly. The admin page already does this as fallback. This avoids any base.html changes.

**Decision for planner:** Use CDN URL for v1 (`https://cdn.jsdelivr.net/npm/chart.js@4.4/dist/chart.umd.min.js`). Same URL already used in admin model_detail fallback. Can upgrade to vendored URL later if needed.

### SPARQL API Details

Endpoint: `POST /api/sparql` with `Content-Type: application/json` body `{"query": "SELECT ..."}`.

Response shape:
```json
{
    "head": {"vars": ["count"]},
    "results": {"bindings": [
        {"count": {"type": "literal", "value": "42", "datatype": "http://www.w3.org/2001/XMLSchema#integer"}}
    ]}
}
```

For stat-card: extract `results.bindings[0][vars[0]].value`.
For chart: map `results.bindings[*].label.value` → labels, `results.bindings[*].value.value` → data.
For sparql-result table: render `head.vars` as column headers, `results.bindings` as rows.

**Auth:** The SPARQL endpoint requires authentication (session cookie). Dashboard blocks load within the authenticated workspace context, so fetch calls will include the cookie automatically.

**Error handling:** If the query fails (400), display the error message in the block. If the network fails, show a generic error.

### Frontend Hook Point

The `htmx:afterSettle` event on `document.body` (line 3194 of `workspace.js`) already fires after block content loads. The new `_executeSparqlWidgets()` function should be called from this handler, scoped to the settled element:

```javascript
document.body.addEventListener('htmx:afterSettle', function(e) {
    var target = e.detail.elt;
    // Existing: Lucide icons
    if (typeof lucide !== 'undefined') {
        lucide.createIcons({ root: target });
    }
    // New: activate SPARQL widgets
    _executeSparqlWidgets(target);
    // New: activate chart blocks
    _initChartBlocks(target);
    // New: render markdown blocks
    _renderMarkdownBlocks(target);
});
```

**Important:** The existing `htmx:afterSettle` handler at line 3194 only does Lucide icon init. We need to add the widget activation calls there, OR add a separate handler (both work — htmx supports multiple handlers). Adding to the existing one is cleaner.

### CSS Styling Notes

- **stat-card:** Flex column layout. Large number (1.8em, bold, accent color). Small label above (0.8em, muted, uppercase). Optional Lucide icon. Per CLAUDE.md Lucide rules: size via CSS, `flex-shrink: 0`, `stroke: currentColor`.
- **chart:** Canvas element fills block. Needs `min-height: 0` in flex context to allow Chart.js responsive sizing.
- **heading:** Centered or left-aligned. h1-h4 sizes. Subtitle in muted color beneath. No borders.
- **Existing `.dashboard-block-sparql` CSS** already has nice stat-card-like styling (label + value). The stat-card can reuse this pattern but with more flexibility (icon, color).

### Test Strategy

- `test_block_registry.py`: Update count to 10 (7 existing + 3 new). Parametrized checks for new types' category, icon, config_schema.
- New `test_data_widgets.py` (or extend `test_dashboard.py`): Test `render_block()` output for stat-card, chart, heading, fixed markdown, fixed sparql-result. Verify HTML attributes (`data-sparql-query`, `data-chart-type`, `data-md-content`, etc.).
- Existing tests: `test_dashboard.py` (27 tests) and `test_dashboard_builder.py` (9 tests) must pass unchanged.

### What's NOT in This Slice

- Form-group block (done in S01)
- E2E Playwright tests (S03)
- User guide docs (S03)
- Dashboard viewer inline editing (deferred — BLK-09)
- JSON Schema formalization of config (deferred — BLK-06)
- Multi-dataset chart support (can extend later)

### Constraints and Gotchas

1. **Markdown data attribute escaping.** Multi-line markdown with quotes, angle brackets, etc. will break if stored in a `data-*` attribute. Use a `<script type="text/plain">` container instead — same pattern used by `renderMarkdownBody()` in `markdown-render.js`.

2. **Chart.js canvas sizing in GridStack.** Chart.js uses the canvas parent's dimensions for responsive sizing. Inside a GridStack cell, the parent might have `overflow: hidden` or constrained height. The chart canvas needs explicit `width: 100%; height: 100%` and the Chart.js `responsive: true, maintainAspectRatio: false` options.

3. **SPARQL query in HTML attribute.** The `data-sparql-query` attribute will contain full SPARQL text. This must be properly escaped (HTML entities for `<`, `>`, `&`, `"`). The backend's `HTMLResponse` construction must use proper escaping — not f-string interpolation of raw query text.

4. **htmx:afterSettle fires per-block.** Each block loads independently via `hx-trigger="load"`. The `_executeSparqlWidgets()` function will be called once per block settle. It should be idempotent — only activate widgets within the settled element, not re-process the entire page.

5. **`_builderSave()` config collection.** The save logic uses `querySelectorAll('[data-key]')` to collect config. New block types must follow this pattern — each config input has `data-key="fieldName"`. No special collection needed (unlike form-group which has custom slot/edge collection).
