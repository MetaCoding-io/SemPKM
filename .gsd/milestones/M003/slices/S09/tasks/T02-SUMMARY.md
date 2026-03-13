---
id: T02
parent: S09
milestone: M003
provides:
  - Real avg_connections and last_modified stats rendered on analytics card face
  - Chart.js growth sparkline (line) and link distribution (horizontal bar) charts
  - Lazy chart initialization on flip transitionend (avoids 0×0 canvas pitfall)
  - Chart.js CDN loaded only on model_detail page via {% block scripts %}
  - Chart.getChart() cleanup for htmx re-render safety
key_files:
  - backend/app/admin/router.py
  - backend/app/templates/admin/model_detail.html
  - frontend/static/css/style.css
key_decisions:
  - Chart.js 4.4.x via jsdelivr CDN — no npm dependency needed for a single admin page
  - Sparkline uses pointRadius:0, no axis labels, area fill for compact visual
  - Bar chart uses indexAxis:'y' (horizontal) to match bucket label readability
  - Last modified displayed as date-only substring ([:10]) since ISO timestamps are too long for stat rows
patterns_established:
  - Lazy chart init pattern: initTypeCharts(localName) called from flipCard() transitionend handler
  - Chart.getChart(canvas).destroy() before re-init for htmx-safe chart lifecycle
  - data-growth and data-links canvas attributes hold JSON for chart data (inspectable via DOM)
observability_surfaces:
  - browser_evaluate("document.querySelectorAll('canvas').length") — count chart canvases
  - browser_evaluate("Chart.getChart(document.getElementById('chart-growth-Concept'))") — check chart instance
  - data-growth and data-links attributes on canvas elements contain raw JSON from backend
  - Chart.js initialization errors appear in browser console
duration: 25 minutes
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T02: Replace template placeholders with real stats and Chart.js charts

**Replaced all TODO placeholder HTML/CSS with real Jinja2 data bindings for avg connections and last modified, plus Chart.js sparkline and bar charts for growth trend and link distribution, with lazy initialization on card flip.**

## What Happened

1. **Router wiring** — Added 4 new lines in `admin/router.py` to pass `avg_connections`, `last_modified`, `growth_trend`, and `link_distribution` from `get_type_analytics()` through the existing `type_map` merge pattern.

2. **Template stats** — Replaced the two `.analytics-todo` divs with real Jinja2 bindings: `avg_connections` formatted as "X.Y" (or "—" for 0-instance types), `last_modified` as date substring (or "—" for None).

3. **Chart canvases** — Replaced the `.analytics-placeholder` div with two Chart.js canvas elements wrapped in container divs with headings. Growth sparkline uses `data-growth` attribute with JSON from `|tojson`. Link distribution uses `data-links`. Conditional: types with 0 instances show "No data yet" instead of canvases.

4. **Chart.js CDN + init script** — Added `{% block scripts %}` with Chart.js 4.4.x from jsdelivr CDN. Wrote `initTypeCharts(localName)` function that reads JSON from canvas data attributes, creates a line chart (sparkline: no axes, area fill, smooth tension) for growth and a horizontal bar chart for link distribution. Includes `Chart.getChart()` destroy-before-create for htmx re-render safety.

5. **Lazy init on flip** — Modified the `flipCard()` function's front→back transitionend handler to call `initTypeCharts(localName)` after the face is visible, avoiding the 0×0 canvas sizing pitfall.

6. **CSS cleanup** — Removed `.analytics-todo`, `.todo-val`, `.analytics-placeholder`, `.placeholder-bar`, `.placeholder-label` rule blocks. Added `.chart-section`, `.chart-heading`, `.chart-container`, `.chart-container-sparkline` (48px), `.chart-container-bar` (110px), and `.analytics-right canvas` max-height.

## Verification

- `cd backend && uv run python -m pytest tests/test_model_analytics.py -v` — 32/32 passed
- Docker Compose up → navigated to `/admin/models/basic-pkm` → flipped Concept card to analytics
  - **Avg. connections: 9.0** — real computed value displayed ✓
  - **Last modified: —** — correctly shows dash for types without dcterms:modified ✓
  - **Growth sparkline** rendered as Chart.js line chart ✓
  - **Link distribution** rendered as horizontal bar chart showing 3 instances in 6-10 bucket ✓
- Flipped Note card → **Avg. connections: 8.7**, charts rendered on transitionend ✓
- `browser_evaluate` confirmed:
  - 0 `.analytics-todo`, 0 `.analytics-placeholder`, 0 `.todo-val` elements
  - 8 canvas elements total (2 per type × 4 types)
  - Chart.getChart() returns true for flipped cards, false for unflipped (lazy init working)
- `browser_get_console_logs` — no Chart.js errors
- Slice-level `browser_assert` checks all pass: no placeholder selectors, canvas elements present in `.analytics-right`

## Diagnostics

- `browser_evaluate("document.querySelectorAll('canvas').length")` — should return 8 (2 per type × 4 types) or 0 if type has 0 instances and shows "No data yet"
- `browser_evaluate("Chart.getChart(document.getElementById('chart-growth-Concept'))")` — returns chart instance if card was flipped, null otherwise
- Inspect `data-growth` / `data-links` attributes on canvas elements for raw JSON data from backend
- Chart.js errors surface in browser console (standard Chart.js error messages)

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/admin/router.py` — Added 4 lines wiring avg_connections, last_modified, growth_trend, link_distribution into type_map dicts
- `backend/app/templates/admin/model_detail.html` — Replaced TODO placeholders with real Jinja2 bindings + Chart.js canvases + initTypeCharts() script + CDN link in {% block scripts %}
- `frontend/static/css/style.css` — Removed 5 placeholder CSS rules, added chart container/heading styles
