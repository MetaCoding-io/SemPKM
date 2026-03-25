# S01: Centralized Fetch Wrapper & Migration

**Goal:** All 167 fetch() calls across 36 files route through apiFetch() with consistent error handling — network failures show user-facing toasts, non-2xx responses throw structured errors, and AbortError/silent fetches are handled gracefully.
**Demo:** After this: all 131 fetch() calls route through apiFetch() with consistent error handling — network failures show user-facing toasts instead of silently failing

## Must-Haves

- ## Must-Haves
- `frontend/static/js/api-fetch.js` exists with `window.apiFetch()` wrapper that: returns raw Response, checks `response.ok` and throws on non-2xx, catches network errors and shows toast, handles AbortError silently, supports `{ silent: true }` option, redirects to login on 401
- Toast CSS moved from `workspace.css` to `theme.css` (available on all pages)
- `api-fetch.js` loaded in `base.html` and all standalone auth pages (login, setup, invite)
- All 131 JS fetch() calls across 19 files migrated to apiFetch()
- All 36 HTML template fetch() calls across 17 files migrated to apiFetch()
- Copilot SSE streaming fetch works correctly through apiFetch (returns raw Response for `.body.getReader()`)
- `rg 'fetch(' frontend/static/js/ -g '*.js' | grep -v apiFetch | grep -v '// raw-fetch'` returns zero results
- `rg 'fetch(' backend/app/templates/ -g '*.html' | grep -v apiFetch` returns zero results
- ## Proof Level
- This slice proves: operational
- Real runtime required: yes (Docker test stack for E2E verification)
- Human/UAT required: no
- ## Verification
- `rg '\bfetch\(' frontend/static/js/ -g '*.js' | grep -v apiFetch | grep -v '// raw-fetch' | grep -v vendor.js | wc -l` returns 0
- `rg '\bfetch\(' backend/app/templates/ -g '*.html' | grep -v apiFetch | wc -l` returns 0
- `test -f frontend/static/js/api-fetch.js` passes
- `rg 'api-fetch.js' backend/app/templates/base.html` returns at least 1 match
- `rg 'api-fetch.js' frontend/static/login.html` returns at least 1 match
- `rg 'sempkm-toast' frontend/static/css/theme.css` returns at least 1 match
- ## Observability / Diagnostics
- Runtime signals: `apiFetch()` catches network errors and non-2xx responses, shows toast via `window.showToast()` (degrades to console.warn when unavailable), logs error detail to console
- Inspection surfaces: Browser console shows `[apiFetch]` prefixed warnings for suppressed errors; Network tab shows all fetch calls unchanged
- Failure visibility: Toast appears for every unsilenced fetch failure; AbortError is silently caught; 401 triggers redirect to /login.html
- Redaction constraints: none
- ## Integration Closure
- Upstream surfaces consumed: `window.showToast()` from workspace.js IIFE; toast CSS classes from workspace.css (moved to theme.css)
- New wiring introduced in this slice: `window.apiFetch()` global function loaded early in script chain; script tag added to base.html + standalone pages
- What remains before the milestone is truly usable end-to-end: S02-S06 address other quality areas; S07 runs full E2E regression

## Proof Level

- This slice proves: operational

## Integration Closure

Upstream: window.showToast() from workspace.js, toast CSS from workspace.css. New wiring: window.apiFetch() global loaded in base.html and standalone pages. Remaining: S02-S06 other quality areas, S07 E2E regression.

## Verification

- apiFetch logs [apiFetch] prefixed errors to console, shows toast for user-facing failures, silently handles AbortError and {silent:true} calls.

## Tasks

- [ ] **T01: Create apiFetch wrapper, move toast CSS, wire script loading** `est:30m`
  Create the centralized fetch wrapper in a new file, move toast CSS to theme.css for cross-page availability, and wire the script tag into base.html and standalone auth pages.
  - Files: `frontend/static/js/api-fetch.js`, `frontend/static/css/theme.css`, `frontend/static/css/workspace.css`, `backend/app/templates/base.html`, `frontend/static/login.html`, `frontend/static/setup.html`, `frontend/static/invite.html`
  - Verify: rg 'window.apiFetch' frontend/static/js/api-fetch.js && rg 'api-fetch.js' backend/app/templates/base.html && rg 'api-fetch.js' frontend/static/login.html && rg 'sempkm-toast' frontend/static/css/theme.css && ! rg 'sempkm-toast' frontend/static/css/workspace.css

- [ ] **T02: Migrate high-volume JS files to apiFetch (workspace, sparql-console, copilot, canvas, auth, federation, vfs-browser)** `est:1h`
  Replace fetch() with apiFetch() in the 7 largest JS files (93 calls total). Handle special cases: copilot SSE streaming (keep raw Response chain for .body.getReader()), AbortController signals, federation's local showToast, and auth page 401 handling.
  - Files: `frontend/static/js/workspace.js`, `frontend/static/js/sparql-console.js`, `frontend/static/js/copilot.js`, `frontend/static/js/canvas.js`, `frontend/static/js/auth.js`, `frontend/static/js/federation.js`, `frontend/static/js/vfs-browser.js`
  - Verify: count=$(rg '\bfetch\(' frontend/static/js/workspace.js frontend/static/js/sparql-console.js frontend/static/js/copilot.js frontend/static/js/canvas.js frontend/static/js/auth.js frontend/static/js/federation.js frontend/static/js/vfs-browser.js | grep -v apiFetch | grep -v '// raw-fetch' | wc -l) && test "$count" -eq 0

- [ ] **T03: Migrate remaining JS files and all HTML templates to apiFetch** `est:45m`
  Replace fetch() with apiFetch() in the 12 small JS files (38 calls) and all 17 HTML template files (36 calls). These are mostly 1-4 call files with straightforward patterns.
  - Files: `frontend/static/js/settings.js`, `frontend/static/js/app.js`, `frontend/static/js/graph.js`, `frontend/static/js/quadrant.js`, `frontend/static/js/posthog.js`, `frontend/static/js/okr.js`, `frontend/static/js/markdown-render.js`, `frontend/static/js/kanban.js`, `frontend/static/js/editor.js`, `frontend/static/js/context-indicator.js`, `frontend/static/js/bmc.js`, `frontend/static/js/calendar.js`, `backend/app/templates/browser/_webid_settings.html`, `backend/app/templates/browser/_context_rules.html`, `backend/app/templates/browser/workflow_builder.html`, `backend/app/templates/browser/_notification_preferences.html`, `backend/app/templates/browser/dashboard_builder.html`, `backend/app/templates/browser/_vfs_settings.html`, `backend/app/templates/browser/timeline_view.html`, `backend/app/templates/browser/my_views.html`, `backend/app/templates/obsidian/partials/scan_trigger.html`, `backend/app/templates/notion/partials/scan_trigger.html`, `backend/app/templates/browser/workflow_explorer.html`, `backend/app/templates/browser/view_toolbar.html`, `backend/app/templates/browser/template_picker.html`, `backend/app/templates/browser/object_read.html`, `backend/app/templates/browser/map_view.html`, `backend/app/templates/browser/_llm_settings.html`, `backend/app/templates/browser/dashboard_explorer.html`
  - Verify: js_count=$(rg '\bfetch\(' frontend/static/js/settings.js frontend/static/js/app.js frontend/static/js/graph.js frontend/static/js/quadrant.js frontend/static/js/posthog.js frontend/static/js/okr.js frontend/static/js/markdown-render.js frontend/static/js/kanban.js frontend/static/js/editor.js frontend/static/js/context-indicator.js frontend/static/js/bmc.js frontend/static/js/calendar.js | grep -v apiFetch | grep -v '// raw-fetch' | wc -l) && html_count=$(rg '\bfetch\(' backend/app/templates/ -g '*.html' | grep -v apiFetch | wc -l) && test "$js_count" -eq 0 && test "$html_count" -eq 0

- [ ] **T04: Full codebase verification sweep and cleanup** `est:15m`
  Final sweep to confirm zero remaining bare fetch() calls, verify the wrapper handles all edge cases, and clean up any redundant error handling that the wrapper now covers.
  - Files: `frontend/static/js/api-fetch.js`
  - Verify: total_js=$(rg '\bfetch\(' frontend/static/js/ -g '*.js' | grep -v apiFetch | grep -v '// raw-fetch' | grep -v vendor.js | wc -l) && total_html=$(rg '\bfetch\(' backend/app/templates/ -g '*.html' | grep -v apiFetch | wc -l) && echo "JS: $total_js, HTML: $total_html" && test "$total_js" -eq 0 && test "$total_html" -eq 0

## Files Likely Touched

- frontend/static/js/api-fetch.js
- frontend/static/css/theme.css
- frontend/static/css/workspace.css
- backend/app/templates/base.html
- frontend/static/login.html
- frontend/static/setup.html
- frontend/static/invite.html
- frontend/static/js/workspace.js
- frontend/static/js/sparql-console.js
- frontend/static/js/copilot.js
- frontend/static/js/canvas.js
- frontend/static/js/auth.js
- frontend/static/js/federation.js
- frontend/static/js/vfs-browser.js
- frontend/static/js/settings.js
- frontend/static/js/app.js
- frontend/static/js/graph.js
- frontend/static/js/quadrant.js
- frontend/static/js/posthog.js
- frontend/static/js/okr.js
- frontend/static/js/markdown-render.js
- frontend/static/js/kanban.js
- frontend/static/js/editor.js
- frontend/static/js/context-indicator.js
- frontend/static/js/bmc.js
- frontend/static/js/calendar.js
- backend/app/templates/browser/_webid_settings.html
- backend/app/templates/browser/_context_rules.html
- backend/app/templates/browser/workflow_builder.html
- backend/app/templates/browser/_notification_preferences.html
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
