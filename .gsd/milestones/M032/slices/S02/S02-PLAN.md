# S02: Data-Driven Widget Types (stat-card, chart, heading)

**Goal:** The BlockRegistry includes stat-card, chart, and heading widget types, each with a config panel in the builder and server-side rendering that produces live data from SPARQL queries (stat-card, chart) or static content (heading). Chart.js is loaded globally. The M032 design document is written.

**Demo:** A user opens the dashboard builder, adds a stat-card block configured with a SPARQL count query, a chart block with a bar chart query, and a heading block with "Overview" text. Saving and opening the dashboard shows a large metric number on the stat-card, a Chart.js bar chart on the chart block, and an h2 heading — all rendered server-side via the existing htmx block-loading pattern.

## Must-Haves

- `stat-card`, `chart`, and `heading` registered in `BLOCK_REGISTRY` with correct config schemas, icons, categories, and default dimensions
- `render_block()` in `router.py` executes SPARQL queries server-side for stat-card and chart blocks using `TriplestoreClient`
- Chart.js CDN loaded in `base.html` (both dev and prod blocks)
- Builder config panels for all 3 new types in `dashboard_builder.html`
- Jinja2 templates for stat-card and chart blocks in `backend/app/templates/browser/blocks/`
- CSS styles for stat-card (flex layout, large metric), chart (responsive canvas), and heading
- Unit tests updated: 9 block types registered, validation passes for new types
- SPARQL errors in stat-card/chart render user-friendly error HTML, not exceptions
- `M032-DESIGN.md` written summarizing architecture decisions from S01-S02

## Proof Level

- This slice proves: integration (server-side SPARQL → rendered HTML via htmx)
- Real runtime required: yes (Chart.js rendering, SPARQL execution need Docker stack)
- Human/UAT required: yes (visual verification of stat-card appearance and chart rendering)

## Verification

- `cd backend && python -m pytest tests/test_block_registry.py -v` — all pass, 9 types registered
- `grep -q "chart.js" backend/app/templates/base.html` — Chart.js CDN present
- `test -f backend/app/templates/browser/blocks/block_stat_card.html` — stat-card template exists
- `test -f backend/app/templates/browser/blocks/block_chart.html` — chart template exists
- `test -f .gsd/milestones/M032/M032-DESIGN.md` — design doc exists
- `python3 -c "from app.dashboard.registry import BLOCK_REGISTRY; assert len(BLOCK_REGISTRY.all_types()) == 9"` (run from backend/)
- `python3 -c "from app.dashboard.registry import BLOCK_REGISTRY; BLOCK_REGISTRY.validate_block({'type':'stat-card','config':{'query':42}})"` (run from backend/) — must raise ValueError (diagnostic failure-path check)

## Observability / Diagnostics

- Runtime signals: `logger.warning()` on SPARQL query failure in `render_block()` with query text and error message
- Inspection surfaces: block HTML includes error class `dashboard-block-error` when SPARQL fails — visible in DOM
- Failure visibility: stat-card shows "Query Error" text, chart shows "Chart Error" text — user-visible in dashboard
- Redaction constraints: SPARQL query text logged at warning level (no user secrets in SPARQL)

## Integration Closure

- Upstream surfaces consumed: `BLOCK_REGISTRY` singleton from S01, `_execute_sparql()` from `sparql/router.py`, `get_triplestore_client` from `dependencies.py`, `dashboard_builder.html` config panel pattern from S01
- New wiring introduced: `TriplestoreClient` dependency injected into `render_block()`, Chart.js CDN in `base.html`, `blocks/` template directory
- What remains before the milestone is truly usable end-to-end: S03 (form-group block for multi-object transactions)

## Tasks

- [x] **T01: Register stat-card, chart, heading block types with builder config panels and tests** `est:30m`
  - Why: Establishes the 3 new block types in the registry, adds their config UIs to the builder, and updates unit tests to cover them — without this, no rendering or validation can happen.
  - Files: `backend/app/dashboard/registry.py`, `backend/app/templates/browser/dashboard_builder.html`, `backend/tests/test_block_registry.py`
  - Do: Add 3 `BLOCK_REGISTRY.register(BlockTypeSpec(...))` calls for stat-card (category=data, icon=hash, schema: query/label/icon/color as str, default 3×2), chart (category=data, icon=bar-chart-2, schema: query/chart_type/label_var/value_var as str, default 6×4), heading (category=layout, icon=type, schema: text/level as str, default 12×1). Add 3 cases to `getTypeConfigHTML()` in builder template: stat-card gets query textarea + label/icon/color inputs; chart gets query textarea + chart_type select (bar/line/pie/doughnut) + label_var/value_var inputs; heading gets text input + level select (h1-h4). Update test_block_registry.py: change EXPECTED_TYPES to 9, add parameterized test cases for new types, add validation test cases for new config schemas.
  - Verify: `cd backend && python -m pytest tests/test_block_registry.py -v` — all pass with 9 types
  - Done when: `BLOCK_REGISTRY.all_types()` returns 9 types including stat-card, chart, heading; builder template has config panels for all 3; all unit tests pass

- [x] **T02: Implement server-side block rendering with SPARQL execution, Chart.js, and CSS** `est:45m`
  - Why: Makes the 3 new block types actually render visible content — stat-card shows a live SPARQL metric, chart renders a Chart.js visualization from SPARQL results, heading shows styled text.
  - Files: `backend/app/dashboard/router.py`, `backend/app/templates/browser/blocks/block_stat_card.html`, `backend/app/templates/browser/blocks/block_chart.html`, `backend/app/templates/base.html`, `frontend/static/css/workspace.css`
  - Do: (1) Add Chart.js 4.x CDN script tag to both dev and prod blocks in `base.html`. (2) Create `blocks/` template directory. (3) Write `block_stat_card.html` — flex layout with optional Lucide icon, large `.stat-value` number, `.stat-label` text, optional color accent. (4) Write `block_chart.html` — `<canvas>` element with unique ID + inline `<script>` that creates `new Chart()` instance reading CSS custom properties for dark theme colors, using `responsive: true, maintainAspectRatio: false`. (5) Add `TriplestoreClient` as a Depends parameter on `render_block()`. (6) Add 3 `elif` branches: heading renders inline `<hN>` with HTML-escaped text (validate level h1-h4, default h2); stat-card executes SPARQL via imported `_execute_sparql`, extracts first binding's first value, renders via Jinja2 template; chart executes SPARQL, serializes labels[] and values[] as JSON into template context, renders via Jinja2 template. (7) Wrap all SPARQL execution in try/except — render error HTML on failure. (8) Add CSS for `.dashboard-block-stat-card` (flex, large font stat-value, muted label, `flex-shrink: 0` on SVG per CLAUDE.md), `.dashboard-block-chart` (height:100%, relative positioning, canvas fill), `.dashboard-block-heading` (typography sizing). Also add `.dashboard-page .dashboard-block-stat-card`, `.dashboard-page .dashboard-block-chart`, `.dashboard-page .dashboard-block-heading` variants matching the existing pattern.
  - Verify: `grep -q "chart.js" backend/app/templates/base.html && test -f backend/app/templates/browser/blocks/block_stat_card.html && test -f backend/app/templates/browser/blocks/block_chart.html && grep -q "stat-card" backend/app/dashboard/router.py && grep -q "dashboard-block-stat-card" frontend/static/css/workspace.css`
  - Done when: `render_block()` handles stat-card/chart/heading types; Chart.js CDN loads globally; Jinja2 templates render block HTML; CSS styles are in place; SPARQL errors produce user-friendly error blocks

- [x] **T03: Write M032 architecture design document** `est:20m`
  - Why: M032-DESIGN.md is a slice deliverable that documents the architecture decisions, block registry schema, widget inventory, and migration strategy from S01-S02 for future reference.
  - Files: `.gsd/milestones/M032/M032-DESIGN.md`
  - Do: Write the design document covering: (1) Architecture overview — GridStack + BlockRegistry + htmx server-rendering pipeline, (2) Block Registry schema — BlockTypeSpec fields, validation approach, auto-derived VALID_BLOCK_TYPES, (3) Widget inventory — all 9 block types with config schemas and rendering approach, (4) Layout migration strategy — 5 legacy layouts to GridStack positions, lazy migration on access, (5) Data flow — SPARQL execution in render_block for data widgets, Chart.js initialization post-htmx-swap, (6) Key decisions made during S01-S02 (event isolation, CDN loading, server-side vs client-side rendering). Reference concrete file paths throughout.
  - Verify: `test -f .gsd/milestones/M032/M032-DESIGN.md && grep -c "^## " .gsd/milestones/M032/M032-DESIGN.md` returns >= 4
  - Done when: M032-DESIGN.md exists with 4+ sections covering architecture, registry, widgets, and migration

## Files Likely Touched

- `backend/app/dashboard/registry.py`
- `backend/app/dashboard/router.py`
- `backend/app/templates/browser/dashboard_builder.html`
- `backend/app/templates/base.html`
- `backend/app/templates/browser/blocks/block_stat_card.html` (new)
- `backend/app/templates/browser/blocks/block_chart.html` (new)
- `frontend/static/css/workspace.css`
- `backend/tests/test_block_registry.py`
- `.gsd/milestones/M032/M032-DESIGN.md` (new)
