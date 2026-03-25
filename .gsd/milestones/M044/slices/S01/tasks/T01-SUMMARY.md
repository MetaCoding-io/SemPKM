---
id: T01
parent: S01
milestone: M044
key_files:
  - frontend/static/js/api-fetch.js
  - frontend/static/css/theme.css
  - frontend/static/css/workspace.css
  - backend/app/templates/base.html
  - frontend/static/login.html
  - frontend/static/setup.html
  - frontend/static/invite.html
key_decisions:
  - Toast CSS moved to theme.css with fallback values (--color-bg-panel → --color-surface → raw hex) so it works on all pages regardless of which CSS files are loaded
  - apiFetch toast fallback chain: window.showToast → _showGlobalToast → console.warn — ensures toast works in workspace (showToast from workspace.js), base template pages (_showGlobalToast inline), and standalone pages (console.warn)
  - AbortError returns undefined rather than throwing — callers using AbortController should check for undefined return
duration: ""
verification_result: passed
completed_at: 2026-03-25T15:55:54.420Z
blocker_discovered: false
---

# T01: Create apiFetch wrapper with toast/error/abort handling, move toast CSS to theme.css, wire script into all pages

**Create apiFetch wrapper with toast/error/abort handling, move toast CSS to theme.css, wire script into all pages**

## What Happened

Created `frontend/static/js/api-fetch.js` — a centralized `window.apiFetch()` wrapper that:

1. Wraps native `fetch()` and returns the raw `Response` on success (caller parses as needed)
2. Catches network errors → shows toast via `window.showToast` / `_showGlobalToast` / `console.warn` fallback chain → rethrows
3. Checks `response.ok` — if false, extracts error body text, shows toast with friendly message, throws structured error with `.status`, `.body`, and `.response` properties
4. Detects `AbortError` (from AbortController) and suppresses silently — no toast, returns undefined
5. Supports `{ silent: true }` in options to suppress all toasts for intentionally-quiet calls
6. Handles 401 by redirecting to `/login.html` unless already on an auth page
7. Passes all standard fetch options through (strips `silent` before forwarding)
8. Logs `[apiFetch]` prefixed errors to console for observability

Moved toast CSS (`.sempkm-toast`, `--visible`, `--warning`, `--error`) from `workspace.css` to `theme.css` so toasts render on all pages including standalone auth pages. Added CSS variable fallbacks (`--color-bg-panel` → `--color-surface` → raw hex) for pages that don't load the full workspace token set.

Wired `<script src="api-fetch.js">` into:
- `base.html` (after posthog.js, before auth.js) — uses Jinja2 `asset_url` filter
- `login.html`, `setup.html`, `invite.html` — uses direct `/js/` path

Also fixed `invite.html` which was missing `theme.css` — added it so toast CSS actually loads on that page.

## Verification

Ran the task verification command (7 checks):
1. `window.apiFetch` present in api-fetch.js ✅
2. `api-fetch.js` referenced in base.html ✅
3. `api-fetch.js` referenced in login.html ✅
4. `api-fetch.js` referenced in setup.html ✅
5. `api-fetch.js` referenced in invite.html ✅
6. `sempkm-toast` present in theme.css ✅
7. `sempkm-toast` absent from workspace.css ✅

Slice-level verification (partial — T01 is the foundation):
- apiFetch logs [apiFetch] prefixed errors to console ✅ (3 console.error/warn calls with prefix)
- Shows toast for user-facing failures ✅ (_toast called for network errors and non-2xx)
- Silently handles AbortError ✅ (returns undefined, no toast)
- Handles {silent:true} calls ✅ (suppresses toast when silent flag set)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg 'window.apiFetch' frontend/static/js/api-fetch.js && rg 'api-fetch.js' backend/app/templates/base.html && rg 'api-fetch.js' frontend/static/login.html && rg 'api-fetch.js' frontend/static/setup.html && rg 'api-fetch.js' frontend/static/invite.html && rg 'sempkm-toast' frontend/static/css/theme.css && ! rg 'sempkm-toast' frontend/static/css/workspace.css` | 0 | ✅ pass | 320ms |


## Deviations

Added theme.css link to invite.html — it was missing, which would have prevented toast CSS from loading on that page. Not in the plan but necessary for correctness.

Added CSS variable fallbacks in the theme.css toast rules (--color-bg-panel → --color-surface → raw hex) since --color-bg-panel is only defined in workspace.css. Without fallbacks, toast background would be transparent on auth pages.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/api-fetch.js`
- `frontend/static/css/theme.css`
- `frontend/static/css/workspace.css`
- `backend/app/templates/base.html`
- `frontend/static/login.html`
- `frontend/static/setup.html`
- `frontend/static/invite.html`
