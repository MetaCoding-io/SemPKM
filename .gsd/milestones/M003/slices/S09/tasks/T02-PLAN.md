---
estimated_steps: 5
estimated_files: 4
---

# T02: Replace template placeholders with real stats and Chart.js charts

**Slice:** S09 — Admin Model Detail Stats & Charts
**Milestone:** M003

## Description

Replace all TODO placeholder HTML and CSS in `model_detail.html` with real data bindings for avg connections and last modified, and Chart.js canvas elements for growth sparkline and link distribution bar chart. Add Chart.js via CDN in `{% block scripts %}`. Hook chart initialization to the flip card transitionend so charts render correctly when the analytics face becomes visible. Remove obsolete placeholder CSS.

## Steps

1. In `model_detail.html`, replace the two `analytics-todo` `<div>` rows (lines ~204-211) with real Jinja2 bindings: `{{ td.avg_connections }}` for avg connections (format as "X.Y" or "—" if 0), and `{{ td.last_modified }}` for last modified (format as human-readable date or "—" if None). Wire these through the existing `type_map` merge in `admin/router.py` — add `td["avg_connections"] = a["avg_connections"]` etc. alongside the existing `td["instance_count"]`, `td["top_nodes"]` assignments.
2. Replace the `analytics-placeholder` `<div>` (lines ~234-239) with two Chart.js canvas elements: (a) `<canvas id="chart-growth-{{ td.local_name }}" data-growth='{{ td.growth_trend | tojson }}'>` for sparkline and (b) `<canvas id="chart-links-{{ td.local_name }}" data-links='{{ td.link_distribution | tojson }}'>` for bar chart. Wrap each in a container div with heading. Add conditional: if `td.instance_count == 0`, show `<p class="analytics-empty">No data yet</p>` instead of canvases.
3. Add `{% block scripts %}` at the bottom of model_detail.html (before `{% endblock %}`) with Chart.js 4.4.x CDN (`<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4/dist/chart.umd.min.js"></script>`). Write a `initTypeCharts(localName)` JS function that: reads JSON from the canvas data attributes, creates a Chart.js line chart (sparkline, no axes labels, just the trend line with area fill) for growth and a horizontal bar chart for link distribution. Include Chart.getChart() cleanup to handle htmx re-renders.
4. Modify the existing `flipCard()` function's `transitionend` handler for the front→back path: after `front.classList.add('face-hidden')`, call `initTypeCharts(localName)`. This ensures charts initialize only when the canvas is visible (avoiding the 0×0 sizing pitfall). Also call it for cards that start flipped (edge case — not currently possible but defensive).
5. In `frontend/static/css/style.css`: remove the `.analytics-todo`, `.todo-val`, `.analytics-placeholder`, `.placeholder-bar`, `.placeholder-label` rule blocks (~lines 1401-1494). Add new styles for `.chart-container` (height constraint for canvas), `.chart-heading` (small label above chart), and ensure `.analytics-right canvas` has a reasonable max-height.

## Must-Haves

- [ ] No `.analytics-todo`, `.todo-val`, `.analytics-placeholder`, `.placeholder-bar`, `.placeholder-label` HTML or CSS remains
- [ ] Avg connections shows real computed number (or "—" for 0 instances)
- [ ] Last modified shows formatted date (or "—" for None)
- [ ] Growth sparkline renders as Chart.js line chart when card is flipped to analytics
- [ ] Link distribution renders as Chart.js horizontal bar chart when card is flipped
- [ ] Empty types (0 instances) show "No data yet" instead of broken charts
- [ ] Chart.js loaded only on model_detail page via `{% block scripts %}`
- [ ] Charts initialize lazily on flip transitionend, not on page load
- [ ] Router passes new analytics fields through existing type_map merge pattern

## Verification

- Docker Compose up → navigate to `/admin/models/basic-pkm` → flip a type card to analytics
- `browser_assert` checks: no `.analytics-todo` selector visible, no `.analytics-placeholder` selector visible
- `browser_assert` checks: canvas elements present inside flipped card's `.analytics-right`
- Visual confirmation: sparkline shows data trend, bar chart shows distribution buckets
- Page loads without console JS errors related to Chart.js

## Observability Impact

- Signals added/changed: Chart.js initialization failures would appear as browser console errors (standard Chart.js error messages). No backend changes.
- How a future agent inspects this: `browser_evaluate("document.querySelectorAll('canvas').length")` to check chart canvases exist; `browser_get_console_logs()` to verify no Chart.js errors; inspect `data-growth` and `data-links` attributes on canvas elements for the raw JSON data being passed to charts.
- Failure state exposed: If SPARQL returned defaults, the template shows "—" and "No data yet" — visually distinguishable from real data. Canvas with 0-width/height indicates the lazy-init hook failed.

## Inputs

- `backend/app/services/models.py` — T01's extended `get_type_analytics()` returning all 6 keys per type
- `backend/app/admin/router.py` — existing `admin_model_detail()` type_map merge pattern (lines ~128-131)
- `backend/app/templates/admin/model_detail.html` — existing template with TODO placeholders
- `frontend/static/css/style.css` — existing placeholder CSS to remove (~lines 1401-1494)
- S09-RESEARCH.md — Chart.js CDN strategy, lazy init pitfall, data serialization pattern

## Expected Output

- `backend/app/admin/router.py` — 4 new lines wiring analytics fields into type_map dicts
- `backend/app/templates/admin/model_detail.html` — TODO HTML replaced with real bindings + Chart.js canvases + init script + CDN link
- `frontend/static/css/style.css` — placeholder CSS removed, chart container CSS added
