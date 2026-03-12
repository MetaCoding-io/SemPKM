---
id: S54
parent: M001
milestone: M001
provides:
  - "SharedQueryAccess and PromotedQueryView SQLAlchemy models"
  - "Migration 008 with shared_query_access and promoted_query_views tables"
  - "Share/unshare, list-users, fork, mark-viewed API endpoints"
  - "Saved dropdown with My Queries and Shared with Me sections"
  - "Inline share picker with instant checkbox toggle"
  - "Updated badge and fork action for shared queries"
  - Promote/demote API endpoints (POST/DELETE/GET /api/sparql/saved/{id}/promote)
  - ViewSpecService.get_user_promoted_view_specs() for user-promoted views
  - ViewSpecService.get_view_spec_by_iri() extended for urn:sempkm:user-view: IRIs
  - _extract_select_var_names() for auto-detecting columns from SELECT clause
  - execute_table_query skips ?s dedup for source_model="user" specs
  - My Views nav tree section with htmx lazy load
  - Promote dialog with renderer picker and graph warning
  - Save as View button in SPARQL results info area
requires: []
affects: []
key_files: []
key_decisions:
  - "PromotedQueryView model created in same migration as SharedQueryAccess for migration efficiency"
  - "Share picker uses immediate PUT on checkbox change, no Apply button needed"
  - "include_shared=false default preserves backward compatibility for existing callers"
  - "Updated badge compares query.updated_at > access.last_viewed_at, null treated as always updated"
  - "User-promoted ViewSpecs NOT cached -- fetched from SQLite per request to avoid cache invalidation complexity"
  - "COUNT(*) for user view pagination instead of COUNT(DISTINCT ?s) since user queries have arbitrary variables"
  - "URI values in user view tables render as plain clickable links (not IRI pills) per user decision"
  - "Demote uses JS fetch+htmx refresh pattern instead of pure htmx (DELETE 204 returns no content to swap)"
patterns_established:
  - "Inline picker pattern: toggle visibility on same button click, close on re-click"
  - "Backward-compatible list endpoint: query param switches between list and object response"
  - "ViewSpec source_model='user' branch in execute_table_query skips ?s dedup and renders all rows"
  - "get_view_spec_by_iri accepts optional user_id/db params for user-view resolution"
observability_surfaces: []
drill_down_paths: []
duration: 7min
verification_result: passed
completed_at: 2026-03-10
blocker_discovered: false
---
# S54: Sparql Advanced

**# Phase 54 Plan 01: Query Sharing Summary**

## What Happened

# Phase 54 Plan 01: Query Sharing Summary

**SPARQL query sharing with SharedQueryAccess model, 6 new API endpoints, inline user picker, Shared with Me section, fork action, and Updated badge**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-10T07:05:16Z
- **Completed:** 2026-03-10T07:09:51Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- SharedQueryAccess and PromotedQueryView models with migration 008 creating both tables
- Six new API endpoints: list users, get/set shares, mark-viewed, fork, combined saved+shared listing
- Saved dropdown split into "My Queries" (with share/promote/delete) and "Shared with Me" sections
- Inline share picker fetches users and current shares, toggles sharing instantly on checkbox change
- Updated badge appears when query changed since last viewed, clears on load via mark-viewed endpoint
- Fork creates personal copy named "Copy of {original}" and refreshes dropdown

## Task Commits

Each task was committed atomically:

1. **Task 1: Data models, migration, and sharing API endpoints** - `ca9c87b` (feat)
2. **Task 2: Saved dropdown share UI, user picker, Shared with Me section, fork action** - `2eee92a` (feat)

## Files Created/Modified
- `backend/app/sparql/models.py` - Added SharedQueryAccess and PromotedQueryView models
- `backend/app/sparql/schemas.py` - Added ShareableUserOut, SharedQueryOut, ShareUpdateRequest schemas
- `backend/app/sparql/router.py` - Added 6 new endpoints for sharing workflow
- `backend/migrations/versions/008_sharing_promotion.py` - Migration creating shared_query_access and promoted_query_views tables
- `backend/migrations/env.py` - Updated model imports for autogenerate
- `backend/app/templates/browser/sparql_panel.html` - Added data-current-user-id attribute
- `frontend/static/js/sparql-console.js` - Extended loadSaved(), added toggleSharePicker(), forkSharedQuery()
- `frontend/static/css/workspace.css` - Added sharing UI styles (section headers, picker, badges)

## Decisions Made
- PromotedQueryView model created in same migration 008 as SharedQueryAccess to avoid an extra migration in Plan 54-02
- Share picker uses immediate PUT on each checkbox change rather than a separate Apply button, for instant feedback
- include_shared=false default on GET /sparql/saved preserves backward compatibility
- Updated badge logic: null last_viewed_at treated as always updated (new shares always show badge)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Docker rebuild required for migration visibility**
- **Found during:** Task 1
- **Issue:** Migration 008 file was not visible inside Docker container because migrations/ directory is not volume-mounted
- **Fix:** Ran `docker compose build api && docker compose up -d api` to rebuild and restart the API container
- **Files modified:** None (infrastructure fix)
- **Verification:** `alembic current` shows 008 (head)
- **Committed in:** ca9c87b (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary for migration execution. No scope creep.

## Issues Encountered
None beyond the Docker rebuild for migration visibility.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- SharedQueryAccess model ready for use
- PromotedQueryView model ready for Plan 54-02 (promoted views/dashboard pinning)
- Share picker pattern established for reuse

## Self-Check: PASSED

All 8 files verified present. Both task commits (ca9c87b, 2eee92a) verified in git log.

---
*Phase: 54-sparql-advanced*
*Completed: 2026-03-10*

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
