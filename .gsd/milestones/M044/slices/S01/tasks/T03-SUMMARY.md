---
id: T03
parent: S01
milestone: M044
key_files:
  - frontend/static/js/settings.js
  - frontend/static/js/app.js
  - frontend/static/js/graph.js
  - frontend/static/js/calendar.js
  - frontend/static/js/quadrant.js
  - frontend/static/js/okr.js
  - frontend/static/js/bmc.js
  - frontend/static/js/kanban.js
  - frontend/static/js/posthog.js
  - frontend/static/js/markdown-render.js
  - frontend/static/js/editor.js
  - frontend/static/js/context-indicator.js
  - backend/app/templates/browser/_webid_settings.html
  - backend/app/templates/browser/_context_rules.html
  - backend/app/templates/browser/_notification_preferences.html
  - backend/app/templates/browser/workflow_builder.html
  - backend/app/templates/browser/dashboard_builder.html
  - backend/app/templates/browser/_vfs_settings.html
  - backend/app/templates/browser/timeline_view.html
  - backend/app/templates/browser/my_views.html
  - backend/app/templates/obsidian/partials/scan_trigger.html
  - backend/app/templates/notion/partials/scan_trigger.html
  - backend/app/templates/browser/workflow_explorer.html
  - backend/app/templates/browser/view_toolbar.html
  - backend/app/templates/browser/template_picker.html
  - backend/app/templates/browser/object_read.html
  - backend/app/templates/browser/map_view.html
  - backend/app/templates/browser/_llm_settings.html
  - backend/app/templates/browser/dashboard_explorer.html
key_decisions:
  - All 29 files use { silent: true } — every file has its own error handling (inline UI messages, alerts, console.error, status elements) and double-toasting would be confusing
  - Dead resp.ok/!resp.ok branches cleaned rather than left as harmless dead code — apiFetch's throw-on-non-2xx makes them unreachable and leaving them would confuse future readers about the actual error flow
  - Error detail extraction in app.js and _context_rules.html restructured to use err.body from apiFetch's structured error object instead of the old resp.json() + !resp.ok pattern
duration: ""
verification_result: passed
completed_at: 2026-03-25T16:38:52.071Z
blocker_discovered: false
---

# T03: Migrate all remaining fetch() calls (12 JS files + 17 HTML templates) to apiFetch with silent:true and clean dead-code branches

**Migrate all remaining fetch() calls (12 JS files + 17 HTML templates) to apiFetch with silent:true and clean dead-code branches**

## What Happened

Migrated all 56 remaining raw fetch() calls across 29 files to apiFetch(). This was the final migration task in the slice — every fetch() call in the codebase now routes through the centralized wrapper except auth.js (intentional raw-fetch exemption from T02).

**JS files (12 files, 20 calls):** settings.js (3), app.js (3), graph.js (2), calendar.js (4), quadrant.js (1), okr.js (1), bmc.js (1), kanban.js (1), posthog.js (1), markdown-render.js (1), editor.js (1), context-indicator.js (1). All use `{ silent: true }` since each has its own error handling.

**HTML templates (17 files, 36 calls):** _webid_settings.html (5), _context_rules.html (5), _notification_preferences.html (4), workflow_builder.html (4), dashboard_builder.html (3), _vfs_settings.html (2), timeline_view.html (2), my_views.html (2), scan_trigger.html ×2 (1 each), workflow_explorer.html (1), view_toolbar.html (1), template_picker.html (1), object_read.html (1), map_view.html (1), _llm_settings.html (1), dashboard_explorer.html (1). All use `{ silent: true }`.

**Dead code cleanup:** Since apiFetch throws on non-2xx before returning, any `.then(function(resp) { if (!resp.ok) ... })` branches became unreachable. I cleaned these in: context_rules (create/update/toggle/delete), workflow_explorer (delete), dashboard_explorer (delete), view_toolbar (save), template_picker (instantiate), editor.js (save body), and notification_preferences (update). The error handling is preserved via the `.catch()` blocks which now catch both network errors and HTTP errors from apiFetch's structured throws.

**Restructured patterns:** For app.js (debug console), the two /api/commands calls were restructured — the try/catch now extracts error details from `err.body` (apiFetch's structured error) instead of the old `resp.json()` + `!resp.ok` pattern. For context_rules, error detail extraction uses `JSON.parse(err.body).detail`.

## Verification

Ran the task verification command: rg for raw fetch() across all 12 JS files and all HTML templates, excluding apiFetch and // raw-fetch comments. Result: JS: 0, HTML: 0 — zero remaining raw fetch() calls in scope.

Also verified: only auth.js (intentional exemption) and api-fetch.js (the wrapper itself) contain raw fetch() across the entire frontend/static/js/ directory. All apiFetch logging uses [apiFetch] prefix. AbortError handling and {silent:true} option confirmed in wrapper.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg '\bfetch\(' (12 JS files) | grep -v apiFetch | grep -v '// raw-fetch' | wc -l && rg '\bfetch\(' backend/app/templates/ -g '*.html' | grep -v apiFetch | wc -l && test both -eq 0` | 0 | ✅ pass | 150ms |
| 2 | `rg '\bfetch\(' frontend/static/js/ -l (global check)` | 0 | ✅ pass — only auth.js (exempted) and api-fetch.js (wrapper) remain | 80ms |
| 3 | `rg '\[apiFetch\]' frontend/static/js/api-fetch.js` | 0 | ✅ pass — [apiFetch] prefix on all error/warning console output | 30ms |


## Deviations

Cleaned dead code branches where apiFetch's throw-on-non-2xx made resp.ok checks unreachable. This was a logical consequence of the migration, not planned explicitly. In app.js, restructured error extraction to use err.body from apiFetch's structured error instead of the old resp.json() pattern.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/settings.js`
- `frontend/static/js/app.js`
- `frontend/static/js/graph.js`
- `frontend/static/js/calendar.js`
- `frontend/static/js/quadrant.js`
- `frontend/static/js/okr.js`
- `frontend/static/js/bmc.js`
- `frontend/static/js/kanban.js`
- `frontend/static/js/posthog.js`
- `frontend/static/js/markdown-render.js`
- `frontend/static/js/editor.js`
- `frontend/static/js/context-indicator.js`
- `backend/app/templates/browser/_webid_settings.html`
- `backend/app/templates/browser/_context_rules.html`
- `backend/app/templates/browser/_notification_preferences.html`
- `backend/app/templates/browser/workflow_builder.html`
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
