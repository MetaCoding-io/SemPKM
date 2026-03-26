# FIXES.md — Running Fix Log

Append-only log of bug fixes applied during debugging sessions.

---

### 2026-03-25 — Console errors & guide page fixes

**1. Script load order: `posthog.js` before `api-fetch.js`**
- **Symptom:** `Uncaught ReferenceError: apiFetch is not defined` in posthog.js on every page load
- **Root cause:** `posthog.js` was loaded before `api-fetch.js` in both `login.html` and `base.html`. PostHog's IIFE calls `apiFetch()` immediately at parse time.
- **Fix:** Swapped script order — `api-fetch.js` now loads before `posthog.js` in `frontend/static/login.html` and `backend/app/templates/base.html`.

**2. Missing `window.apiFetch` backward-compat shim**
- **Symptom:** Same `apiFetch is not defined` error even after reorder, in files using bare `apiFetch` (19 JS files).
- **Root cause:** M044/S03 namespace migration moved export to `window.SemPKM.apiFetch` but removed the `window.apiFetch` shim. 19 consumer files still reference bare `apiFetch`.
- **Fix:** Added `window.apiFetch = apiFetch;` shim back in `frontend/static/js/api-fetch.js`.

**3. CSP blocking `esm.sh` scripts and source maps**
- **Symptom:** 4 errors blocking CodeMirror scripts from `esm.sh`; 20+ errors blocking `.map` source map fetches from `esm.sh` and `cdn.jsdelivr.net`.
- **Root cause:** `Content-Security-Policy` in `frontend/nginx.conf` had `script-src` and `connect-src` that didn't include `esm.sh` or `cdn.jsdelivr.net`.
- **Fix:** Added `https://esm.sh` to `script-src`; added `https://esm.sh https://cdn.jsdelivr.net` to `connect-src`.

**4. `#nav-pane` selector error on non-workspace pages**
- **Symptom:** `Error: Selector #nav-pane did not match a DOM element` on dashboard and other non-workspace pages.
- **Root cause:** `workspace.js` `initSplit()` runs on every page (loaded via `base.html`) but `#nav-pane` only exists in `browser/workspace.html`.
- **Fix:** Added early return guard `if (!document.getElementById('nav-pane')) return;` in `initSplit()` in `frontend/static/js/workspace.js`.

**5. Dockview layout restore crash: `panels.filter is not a function`**
- **Symptom:** `TypeError: n.panels.filter is not a function` when restoring saved dockview layout.
- **Root cause:** Saved layout JSON `panels` field was not an array. Guard `if (saved.panels)` is truthy for non-array values (e.g. object).
- **Fix:** Changed guards to `Array.isArray(saved.panels)` in two places in `frontend/static/js/workspace-layout.js`.

**6. Guide page 500 error: `'builtin_function_or_method' object is not iterable`**
- **Symptom:** Navigating to `/guide` returned HTTP 500.
- **Root cause:** Jinja2 `section.items` resolves to the dict `.items()` method, not the `items` key. Same gotcha documented in KNOWLEDGE.
- **Fix:** Changed `section.items` → `section['items']` in three places in `backend/app/templates/guide.html`.

**7. Guide page missing CSS — unstyled layout**
- **Symptom:** Guide page renders with no card layout, raw stacked elements, overflowing chapter buttons.
- **Root cause:** `guide.html` overrides `{% block page_css %}` with an empty block, wiping out `workspace.css` which contains all `.docs-*` styles.
- **Fix:** Changed the empty override to include `workspace.css`: `{% block page_css %}<link rel="stylesheet" href="{{ 'workspace.css' | asset_url }}">{% endblock %}`.

**Files changed:**
- `frontend/static/login.html` — script order
- `frontend/static/js/api-fetch.js` — apiFetch shim
- `frontend/nginx.conf` — CSP policy
- `frontend/static/js/workspace.js` — nav-pane guard
- `frontend/static/js/workspace-layout.js` — Array.isArray guards
- `backend/app/templates/base.html` — script order
- `backend/app/templates/guide.html` — Jinja2 dict access + CSS block

---

### 2026-03-25 — E2E spec repair + CDN elimination

**8. Fix 19 E2E spec files with merge corruption**
- **Symptom:** `npx playwright test` failed to parse 19 spec files — syntax errors from duplicate code blocks, unclosed braces, duplicate variable declarations.
- **Root cause:** Bad git merges (K005/K006) pasted older versions of code inside or after newer consolidated versions across 19 test files.
- **Fix:** Identified and removed the duplicate/orphaned code blocks in each file. 1,247 lines of dead code removed.

**9. Eliminate all CDN dependencies — vendor everything locally**
- **Symptom:** 39 CDN URLs across templates and JS files. Calendar/timeline E2E tests fail in Docker (can't reach CDN). CDN outage would break production.
- **Root cause:** M029 vendor pipeline only bundled ~18 of ~24 libraries. 6 were never vendored (gridstack, fullcalendar, leaflet, leaflet.markercluster, frappe-gantt, codemirror). Templates still had CDN `<script>` tags even for already-vendored libs.
- **Fix:** Added 6 missing packages to `frontend/package.json`. Created CodeMirror IIFE bundles (markdown + sparql) via esbuild entry files. Updated all templates to use `asset_url`. Updated JS files to use vendored globals instead of `esm.sh` imports. Tightened CSP to `'self'` only.
- **Verified:** `grep -r 'unpkg\|cdn\.jsdelivr\|cdnjs\.cloudflare\|esm\.sh' backend/app/templates/ frontend/static/js/` returns zero results.

**10. Remove dead yasgui code**
- **Symptom:** ~400KB yasgui package vendored and built, but no route serves the template.
- **Root cause:** `/admin/sparql` route was changed to redirect to `/browser?panel=sparql` (workspace custom SPARQL console). The yasgui template at `admin/sparql.html` became an orphan.
- **Fix:** Removed `@zazuko/yasgui` from package.json, removed build step from `build.js`, deleted orphan template.
