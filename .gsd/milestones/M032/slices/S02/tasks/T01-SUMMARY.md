---
id: T01
parent: S02
milestone: M032
provides:
  - 10 block types registered in BLOCK_REGISTRY (3 new: stat-card, chart, heading)
  - render_block HTML output with data-* attributes for stat-card, chart, heading
  - Fixed markdown render_block: script type="text/plain" + data-md-block
  - Fixed sparql-result render_block: data-sparql-query + data-sparql-table
  - Test coverage for all 5 block type render outputs
key_files:
  - backend/app/dashboard/registry.py
  - backend/app/dashboard/router.py
  - backend/tests/test_block_registry.py
  - backend/tests/test_data_widgets.py
key_decisions:
  - Heading level clamped to 1-4 (not 1-6) — h5/h6 are too small for dashboard headings
  - Markdown content placed in script type="text/plain" without HTML-escaping — browsers don't parse script tag content as HTML, so raw markdown is safe there
  - sparql-result uses both data-sparql-query (unified selector for frontend) and data-sparql-table (distinguishes table mode from scalar stat mode)
patterns_established:
  - All SPARQL query text in data attributes uses html.escape(query, quote=True)
  - Error blocks use consistent dashboard-block-error class with descriptive message
  - stat-card icon uses Lucide i[data-lucide] pattern consistent with codebase
observability_surfaces:
  - dashboard-block-error class in rendered HTML for missing config
  - data-sparql-query, data-chart-query, data-chart-type, data-sparql-table, data-stat-target, data-md-block attributes inspectable in DevTools
duration: 20m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T01: Register stat-card, chart, heading blocks and fix markdown/sparql-result render handlers

**Registered 3 new block types (stat-card, chart, heading) and fixed markdown/sparql-result render handlers to emit correct data-* attributes for frontend JS pickup**

## What Happened

Added stat-card (data category, 3×2, query+label+icon+color config), chart (data category, 6×4, query+chart_type+label config), and heading (content category, 12×2, text+level+subtitle+align config) to `_build_default_registry()` in registry.py.

Added three new `elif` branches in `render_block()` in router.py:
- **stat-card**: emits `data-sparql-query` with escaped query, `data-stat-target` on the value span, Lucide icon, optional color style
- **chart**: emits `data-chart-query` and `data-chart-type`, contains a `<canvas class="chart-canvas">`, optional label span
- **heading**: emits configurable `<h1>`–`<h4>` (level clamped to 1–4), optional subtitle, configurable text-align

Fixed two existing handlers:
- **markdown**: replaced `html.escape()` + paragraph-split with `<script type="text/plain" class="md-source">` inside a `data-md-block` wrapper, plus an `md-rendered` div for client-side rendering
- **sparql-result**: changed `data-query` to `data-sparql-query`, added `data-sparql-table` attribute, replaced inline `<span>` with a `sparql-table-container` div

Updated test_block_registry.py (EXPECTED_TYPES now has 10, added spec tests for all 3 new types). Created test_data_widgets.py with 28 tests covering all 5 block types' render output.

## Verification

- `test_block_registry.py`: 38/38 passed — 10 types registered, new types have correct specs
- `test_data_widgets.py`: 28/28 passed — render output assertions for stat-card, chart, heading, markdown, sparql-result
- `test_dashboard.py`: 27/27 passed — no regressions
- `test_dashboard_builder.py`: 6/9 passed — 3 pre-existing failures (layout radio button checks removed in prior GridStack migration, confirmed same failures on `main` before this task)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_block_registry.py -v` | 0 | ✅ pass | 4.2s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_data_widgets.py -v` | 0 | ✅ pass | 4.2s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_dashboard.py tests/test_dashboard_builder.py -v` | 1 | ⚠️ partial (3 pre-existing failures) | 4.2s |

## Diagnostics

- Rendered blocks can be inspected by hitting `GET /browser/dashboard/{id}/block/{index}` — the raw HTML shows all data-* attributes
- Missing config produces a `<div class="dashboard-block-error">` with descriptive text (e.g., "No query configured")
- Query escaping verified by test assertions checking for `&amp;` in rendered output
- Registry state inspectable via `python -c "from app.dashboard.registry import BLOCK_REGISTRY; print(BLOCK_REGISTRY.all_types())"` from backend dir

## Deviations

None — implementation matched the task plan exactly.

## Known Issues

- 3 pre-existing test failures in `test_dashboard_builder.py` (tests check for layout radio buttons that were removed during GridStack migration in S01). Not caused by this task — confirmed by running the same tests on the unmodified codebase.

## Files Created/Modified

- `backend/app/dashboard/registry.py` — added stat-card, chart, heading BlockTypeSpec registrations (7→10 types)
- `backend/app/dashboard/router.py` — added 3 new render_block branches, fixed markdown and sparql-result handlers
- `backend/tests/test_block_registry.py` — updated EXPECTED_TYPES to 10, added spec tests for new types
- `backend/tests/test_data_widgets.py` — new file, 28 tests for render_block output of 5 block types
- `.gsd/milestones/M032/slices/S02/tasks/T01-PLAN.md` — added Observability Impact section (pre-flight fix)
- `.gsd/milestones/M032/slices/S02/S02-PLAN.md` — added diagnostic verification step (pre-flight fix)
