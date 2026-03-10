---
phase: 54-sparql-advanced
plan: 02
subsystem: api, ui
tags: [sparql, viewspec, promotion, nav-tree, htmx, dialog]

requires:
  - phase: 54-01
    provides: PromotedQueryView model, SavedSparqlQuery model, sparql-console.js saved dropdown with promote button placeholder

provides:
  - Promote/demote API endpoints (POST/DELETE/GET /api/sparql/saved/{id}/promote)
  - ViewSpecService.get_user_promoted_view_specs() for user-promoted views
  - ViewSpecService.get_view_spec_by_iri() extended for urn:sempkm:user-view: IRIs
  - _extract_select_var_names() for auto-detecting columns from SELECT clause
  - execute_table_query skips ?s dedup for source_model="user" specs
  - My Views nav tree section with htmx lazy load
  - Promote dialog with renderer picker and graph warning
  - Save as View button in SPARQL results info area

affects: [views, browser, sparql]

tech-stack:
  added: []
  patterns:
    - "User-promoted views as ViewSpec with source_model='user' -- NOT cached, fetched from SQLite per request"
    - "urn:sempkm:user-view:{uuid} IRI scheme for promoted view specs"
    - "_extract_select_var_names regex for SPARQL SELECT variable extraction including aliases"

key-files:
  created:
    - backend/app/templates/browser/my_views.html
    - backend/app/templates/browser/promote_dialog.html
  modified:
    - backend/app/sparql/router.py
    - backend/app/views/service.py
    - backend/app/views/router.py
    - backend/app/browser/router.py
    - backend/app/templates/browser/workspace.html
    - backend/app/templates/browser/table_view.html
    - frontend/static/js/sparql-console.js
    - frontend/static/css/workspace.css

key-decisions:
  - "User-promoted ViewSpecs NOT cached -- fetched from SQLite per request to avoid cache invalidation complexity"
  - "COUNT(*) for user view pagination instead of COUNT(DISTINCT ?s) since user queries have arbitrary variables"
  - "URI values in user view tables render as plain clickable links (not IRI pills) per user decision"
  - "Demote uses JS fetch+htmx refresh pattern instead of pure htmx (DELETE 204 returns no content to swap)"

patterns-established:
  - "ViewSpec source_model='user' branch in execute_table_query skips ?s dedup and renders all rows"
  - "get_view_spec_by_iri accepts optional user_id/db params for user-view resolution"

requirements-completed: [SPARQL-07]

duration: 7min
completed: 2026-03-10
---

# Phase 54 Plan 02: View Promotion Summary

**SPARQL query promotion to nav tree views with auto-detected columns, renderer picker, and ViewSpec integration**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-10T07:13:29Z
- **Completed:** 2026-03-10T07:20:29Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Promote/demote endpoints with owner-only access and 409 conflict detection
- ViewSpecService extended to resolve user-view URIs from SQLite and auto-detect SELECT variables
- execute_table_query handles promoted views without ?s-based deduplication
- My Views nav tree section shows promoted views with renderer-specific icons and demote action
- Promote dialog with name field, renderer picker (table/cards/graph), and graph variable warning
- "Save as View" button appears in results info area when a saved query is executed

## Task Commits

Each task was committed atomically:

1. **Task 1: Promote/demote endpoints, ViewSpecService integration, SELECT variable extraction** - `b26be82` (feat)
2. **Task 2: Promote UI in dropdown/results, My Views nav tree section, demote action, CSS** - `e37a85e` (feat)

## Files Created/Modified
- `backend/app/sparql/router.py` - Added promote/demote/promotion endpoints
- `backend/app/views/service.py` - Added _extract_select_var_names, get_user_promoted_view_specs, extended get_view_spec_by_iri, modified execute_table_query for user views
- `backend/app/views/router.py` - Pass user_id/db to view spec resolution, handle user view context
- `backend/app/browser/router.py` - Added GET /browser/my-views endpoint
- `backend/app/templates/browser/my_views.html` - New: promoted view tree entries with demote action
- `backend/app/templates/browser/promote_dialog.html` - New: promotion dialog with renderer picker
- `backend/app/templates/browser/workspace.html` - Added My Views section, included promote dialog
- `backend/app/templates/browser/table_view.html` - Render URI values as plain links for user views
- `frontend/static/js/sparql-console.js` - Promote dialog JS, currentSavedQueryId tracking, Save as View button
- `frontend/static/css/workspace.css` - My Views tree, promote dialog, save-as-view button styles

## Decisions Made
- User-promoted ViewSpecs are NOT cached (fetched from SQLite per request) to avoid cache invalidation complexity on promote/demote
- User view count query uses COUNT(*) instead of COUNT(DISTINCT ?s) since user queries have arbitrary variables
- URI values in user view tables render as plain clickable links per user decision from CONTEXT.md
- Demote action uses JS fetch + htmx refresh pattern since DELETE 204 returns no swappable content

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- View promotion feature complete -- promoted queries render via existing ViewSpec infrastructure
- All Phase 54 plans complete (54-01 sharing + 54-02 promotion)
- Ready for verification via /gsd:verify-work

---
*Phase: 54-sparql-advanced*
*Completed: 2026-03-10*
