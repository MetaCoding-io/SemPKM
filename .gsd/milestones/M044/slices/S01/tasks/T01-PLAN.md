---
estimated_steps: 10
estimated_files: 7
skills_used: []
---

# T01: Create apiFetch wrapper, move toast CSS, wire script loading

Create the centralized `window.apiFetch()` wrapper in a new `frontend/static/js/api-fetch.js` file. Move toast CSS from workspace.css to theme.css so it's available on all pages (including standalone auth pages). Wire the script tag into base.html (after posthog.js, before auth.js) and all standalone auth pages.

The wrapper must:
1. Be an async function that wraps native `fetch()` and returns the raw `Response` (not auto-parsed)
2. Catch network errors → show toast via `window.showToast()` (degrade to `console.warn` if unavailable) → rethrow
3. Check `response.ok` — if false, extract error body text, show toast, throw structured error with status + body
4. Detect `AbortError` (from AbortController) and suppress toast/rethrow silently
5. Support `{ silent: true }` in options to suppress toast for intentionally-quiet calls
6. Handle 401 by redirecting to `/login.html` (matching existing auth.js pattern) — but only when NOT on an auth page already
7. Accept all standard fetch options (method, headers, body, signal, etc.) and pass them through
8. Go on `window.apiFetch` so all IIFEs and inline template scripts can call it

## Inputs

- `frontend/static/css/workspace.css`
- `frontend/static/css/theme.css`
- `backend/app/templates/base.html`
- `frontend/static/login.html`
- `frontend/static/setup.html`
- `frontend/static/invite.html`

## Expected Output

- `frontend/static/js/api-fetch.js`
- `frontend/static/css/theme.css`
- `frontend/static/css/workspace.css`
- `backend/app/templates/base.html`
- `frontend/static/login.html`
- `frontend/static/setup.html`
- `frontend/static/invite.html`

## Verification

rg 'window.apiFetch' frontend/static/js/api-fetch.js && rg 'api-fetch.js' backend/app/templates/base.html && rg 'api-fetch.js' frontend/static/login.html && rg 'api-fetch.js' frontend/static/setup.html && rg 'api-fetch.js' frontend/static/invite.html && rg 'sempkm-toast' frontend/static/css/theme.css && ! rg 'sempkm-toast' frontend/static/css/workspace.css
