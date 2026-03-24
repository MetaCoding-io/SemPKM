# S06: Stats Dashboard + Polish

**Goal:** Media consumption stats visible in the app, status badges polished, and user guide chapter published.
**Demo:** User clicks the Stats tab in the Media Scheduler app and sees three Chart.js charts: hours by source type, top 10 most-played sources, and weekly activity trend. Status badges in the today view have refined visual treatment. Chapter 49 of the user guide documents the full app.

## Must-Haves

- Stats service with SPARQL aggregate queries for hours-by-type, top-sources, weekly-trends
- Stats route (`GET /_fragments/stats`) returns server-rendered HTML with Chart.js charts
- Stats tab button added to `main.html` with correct tab wiring
- Chart.js lazy-loaded via CDN (version 4.4, consistent with codebase pattern)
- Status badge CSS polish (improved visual weight for completed/skipped/saved states)
- Unit tests for stats service query building and route handler
- User guide chapter 49 covering the full Media Scheduler app
- Three guide index files updated (README.md, index.html, guide.html)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v -k "stats" --tb=short` — all stats tests pass
- `python3 -c "import ast; ast.parse(open('apps/media-scheduler/app.py').read())"` — no syntax errors
- `python3 -c "import ast; ast.parse(open('apps/media-scheduler/services/stats_service.py').read())"` — no syntax errors
- `test -f apps/media-scheduler/frontend/templates/stats.html` — template exists
- `test -f docs/guide/49-media-scheduler.md` — guide chapter exists
- `grep -q "49-media-scheduler" docs/guide/README.md` — guide TOC updated
- `grep -q "49-media-scheduler" docs/guide/index.html` — HTML sidebar updated
- `grep -q "49-media-scheduler" backend/app/templates/guide.html` — in-app guide updated

## Tasks

- [x] **T01: Stats service, route, chart template, and status polish** `est:45m`
  - Why: Delivers the core stats dashboard — SPARQL queries, route handler, Chart.js template, tab wiring, status CSS polish, and tests.
  - Files: `apps/media-scheduler/services/stats_service.py`, `apps/media-scheduler/app.py`, `apps/media-scheduler/frontend/templates/main.html`, `apps/media-scheduler/frontend/templates/stats.html`, `apps/media-scheduler/frontend/static/styles.css`, `backend/tests/test_media_scheduler.py`
  - Do: Create stats_service.py with three SPARQL aggregate query builders (hours-by-type, top-sources, weekly-trends). Add `/_fragments/stats` route to app.py that calls the service and renders stats.html. Create stats.html with Chart.js CDN lazy-load and three charts. Add Stats tab button to main.html. Polish status badge CSS. Add unit tests for query building, result parsing, and route handler.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v -k "stats" --tb=short` passes; AST parse of app.py and stats_service.py succeeds
  - Done when: Stats tab loads and renders three charts from server-provided data; all stats tests pass; status badges have improved visual treatment

- [x] **T02: User guide chapter 49** `est:20m`
  - Why: Completes the slice by documenting the full Media Scheduler app for users. All three guide index files must be updated per KNOWLEDGE.md rule.
  - Files: `docs/guide/49-media-scheduler.md`, `docs/guide/README.md`, `docs/guide/index.html`, `backend/app/templates/guide.html`
  - Do: Write chapter 49 following the format of chapter 40 (RSS Reader). Cover: prerequisites, installing model + app, adding sources (podcast/YouTube/Spotify), schedule rules, today's plan, stats dashboard, mobile integration, troubleshooting. Update all three index files.
  - Verify: `test -f docs/guide/49-media-scheduler.md && grep -q "49-media-scheduler" docs/guide/README.md && grep -q "49-media-scheduler" docs/guide/index.html && grep -q "49-media-scheduler" backend/app/templates/guide.html`
  - Done when: Chapter 49 exists with all sections; all three index files reference it

## Files Likely Touched

- `apps/media-scheduler/services/stats_service.py`
- `apps/media-scheduler/app.py`
- `apps/media-scheduler/frontend/templates/main.html`
- `apps/media-scheduler/frontend/templates/stats.html`
- `apps/media-scheduler/frontend/static/styles.css`
- `backend/tests/test_media_scheduler.py`
- `docs/guide/49-media-scheduler.md`
- `docs/guide/README.md`
- `docs/guide/index.html`
- `backend/app/templates/guide.html`

## Observability / Diagnostics

- **Stats route logging:** `stats_fragment` logs `stats.rendered hours=N top=N weekly=N` on each render — visible in app container logs.
- **Query failure resilience:** Each stats query function catches exceptions and logs `stats.<function_name> query failed: <error>` before returning `[]`. The stats route never 500s — it renders the template with empty data, and Chart.js shows "No data" empty states.
- **Inspection surface:** Hit `GET /app/media-scheduler/_fragments/stats` directly — the rendered HTML includes `{{ stats_json }}` with the full data payload, inspectable in browser devtools.
- **Redaction:** No user secrets in stats data — only aggregate counts and source type strings.
