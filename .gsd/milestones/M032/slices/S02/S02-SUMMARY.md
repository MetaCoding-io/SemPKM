---
id: S02
parent: M032
milestone: M032
provides:
  - 10 block types in BLOCK_REGISTRY (3 new: stat-card, chart, heading)
  - render_block HTML with data-* attributes for all new and fixed block types
  - _executeSparqlWidgets() for live SPARQL stat-card and sparql-result rendering
  - _initChartBlocks() with lazy Chart.js CDN loading for chart visualization
  - _renderMarkdownBlocks() with marked.js + DOMPurify for full markdown rendering
  - Builder config forms for stat-card, chart, heading block types
requires:
  - slice: S01
    provides: form-group block type (7 types baseline)
affects:
  - S03
key_files:
  - backend/app/dashboard/registry.py
  - backend/app/dashboard/router.py
  - frontend/static/js/workspace.js
  - frontend/static/css/workspace.css
  - backend/app/templates/browser/dashboard_builder.html
  - backend/tests/test_block_registry.py
  - backend/tests/test_data_widgets.py
key_decisions:
  - Chart.js loaded from jsdelivr CDN (chart.js@4.4 UMD build) with lazy singleton pattern
  - Heading level clamped to 1-4 (h5/h6 too small for dashboard headings)
  - Markdown placed in script type="text/plain" (browsers don't parse script content as HTML)
  - sparql-result uses both data-sparql-query (unified selector) and data-sparql-table (distinguishes table from scalar mode)
  - Stat-card scalar extraction uses first binding's first variable (simple and generic)
patterns_established:
  - data-*-loaded attributes for idempotent widget activation (prevents re-execution on htmx re-settle)
  - "[SemPKM]" console.warn prefix with query excerpt (first 120 chars) for debugging
  - Chart.js callback queue pattern (_chartJsCallbacks) for concurrent chart blocks
  - Error blocks use consistent dashboard-block-error / dashboard-block-error-inline classes
  - All SPARQL query text in data attributes uses html.escape(query, quote=True)
observability_surfaces:
  - "console.warn('[SemPKM] SPARQL widget error: ...') with query excerpt"
  - "console.warn('[SemPKM] Chart block error: ...') for query/render failures"
  - "console.warn('[SemPKM] Chart.js failed to load') for CDN issues"
  - "data-sparql-loaded, data-chart-loaded, data-md-rendered attributes on processed blocks"
  - "_chartJsLoaded / _chartJsLoading globals track CDN load state"
  - ".dashboard-block-error-inline elements in DOM on fetch/render failures"
drill_down_paths:
  - .gsd/milestones/M032/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M032/slices/S02/tasks/T02-SUMMARY.md
duration: 40min
verification_result: passed
completed_at: 2026-03-22
---

# S02: Data-Driven Widgets (stat-card, chart, heading) + Block Fixes

**Registered 3 new block types (stat-card, chart, heading), fixed markdown/sparql-result rendering, added frontend JS for live SPARQL widget execution and Chart.js visualization, plus builder config forms for all new types.**

## What Happened

T01 registered stat-card (3×2, query+label+icon+color), chart (6×4, query+chart_type+label), and heading (12×2, text+level+subtitle+align) in the block registry, bringing the total to 10 types. Added render_block branches emitting HTML with data-* attributes for frontend JS pickup. Fixed the markdown handler (replaced html.escape paragraph-split with `<script type="text/plain">` + `data-md-block` for client-side marked.js rendering) and the sparql-result handler (changed data-query to data-sparql-query, added data-sparql-table). Created test_data_widgets.py with 28 tests covering all 5 block types' render output.

T02 added three JS functions hooked into htmx:afterSettle: `_executeSparqlWidgets()` (POSTs SPARQL queries, populates stat-card values and sparql-result tables), `_initChartBlocks()` (lazy-loads Chart.js from CDN, creates Chart instances from SPARQL data with bar/line/pie support), and `_renderMarkdownBlocks()` (renders via marked.parse + DOMPurify.sanitize with raw-text fallback). Added CSS for stat-card (accent-colored value, icon, label), chart (responsive canvas), heading (configurable h1-h4 with subtitle), and error states. Added builder config forms for all three new types.

## Verification

- `test_block_registry.py`: 38/38 passed (10 types registered)
- `test_data_widgets.py`: 28/28 passed (all render output assertions)
- `test_dashboard.py`: 27/27 passed (no regressions)
- `test_dashboard_builder.py`: 6/9 passed (3 pre-existing failures)
- Error-path tests: 3/3 passed (missing query → error div)
- Frontend hooks: grep confirms ≥3 function definitions, ≥3 builder cases, ≥3 CSS class definitions

## Requirements Advanced

- DASH-01 — Dashboard block types expanded from 7 to 10 (stat-card, chart, heading add data visualization and layout structure)

## Requirements Validated

None in this slice alone — validated as part of full M032 milestone with E2E tests in S03.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

- Chart label is read from `.chart-label` span textContent rather than a separate JS variable — simpler since backend already renders the label.
- Added root-element self-match checks in all three widget functions — handles the edge case where the htmx-settled element itself is a widget block.

## Known Limitations

- Chart.js CDN dependency means charts won't render offline.
- marked.js and DOMPurify must be loaded separately — markdown blocks fall back to raw text without them.
- 3 pre-existing test failures in test_dashboard_builder.py from prior GridStack migration.

## Follow-ups

None.

## Files Created/Modified

- `backend/app/dashboard/registry.py` — Added stat-card, chart, heading BlockTypeSpec (7→10 types)
- `backend/app/dashboard/router.py` — Added 3 new + fixed 2 existing render_block branches
- `backend/tests/test_block_registry.py` — Updated to expect 10 types
- `backend/tests/test_data_widgets.py` — New: 28 tests for block render output
- `frontend/static/js/workspace.js` — Added _executeSparqlWidgets, _initChartBlocks, _renderMarkdownBlocks, _ensureChartJs
- `frontend/static/css/workspace.css` — Added stat-card, chart, heading, sparql-result table, error styles
- `backend/app/templates/browser/dashboard_builder.html` — Added stat-card, chart, heading builder config cases

## Forward Intelligence

### What the next slice should know
- data-sparql-loaded and data-chart-loaded are dedup guards set BEFORE the async fetch, not readiness signals. E2E tests must wait for actual content changes (stat value ≠ "…", canvas drawn) not just attribute presence.
- Chart.js uses `Chart.getChart(canvas)` for instance detection (v4.x API), not a `__chartjs_instance__` property.

### What's fragile
- Stat-card scalar extraction takes the first binding's first variable — if the query returns multiple columns, only the first is shown. No column name matching.
- Chart SPARQL query must return `?label` and `?value` columns exactly — the JS iterates bindings looking for these names.

### Authoritative diagnostics
- Browser console filter `[SemPKM]` shows all widget errors with query excerpts
- DevTools `data-sparql-loaded="1"` / `data-chart-loaded="1"` confirms the widget function ran (but not that the async work completed)
- `window._chartJsLoaded` in console confirms CDN load state

### What assumptions changed
- data-*-loaded attributes are idempotency guards, not completion signals — this is the critical insight for E2E test design.
