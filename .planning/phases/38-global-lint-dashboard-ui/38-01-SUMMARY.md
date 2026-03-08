---
phase: 38-global-lint-dashboard-ui
plan: 01
subsystem: ui
tags: [htmx, shacl, lint, sparql, jinja2]

requires:
  - phase: 37-shacl-lint-engine
    provides: LintService with structured results, SSE broadcast
provides:
  - Global lint dashboard htmx partial with filter/sort/pagination
  - GET /browser/lint-dashboard endpoint
  - Extended /api/lint/results with search and sort params
  - LINT tab registered in workspace bottom panel
affects: [38-02-PLAN]

tech-stack:
  added: []
  patterns: [htmx lazy-load panel via hx-trigger revealed, hx-include filter aggregation]

key-files:
  created:
    - backend/app/templates/browser/lint_dashboard.html
  modified:
    - backend/app/lint/router.py
    - backend/app/lint/service.py
    - backend/app/browser/router.py
    - backend/app/templates/browser/workspace.html
    - frontend/static/css/workspace.css

key-decisions:
  - "Lazy-load lint dashboard via hx-trigger=revealed instead of server-side include to avoid adding lint context to workspace route"
  - "SPARQL search filter uses CONTAINS(LCASE()) across message, focusNode IRI, and path for broad keyword matching"
  - "Sort order validated against allowlist to prevent SPARQL injection"

patterns-established:
  - "Bottom panel lazy-load: use hx-trigger=revealed on panel pane div pointing to dedicated browser endpoint"
  - "Filter aggregation: hx-include with class prefix wildcard for multi-control filtering"

requirements-completed: [LINT-04, LINT-05, LINT-06, LINT-07]

duration: 5min
completed: 2026-03-05
---

# Phase 38 Plan 01: Global Lint Dashboard UI Summary

**Server-rendered lint dashboard with severity/type/keyword filters, sortable result table, and pagination in workspace bottom panel**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-05T04:02:09Z
- **Completed:** 2026-03-05T04:07:13Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Extended lint API with search (keyword across message/IRI/path) and sort (severity/object/path) params
- Created full lint dashboard template with summary bar, filter toolbar, result table, and pagination
- Registered LINT tab in workspace bottom panel with lazy-loading via htmx

## Task Commits

Each task was committed atomically:

1. **Task 1: Add search and sort params to lint API + browser endpoint** - `ce627c7` (feat)
2. **Task 2: Create lint dashboard template and register tab in workspace** - `02fde97` (feat)

## Files Created/Modified
- `backend/app/lint/router.py` - Added search and sort query params to GET /api/lint/results
- `backend/app/lint/service.py` - SPARQL search filter and dynamic ORDER BY with allowlist
- `backend/app/browser/router.py` - New GET /browser/lint-dashboard endpoint
- `backend/app/templates/browser/lint_dashboard.html` - Full dashboard partial with filters, table, pagination
- `backend/app/templates/browser/workspace.html` - LINT tab button and lazy-loaded pane
- `frontend/static/css/workspace.css` - Dashboard layout, severity borders, badges, pagination styles

## Decisions Made
- Used lazy-loading (hx-trigger="revealed") instead of server-side include to avoid coupling lint context to the workspace route
- SPARQL search uses CONTAINS(LCASE()) across message, STR(focusNode), and STR(path) for broad matching
- Sort validated against strict allowlist (severity, object, path) to prevent injection

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Changed server-side include to htmx lazy-load**
- **Found during:** Task 2 (Template registration in workspace)
- **Issue:** Plan specified `{% include 'browser/lint_dashboard.html' %}` but workspace route does not provide lint context variables (results, status, types), which would cause a Jinja2 UndefinedError
- **Fix:** Changed to `hx-get="/browser/lint-dashboard" hx-trigger="revealed"` on the panel pane div, matching the inference panel lazy-load pattern
- **Files modified:** backend/app/templates/browser/workspace.html
- **Verification:** Workspace loads without error, LINT tab content loads on reveal
- **Committed in:** 02fde97 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential fix to prevent runtime template error. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Dashboard UI complete, ready for Plan 02 (JS wiring for SSE live updates, command palette integration)
- Badge span element pre-placed for Plan 02 JS to populate

---
*Phase: 38-global-lint-dashboard-ui*
*Completed: 2026-03-05*
