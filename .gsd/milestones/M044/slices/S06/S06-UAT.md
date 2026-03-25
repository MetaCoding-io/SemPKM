# S06: Console Cleanup & Convention Documentation — UAT

**Milestone:** M044
**Written:** 2026-03-25T22:20:19.863Z

## UAT: S06 — Console Cleanup & Convention Documentation

### Preconditions
- SemPKM workspace accessible in browser
- Browser developer tools available (F12)
- Access to the project filesystem

### Test 1: Production Console is Clean
1. Open the SemPKM workspace in Chrome/Firefox
2. Open DevTools → Console tab
3. Clear the console
4. Navigate through several workspace pages (objects, views, admin)
5. Open and close dockview panels (graph, kanban, SPARQL console)
6. **Expected:** Zero `console.log` output in the console. Only `console.warn` and `console.error` messages (if any) should appear.

### Test 2: Debug Logging Activation
1. Open DevTools → Console tab
2. Run: `localStorage.setItem('sempkm_debug', '1')`
3. Reload the page
4. Navigate to a view that triggers debug output (e.g., open a calendar view, use copilot chat)
5. **Expected:** Console shows tagged messages like `[calendar] ...`, `[copilot] ...`, `[SemPKM] ...`
6. Run: `localStorage.removeItem('sempkm_debug')`
7. Reload the page and repeat the navigation
8. **Expected:** No debug messages appear in console

### Test 3: SemPKM.debug() API Available
1. Open DevTools → Console tab
2. Run: `typeof window.SemPKM.debug`
3. **Expected:** Returns `"function"`
4. Run: `window.SemPKM.debug('test', 'hello', {a: 1})`
5. **Expected:** No output (debug flag not set)
6. Run: `localStorage.setItem('sempkm_debug', '1')`
7. Run: `window.SemPKM.debug('test', 'hello', {a: 1})`
8. **Expected:** Console shows `[test] hello {a: 1}`

### Test 4: console.warn and console.error Preserved
1. In the project directory, run: `grep -rn 'console\.warn' frontend/static/js/ --include='*.js' | wc -l`
2. **Expected:** 48 (unchanged from pre-S06 baseline)
3. Run: `grep -rn 'console\.error' frontend/static/js/ --include='*.js' | wc -l`
4. **Expected:** 49 (unchanged from pre-S06 baseline)

### Test 5: Frontend Conventions Document
1. Open `docs/FRONTEND-CONVENTIONS.md`
2. **Expected:** Document exists with at least 8 `## ` section headings
3. Verify sections cover: htmx Patterns, JavaScript Module Structure, CSS Theme System, Debug Logging, Fetch Conventions, Event Cleanup, Lucide Icons, File Serving
4. Spot-check: the htmx section mentions innerHTML/outerHTML swap modes; the fetch section describes apiFetch() behavior; the CSS section mentions color-mix() pattern
5. **Expected:** All claims reference actual codebase patterns (not generic advice)

### Test 6: Zero Stray console.log Calls
1. Run: `grep -rn 'console\.log' frontend/static/js/ backend/app/templates/ --include='*.js' --include='*.html' | grep -v api-fetch.js`
2. **Expected:** Zero results — no console.log calls exist outside the debug utility implementation

### Edge Cases
- **Private browsing mode:** SemPKM.debug() should not throw errors when localStorage is unavailable (try/catch wraps the access)
- **Empty debug flag:** `localStorage.setItem('sempkm_debug', '')` should NOT enable logging (falsy check)
- **Non-empty debug flag:** `localStorage.setItem('sempkm_debug', 'verbose')` should enable logging (any truthy value)
