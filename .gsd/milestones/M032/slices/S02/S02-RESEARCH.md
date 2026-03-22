# S02 Research: Data-Driven Widget Types (stat-card, chart, heading)

**Depth:** Targeted — known technologies (Chart.js, SPARQL), established patterns (BlockRegistry, htmx server-rendering), moderate integration complexity (server-side SPARQL execution in block renderer).

## Summary

This slice adds three new block types (`stat-card`, `chart`, `heading`) to the BlockRegistry and renders them via the existing `render_block()` endpoint. The heading block is trivial (pure config, no data dependency). The stat-card and chart blocks require **server-side SPARQL execution** during render — a new capability for the block renderer. The existing infrastructure (`_execute_sparql()`, `TriplestoreClient`, `scope_to_current_graph()`) is mature and importable. Chart.js is **not yet loaded** in `base.html` and must be added to both dev (CDN) and prod (CDN until vendored) asset blocks.

The slice also writes the M032 design document (`M032-DESIGN.md`) as a deliverable.

## Recommendation

**Straightforward three-task slice:**
1. **Register 3 new block types** in `registry.py` + add config panel HTML in `dashboard_builder.html` + unit tests
2. **Add server-side rendering** in `router.py` for all 3 types (heading inline, stat-card/chart via Jinja2 templates) + add Chart.js CDN to `base.html` + CSS for stat-card/chart widgets
3. **Write M032-DESIGN.md** summarizing the architecture decisions from S01-S02

All three block types should be rendered **server-side** during `render_block()` — the router should execute the SPARQL query, extract results, and return fully-rendered HTML. This matches the existing htmx pattern (blocks load via `hx-get` on page load) and avoids client-side SPARQL execution complexity. Chart.js initialization happens post-htmx-swap via an inline `<script>` in the rendered block HTML.

## Implementation Landscape

### Files That Change

| File | Change | Complexity |
|------|--------|------------|
| `backend/app/dashboard/registry.py` | Add 3 `BLOCK_REGISTRY.register()` calls for stat-card, chart, heading | Low |
| `backend/app/dashboard/router.py` | Add 3 new `elif` branches in `render_block()`, import `_execute_sparql` + `TriplestoreClient`, add `get_triplestore_client` dependency to `render_block()` | Medium |
| `backend/app/templates/browser/dashboard_builder.html` | Add `getTypeConfigHTML()` cases for stat-card, chart, heading | Low |
| `backend/app/templates/base.html` | Add Chart.js CDN in both dev and prod blocks | Low |
| `frontend/static/css/workspace.css` | Add `.dashboard-block-stat-card`, `.dashboard-block-chart`, `.dashboard-block-heading` styles | Low |
| `backend/tests/test_block_registry.py` | Update expected type count (6→9), add parameterized tests for new types | Low |

### Files That DON'T Change

- `models.py` — `VALID_BLOCK_TYPES` is derived from `BLOCK_REGISTRY.all_types()`, auto-updated
- `service.py` — validation delegates to `BLOCK_REGISTRY.validate_block()`, auto-covers new types
- `migration.py` — only handles legacy layout→GridStack position mapping, no new-type concern
- `dashboard_page.html` — blocks already load via `hx-get`, no type-specific rendering needed there

### New Dependencies

**Chart.js 4.4** — needs a CDN `<script>` tag in `base.html`. The research doc (§3.1) mentions it's "already CDN-loaded" but this is incorrect — it's referenced in the M032 research as a future addition but **does not appear in `base.html` yet**. Needs adding.

**CDN URL (dev):** `https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js`
**CDN URL (prod):** Same (not yet in vendor bundle, matches GridStack pattern)

### New Templates (Optional)

Block rendering can stay inline in the router (matching existing pattern) or use Jinja2 templates. For stat-card and chart, Jinja2 templates are recommended because:
- Stat-card HTML is non-trivial (icon, label, value, color accent)
- Chart block needs a `<canvas>` element + inline `<script>` for Chart.js initialization
- Templates are easier to iterate on for CSS/layout adjustments

Suggested template paths:
- `backend/app/templates/browser/blocks/block_stat_card.html`
- `backend/app/templates/browser/blocks/block_chart.html`

Heading can stay inline (it's just an `<hN>` tag).

## Key Technical Details

### 1. Server-Side SPARQL Execution in render_block()

The `render_block()` function currently does **not** have access to `TriplestoreClient`. It needs to be added as a dependency:

```python
from app.dependencies import get_triplestore_client
from app.triplestore.client import TriplestoreClient
from app.sparql.client import inject_prefixes, scope_to_current_graph

@browser_router.get("/{dashboard_id}/block/{block_index}")
async def render_block(
    request: Request,
    dashboard_id: str,
    block_index: int,
    context_iri: str = Query(default=""),
    context_var: str = Query(default=""),
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),  # NEW
):
```

Then for stat-card/chart blocks:
```python
# Execute SPARQL and extract value
processed = inject_prefixes(config.get("query", ""))
processed = scope_to_current_graph(processed)
results = await client.query(processed)
bindings = results.get("results", {}).get("bindings", [])
```

The `_execute_sparql()` helper from `sparql/router.py` wraps this exact pattern but it's a module-level function with extra parameters. Importing it directly is fine:
```python
from app.sparql.router import _execute_sparql
```

This is already done in `browser/sparql_result.py` — proven import pattern.

### 2. Stat-Card Block

**Config schema:**
```python
BlockTypeSpec(
    type_name="stat-card",
    label="Stat Card",
    icon="hash",
    category="data",
    config_schema={
        "query": str,      # SPARQL SELECT returning 1 row, 1 variable
        "label": str,       # Display label (e.g. "Total Projects")
        "icon": str,        # Lucide icon name (optional)
        "color": str,       # Accent color token or hex (optional)
    },
    default_w=3,
    default_h=2,
)
```

**Rendering:** Execute SPARQL query → extract first binding's first value → render as styled card with large number + label + icon.

**SPARQL result extraction pattern:**
```python
bindings = results.get("results", {}).get("bindings", [])
vars = results.get("head", {}).get("vars", [])
if bindings and vars:
    value = bindings[0].get(vars[0], {}).get("value", "—")
```

**Error states:** empty query → error message; SPARQL failure → "Query Error"; no results → "—" (dash).

### 3. Chart Block

**Config schema:**
```python
BlockTypeSpec(
    type_name="chart",
    label="Chart",
    icon="bar-chart-2",
    category="data",
    config_schema={
        "query": str,           # SPARQL SELECT returning rows with label + value columns
        "chart_type": str,      # "bar", "line", "pie", "doughnut"
        "label_var": str,       # Variable name for labels (optional, defaults to first var)
        "value_var": str,       # Variable name for values (optional, defaults to second var)
    },
    default_w=6,
    default_h=4,
)
```

**Rendering:** Execute SPARQL query → extract all bindings → serialize labels[] and values[] into JSON → render `<canvas>` element + inline `<script>` that creates a Chart.js instance.

**Chart.js initialization post-htmx-swap:** The inline `<script>` in the rendered HTML runs when htmx swaps the block content. Chart.js must already be loaded globally. The script creates a `new Chart(canvas, {type, data, options})` instance. The canvas element needs a unique ID per block (use block index or a random suffix).

**Chart.js dark theme integration:** Use CSS variable values for chart colors. The inline script can read computed styles:
```javascript
var style = getComputedStyle(document.documentElement);
var textColor = style.getPropertyValue('--color-text').trim();
var borderColor = style.getPropertyValue('--color-border').trim();
```

### 4. Heading Block

**Config schema:**
```python
BlockTypeSpec(
    type_name="heading",
    label="Heading",
    icon="type",
    category="layout",
    config_schema={
        "text": str,    # Heading text
        "level": str,   # "h1", "h2", "h3", "h4" (default "h2")
    },
    default_w=12,
    default_h=1,
)
```

**Rendering:** Pure HTML — `<hN class="dashboard-block-heading">text</hN>`. HTML-escape the text. Validate level is h1-h4.

### 5. Builder Config Panels

Add three new cases to `getTypeConfigHTML()` in `dashboard_builder.html`:

- **stat-card:** SPARQL query textarea + label text input + icon text input + color picker/text input
- **chart:** SPARQL query textarea + chart_type select (bar/line/pie/doughnut) + label_var input + value_var input
- **heading:** text input + level select (h1/h2/h3/h4)

The existing builder save serialization already handles `[data-key]` elements generically — no save logic changes needed.

### 6. CSS Styling

**Stat-card:** Needs a distinctive visual — large metric number, muted label below, optional icon left-aligned, optional color accent on left border or background tint. Reference: Grafana stat panels, Zabbix stat widgets.

```css
.dashboard-block-stat-card {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px;
    height: 100%;
}
.dashboard-block-stat-card .stat-icon { /* Lucide icon */ }
.dashboard-block-stat-card .stat-value { font-size: 2rem; font-weight: 700; }
.dashboard-block-stat-card .stat-label { font-size: 0.85rem; color: var(--color-text-muted); }
```

**Chart:** Needs a canvas container that fills the GridStack widget. Chart.js is responsive by default when `responsive: true` and `maintainAspectRatio: false`.

```css
.dashboard-block-chart {
    height: 100%;
    padding: 8px;
    position: relative;
}
.dashboard-block-chart canvas {
    width: 100% !important;
    height: 100% !important;
}
```

**Heading:** Minimal — just typography sizing.

**Important CSS notes per CLAUDE.md:** Lucide icons inside stat-card flex containers need `flex-shrink: 0` on the SVG. Stroke inheritance via `stroke: currentColor`.

### 7. Existing sparql-result Block Issue

The current `sparql-result` block renders a placeholder with `data-query` attribute but **no client-side JS ever executes it**. It's effectively broken/incomplete. The stat-card block supersedes it for single-value metrics with proper server-side execution. This is not a blocker for S02 but worth noting — `sparql-result` should eventually be refactored to use server-side execution too.

## Constraints & Gotchas

1. **Chart.js CDN must load before dashboard blocks render** — It's in `<head>` so this is fine for normal page loads. For dockview panel opens (htmx-loaded content), Chart.js is already available globally since `base.html` loads it once.

2. **Chart.js canvas sizing in GridStack widgets** — Chart.js needs `responsive: true, maintainAspectRatio: false` to fill the widget cell. The canvas parent must have a defined height (GridStack provides this via `cellHeight`).

3. **SPARQL query errors should not crash the block** — Wrap SPARQL execution in try/except and render a user-friendly error message in the block HTML.

4. **render_block() signature change** — Adding `client: TriplestoreClient` as a FastAPI dependency parameter is backward-compatible (FastAPI injects it automatically). Existing block types ignore it.

5. **Block templates directory** — `backend/app/templates/browser/blocks/` doesn't exist yet. Creating it establishes a clean pattern for future block templates.

6. **Inline `<script>` in htmx-swapped content** — htmx evaluates inline scripts in swapped content by default (htmx v2 `hx-swap="innerHTML"` behavior). The Chart.js init script will run. No special configuration needed.

7. **Chart.js color palette for data series** — Use a fixed palette that works in both light and dark themes. Chart.js doesn't auto-adapt to CSS themes, so the init script should read CSS custom properties.

## Verification Strategy

### Unit Tests (no Docker)
- Registry: 9 block types registered (was 6), all specs have valid fields
- Registry: validate_block() passes for valid stat-card/chart/heading configs
- Registry: validate_block() rejects wrong config types for new block types
- **Run:** `cd backend && python -m pytest tests/test_block_registry.py -v`

### Integration Tests (Docker stack)
- Create a dashboard with stat-card block configured with `SELECT (COUNT(*) AS ?count) WHERE { ?s a ?o }` → stat-card renders a number
- Create a dashboard with chart block → Chart.js canvas renders
- Create a dashboard with heading block → h2 element renders
- **Verify via browser:** Open dashboard page, inspect that blocks load via htmx and display data

### File Presence Checks
- `backend/app/templates/browser/blocks/block_stat_card.html` exists
- `backend/app/templates/browser/blocks/block_chart.html` exists
- Chart.js CDN appears in `backend/app/templates/base.html`
- `stat-card`, `chart`, `heading` appear in `BLOCK_REGISTRY.all_types()`
