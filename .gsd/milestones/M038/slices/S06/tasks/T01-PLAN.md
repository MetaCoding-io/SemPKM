---
estimated_steps: 6
estimated_files: 6
skills_used: []
---

# T01: Stats service, route, chart template, and status polish

**Slice:** S06 — Stats Dashboard + Polish
**Milestone:** M038

## Description

Create the stats backend service with three SPARQL aggregate queries, wire a new route in app.py, build a Chart.js dashboard template, add the Stats tab to the main layout, polish status badge CSS, and add unit tests. This is the functional core of S06.

## Steps

1. **Create `apps/media-scheduler/services/stats_service.py`** with three functions:
   - `get_hours_by_source_type(ctx)` — SPARQL aggregating `ms:duration` from completed PlanEntry objects, joined through MediaItem → MediaSource → `ms:sourceType`. GROUP BY sourceType, SUM durations. Convert seconds to hours. Return list of `{"source_type": str, "hours": float}`.
   - `get_top_sources(ctx, limit=10)` — COUNT completed PlanEntry objects joined to MediaItem → MediaSource → `dcterms:title`. GROUP BY source title, ORDER BY DESC count. Return list of `{"source_title": str, "count": int}`.
   - `get_weekly_trends(ctx, days=7)` — COUNT completed PlanEntry objects per day for the last N days. Use the PlanEntry's parent DailyMediaPlan which has a `dcterms:date` property. GROUP BY date, ORDER chronologically. Return list of `{"date": str, "count": int}`.
   - All queries must FILTER `?entryStatus = "completed"` (only completed entries count for stats). Use `MS_NS = "urn:sempkm:model:media-scheduler:"` consistent with plan_service.py.
   - Each function takes `ctx: AppContext` and uses `ctx.graph.query()`.

2. **Create `apps/media-scheduler/frontend/templates/stats.html`** with three chart sections:
   - "Hours by Category" — horizontal bar chart (podcast/youtube/spotify)
   - "Top Sources" — horizontal bar chart (top 10 by completion count)
   - "Weekly Activity" — line chart (completions per day)
   - Use Chart.js CDN lazy-load pattern: check `typeof Chart !== 'undefined'`, else create `<script>` element with `src='https://cdn.jsdelivr.net/npm/chart.js@4.4/dist/chart.umd.min.js'` and `onload` callback.
   - Stats data is injected server-side as `{{ stats_json }}` — parse with `JSON.parse()` in the boot function.
   - Wrap charts in `.ms-stats-view` container. Each chart in a `.ms-stats-card` with heading and `<canvas>`.

3. **Add stats route to `apps/media-scheduler/app.py`**:
   - Import stats_service functions.
   - Add `GET /_fragments/stats` handler: call all three stats functions, combine into a stats dict, JSON-serialize, render `stats.html` template with `stats_json` context variable.
   - Register the route with `@app.route("/_fragments/stats")`.

4. **Update `apps/media-scheduler/frontend/templates/main.html`**:
   - Add 4th tab button after the Rules tab: `<button class="ms-tab" data-tab="stats" onclick="msSelectTab(this, 'stats')"><i data-lucide="bar-chart-3"></i><span>Stats</span></button>`
   - Add `stats: '/app/media-scheduler/_fragments/stats'` to the `urls` map in `msSelectTab()`.

5. **Polish status badge CSS in `apps/media-scheduler/frontend/static/styles.css`**:
   - Add `.ms-stats-view`, `.ms-stats-card`, `.ms-stats-card h4`, `.ms-stats-card canvas` styles for the stats dashboard layout.
   - Improve `.ms-status-completed` with a subtle green background tint.
   - Improve `.ms-status-skipped` with a subtle orange/amber background tint.
   - Improve `.ms-status-saved` with a subtle blue background tint.
   - Add hover transitions to `.ms-action-btn` for smoother interaction feel.

6. **Add stats tests to `backend/tests/test_media_scheduler.py`**:
   - `TestStatsService` class with tests for each query builder function: verify SPARQL contains correct GROUP BY, FILTER, aggregation. Test result parsing with mock bindings.
   - `TestStatsRoute` class with tests for the stats route handler: mock graph queries, verify template rendering, verify JSON data injection.
   - Follow existing test patterns in the file (mock ctx, mock graph.query results).

## Must-Haves

- [ ] `stats_service.py` with three working SPARQL query functions
- [ ] `stats.html` template with Chart.js lazy-load and three chart canvases
- [ ] Stats route in `app.py` returning rendered template with data
- [ ] Stats tab button in `main.html` with correct URL wiring
- [ ] Status badge CSS improvements (completed=green, skipped=amber, saved=blue tints)
- [ ] Stats chart layout CSS (`.ms-stats-view`, `.ms-stats-card`)
- [ ] Unit tests for stats service and route

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v -k "stats" --tb=short` — all stats tests pass
- `python3 -c "import ast; ast.parse(open('apps/media-scheduler/app.py').read())"` — no syntax errors
- `python3 -c "import ast; ast.parse(open('apps/media-scheduler/services/stats_service.py').read())"` — no syntax errors
- `test -f apps/media-scheduler/frontend/templates/stats.html` — template exists
- `grep -q "stats" apps/media-scheduler/frontend/templates/main.html` — tab wired
- `grep -q "ms-stats-view" apps/media-scheduler/frontend/static/styles.css` — styles present

## Inputs

- `apps/media-scheduler/app.py` — existing app with routes and SPARQL patterns
- `apps/media-scheduler/services/plan_service.py` — MS_NS constant and SPARQL patterns for PlanEntry/MediaItem/MediaSource joins
- `apps/media-scheduler/frontend/templates/main.html` — tab structure to extend
- `apps/media-scheduler/frontend/templates/today.html` — status badge markup reference
- `apps/media-scheduler/frontend/static/styles.css` — existing styles to extend
- `backend/tests/test_media_scheduler.py` — existing test file to append to

## Expected Output

- `apps/media-scheduler/services/stats_service.py` — new stats service module
- `apps/media-scheduler/frontend/templates/stats.html` — new Chart.js dashboard template
- `apps/media-scheduler/app.py` — modified with stats route
- `apps/media-scheduler/frontend/templates/main.html` — modified with Stats tab
- `apps/media-scheduler/frontend/static/styles.css` — modified with stats + polish styles
- `backend/tests/test_media_scheduler.py` — modified with stats test classes
