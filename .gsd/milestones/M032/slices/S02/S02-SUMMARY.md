# S02 Summary: Data-Driven Widget Types (stat-card, chart, heading)

**Status:** Complete
**Duration:** ~34 minutes across 3 tasks
**Verification:** All 7 slice-level checks pass; 44 unit tests pass

## What This Slice Delivered

Three new block types — `stat-card`, `chart`, and `heading` — are registered in `BLOCK_REGISTRY` (now 9 types total), have builder config panels in the dashboard builder, render server-side via `render_block()`, and are styled in `workspace.css`. The M032 architecture design document is written.

### stat-card
- Executes a SPARQL query server-side, extracts the first variable's first binding value
- Renders via `block_stat_card.html`: flex layout with optional Lucide icon, large `.stat-value` number, `.stat-label` text, optional color accent
- Default grid size: 3×2 cells

### chart
- Executes a SPARQL query server-side, extracts label/value columns from result bindings
- Renders via `block_chart.html`: `<canvas>` + Chart.js IIFE that creates the chart immediately
- Supports bar/line/pie/doughnut via `chart_type` config
- Theme-aware: reads CSS custom properties for axis colors; uses a 10-color palette that works light+dark
- Canvas uses `responsive: true, maintainAspectRatio: false` for fill behavior
- Chart ID uses `{dashboard_id}-{block_index}` for uniqueness
- Default grid size: 6×4 cells

### heading
- Renders an `<hN>` element (h1–h4, default h2) with HTML-escaped text
- Inline rendering (no template file needed)
- Default grid size: 12×1 cells

### Error handling
- All SPARQL execution wrapped in try/except
- Failures render user-visible `.dashboard-block-error` HTML (stat-card: "Query Error", chart: "Chart Error")
- `logger.warning()` logs query text + error for debugging (no secrets in SPARQL)

### Design document
- `M032-DESIGN.md` has 8 sections covering architecture, registry API, all 9 widgets, layout migration, SPARQL data flow, Chart.js integration, and key decisions

## Key Files

| File | Change |
|------|--------|
| `backend/app/dashboard/registry.py` | 3 new `BlockTypeSpec` registrations; docstring updated to "9 built-in block types" |
| `backend/app/dashboard/router.py` | `TriplestoreClient` dependency on `render_block()`; 3 new `elif` branches for heading/stat-card/chart |
| `backend/app/templates/browser/dashboard_builder.html` | 3 new `case` branches in `getTypeConfigHTML()` with config inputs |
| `backend/app/templates/base.html` | Chart.js 4.x CDN in both dev and prod asset blocks |
| `backend/app/templates/browser/blocks/block_stat_card.html` | New — Jinja2 template for stat-card widget |
| `backend/app/templates/browser/blocks/block_chart.html` | New — Jinja2 template with Chart.js IIFE |
| `frontend/static/css/workspace.css` | CSS for `.dashboard-block-stat-card`, `.dashboard-block-chart`, `.dashboard-block-heading` + `.dashboard-page` variants |
| `backend/tests/test_block_registry.py` | EXPECTED_TYPES → 9; `TestS02BlockTypes` class with 11 new tests |
| `.gsd/milestones/M032/M032-DESIGN.md` | New — 8-section architecture document |

## Patterns Established

1. **SPARQL execution in non-API routes:** `_execute_sparql` imported from `sparql.router` and called in `render_block()` — same pattern as `sparql_result.py`
2. **Block-level Jinja2 templates:** `templates.env.get_template()` for rendering block HTML fragments (not full page responses) in `blocks/` directory
3. **Chart.js IIFE init:** Chart blocks include an inline IIFE that runs immediately when the HTML is swapped in by htmx — no event listener or mutation observer needed
4. **Data-category config panels:** SPARQL query textarea with placeholder text + typed inputs for binding variable names
5. **Error blocks:** `.dashboard-block-error` class + user-facing text for any SPARQL failure — inspectable in DOM

## What the Next Slice (S03) Should Know

- `render_block()` now has a `TriplestoreClient` dependency parameter — S03 form-group rendering can use it directly
- The `blocks/` template directory exists at `backend/app/templates/browser/blocks/` — add `block_form_group.html` there
- Builder config panels follow the `case 'type-name':` pattern in `getTypeConfigHTML()` — add a new case for form-group
- BLOCK_REGISTRY.register() with BlockTypeSpec is the pattern — S03 adds type #10
- Chart.js CDN is in both dev and prod blocks of `base.html` — no additional CDN setup needed for S03
- The test file expects `EXPECTED_TYPES` count to match — S03 must bump this to 10

## Verification Results

| Check | Result |
|-------|--------|
| `pytest tests/test_block_registry.py -v` — 44 tests | ✅ PASS |
| `grep -q "chart.js" base.html` | ✅ PASS |
| `test -f blocks/block_stat_card.html` | ✅ PASS |
| `test -f blocks/block_chart.html` | ✅ PASS |
| `test -f M032-DESIGN.md` (8 sections) | ✅ PASS |
| `BLOCK_REGISTRY.all_types()` returns 9 | ✅ PASS |
| `validate_block({'type':'stat-card','config':{'query':42}})` raises ValueError | ✅ PASS |
