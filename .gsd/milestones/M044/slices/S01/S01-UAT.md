# S01: Centralized Fetch Wrapper & Migration — UAT

**Milestone:** M044
**Written:** 2026-03-25T16:51:16.642Z

## Preconditions
- Docker test stack running (`docker compose up -d`)
- Browser open to workspace at `http://localhost:3901/browser/`

## Test Cases

### TC-01: apiFetch loads and is globally available
1. Open browser DevTools console on any page (workspace, login, setup, invite)
2. Type `typeof window.apiFetch` → **Expected:** `"function"`
3. Type `window.apiFetch.toString().includes('[apiFetch]')` → **Expected:** `true`

### TC-02: Network error produces toast
1. Open workspace page
2. In DevTools Network tab, enable "Offline" mode
3. Click any action that triggers a fetch (e.g., expand an explorer section, open an object)
4. **Expected:** A toast notification appears with error message; console shows `[apiFetch]` prefixed error
5. Disable "Offline" mode

### TC-03: Non-2xx response produces toast
1. Open workspace page
2. Navigate to a non-existent object URL (e.g., `/browser/objects/urn:nonexistent:object123`)
3. **Expected:** Page loads with error state; if fetch calls fire, toast appears for non-2xx responses; console shows `[apiFetch]` prefixed error with status code

### TC-04: 401 triggers login redirect
1. Open workspace page
2. Clear cookies (DevTools → Application → Cookies → Clear all)
3. Trigger any fetch action
4. **Expected:** Browser redirects to `/login.html`

### TC-05: Auth page 401 does NOT redirect (would cause loop)
1. Open `/login.html` directly
2. In console, run: `apiFetch('/api/auth/me').catch(e => console.log('caught', e.status))`
3. **Expected:** Error is caught, no redirect occurs (auth page is excluded from 401 redirect)

### TC-06: AbortError is silently suppressed
1. In console on workspace page, run:
   ```js
   const ac = new AbortController();
   const p = apiFetch('/api/sparql?query=SELECT+*+WHERE+{?s+?p+?o}+LIMIT+1', {signal: ac.signal});
   ac.abort();
   p.then(r => console.log('result:', r)).catch(e => console.log('error:', e));
   ```
2. **Expected:** Logs `result: undefined` — no toast, no error thrown

### TC-07: Silent mode suppresses toasts
1. In console on workspace page, run:
   ```js
   apiFetch('/api/nonexistent-endpoint-12345', {silent: true}).catch(e => console.log('silent error:', e.status));
   ```
2. **Expected:** Console shows `silent error: 404` (or similar) — NO toast notification appears

### TC-08: Copilot SSE streaming still works
1. Open AI Copilot tab in workspace
2. Type a message and send it
3. **Expected:** Response streams in character-by-character (SSE streaming via .body.getReader() works through apiFetch)

### TC-09: Zero bare fetch() in JS files
1. Run: `rg '\bfetch\(' frontend/static/js/ -g '*.js' | grep -v apiFetch | grep -v '// raw-fetch' | grep -v vendor.js`
2. **Expected:** Zero results

### TC-10: Zero bare fetch() in HTML templates
1. Run: `rg '\bfetch\(' backend/app/templates/ -g '*.html' | grep -v apiFetch`
2. **Expected:** Zero results

### TC-11: Toast CSS renders on auth pages
1. Open `/login.html`
2. In DevTools Elements panel, search for `.sempkm-toast` in computed styles
3. **Expected:** Toast CSS rules are defined (from theme.css)
4. Repeat for `/setup.html` and `/invite.html`

### Edge Cases

### EC-01: Structured error object contains expected properties
1. In console: `apiFetch('/api/nonexistent').catch(e => console.log(e.status, typeof e.body, typeof e.response))`
2. **Expected:** Logs status number (404), string (body text), object (Response)

### EC-02: Auth.js return-URL preservation
1. Navigate to `/browser/objects/some-object` while not logged in
2. **Expected:** Redirected to `/login.html?next=/browser/objects/some-object` (the auth.js raw-fetch preserves the ?next= parameter)
