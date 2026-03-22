# M032 Design: Block-Based Custom UI Builder

## Overview

M032 replaced the fixed CSS Grid dashboard layout system with a free-form, drag-and-drop GridStack.js canvas backed by a typed BlockRegistry. The milestone was structured as two slices:

- **S01 — GridStack Layout Engine + Block Registry:** Introduced the GridStack 12-column grid, the `BlockRegistry` singleton with 6 initial block types, categorised builder palette, layout migration for 5 legacy CSS Grid layouts, and static (read-only) viewer rendering.
- **S02 — Data-Driven Widget Types:** Added 3 new block types (stat-card, chart, heading) with server-side SPARQL execution, Chart.js visualization, and themed CSS styling.

**Before M032:** Dashboards used one of 5 hardcoded CSS Grid layouts (`single`, `sidebar-main`, `grid-2x2`, `grid-3`, `top-bottom`). Blocks were assigned to named slots. There was no drag, resize, or free positioning.

**After M032:** Dashboards use a 12-column GridStack grid. Each block stores `{x, y, w, h}` position data. The builder provides a categorised palette with click-to-add and drag-to-add. Data-driven widgets execute SPARQL queries server-side and render results as numbers, charts, or styled headings.

## Architecture

The dashboard system is a pipeline of four layers: **registry → builder → persistence → viewer**.

```
                     ┌──────────────────────┐
                     │   BlockRegistry       │  (Python singleton)
                     │   9 BlockTypeSpecs    │
                     └──────────┬───────────┘
                                │ spec data
                     ┌──────────▼───────────┐
                     │   Builder UI          │  (GridStack.js + htmx)
                     │   Palette + Canvas    │
                     └──────────┬───────────┘
                                │ JSON blocks array
                     ┌──────────▼───────────┐
                     │   DashboardSpec       │  (SQLAlchemy / SQLite)
                     │   blocks_json column  │
                     └──────────┬───────────┘
                                │ block list
                     ┌──────────▼───────────┐
                     │   Viewer              │  (Static GridStack grid)
                     │   htmx lazy-load      │  → render_block() per block
                     └──────────────────────┘
```

### GridStack.js Integration

GridStack.js (loaded from CDN) provides the 12-column drag-and-resize grid for both the builder and viewer:

- **Builder** (`dashboard_builder.html`): Interactive mode — users drag blocks from the palette or click to add. GridStack manages `{x, y, w, h}` positions. Serialization reads `el.gridstackNode` for positions and `[data-key]` elements for config values.
- **Viewer** (`dashboard_page.html`): Static mode (`staticGrid: true`, `gs-no-resize`, `gs-no-move`) — blocks render at their stored positions. Each block loads its content via an htmx `hx-get` to `/browser/dashboard/{id}/block/{index}`.

### htmx Server-Rendering Pipeline

Dashboard blocks are lazy-loaded via htmx. The viewer template places `hx-get="/browser/dashboard/{id}/block/{index}"` on each GridStack widget content div with `hx-trigger="load"`. The `render_block()` endpoint in `router.py` dispatches by block type, executing any necessary server-side logic (SPARQL queries for data blocks) and returning HTML fragments.

### Dockview Event Isolation

The dashboard builder runs inside a dockview panel. GridStack's drag events would normally bubble up and trigger dockview's panel drag. Both the builder canvas and palette wrapper use `stopPropagation()` on `mousedown`, `pointerdown`, and `touchstart` events to prevent interference — the same proven pattern used by `canvas.js` and `kanban.js`.

### CDN Loading Strategy

GridStack.js and Chart.js are loaded from CDN in both dev and prod asset blocks of `base.html`. They are not yet vendored into the esbuild bundle. This is a pragmatic choice for iteration speed; vendoring is planned for a future stabilisation pass.

**Key files:**

| File | Role |
|------|------|
| `backend/app/dashboard/registry.py` | BlockRegistry singleton with 9 BlockTypeSpec declarations |
| `backend/app/dashboard/router.py` | Browser routes (builder, viewer, block renderer) and JSON API |
| `backend/app/dashboard/models.py` | SQLAlchemy model, VALID_LAYOUTS, VALID_BLOCK_TYPES (derived from registry) |
| `backend/app/dashboard/service.py` | CRUD operations with registry-based validation |
| `backend/app/dashboard/migration.py` | Legacy CSS Grid → GridStack position migration |
| `backend/app/templates/browser/dashboard_builder.html` | Builder UI with GridStack canvas and categorised palette |
| `backend/app/templates/browser/dashboard_page.html` | Viewer with static GridStack grid and htmx block loading |
| `backend/app/templates/browser/blocks/block_stat_card.html` | Jinja2 template for stat-card widget rendering |
| `backend/app/templates/browser/blocks/block_chart.html` | Jinja2 template for Chart.js widget rendering |
| `backend/app/templates/base.html` | GridStack.js + Chart.js CDN script tags |
| `frontend/static/css/workspace.css` | Dashboard builder, viewer, and widget CSS (~335 lines) |

## Block Registry

The `BlockRegistry` is the single source of truth for which block types exist and how they are validated.

### BlockTypeSpec Dataclass

Each block type is declared as a `BlockTypeSpec` (frozen dataclass) with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `type_name` | `str` | Machine-readable identifier (e.g. `"markdown"`, `"stat-card"`) |
| `label` | `str` | Human-readable display name |
| `icon` | `str` | Lucide icon name for palette / UI |
| `category` | `str` | Grouping key: `"content"`, `"data"`, or `"layout"` |
| `config_schema` | `dict[str, type]` | Maps config key names to expected Python types |
| `default_w` | `int` | Default GridStack width in columns (1–12) |
| `default_h` | `int` | Default GridStack height in rows (≥ 1) |

### BLOCK_REGISTRY Singleton API

The module-level `BLOCK_REGISTRY` is constructed by `_build_default_registry()` at import time.

| Method | Signature | Description |
|--------|-----------|-------------|
| `register` | `(spec: BlockTypeSpec) → None` | Add a new block type; raises `ValueError` on duplicate |
| `get` | `(type_name: str) → BlockTypeSpec` | Look up by type name; raises `KeyError` if unknown |
| `all_types` | `() → list[str]` | Sorted list of all registered type names |
| `all_specs` | `() → list[BlockTypeSpec]` | All specs sorted by type name |
| `by_category` | `() → dict[str, list[BlockTypeSpec]]` | Specs grouped by category |
| `validate_block` | `(block: dict) → None` | Validates type exists, config is a dict, config values match schema types |
| `validate_position` | `(block: dict) → None` | Validates x/y/w/h are ints within GridStack bounds (12-col) |

### Config Schema Validation

Validation is lightweight and intentionally lenient:

- Config keys declared in the schema are type-checked when present.
- All config keys are optional — this allows partial/progressive configuration in the builder.
- Unknown config keys are silently ignored.
- Type checking uses `isinstance()` against the declared Python type.

The `VALID_BLOCK_TYPES` set in `models.py` is derived from the registry at import time via `set(BLOCK_REGISTRY.all_types())`, ensuring the model layer stays in sync with registered types.

## Widget Inventory

All 9 registered block types:

| Type Name | Category | Config Keys | Rendering | Default Size |
|-----------|----------|-------------|-----------|--------------|
| `markdown` | content | `content: str` | Inline HTML — escapes content, splits on double newlines into `<p>` tags | 6×4 |
| `view-embed` | data | `spec_iri: str`, `height: str`, `renderer_type: str`, `emits_context: bool`, `listens_to_context: str` | htmx `hx-get` to existing view renderer; supports cross-block context passing | 6×4 |
| `object-embed` | data | `object_iri: str`, `mode: str` | htmx `hx-get` to object detail view | 6×4 |
| `create-form` | data | `target_class: str`, `defaults: dict` | htmx `hx-get` to SHACL create-form | 6×6 |
| `sparql-result` | data | `query: str`, `label: str` | Inline HTML with data-query attribute for client-side execution | 4×3 |
| `divider` | layout | *(none)* | Inline `<hr>` element | 12×1 |
| `stat-card` | data | `query: str`, `label: str`, `icon: str`, `color: str` | Server-side SPARQL → Jinja2 template (`block_stat_card.html`); flex layout with optional Lucide icon, large metric value, accent color border | 3×2 |
| `chart` | data | `query: str`, `chart_type: str`, `label_var: str`, `value_var: str` | Server-side SPARQL → Jinja2 template (`block_chart.html`); Chart.js canvas with IIFE init script, 10-color palette, theme-aware axis colors | 6×4 |
| `heading` | layout | `text: str`, `level: str` | Inline `<hN>` element (h1–h4, default h2); HTML-escaped text | 12×1 |

### Category Breakdown

- **content** (1): markdown
- **data** (5): view-embed, object-embed, create-form, sparql-result, stat-card, chart
- **layout** (2): divider, heading

## Layout Migration

The `migrate_layout_to_gridstack()` function in `migration.py` converts legacy CSS Grid layouts to GridStack positions. It maps each of the 5 legacy layouts to `{x, y, w, h}` positions based on the block's `slot` field.

### Slot Mappings

| Layout | Slots → Positions |
|--------|-------------------|
| `single` | All blocks stack vertically at full width: `(0, y, 12, 4)` with auto-incrementing y |
| `sidebar-main` | `sidebar → (0,0,3,6)`, `main → (3,0,9,6)` |
| `grid-2x2` | `top-left → (0,0,6,4)`, `top-right → (6,0,6,4)`, `bottom-left → (0,4,6,4)`, `bottom-right → (6,4,6,4)` |
| `grid-3` | `left → (0,0,4,6)`, `center → (4,0,4,6)`, `right → (8,0,4,6)` |
| `top-bottom` | `top → (0,0,12,4)`, `bottom → (0,4,12,4)` |

### Migration Behaviour

- **Lazy migration:** Runs on first dashboard access in `render_dashboard()` when `dashboard.layout != "gridstack"`. The migrated layout is persisted via `service.update()` so future loads skip migration.
- **Idempotency:** Blocks that already carry GridStack position fields (`x` present) pass through unchanged.
- **Unmatched slots:** Blocks whose slot doesn't match any known position in the layout are stacked vertically at full width below the last positioned block.
- **Input immutability:** Blocks are shallow-copied (with deep-copied config) to avoid mutating the input list.

### Verification

Layout migration is covered by 14 unit tests in `backend/tests/test_layout_migration.py`, testing all 5 layouts, edge cases, idempotency, and input immutability.

## Data Flow for SPARQL Widgets

The stat-card and chart block types execute SPARQL queries server-side in the `render_block()` endpoint, producing fully-rendered HTML that the viewer loads via htmx.

### Execution Path

```
1. Viewer loads → htmx fires GET /browser/dashboard/{id}/block/{index}
2. render_block() reads block type + config from DashboardSpec
3. For stat-card/chart: extracts query string from config
4. Calls _execute_sparql(query, client) using the TriplestoreClient dependency
5. Parses SPARQL JSON results:
   - stat-card: extracts first binding's first variable value → single metric
   - chart: extracts label_var and value_var columns → labels[] + values[]
6. Renders Jinja2 template with extracted data
7. Returns HTMLResponse fragment → htmx swaps into widget content div
```

### SPARQL Result Extraction

- **stat-card:** Uses `head.vars[0]` (first SPARQL variable) to extract the metric value from the first binding. Falls back to em-dash (—) when no bindings are returned.
- **chart:** Uses `config.label_var` or `head.vars[0]` for labels, `config.value_var` or `head.vars[1]` for values. Values are coerced to `float` with fallback to `0` for Chart.js numeric requirements.

### Chart.js Initialization

The chart template (`block_chart.html`) contains an inline IIFE script that:

1. Gets the canvas element by `chart-{dashboard_id}-{block_index}` ID.
2. Reads CSS custom properties (`--color-text`, `--color-border`) for theme-aware colors.
3. Uses a fixed 10-color palette that works in both light and dark themes.
4. Creates a `Chart` instance with `responsive: true` and `maintainAspectRatio: false`.
5. Conditionally adds axis scales only for non-radial chart types (skips pie/doughnut).

This IIFE runs immediately after htmx swaps the block content into the DOM, ensuring the canvas is available and the Chart.js global (`Chart`) is already loaded from the CDN.

### Error Handling

SPARQL query failures are handled at two levels:

- **Logging:** `logger.warning()` logs the dashboard ID, block index, exception message, and the full SPARQL query text. This is safe because SPARQL queries contain no user secrets.
- **User-visible error:** The block renders a `<div class="dashboard-block-error">` with "Query Error" (stat-card) or "Chart Error" (chart) text. This class is styled distinctly and is inspectable in the DOM for diagnostics.

Missing or empty query config produces a similar error block with "No query configured" text, without logging (since there's no query to execute).

## Key Decisions

### Event Isolation via stopPropagation

GridStack drag events would bubble up and trigger dockview's panel drag handler. The builder canvas and palette both call `stopPropagation()` on `mousedown`, `pointerdown`, and `touchstart`. This is the same pattern proven in `canvas.js` and `kanban.js` and has been reliable across all dashboard testing.

### Server-Side SPARQL Execution

SPARQL queries for stat-card and chart blocks are executed server-side in `render_block()`, not client-side. This keeps query logic in Python where the `TriplestoreClient` dependency is available, avoids CORS/auth complexity for client-side SPARQL, and produces fully-rendered HTML that htmx can swap directly. The tradeoff is that dashboard refresh requires a round-trip per data block, but htmx's lazy loading parallelises these naturally.

### CDN Loading (Not Yet Vendored)

GridStack.js and Chart.js are loaded from CDN in both dev and prod blocks of `base.html`. This was chosen for iteration speed during M032 development. A future stabilisation pass should vendor these into the esbuild bundle (following the M029 pattern) to eliminate the external dependency.

### Chart.js Theme Integration

Chart.js reads CSS custom properties (`--color-text`, `--color-border`) at render time for theme-aware axis and legend colors. The 10-color data palette is a fixed set chosen to provide good contrast in both light and dark themes. This approach avoids coupling Chart.js config to the application's theme system while still responding to theme changes on page load.

### Lightweight Config Validation

The registry validates config value types but does not enforce required keys. All config keys are optional, allowing users to progressively build block configuration in the builder. This means a block can be saved with partial config (e.g. a chart with only a query but no chart_type yet) and will use defaults at render time.

### stat-card / chart / heading Default Dimensions

Default GridStack cell sizes reflect typical usage patterns:

- **stat-card** (3×2): Compact metric display, fits 4 across a 12-column grid.
- **chart** (6×4): Half-width, enough vertical space for axes and legend.
- **heading** (12×1): Full-width, single row — acts as a section divider with text.

## Observability and Diagnostics

### Inspect Registered Block Types

```bash
cd backend && python3 -c "from app.dashboard.registry import BLOCK_REGISTRY; print(BLOCK_REGISTRY.all_types())"
# → ['chart', 'create-form', 'divider', 'heading', 'markdown', 'object-embed', 'sparql-result', 'stat-card', 'view-embed']
```

### Inspect a Specific Block Type

```bash
cd backend && python3 -c "from app.dashboard.registry import BLOCK_REGISTRY; print(BLOCK_REGISTRY.get('stat-card'))"
```

### Test Validation Failure Path

```bash
cd backend && python3 -c "from app.dashboard.registry import BLOCK_REGISTRY; BLOCK_REGISTRY.validate_block({'type':'stat-card','config':{'query':42}})"
# → ValueError: Block 'stat-card' config key 'query' must be str, got int
```

### Check SPARQL Error in DOM

When a stat-card or chart block's SPARQL query fails, the rendered HTML contains:
```html
<div class="dashboard-block dashboard-block-error">Query Error</div>
```
Inspect for `.dashboard-block-error` elements in the dashboard DOM.

### Check Backend Logs

SPARQL failures are logged at WARNING level:
```
SPARQL query failed for stat-card in dashboard <uuid> block <index>: <error> — query: <sparql>
```

### Verify Chart.js is Loaded

In the browser console: `typeof Chart !== 'undefined'` should return `true`.
