---
estimated_steps: 15
estimated_files: 29
skills_used: []
---

# T03: Migrate remaining JS files and all HTML templates to apiFetch

Replace all `fetch()` calls with `apiFetch()` in the remaining 12 JS files (38 calls) and all 17 HTML template files (36 calls). These are mostly 1-4 call files with straightforward replacement patterns.

**JS files (12 files, 38 calls total):**
- `settings.js` (3 calls) — fire-and-forget settings saves; use `{ silent: true }` since failure isn't critical
- `app.js` (3 calls) — debug console; straightforward swap
- `graph.js` (2 calls) — data + expand fetches; straightforward swap
- `calendar.js` (4 calls) — CDN lazy-loaded view template; straightforward swap
- `quadrant.js` (1 call), `okr.js` (1 call), `bmc.js` (1 call), `kanban.js` (1 call) — single data fetch in each view renderer
- `posthog.js` (1 call) — analytics config fetch; use `{ silent: true }`
- `markdown-render.js` (1 call), `editor.js` (1 call), `context-indicator.js` (1 call) — single calls each

**HTML template files (17 files, 36 calls total):**
- `_webid_settings.html` (5 calls), `_context_rules.html` (5 calls), `_notification_preferences.html` (4 calls) — settings partials with JSON API + htmx reload pattern
- `workflow_builder.html` (4 calls), `dashboard_builder.html` (3 calls) — builder modals
- `_vfs_settings.html` (2 calls), `timeline_view.html` (2 calls), `my_views.html` (2 calls) — mixed
- 9 files with 1 call each: `scan_trigger.html` ×2, `workflow_explorer.html`, `view_toolbar.html`, `template_picker.html`, `object_read.html`, `map_view.html`, `_llm_settings.html`, `dashboard_explorer.html`

**Important:** HTML template inline scripts have access to `apiFetch` because `api-fetch.js` is loaded in `base.html` before any template partials render. Template partials rendered via htmx swaps also have access since the parent page loaded the script.

## Inputs

- `frontend/static/js/api-fetch.js`
- `frontend/static/js/settings.js`
- `frontend/static/js/app.js`
- `frontend/static/js/graph.js`
- `frontend/static/js/quadrant.js`
- `frontend/static/js/posthog.js`
- `frontend/static/js/okr.js`
- `frontend/static/js/markdown-render.js`
- `frontend/static/js/kanban.js`
- `frontend/static/js/editor.js`
- `frontend/static/js/context-indicator.js`
- `frontend/static/js/bmc.js`
- `frontend/static/js/calendar.js`
- `backend/app/templates/browser/_webid_settings.html`
- `backend/app/templates/browser/_context_rules.html`

## Expected Output

- `frontend/static/js/settings.js`
- `frontend/static/js/app.js`
- `frontend/static/js/graph.js`
- `frontend/static/js/quadrant.js`
- `frontend/static/js/posthog.js`
- `frontend/static/js/okr.js`
- `frontend/static/js/markdown-render.js`
- `frontend/static/js/kanban.js`
- `frontend/static/js/editor.js`
- `frontend/static/js/context-indicator.js`
- `frontend/static/js/bmc.js`
- `frontend/static/js/calendar.js`
- `backend/app/templates/browser/_webid_settings.html`
- `backend/app/templates/browser/_context_rules.html`
- `backend/app/templates/browser/workflow_builder.html`
- `backend/app/templates/browser/_notification_preferences.html`
- `backend/app/templates/browser/dashboard_builder.html`
- `backend/app/templates/browser/_vfs_settings.html`
- `backend/app/templates/browser/timeline_view.html`
- `backend/app/templates/browser/my_views.html`
- `backend/app/templates/obsidian/partials/scan_trigger.html`
- `backend/app/templates/notion/partials/scan_trigger.html`
- `backend/app/templates/browser/workflow_explorer.html`
- `backend/app/templates/browser/view_toolbar.html`
- `backend/app/templates/browser/template_picker.html`
- `backend/app/templates/browser/object_read.html`
- `backend/app/templates/browser/map_view.html`
- `backend/app/templates/browser/_llm_settings.html`
- `backend/app/templates/browser/dashboard_explorer.html`

## Verification

js_count=$(rg '\\bfetch\\(' frontend/static/js/settings.js frontend/static/js/app.js frontend/static/js/graph.js frontend/static/js/quadrant.js frontend/static/js/posthog.js frontend/static/js/okr.js frontend/static/js/markdown-render.js frontend/static/js/kanban.js frontend/static/js/editor.js frontend/static/js/context-indicator.js frontend/static/js/bmc.js frontend/static/js/calendar.js | grep -v apiFetch | grep -v '// raw-fetch' | wc -l) && html_count=$(rg '\\bfetch\\(' backend/app/templates/ -g '*.html' | grep -v apiFetch | wc -l) && echo "JS: $js_count, HTML: $html_count" && test "$js_count" -eq 0 && test "$html_count" -eq 0
