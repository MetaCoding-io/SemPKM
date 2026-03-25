# S01 Research: Centralized Fetch Wrapper & Migration

## Summary

Create a shared `apiFetch()` wrapper and migrate all 167 fetch() call sites (131 in JS files, 36 in HTML templates) across 36 files. The codebase currently has **zero centralized error handling** — 67 JS fetch calls lack `.catch()` and 32 lack `response.ok` checks. A toast notification system already exists (`window.showToast` in workspace.js). The main risk is the copilot SSE streaming fetch and ~9 HTML-fragment-swap fetches that need raw response access rather than auto-parsed JSON.

## Recommendation

**Approach:** Create a new `frontend/static/js/api-fetch.js` file loaded early in `base.html` (after `posthog.js`, before `auth.js`). Also add a `<script>` tag on the standalone auth pages (`login.html`, `setup.html`, `invite.html`). The wrapper goes on `window.apiFetch` so all IIFEs and inline template scripts can call it without imports.

**Wrapper design:**
- Returns the full `Response` object (not auto-parsed) so callers choose `.json()`, `.text()`, or `.body.getReader()`
- Checks `response.ok` and throws a structured error with status + body for non-2xx
- Wraps network errors in a catch that shows a toast and re-throws
- Accepts an options bag extending standard fetch options with `{ silent: true }` to suppress toast for background/optional fetches
- Handles 401 by redirecting to login (matching existing auth.js pattern)
- Passes through `signal` for AbortController support — aborted fetches don't show toasts

**Migration strategy:** Mechanical file-by-file replacement. The wrapper returns the Response, so existing `.then(r => r.json())` chains just work — the wrapper adds the error floor underneath.

## Implementation Landscape

### Current Architecture

**Script loading order** (from `base.html`):
1. `vendor.js` (third-party bundled libs)
2. CDN scripts (htmx, split.js, ninja-keys, cytoscape, marked, dompurify, lucide, driver.js, gridstack)
3. `posthog.js` → `auth.js` — pre-workspace utilities
4. `tutorials.js`
5. Inline `<script>` block (htmx config, event handlers)
6. `cleanup.js` → `markdown-render.js` → `editor.js` (module) → `sidebar.js` → `theme.js` → `settings.js`
7. `workspace-layout.js` → `named-layouts.js` → `workspace.js` → `graph.js` → `kanban.js` → `canvas.js` → `column-prefs.js`

**Standalone auth pages** (`login.html`, `setup.html`, `invite.html`): Load `posthog.js`, `auth.js`, `theme.js` directly — no `base.html`.

**Dynamic ES modules:** `sparql-console.js` and `copilot.js` are loaded via `import()` from workspace.js. `editor.js` is loaded as `type="module"` in base.html.

**Toast system:** `showToast(message, duration)` defined in workspace.js IIFE, exported as `window.showToast`. CSS classes `.sempkm-toast`, `.sempkm-toast--visible`, `.sempkm-toast--warning`, `.sempkm-toast--error` in workspace.css. Federation.js has its own local `showToast` (different signature — adds `type` param).

### Fetch Call Inventory

| File | Count | Has .catch | Has .ok | Notes |
|------|-------|-----------|---------|-------|
| workspace.js | 49 | 19 partial | 20 partial | Largest file; mix of JSON + HTML fragment fetches |
| sparql-console.js | 15 | 4 partial | 10 | ES module; uses await |
| copilot.js | 13 | 0 | 1 | ES module; **1 SSE streaming fetch** (getReader) |
| canvas.js | 11 | 5 partial | 7 | Some use await, some .then() |
| auth.js | 9 | 1 | 5 | Standalone page; all async/await |
| federation.js | 8 | 5 | 5 | Has own showToast; all .then() |
| vfs-browser.js | 6 | 3 | 3 | IIFE; 2 HTML-swap fetches |
| calendar.js | 4 | 1 | 1 | View template; CDN lazy-loaded |
| settings.js | 3 | 0 | 0 | IIFE; fire-and-forget pattern |
| app.js | 3 | 0 | 2 | Debug console; async/await |
| graph.js | 2 | 1 | 0 | IIFE; data + expand fetches |
| **HTML templates** | **36** | **~12** | **~18** | Inline `<script>` in partials |

Total: **167 fetch calls** across **36 files** (19 JS + 17 HTML templates).

### Special Cases

1. **Copilot SSE streaming** (`copilot.js:485`): `fetch('/api/copilot/chat', {...}).then(r => r.body.getReader())`. Can use `apiFetch` for the fetch itself (wrapper returns Response), but the caller chains `.body.getReader()` instead of `.json()`.

2. **HTML fragment fetches** (~9 calls): `fetch(url, { headers: {'HX-Request':'true'} }).then(r => r.text()).then(html => { el.innerHTML = html })`. These use `.text()` not `.json()`. The wrapper returning the raw Response handles this — caller just chains `.text()`.

3. **AbortController signal** (3 calls in workspace.js, 1 in copilot.js): Aborted fetches throw `AbortError` — the wrapper must detect this and suppress toast/error handling.

4. **Auth page fetches** (auth.js, 9 calls): These run on standalone pages without workspace.js — no `showToast` available. The wrapper needs either: (a) a graceful degradation when `showToast` isn't on `window`, or (b) inline the toast function in api-fetch.js. Option (a) is simpler and fine since auth pages already handle errors inline.

5. **Fire-and-forget fetches** (settings.js, sparql mark-viewed, etc.): Some calls intentionally ignore errors. The wrapper should support `{ silent: true }` to suppress toasts.

### Toast System Placement

The toast CSS is in `workspace.css` which is only loaded on workspace pages. For the wrapper to show toasts on any page, either:
- (a) Move toast CSS to `theme.css` (loaded everywhere), or
- (b) The wrapper creates inline styles if the CSS class doesn't have styles

Option (a) is cleaner — the toast CSS is only ~30 lines and theme.css is the right home for cross-page UI utilities.

### Files That Need Changes

**New file:**
- `frontend/static/js/api-fetch.js` — the wrapper (~60-80 lines)

**Modified — script loading:**
- `backend/app/templates/base.html` — add `<script src="{{ 'api-fetch.js' | asset_url }}"></script>` after posthog.js, before auth.js
- `frontend/static/login.html` — add `<script src="/js/api-fetch.js"></script>` before auth.js
- `frontend/static/setup.html` — same
- `frontend/static/invite.html` — same
- `frontend/static/index.html` — check if it has fetch calls (likely redirect-only, may not need it)

**Modified — CSS:**
- `frontend/static/css/workspace.css` — remove toast CSS block (~30 lines)
- `frontend/static/css/theme.css` — add toast CSS block

**Modified — JS migration (19 files):**
- `workspace.js` (49 calls) — biggest migration
- `sparql-console.js` (15 calls)
- `copilot.js` (13 calls)
- `canvas.js` (11 calls)
- `auth.js` (9 calls)
- `federation.js` (8 calls)
- `vfs-browser.js` (6 calls)
- `calendar.js` (4 calls)
- `settings.js` (3 calls)
- `app.js` (3 calls)
- `graph.js` (2 calls)
- `posthog.js` (1 call — analytics, probably stays raw)
- `quadrant.js` (1 call)
- `okr.js` (1 call)
- `bmc.js` (1 call)
- `kanban.js` (1 call)
- `editor.js` (1 call)
- `context-indicator.js` (1 call)
- `markdown-render.js` (1 call)

**Modified — HTML template migration (17 files):**
- `_webid_settings.html` (5 calls)
- `_context_rules.html` (5 calls)
- `workflow_builder.html` (4 calls)
- `_notification_preferences.html` (4 calls)
- `dashboard_builder.html` (3 calls)
- `_vfs_settings.html` (2 calls)
- `timeline_view.html` (2 calls)
- `my_views.html` (2 calls)
- `scan_trigger.html` × 2 (1 call each)
- `workflow_explorer.html` (1 call)
- `view_toolbar.html` (1 call)
- `template_picker.html` (1 call)
- `object_read.html` (1 call)
- `map_view.html` (1 call)
- `_llm_settings.html` (1 call)
- `dashboard_explorer.html` (1 call)

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Migration introduces subtle behavior change (e.g., toast on errors that were previously silent) | Medium | Use `{ silent: true }` for intentionally-quiet calls; test key flows |
| `showToast` undefined on auth pages | Low | Wrapper degrades gracefully — logs to console when toast unavailable |
| Copilot streaming fetch breaks if wrapper auto-consumes body | Low | Wrapper returns raw Response — doesn't touch body at all |
| 401 redirect conflicts with auth.js own redirect logic | Medium | Auth.js calls can use `{ noRedirect: true }` or wrapper skips redirect for auth endpoints |
| Missed a fetch call → verification catches it | Low | Verify with `rg 'fetch(' ... | grep -v apiFetch` |

## Task Decomposition Guidance

Natural seam: **wrapper creation → migration → verification**.

**T01: Create apiFetch wrapper + toast CSS move + script wiring** (~30 min)
- Create `api-fetch.js` with `window.apiFetch`
- Move toast CSS from workspace.css to theme.css
- Wire script loading in base.html + standalone pages
- Verify: new file loads, `window.apiFetch` available in console, toast renders

**T02: Migrate JS files** (~60 min, mechanical)
- Replace `fetch(` with `apiFetch(` across all 19 JS files
- Remove redundant `.catch()`/`.ok` checks where the wrapper handles them
- Keep explicit error handling where the caller does something specific (e.g., copilot shows inline error, auth redirects)
- Special cases: copilot streaming (keep raw Response chain), posthog (may skip — analytics)

**T03: Migrate HTML template files** (~30 min, mechanical)
- Replace `fetch(` with `apiFetch(` across all 17 HTML template files
- Same pattern as T02

**T04: Verification sweep** (~15 min)
- Run `rg 'fetch(' frontend/static/js/ -g '*.js' | grep -v apiFetch | grep -v '// raw-fetch'` — should return only posthog.js (or zero)
- Same check for templates
- Verify Docker test stack starts and key flows work (login, open object, save, copilot chat)

## Don't Hand-Roll

The wrapper is intentionally simple — no library needed. It's ~60 lines wrapping the native `fetch()` with:
1. `try { response = await fetch(...) } catch (networkError) { toast + rethrow }`
2. `if (!response.ok) { toast + throw structured error }`
3. Return `response` (not parsed body)

This is the standard pattern used by most frontend projects. No need for axios, ky, or similar — the native fetch API is fine and already used everywhere.
