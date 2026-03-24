---
id: S06
milestone: M038
title: "Stats Dashboard + Polish"
status: done
started: 2026-03-23
completed: 2026-03-23
tasks_completed: 2
tasks_total: 2
---

# S06: Stats Dashboard + Polish — Summary

## What This Slice Delivered

Media consumption stats dashboard with three Chart.js charts, polished status badges, and comprehensive user guide chapter 49 documenting the full Media Scheduler app.

### Stats Dashboard (T01)

Created `stats_service.py` with three async SPARQL aggregate query functions:

- **Hours by source type** — `SUM` of durations grouped by `sourceType`, filtered to `entryStatus = "completed"`, converted to decimal hours
- **Top 10 sources** — `COUNT` of completions per source title with configurable limit, `ORDER BY DESC`
- **Weekly trends** — `COUNT` per day over trailing 7 days with zero-fill for days with no activity (continuous line chart)

All three functions catch exceptions and return `[]` on failure — the stats route never 500s.

Added `GET /_fragments/stats` route to `app.py` that calls all three functions, serializes results to JSON, and renders `stats.html`. The template lazy-loads Chart.js 4.4 from CDN using the established pattern (check `typeof Chart`, else inject `<script>` with `onload`). Three charts render: horizontal bar for hours by category, horizontal bar for top sources, and filled line chart for weekly trends. Empty states display "No data" when no completed items exist.

Stats tab button added to `main.html` with `bar-chart-3` Lucide icon, wired into the `msSelectTab` URL map.

### Status Badge Polish (T01)

- `.ms-status-completed` — green background + border
- `.ms-status-skipped` — amber background + border
- `.ms-status-saved` — changed from yellow to blue for better visual distinction from skipped
- `.ms-action-btn` — added `transform: scale(1.08)` + `box-shadow` hover transition

### User Guide (T02)

Chapter 49 (`docs/guide/49-media-scheduler.md`) with 13 sections covering: prerequisites, installation, interface layout, adding sources (podcast/YouTube/Spotify), schedule rules, today's plan, stats dashboard, managing sources, mobile integration, admin monitoring, and troubleshooting. All three guide index files updated (README.md, index.html, guide.html).

## Verification Results

| # | Check | Result |
|---|-------|--------|
| 1 | `pytest tests/test_media_scheduler.py -k "stats"` — 19 tests | ✅ pass |
| 2 | AST parse `app.py` | ✅ pass |
| 3 | AST parse `stats_service.py` | ✅ pass |
| 4 | `stats.html` exists | ✅ pass |
| 5 | `docs/guide/49-media-scheduler.md` exists | ✅ pass |
| 6 | README.md references chapter 49 | ✅ pass |
| 7 | index.html references chapter 49 | ✅ pass |
| 8 | guide.html references chapter 49 | ✅ pass |

## Test Coverage

19 new tests in `TestStatsService` (16) and `TestStatsRoute` (3):
- Each query function: empty results, data parsing, SPARQL template content, error handling
- Weekly trends: zero-fill verification, chronological ordering
- Route handler: template rendering, JSON injection, populated data flow

## Files Changed

- `apps/media-scheduler/services/stats_service.py` — new (stats service)
- `apps/media-scheduler/app.py` — added stats route + imports
- `apps/media-scheduler/frontend/templates/stats.html` — new (Chart.js dashboard)
- `apps/media-scheduler/frontend/templates/main.html` — Stats tab button
- `apps/media-scheduler/frontend/static/styles.css` — status badges + stats layout
- `backend/tests/test_media_scheduler.py` — 19 new tests
- `docs/guide/49-media-scheduler.md` — new (chapter 49)
- `docs/guide/README.md` — TOC entry
- `docs/guide/index.html` — sidebar link
- `backend/app/templates/guide.html` — in-app guide button

## Observability

- `stats.rendered hours=N top=N weekly=N` log line on each stats fragment load
- Query failures logged as `stats.<function_name> query failed: <error>`
- Raw JSON data inspectable in rendered HTML source at `GET /app/media-scheduler/_fragments/stats`

## What S07 Should Know

- Stats queries filter on `entryStatus = "completed"` only — E2E tests need items with that status to see non-empty charts
- Chart.js CDN lazy-load pattern is the same as calendar/map views — CDN outage risk applies
- The stats route is resilient (never 500s) but returns empty charts on query failures — E2E should verify both happy path and graceful degradation
- User guide chapter 49 documents the entire app end-to-end — E2E scenarios can reference it for expected behavior descriptions
