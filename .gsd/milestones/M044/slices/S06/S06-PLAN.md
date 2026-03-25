# S06: Console Cleanup & Convention Documentation

**Goal:** Browser console is clean in production (zero console.log calls); debug logging available via localStorage flag; htmx and frontend conventions documented.
**Demo:** After this: browser console is clean in production; htmx conventions are documented; debug logging available via flag

## Must-Haves

- `grep -rn 'console\.log' frontend/static/js/ backend/app/templates/ --include='*.js' --include='*.html'` returns zero results
- `SemPKM.debug(tag, ...args)` function exists in api-fetch.js, gated by `localStorage.getItem('sempkm_debug')`
- `docs/FRONTEND-CONVENTIONS.md` exists with sections covering: htmx patterns, JS module structure, CSS theme system, debug logging, fetch conventions, event cleanup
- console.warn and console.error calls remain unchanged (they are legitimate operational signals)

## Proof Level

- This slice proves: Contract — verified by grep assertions (no runtime required)

## Integration Closure

No upstream surfaces consumed. No new wiring — purely additive debug utility and documentation. Nothing remains for milestone integration beyond S07 E2E regression suite.

## Verification

- SemPKM.debug() adds opt-in development tracing gated by localStorage flag. No production observability change.

## Tasks

- [x] **T01: Add SemPKM.debug() utility and migrate all console.log calls** `est:45m`
  Create a SemPKM.debug(tag, ...args) function in api-fetch.js gated by localStorage flag, then replace all 37 console.log calls across 14 files with SemPKM.debug() calls. Keep console.warn/error untouched.
  - Files: `frontend/static/js/api-fetch.js`, `frontend/static/js/copilot.js`, `frontend/static/js/calendar.js`, `frontend/static/js/workspace.js`, `frontend/static/js/graph.js`, `frontend/static/js/tutorials.js`, `frontend/static/js/bmc.js`, `frontend/static/js/decision-matrix.js`, `frontend/static/js/kanban.js`, `frontend/static/js/okr.js`, `frontend/static/js/quadrant.js`, `frontend/static/js/recurrence-editor.js`, `backend/app/templates/browser/timeline_view.html`, `backend/app/templates/browser/workspace.html`
  - Verify: grep -rn 'console\.log' frontend/static/js/ backend/app/templates/ --include='*.js' --include='*.html' | grep -v node_modules | wc -l  # must be 0

- [x] **T02: Write frontend conventions documentation** `est:30m`
  Create docs/FRONTEND-CONVENTIONS.md covering the six convention areas established by M044: htmx patterns, JS module structure, CSS theme system, debug logging, fetch conventions, and event cleanup. Developer-facing reference documenting the codebase's frontend patterns as they exist post-M044.
  - Files: `docs/FRONTEND-CONVENTIONS.md`
  - Verify: test -f docs/FRONTEND-CONVENTIONS.md && grep -c '^## ' docs/FRONTEND-CONVENTIONS.md  # must be >= 6 sections

## Files Likely Touched

- frontend/static/js/api-fetch.js
- frontend/static/js/copilot.js
- frontend/static/js/calendar.js
- frontend/static/js/workspace.js
- frontend/static/js/graph.js
- frontend/static/js/tutorials.js
- frontend/static/js/bmc.js
- frontend/static/js/decision-matrix.js
- frontend/static/js/kanban.js
- frontend/static/js/okr.js
- frontend/static/js/quadrant.js
- frontend/static/js/recurrence-editor.js
- backend/app/templates/browser/timeline_view.html
- backend/app/templates/browser/workspace.html
- docs/FRONTEND-CONVENTIONS.md
