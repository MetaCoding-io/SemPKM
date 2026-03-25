---
estimated_steps: 9
estimated_files: 7
skills_used: []
---

# T02: Migrate high-volume JS files to apiFetch (workspace, sparql-console, copilot, canvas, auth, federation, vfs-browser)

Replace all `fetch()` calls with `apiFetch()` in the 7 highest-volume JS files (93 calls total). This is the riskiest migration batch — these files contain the copilot SSE streaming, AbortController signals, HTML-fragment-swap fetches, and federation's local toast handling.

**File-by-file guidance:**

**workspace.js** (49 calls): The biggest file. Mix of JSON API calls, HTML fragment fetches (using `headers: {'HX-Request': 'true'}` → `.text()` → `innerHTML`), and fire-and-forget calls. The wrapper returns raw Response so `.then(r => r.json())` and `.then(r => r.text())` chains work unchanged. Remove redundant `.catch()` blocks where the wrapper's toast covers it. Keep explicit `.catch()` where the caller does something specific (e.g., shows inline error in a form, updates a status indicator).

**sparql-console.js** (15 calls): ES module, uses async/await. Replace `fetch(` with `apiFetch(` — the try/catch blocks that show inline SPARQL errors should be kept (they're caller-specific error handling).

**copilot.js** (13 calls, CRITICAL): ES module. **One SSE streaming fetch at ~line 485** uses `fetch('/api/copilot/chat', {...}).then(r => r.body.getReader())`. The wrapper returns the raw Response, so this chain works unchanged — just swap `fetch(` to `apiFetch(`. The caller already handles errors from the streaming reader. Also has AbortController usage — the wrapper silently catches AbortError.

**canvas.js** (11 calls): Mix of async/await and .then() chains. Straightforward replacement.

**auth.js** (9 calls): Standalone page — no workspace.js loaded. All async/await. Has its own 401 redirect logic. The wrapper also redirects on 401 but has auth-page detection to avoid redirect loops. Keep auth.js's own inline error handling for login/setup forms (shows validation messages). Mark fire-and-forget token refresh as `{ silent: true }`.

**federation.js** (8 calls): Has its own local `showToast(message, type, duration)` function with different CSS classes (`federation-toast-*`). The wrapper's toast will fire AND federation's own handling will fire — this is fine because federation catches errors to show its own toast. Use `{ silent: true }` for federation's calls so the wrapper doesn't double-toast, OR remove federation's redundant catches. The simpler approach: keep federation's own error handling and pass `{ silent: true }` to suppress wrapper toasts.

**vfs-browser.js** (6 calls): IIFE. 2 HTML-swap fetches, 4 JSON fetches. Straightforward replacement.

## Inputs

- `frontend/static/js/api-fetch.js`
- `frontend/static/js/workspace.js`
- `frontend/static/js/sparql-console.js`
- `frontend/static/js/copilot.js`
- `frontend/static/js/canvas.js`
- `frontend/static/js/auth.js`
- `frontend/static/js/federation.js`
- `frontend/static/js/vfs-browser.js`

## Expected Output

- `frontend/static/js/workspace.js`
- `frontend/static/js/sparql-console.js`
- `frontend/static/js/copilot.js`
- `frontend/static/js/canvas.js`
- `frontend/static/js/auth.js`
- `frontend/static/js/federation.js`
- `frontend/static/js/vfs-browser.js`

## Verification

count=$(rg '\\bfetch\\(' frontend/static/js/workspace.js frontend/static/js/sparql-console.js frontend/static/js/copilot.js frontend/static/js/canvas.js frontend/static/js/auth.js frontend/static/js/federation.js frontend/static/js/vfs-browser.js | grep -v apiFetch | grep -v '// raw-fetch' | wc -l) && echo "Remaining bare fetch calls: $count" && test "$count" -eq 0

## Observability Impact

Existing fetch error handling preserved where it does caller-specific work (inline errors, form validation). Wrapper adds a toast safety net for the ~67 calls that previously had no .catch() at all.
