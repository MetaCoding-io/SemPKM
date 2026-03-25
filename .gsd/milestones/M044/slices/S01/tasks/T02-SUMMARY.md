---
id: T02
parent: S01
milestone: M044
key_files:
  - frontend/static/js/workspace.js
  - frontend/static/js/sparql-console.js
  - frontend/static/js/copilot.js
  - frontend/static/js/canvas.js
  - frontend/static/js/auth.js
  - frontend/static/js/federation.js
  - frontend/static/js/vfs-browser.js
key_decisions:
  - All 7 files use { silent: true } on every apiFetch call — each file has its own error handling (inline UI, custom toasts, form messages) and double-toasting would be confusing
  - Auth.js /api/auth/me kept as raw fetch() with // raw-fetch comment — apiFetch's 401 redirect loses the ?next= query parameter needed for return-URL preservation
  - Non-2xx error detail extraction moved from resp.ok checks to catch blocks using err.body (apiFetch throws structured errors with .status, .body, .response properties)
duration: ""
verification_result: passed
completed_at: 2026-03-25T16:26:02.559Z
blocker_discovered: false
---

# T02: Migrate 110 fetch() calls across 7 high-volume JS files to apiFetch() with consistent error handling

**Migrate 110 fetch() calls across 7 high-volume JS files to apiFetch() with consistent error handling**

## What Happened

Migrated all bare `fetch()` calls in the 7 highest-volume JS files to `apiFetch()`:

- **workspace.js** (49 calls): Mix of JSON API, HTML fragment swaps, fire-and-forget calls, and AbortController-signaled requests. All converted with `{ silent: true }` since workspace.js has its own `showToast()` and inline error handling throughout. Removed redundant `!resp.ok` checks (apiFetch throws on non-2xx).

- **sparql-console.js** (15 calls): ES module with inline SPARQL error display. SPARQL execute and mirror calls restructured to use apiFetch error objects (`err.body`, `err.status`) for detailed inline error messages. Mirror endpoint 403 handling preserved via catch block status checking.

- **copilot.js** (13 calls, CRITICAL): SSE streaming fetch at line ~485 works correctly — apiFetch returns raw Response, so `.body.getReader()` chain works. Added guards for undefined response when AbortError is silently swallowed (apiFetch returns undefined). Existing catch block AbortError check is redundant but harmless.

- **canvas.js** (11 calls): Straightforward replacement. Fire-and-forget session activate call, plus async/await and .then() chains. All use `{ silent: true }` since canvas has its own error handling.

- **auth.js** (8 apiFetch + 1 raw-fetch): Auth pages use inline form messages via `showAuthMessage()`, so all use `{ silent: true }`. Error detail extraction restructured from `!resp.ok` checks to `catch` blocks using `err.body` JSON parsing. One intentional raw `fetch()` kept for `/api/auth/me` — it needs custom 401 redirect with `?next=` parameter, which conflicts with apiFetch's 401 redirect (no query params). Marked with `// raw-fetch` comment for grep exclusion.

- **federation.js** (8 calls): Has its own `showToast()`. All converted with `{ silent: true }` to prevent double-toasting. Non-2xx error detail extraction moved from `!res.ok` branches to catch blocks using `err.body`.

- **vfs-browser.js** (6 calls): IIFE with its own `showVfsToast()`. All converted with `{ silent: true }`. Removed redundant `r.ok` checks.

Total: 110 apiFetch conversions + 1 intentional raw-fetch = 111 original fetch calls handled.

## Verification

Ran task verification command: `rg '\bfetch\(' ... | grep -v apiFetch | grep -v '// raw-fetch' | wc -l` returns 0 across all 7 files. Node.js syntax check (`node -c`) passes for all 7 files. apiFetch counts match expectations: workspace(49), sparql-console(15), copilot(13), canvas(11), auth(8), federation(8), vfs-browser(6) = 110 apiFetch + 1 raw-fetch.

Slice-level checks: apiFetch has 3 `[apiFetch]` prefixed console logs, toast calls for user-facing failures, AbortError silencing, and `silent:true` support — all confirmed.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg '\bfetch\(' frontend/static/js/workspace.js frontend/static/js/sparql-console.js frontend/static/js/copilot.js frontend/static/js/canvas.js frontend/static/js/auth.js frontend/static/js/federation.js frontend/static/js/vfs-browser.js | grep -v apiFetch | grep -v '// raw-fetch' | wc -l` | 0 | ✅ pass | 85ms |
| 2 | `node -c frontend/static/js/workspace.js && node -c frontend/static/js/sparql-console.js && node -c frontend/static/js/copilot.js && node -c frontend/static/js/canvas.js && node -c frontend/static/js/auth.js && node -c frontend/static/js/federation.js && node -c frontend/static/js/vfs-browser.js` | 0 | ✅ pass | 420ms |


## Deviations

Auth.js `/api/auth/me` call kept as raw fetch() instead of apiFetch() — apiFetch's 401 handler redirects to `/login.html` without `?next=` parameter, but auth.js needs the `?next=` parameter to preserve the return URL. Marked with `// raw-fetch` comment for verification grep exclusion.

Federation.js error handling restructured from `if (!res.ok) { res.json().then(...) }` pattern to catch blocks parsing `err.body` from apiFetch's structured errors. Same restructuring applied to auth.js and sparql-console.js where `!resp.ok` branches extracted error details.

Copilot SSE streaming: added null-guards for response and reader in the `.then()` chain to handle the case where apiFetch returns undefined (AbortError).

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/workspace.js`
- `frontend/static/js/sparql-console.js`
- `frontend/static/js/copilot.js`
- `frontend/static/js/canvas.js`
- `frontend/static/js/auth.js`
- `frontend/static/js/federation.js`
- `frontend/static/js/vfs-browser.js`
