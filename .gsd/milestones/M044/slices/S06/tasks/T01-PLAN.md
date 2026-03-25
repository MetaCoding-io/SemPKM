---
estimated_steps: 31
estimated_files: 14
skills_used: []
---

# T01: Add SemPKM.debug() utility and migrate all console.log calls

Create a `SemPKM.debug(tag, ...args)` function in `api-fetch.js` gated by a localStorage flag, then mechanically replace all 37 `console.log` calls across 14 files with `SemPKM.debug()` calls. Keep all `console.warn` and `console.error` calls untouched — they are legitimate operational signals.

The debug utility is simple: check `localStorage.getItem('sempkm_debug')` and only call `console.log` if truthy. This means zero console output in production by default, but developers can enable verbose tracing with `localStorage.setItem('sempkm_debug', '1')`.

**Inventory of 37 console.log calls to migrate:**

JS files (32 calls across 11 files):
- `copilot.js` — 10 calls (tag: 'copilot')
- `calendar.js` — 7 calls (tag: 'calendar')
- `workspace.js` — 5 calls (tags: 'SemPKM', 'scope')
- `graph.js` — 2 calls (tag: 'graph')
- `tutorials.js` — 2 calls (tag: 'SemPKM')
- `bmc.js` — 1 call (tag: 'bmc')
- `decision-matrix.js` — 1 call (tag: 'decision-matrix')
- `kanban.js` — 1 call (tag: 'kanban')
- `okr.js` — 1 call (tag: 'okr')
- `quadrant.js` — 1 call (tag: 'quadrant')
- `recurrence-editor.js` — 1 call (tag: 'recurrence-editor')

Template inline scripts (5 calls across 2 files):
- `timeline_view.html` — 4 calls (tag: 'timeline')
- `workspace.html` — 1 call (tag: 'SemPKM')

**Migration pattern:**
```javascript
// Before:
console.log('[calendar] rendered with', count, 'events');
// After:
SemPKM.debug('calendar', 'rendered with', count, 'events');

// In templates (inline scripts):
// Before:
console.log('[timeline] no tasks to render');
// After:
SemPKM.debug('timeline', 'no tasks to render');
```

Note: The existing `console.debug(...)` call in `workspace.js:2065` is fine — `console.debug` doesn't render in production Chrome (requires Verbose log level). Leave it unchanged.

## Inputs

- `frontend/static/js/api-fetch.js`
- `frontend/static/js/copilot.js`
- `frontend/static/js/calendar.js`
- `frontend/static/js/workspace.js`
- `frontend/static/js/graph.js`
- `frontend/static/js/tutorials.js`
- `frontend/static/js/bmc.js`
- `frontend/static/js/decision-matrix.js`
- `frontend/static/js/kanban.js`
- `frontend/static/js/okr.js`
- `frontend/static/js/quadrant.js`
- `frontend/static/js/recurrence-editor.js`
- `backend/app/templates/browser/timeline_view.html`
- `backend/app/templates/browser/workspace.html`

## Expected Output

- `frontend/static/js/api-fetch.js`
- `frontend/static/js/copilot.js`
- `frontend/static/js/calendar.js`
- `frontend/static/js/workspace.js`
- `frontend/static/js/graph.js`
- `frontend/static/js/tutorials.js`
- `frontend/static/js/bmc.js`
- `frontend/static/js/decision-matrix.js`
- `frontend/static/js/kanban.js`
- `frontend/static/js/okr.js`
- `frontend/static/js/quadrant.js`
- `frontend/static/js/recurrence-editor.js`
- `backend/app/templates/browser/timeline_view.html`
- `backend/app/templates/browser/workspace.html`

## Verification

grep -rn 'console\.log' frontend/static/js/ backend/app/templates/ --include='*.js' --include='*.html' | grep -v node_modules | wc -l  # must be 0
