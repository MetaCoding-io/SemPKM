# S06: Stats Dashboard + Polish — Research

## Summary

Straightforward polish slice. Three deliverables: (1) stats service + SPARQL queries for media consumption data, (2) stats tab with Chart.js visualizations, (3) user guide chapter 49 for the Media Scheduler app. All patterns are established in the codebase — Chart.js CDN lazy-load, htmx tab switching, SPARQL aggregation, guide chapter format. No new dependencies, no new technology.

## Recommendation

Light implementation. Three tasks:
- T01: Stats service + stats route + stats template with Chart.js charts
- T02: Status polish (minor CSS/UX refinements to the today view action buttons)
- T03: User guide chapter 49 (markdown + update 3 index files)

T01 is the bulk of the work (~60%). T02 and T03 are small and independent of each other but both depend on T01 being done so the guide can reference the stats view.

## Implementation Landscape

### Stats Service (`services/stats_service.py`)

New module. Three SPARQL aggregate queries:

**Hours per source type:** Aggregate `ms:duration` from PlanEntry objects with `entryStatus = "completed"`, joined to MediaItem → MediaSource → `ms:sourceType`. Group by sourceType, SUM durations.

**Most-played sources:** COUNT completed PlanEntry objects, joined to MediaItem → MediaSource → `dcterms:title`. Group by source title, ORDER BY DESC count. LIMIT 10.

**Weekly trends:** COUNT completed PlanEntry objects per day for the last 7 days. Uses plan date from the PlanEntry's parent DailyMediaPlan `dcterms:title` (which contains the date string like "Media Plan for 2026-03-23"). Group by date, order chronologically.

Key constants from existing code:
- `MS_NS = "urn:sempkm:model:media-scheduler:"`
- `PLAN_ENTRY_TYPE = f"{MS_NS}PlanEntry"`
- `DAILY_MEDIA_PLAN_TYPE = f"{MS_NS}DailyMediaPlan"`
- Entry status field: `ms:entryStatus` (values: pending, completed, skipped, saved, replaced)
- Item duration field: `ms:duration` (integer seconds)
- Source type field on MediaSource: `ms:sourceType` (podcast, youtube, spotify)

### Stats Tab (UI)

Add a 4th tab to `main.html`:
```html
<button class="ms-tab" data-tab="stats" onclick="msSelectTab(this, 'stats')">
  <i data-lucide="bar-chart-3"></i><span>Stats</span>
</button>
```
Add `stats` to the `urls` map in `msSelectTab()`:
```javascript
stats: '/app/media-scheduler/_fragments/stats'
```

### Stats Template (`frontend/templates/stats.html`)

Three chart sections:
1. **Hours by Category** — horizontal bar chart (podcast vs youtube vs spotify)
2. **Top Sources** — horizontal bar chart (top 10 most-played sources by completion count)
3. **Weekly Activity** — line chart (completions per day, last 7 days)

Chart.js CDN lazy-load pattern from `workspace.js`:
```javascript
(function() {
    function _boot() { /* render charts */ }
    if (typeof Chart !== 'undefined') { _boot(); }
    else {
        var s = document.createElement('script');
        s.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4/dist/chart.umd.min.js';
        s.onload = _boot;
        document.head.appendChild(s);
    }
})();
```

Stats data is fetched inline by the route handler (server-side SPARQL) and injected as JSON into the template via `{{ stats_json }}`. No client-side SPARQL fetch needed — keeps it simple and avoids CORS/auth complexity.

### Stats Route (`app.py`)

New route: `GET /_fragments/stats` → calls stats_service functions → renders `stats.html` with pre-computed data.

### Status Polish

Minor CSS refinements to `styles.css`:
- Improve visual weight of completed/skipped/saved badges
- Add hover states to action buttons
- Ensure the status badge colors are consistent across today view and stats view

The current action buttons use `✓`, `→`, `♡` text characters. Consider adding subtle background colors or border treatments. No structural changes — the htmx wiring from S05 works correctly.

### User Guide Chapter

Create `docs/guide/49-media-scheduler.md` following the format of `40-rss-reader.md`:
- Prerequisites (media-scheduler model + app install)
- Adding media sources (podcast, YouTube, Spotify)
- Schedule rules
- Today's plan view
- Stats dashboard
- Mobile integration
- Troubleshooting

**Three files must be updated** (KNOWLEDGE.md rule):
1. `docs/guide/README.md` — add chapter 49 to the table of contents
2. `docs/guide/index.html` — add `<li>` entry to the HTML sidebar
3. `backend/app/templates/guide.html` — add `<button>` entry to the Jinja2 template

### Tests

Add to `backend/tests/test_media_scheduler.py`:
- `TestStatsService` — unit tests for SPARQL query building + result parsing
- `TestStatsRoute` — route handler tests with mocked graph queries

Stats service functions are pure (build SPARQL, parse bindings) — easy to test without SDK.

## Constraints

- Chart.js version: 4.4 (pinned CDN URL, consistent with `workspace.js` and `model_detail.html`)
- SPARQL queries run through `ctx.graph.query()` (scoped to `urn:sempkm:current`) — no UPDATE needed
- Entry status "replaced" entries must be excluded from all stats (same filter as today view)
- Duration is stored in seconds as integer — convert to hours for display
- The stats route is server-rendered (SPARQL in Python, inject JSON into template) not client-fetched

## Files Affected

| File | Change |
|------|--------|
| `apps/media-scheduler/services/stats_service.py` | **New** — SPARQL queries for hours/sources/trends |
| `apps/media-scheduler/app.py` | Add stats route `/_fragments/stats`, import stats_service |
| `apps/media-scheduler/frontend/templates/main.html` | Add Stats tab button + URL mapping |
| `apps/media-scheduler/frontend/templates/stats.html` | **New** — Chart.js dashboard template |
| `apps/media-scheduler/frontend/static/styles.css` | Stats section styles, status badge polish |
| `docs/guide/49-media-scheduler.md` | **New** — user guide chapter |
| `docs/guide/README.md` | Add chapter 49 link |
| `docs/guide/index.html` | Add chapter 49 sidebar entry |
| `backend/app/templates/guide.html` | Add chapter 49 button |
| `backend/tests/test_media_scheduler.py` | Add stats service + route tests |
