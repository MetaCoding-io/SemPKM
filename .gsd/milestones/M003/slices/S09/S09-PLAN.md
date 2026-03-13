# S09: Admin Model Detail Stats & Charts

**Goal:** Replace all TODO placeholders on the admin model detail analytics back-face with real computed stats and visual charts.
**Demo:** Flip any type card to Analytics — see real avg connections, last modified date, growth sparkline, and link distribution bar chart rendered with Chart.js. Types with zero instances show "No data" gracefully.

## Must-Haves

- Avg connections per node computed via SPARQL (count non-rdf:type triples where subject or object is a type instance, divide by instance count)
- Last modified date per type (MAX dcterms:modified, fallback to most recent event timestamp)
- Growth trend sparkline per type (object.create events per week, last 8 weeks) rendered via Chart.js
- Link distribution horizontal bar chart per type (histogram buckets: 0, 1-2, 3-5, 6-10, 11+) rendered via Chart.js
- Chart.js loaded per-page only (via `{% block scripts %}`) — not globally in base.html
- Charts initialized lazily after flip card transitionend reveals the analytics face
- Empty data states handled gracefully (types with 0 instances show "No data" instead of broken charts)
- TODO placeholder CSS classes and HTML removed from template
- All new stats flow through existing `get_type_analytics()` → router → template pipeline (no new endpoints)

## Proof Level

- This slice proves: integration
- Real runtime required: yes (SPARQL queries against triplestore, Chart.js rendering in browser)
- Human/UAT required: no (automated tests cover SPARQL query correctness and chart rendering)

## Verification

- `cd backend && python -m pytest tests/test_model_analytics.py -v` — unit tests for new SPARQL query builders (avg connections, last modified, growth trend, link distribution) with mock triplestore responses
- Docker Compose up → navigate to `/admin/models/basic-pkm` → flip a type card → verify real stats and charts render (visual integration check via browser tools)
- `browser_assert` checks: no `.analytics-todo`, no `.analytics-placeholder`, no `.todo-val` selectors visible on page; canvas elements present inside `.analytics-right`

## Observability / Diagnostics

- Runtime signals: `get_type_analytics()` logs SPARQL query failures per-type at WARNING level with the type IRI; silently returns defaults (0, "—", empty lists) so the page still renders
- Inspection surfaces: Browser DevTools console shows Chart.js initialization; template renders `data-type-iri` attributes on chart containers for easy DOM inspection
- Failure visibility: Each stat field has a fallback display ("—" for dates, "0" for numbers, "No data" for chart areas) so partial SPARQL failures degrade gracefully rather than breaking the page
- Redaction constraints: none (no secrets or PII in analytics data)

## Integration Closure

- Upstream surfaces consumed: `ModelService.get_type_analytics()` (existing), `admin_model_detail()` router handler (existing), `model_detail.html` template (existing), event named graph SPARQL patterns from `events/query.py` (reference)
- New wiring introduced in this slice: Extended `get_type_analytics()` return dict with 4 new keys (`avg_connections`, `last_modified`, `growth_trend`, `link_distribution`); router passes these through existing `type_map` merge; Chart.js CDN loaded in template `{% block scripts %}`; chart init hooked to `flipCard()` transitionend
- What remains before the milestone is truly usable end-to-end: S10 (E2E test coverage gaps) — independent of this slice

## Tasks

- [x] **T01: Extend ModelService with SPARQL analytics queries** `est:1h`
  - Why: The backend currently returns only instance counts and top nodes. All four new stats (avg connections, last modified, growth trend, link distribution) need SPARQL queries added to `get_type_analytics()`.
  - Files: `backend/app/services/models.py`, `backend/tests/test_model_analytics.py`
  - Do: Add four new SPARQL query sections in `get_type_analytics()`: (1) avg connections — count non-rdf:type triples touching type instances, divide by count; (2) last modified — MAX dcterms:modified with event timestamp fallback; (3) growth trend — count object.create events per week for 8 weeks; (4) link distribution — histogram buckets (0, 1-2, 3-5, 6-10, 11+). Create unit tests that mock `_client.query()` to verify query result parsing logic for each stat. Each stat defaults gracefully on query failure.
  - Verify: `cd backend && python -m pytest tests/test_model_analytics.py -v` — all tests pass
  - Done when: `get_type_analytics()` returns dicts with keys `count`, `top_nodes`, `avg_connections`, `last_modified`, `growth_trend`, `link_distribution` — and all unit tests pass

- [x] **T02: Replace template placeholders with real stats and Chart.js charts** `est:1h`
  - Why: The template currently shows TODO dashes and placeholder bars. This task replaces them with real data bindings and Chart.js canvas elements, and adds lazy chart initialization tied to the flip card animation.
  - Files: `backend/app/templates/admin/model_detail.html`, `frontend/static/css/style.css`
  - Do: (1) Replace the two `analytics-todo` stat rows with real `{{ td.avg_connections }}` and `{{ td.last_modified }}` bindings. (2) Replace the `analytics-placeholder` div with two `<canvas>` elements: growth sparkline and link distribution bar chart. (3) Add `{% block scripts %}` with Chart.js 4.x CDN. (4) Write chart initialization JS that reads JSON data from `data-*` attributes or inline `|tojson` and creates Chart.js instances. (5) Hook chart init to `flipCard()` transitionend callback — only initialize when the analytics face becomes visible. (6) Handle empty states: if instance_count == 0, show "No data" text instead of canvas. (7) Remove `.analytics-todo`, `.todo-val`, `.analytics-placeholder`, `.placeholder-bar`, `.placeholder-label` CSS classes. (8) Add CSS for canvas containers and empty states.
  - Verify: Docker Compose up → browser navigate to `/admin/models/basic-pkm` → flip a type card → verify no TODO placeholders, real numbers in avg connections / last modified, Chart.js canvases render. `browser_assert` checks: no `.analytics-todo` or `.analytics-placeholder` selectors on page.
  - Done when: All TODO placeholder HTML and CSS are replaced with real data and Chart.js charts. Flipping any type card shows computed stats and rendered charts (or "No data" for empty types).

## Files Likely Touched

- `backend/app/services/models.py` — extended `get_type_analytics()` with 4 new SPARQL queries
- `backend/tests/test_model_analytics.py` — new unit tests for analytics query result parsing
- `backend/app/templates/admin/model_detail.html` — replaced TODO placeholders, added Chart.js init
- `frontend/static/css/style.css` — removed placeholder CSS, added chart container styles
