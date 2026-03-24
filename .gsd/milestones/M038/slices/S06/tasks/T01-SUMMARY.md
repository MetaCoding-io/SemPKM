---
id: T01
parent: S06
milestone: M038
provides:
  - Stats service with three SPARQL aggregate queries
  - Stats route handler serving Chart.js dashboard
  - Stats tab in main.html
  - Polished status badge CSS
  - 19 unit tests for stats service and route
key_files:
  - apps/media-scheduler/services/stats_service.py
  - apps/media-scheduler/app.py
  - apps/media-scheduler/frontend/templates/stats.html
  - apps/media-scheduler/frontend/templates/main.html
  - apps/media-scheduler/frontend/static/styles.css
  - backend/tests/test_media_scheduler.py
key_decisions:
  - Stats data injected as server-side JSON into template rather than fetched client-side via separate API endpoint
  - Weekly trends fills zero-count days for continuous chart appearance
  - Chart.js lazy-loaded from CDN consistent with calendar/map view pattern
patterns_established:
  - Stats service pattern: SPARQL aggregate → parse bindings → return typed dicts
observability_surfaces:
  - "stats.rendered hours=N top=N weekly=N" log line on each stats fragment load
  - Each query function logs warnings on SPARQL failures with function name prefix
duration: 18m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T01: Stats service, route, chart template, and status polish

**Add stats dashboard with three Chart.js charts (hours by category, top sources, weekly trends), Stats tab in main nav, polished status badges, and 19 unit tests**

## What Happened

Created `stats_service.py` with three async query functions — `get_hours_by_source_type` (SUM of durations grouped by source type, converted to hours), `get_top_sources` (COUNT completions per source title with configurable limit), and `get_weekly_trends` (COUNT per day with zero-fill for continuous chart data). All queries filter on `entryStatus = "completed"` only and gracefully return `[]` on SPARQL failures.

Added `GET /_fragments/stats` route to `app.py` that calls all three functions, serializes to JSON, and renders `stats.html`. The template uses the CDN lazy-load pattern (check `typeof Chart`, else inject `<script>` with `onload`) for Chart.js 4.4, rendering a horizontal bar chart for hours by category, a horizontal bar chart for top 10 sources, and a line chart with fill for weekly activity trends. Empty states shown when no data exists.

Added the Stats tab button to `main.html` with `bar-chart-3` Lucide icon and wired its URL in the `msSelectTab` function's URL map.

Polished status badges: `.ms-status-completed` now has green background + border, `.ms-status-skipped` has amber background + border, `.ms-status-saved` uses blue instead of yellow (better visual distinction from skipped). Added `transform: scale(1.08)` + `box-shadow` hover transition to `.ms-action-btn` for smoother interaction feel. Added full stats dashboard CSS grid layout (`.ms-stats-view`, `.ms-stats-grid`, `.ms-stats-card`).

Added 19 tests: `TestStatsService` (16 tests covering each query function's empty case, data parsing, error handling, and SPARQL template content checks) and `TestStatsRoute` (3 tests verifying template rendering, JSON data injection, and populated data flow).

## Verification

All 19 stats tests pass. Both AST syntax checks pass. Template exists. Tab is wired. Styles are present. Slice-level checks for guide chapter (T02 scope) expectedly don't pass yet.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v -k "stats" --tb=short` | 0 | ✅ pass | 0.57s |
| 2 | `python3 -c "import ast; ast.parse(open('apps/media-scheduler/app.py').read())"` | 0 | ✅ pass | <1s |
| 3 | `python3 -c "import ast; ast.parse(open('apps/media-scheduler/services/stats_service.py').read())"` | 0 | ✅ pass | <1s |
| 4 | `test -f apps/media-scheduler/frontend/templates/stats.html` | 0 | ✅ pass | <1s |
| 5 | `grep -q "stats" apps/media-scheduler/frontend/templates/main.html` | 0 | ✅ pass | <1s |
| 6 | `grep -q "ms-stats-view" apps/media-scheduler/frontend/static/styles.css` | 0 | ✅ pass | <1s |
| 7 | `test -f docs/guide/49-media-scheduler.md` | 1 | ⏳ T02 scope | — |
| 8 | `grep -q "49-media-scheduler" docs/guide/README.md` | 1 | ⏳ T02 scope | — |

## Diagnostics

- **Logs:** `stats.rendered hours=N top=N weekly=N` appears in app container logs on each Stats tab load.
- **Query failures:** Logged as `stats.hours_by_source_type query failed: ...`, `stats.top_sources query failed: ...`, `stats.weekly_trends query failed: ...` — grep for `stats.` prefix.
- **Data inspection:** Hit `GET /app/media-scheduler/_fragments/stats` and inspect the embedded JSON in the rendered HTML source.
- **Chart rendering:** Open browser devtools console — errors during Chart.js CDN load or JSON parse are logged with `media-scheduler:` prefix.

## Deviations

- Changed `.ms-status-saved` from yellow (#fefce8) to blue (#dbeafe) for better visual distinction from the amber skipped state. The plan said "subtle blue background tint" which aligns with this choice.
- Removed the duplicate `.ms-status-saved` declaration that was at the bottom of styles.css (it's now consolidated in the status badges section).

## Known Issues

None.

## Files Created/Modified

- `apps/media-scheduler/services/stats_service.py` — new stats service with three SPARQL aggregate query functions
- `apps/media-scheduler/frontend/templates/stats.html` — new Chart.js dashboard template with CDN lazy-load
- `apps/media-scheduler/app.py` — added stats_service import block and `/_fragments/stats` route handler
- `apps/media-scheduler/frontend/templates/main.html` — added Stats tab button and URL in msSelectTab map
- `apps/media-scheduler/frontend/static/styles.css` — polished status badges, improved action button hover, added stats dashboard layout styles
- `backend/tests/test_media_scheduler.py` — added 19 tests (TestStatsService + TestStatsRoute) and stats module imports
