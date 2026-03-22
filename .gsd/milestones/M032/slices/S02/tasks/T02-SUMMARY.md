---
id: T02
parent: S02
milestone: M032
provides:
  - Server-side rendering for stat-card, chart, heading block types in render_block()
  - Chart.js CDN globally loaded in base.html (dev and prod)
  - Jinja2 templates for stat-card and chart blocks with theme-aware rendering
  - CSS styles for all 3 new widget types with CLAUDE.md-compliant flex/SVG handling
key_files:
  - backend/app/dashboard/router.py
  - backend/app/templates/browser/blocks/block_stat_card.html
  - backend/app/templates/browser/blocks/block_chart.html
  - backend/app/templates/base.html
  - frontend/static/css/workspace.css
key_decisions:
  - SPARQL result extraction uses first variable from head.vars for stat-card, first two for chart (label_var, value_var)
  - Chart.js palette uses 10 fixed colors that work in both light and dark themes
  - Chart blocks use chart_id = "{dashboard_id}-{block_index}" for canvas uniqueness
  - Heading block validates level to h1-h4 with h2 default, HTML-escapes text
patterns_established:
  - _execute_sparql imported from sparql.router for SPARQL execution in non-API routes (same pattern as sparql_result.py)
  - SPARQL errors in block rendering produce user-visible .dashboard-block-error HTML with logger.warning() including query text
  - Jinja2 template rendering via templates.env.get_template() for block-level HTML (not full page responses)
observability_surfaces:
  - logger.warning() on SPARQL query failure in stat-card/chart branches with dashboard_id, block_index, error, and query text
  - .dashboard-block-error CSS class on error blocks — inspectable in DOM
  - stat-card shows "Query Error", chart shows "Chart Error" text in failure state
duration: 14m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T02: Implement server-side block rendering with SPARQL execution, Chart.js, and CSS

**Added server-side rendering for stat-card (SPARQL metric), chart (Chart.js visualization), and heading (styled text) block types with TriplestoreClient dependency, error handling, and widget CSS**

## What Happened

Added `html` import, `get_triplestore_client`, `TriplestoreClient`, and `_execute_sparql` imports to `router.py`. Added `client: TriplestoreClient = Depends(get_triplestore_client)` parameter to `render_block()`.

Added three `elif` branches to `render_block()`:
- **heading**: Validates level is h1-h4 (default h2), HTML-escapes text via `html.escape()`, returns inline `<hN>` element with `.dashboard-block-heading` class.
- **stat-card**: Executes SPARQL query via `_execute_sparql(query, client)`, extracts first binding's first variable value, renders via `block_stat_card.html` Jinja2 template with value/label/icon/color context. On SPARQL error, logs warning and returns `.dashboard-block-error` HTML.
- **chart**: Executes SPARQL query, extracts label/value columns from bindings (defaults to first two SPARQL variables), serializes as JSON, renders via `block_chart.html` Jinja2 template. Chart.js init script uses responsive:true, maintainAspectRatio:false, a 10-color palette, and reads CSS custom properties for theme-aware axis colors. Pie/doughnut charts skip axis scales.

Added Chart.js 4.x CDN script tag in both dev and prod blocks of `base.html` (after GridStack lines).

Created `blocks/` template directory with `block_stat_card.html` (flex layout with optional Lucide icon, large value, label, optional color accent) and `block_chart.html` (canvas + inline Chart.js IIFE with theme detection).

Added CSS styles for `.dashboard-block-stat-card` (flex, gap, large stat-value font, `flex-shrink: 0` on SVG icons per CLAUDE.md), `.dashboard-block-chart` (height:100%, relative positioning, canvas fill with !important), and `.dashboard-block-heading` (padding, margin:0, font-weight). Added `.dashboard-page` scoped variants for viewer rendering.

## Verification

- All 8 task-level verification checks pass (grep/test commands)
- 44 unit tests pass in test_block_registry.py (unchanged, validates registry consistency)
- 9 block types confirmed registered
- validate_block failure path confirmed raising ValueError for non-string config
- Module import test confirms router.py imports cleanly with all new dependencies
- Chart.js CDN present in both dev and prod blocks (count=2)
- flex-shrink: 0 on .stat-icon svg confirmed
- responsive:true, maintainAspectRatio:false in chart template confirmed

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -q "chart.js" backend/app/templates/base.html` | 0 | ✅ pass | <1s |
| 2 | `test -f backend/app/templates/browser/blocks/block_stat_card.html` | 0 | ✅ pass | <1s |
| 3 | `test -f backend/app/templates/browser/blocks/block_chart.html` | 0 | ✅ pass | <1s |
| 4 | `grep -q "stat-card" backend/app/dashboard/router.py` | 0 | ✅ pass | <1s |
| 5 | `grep -q "get_triplestore_client" backend/app/dashboard/router.py` | 0 | ✅ pass | <1s |
| 6 | `grep -q "dashboard-block-stat-card" frontend/static/css/workspace.css` | 0 | ✅ pass | <1s |
| 7 | `grep -q "dashboard-block-chart" frontend/static/css/workspace.css` | 0 | ✅ pass | <1s |
| 8 | `grep -q "dashboard-block-heading" frontend/static/css/workspace.css` | 0 | ✅ pass | <1s |
| 9 | `cd backend && uv run --extra dev python -m pytest tests/test_block_registry.py -v` | 0 | ✅ pass | 0.04s |
| 10 | `python3 -c "...assert len(BLOCK_REGISTRY.all_types()) == 9"` | 0 | ✅ pass | <1s |
| 11 | `python3 -c "...validate_block({'type':'stat-card','config':{'query':42}})"` — ValueError | 0 | ✅ pass | <1s |
| 12 | `test -f .gsd/milestones/M032/M032-DESIGN.md` | 1 | ❌ fail (T03) | <1s |

Slice check 12 (design doc) is expected to fail — it belongs to T03.

## Diagnostics

- Check rendered block HTML for `.dashboard-block-error` class when SPARQL fails
- Check backend logs for `SPARQL query failed for stat-card` or `SPARQL query failed for chart` with dashboard_id and query text
- Verify Chart.js loaded: browser console `typeof Chart !== 'undefined'`
- Verify stat-card template: `ls backend/app/templates/browser/blocks/`
- Import test: `cd backend && uv run python3 -c "from app.dashboard.router import render_block; print('OK')"`

## Deviations

- Chart template JS uses an IIFE with proper JS variable for chart_type comparison instead of Jinja2 template expressions in JS conditionals (plan's inline approach would produce invalid JS for pie/doughnut conditional).
- Chart values are coerced to float with try/except fallback to 0 (not in plan but necessary for Chart.js numeric data requirement).

## Known Issues

None.

## Files Created/Modified

- `backend/app/dashboard/router.py` — Added html/TriplestoreClient/_execute_sparql imports, client dependency on render_block(), and 3 new elif branches for heading/stat-card/chart types
- `backend/app/templates/browser/blocks/block_stat_card.html` — New Jinja2 template: flex layout with optional Lucide icon, large stat value, label, optional color accent
- `backend/app/templates/browser/blocks/block_chart.html` — New Jinja2 template: canvas element + Chart.js IIFE with theme-aware colors and responsive sizing
- `backend/app/templates/base.html` — Added Chart.js 4.x CDN script tag in both dev and prod vendor blocks
- `frontend/static/css/workspace.css` — Added CSS for .dashboard-block-stat-card (flex, icon sizing), .dashboard-block-chart (responsive canvas), .dashboard-block-heading (typography), and .dashboard-page scoped variants
