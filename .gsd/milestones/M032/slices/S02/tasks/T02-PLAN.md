---
estimated_steps: 5
estimated_files: 5
skills_used:
  - best-practices
---

# T02: Implement server-side block rendering with SPARQL execution, Chart.js, and CSS

**Slice:** S02 — Data-Driven Widget Types (stat-card, chart, heading)
**Milestone:** M032

## Description

Make the 3 new block types registered in T01 actually render content when loaded via htmx. The heading block is pure HTML. The stat-card and chart blocks execute SPARQL queries server-side in `render_block()` and return fully-rendered HTML. Chart.js must be loaded globally for chart initialization. CSS styles make the widgets visually distinct.

The key integration point is adding `TriplestoreClient` as a FastAPI `Depends()` parameter to `render_block()` in `router.py`. This lets stat-card and chart blocks run SPARQL queries during rendering. The `_execute_sparql()` function from `backend/app/sparql/router.py` wraps prefix injection + graph scoping + execution — import it directly (this import pattern is already used by `backend/app/browser/sparql_result.py`).

## Steps

1. **Add Chart.js CDN to `base.html`** — In both the `{% if asset_manifest_available %}` (prod) and `{% else %}` (dev) blocks, add:
   ```html
   <script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
   ```
   Place it after the GridStack lines in each block. Chart.js must load before dashboard blocks render (it's in `<head>` so this is guaranteed for normal page loads).

2. **Create Jinja2 block templates** in `backend/app/templates/browser/blocks/`:

   **`block_stat_card.html`** — a flex container with optional icon, large value, and label:
   ```html
   <div class="dashboard-block dashboard-block-stat-card" {% if color %}style="border-left: 4px solid {{ color }}"{% endif %}>
     {% if icon %}<div class="stat-icon"><i data-lucide="{{ icon }}"></i></div>{% endif %}
     <div class="stat-body">
       <div class="stat-value">{{ value }}</div>
       <div class="stat-label">{{ label }}</div>
     </div>
   </div>
   <script>if(typeof lucide!=='undefined')lucide.createIcons();</script>
   ```
   Template context: `value` (str), `label` (str), `icon` (str or empty), `color` (str or empty).

   **`block_chart.html`** — a canvas element + inline Chart.js initialization script:
   - Canvas with unique `id="chart-{{ chart_id }}"` inside a `.dashboard-block-chart` container
   - Inline `<script>` that:
     - Reads CSS custom properties for theme-aware colors (`--color-text`, `--color-border`)
     - Creates a `new Chart(canvas, {type: chart_type, data: {labels, datasets}, options})` with `responsive: true, maintainAspectRatio: false`
     - Uses a fixed color palette array that works in both light/dark themes
   - Template context: `chart_id` (str), `chart_type` (str), `labels` (JSON string), `values` (JSON string), `label` (str, for dataset label)
   - The chart_id should use a combination of dashboard_id + block_index for uniqueness.

3. **Add `TriplestoreClient` dependency and rendering branches to `render_block()` in `router.py`**:

   Add imports at the top of `router.py`:
   ```python
   from app.dependencies import get_triplestore_client
   from app.triplestore.client import TriplestoreClient
   from app.sparql.router import _execute_sparql
   ```

   Add `client: TriplestoreClient = Depends(get_triplestore_client)` parameter to `render_block()`.

   Add 3 `elif` branches before the final fallback `return`:

   **heading**: Validate `level` is one of h1-h4 (default "h2"). HTML-escape the `text` value using `html.escape()`. Return `HTMLResponse(f'<{level} class="dashboard-block dashboard-block-heading">{escaped_text}</{level}>')`.

   **stat-card**: Get `query` from config. If empty, return error HTML. Execute SPARQL via `_execute_sparql(query, client)` wrapped in try/except. Extract result: `bindings[0][vars[0]]["value"]` (first row, first variable). If no results, value = "—". Render via Jinja2 template `browser/blocks/block_stat_card.html` passing `value`, `label` (from config, default ""), `icon` (from config, default ""), `color` (from config, default ""). On SPARQL error, log warning and return error HTML `<div class="dashboard-block dashboard-block-error">Query Error</div>`.

   **chart**: Get `query` from config. If empty, return error HTML. Execute SPARQL via `_execute_sparql(query, client)` wrapped in try/except. Extract `label_var` and `value_var` from config (default to first and second SPARQL variables). Build `labels` list and `values` list from all bindings. Generate `chart_id = f"{dashboard_id}-{block_index}"`. Render via Jinja2 template `browser/blocks/block_chart.html` passing `chart_id`, `chart_type` (from config, default "bar"), `labels` (JSON-serialized), `values` (JSON-serialized), `label` (dataset label, default "Value"). On SPARQL error, return error HTML.

4. **Add CSS styles to `workspace.css`** at the end of the existing dashboard-block section (after the `.dashboard-page .dashboard-block-divider` block around line 7789):

   ```css
   /* -- Stat card block -- */
   .dashboard-block-stat-card { display: flex; align-items: center; gap: 12px; padding: 16px; height: 100%; }
   .dashboard-block-stat-card .stat-icon { ... flex-shrink: 0; }
   .dashboard-block-stat-card .stat-icon svg { width: 24px; height: 24px; flex-shrink: 0; stroke: currentColor; }
   .dashboard-block-stat-card .stat-value { font-size: 2rem; font-weight: 700; line-height: 1.2; }
   .dashboard-block-stat-card .stat-label { font-size: 0.85rem; color: var(--color-text-muted); margin-top: 2px; }
   /* -- Chart block -- */
   .dashboard-block-chart { height: 100%; padding: 8px; position: relative; }
   .dashboard-block-chart canvas { width: 100% !important; height: 100% !important; }
   /* -- Heading block -- */
   .dashboard-block-heading { padding: 8px 16px; margin: 0; font-weight: 600; }
   ```

   Also add `.dashboard-page` scoped variants matching the existing pattern for consistent rendering in the viewer.

   **Critical per CLAUDE.md**: Lucide icons inside the stat-card flex container MUST have `flex-shrink: 0` on the SVG and `stroke: currentColor` for color inheritance.

5. **Verify all file changes are consistent**: Ensure the `elif` branch names in `router.py` exactly match the `type_name` strings registered in `registry.py` ("stat-card", "chart", "heading").

## Must-Haves

- [ ] Chart.js CDN script tag present in both dev and prod blocks of `base.html`
- [ ] `block_stat_card.html` Jinja2 template renders a flex card with value, label, optional icon, optional color accent
- [ ] `block_chart.html` Jinja2 template renders a canvas + inline Chart.js init script with theme-aware colors
- [ ] `render_block()` has `TriplestoreClient` dependency and handles stat-card, chart, heading types
- [ ] SPARQL errors produce `dashboard-block-error` HTML, not HTTP 500 exceptions
- [ ] CSS for stat-card uses flex with `flex-shrink: 0` on SVG icons per CLAUDE.md
- [ ] Chart.js uses `responsive: true, maintainAspectRatio: false` for proper GridStack sizing

## Verification

- `grep -q "chart.js" backend/app/templates/base.html` — Chart.js CDN present
- `test -f backend/app/templates/browser/blocks/block_stat_card.html` — stat-card template exists
- `test -f backend/app/templates/browser/blocks/block_chart.html` — chart template exists
- `grep -q "stat-card" backend/app/dashboard/router.py` — stat-card branch in renderer
- `grep -q "get_triplestore_client" backend/app/dashboard/router.py` — dependency wired
- `grep -q "dashboard-block-stat-card" frontend/static/css/workspace.css` — CSS added
- `grep -q "dashboard-block-chart" frontend/static/css/workspace.css` — CSS added
- `grep -q "dashboard-block-heading" frontend/static/css/workspace.css` — CSS added

## Observability Impact

- Signals added/changed: `logger.warning()` on SPARQL query failure in stat-card/chart render_block branches, including query text and error message
- How a future agent inspects this: Check rendered block HTML for `.dashboard-block-error` class; check backend logs for "SPARQL" + "error" + dashboard_id
- Failure state exposed: Users see "Query Error" in the block widget instead of empty or broken content

## Inputs

- `backend/app/dashboard/registry.py` — T01 output with 9 registered types (needed for type validation)
- `backend/app/dashboard/router.py` — existing render_block() function to extend
- `backend/app/templates/base.html` — existing template to add Chart.js CDN
- `frontend/static/css/workspace.css` — existing CSS to add new block styles
- `backend/app/sparql/router.py` — `_execute_sparql()` function to import
- `backend/app/dependencies.py` — `get_triplestore_client` dependency to import

## Expected Output

- `backend/app/dashboard/router.py` — 3 new elif branches + TriplestoreClient dependency
- `backend/app/templates/browser/blocks/block_stat_card.html` — new Jinja2 template
- `backend/app/templates/browser/blocks/block_chart.html` — new Jinja2 template
- `backend/app/templates/base.html` — Chart.js CDN added in dev and prod blocks
- `frontend/static/css/workspace.css` — stat-card, chart, heading CSS styles added
