---
phase: 54-sparql-advanced
plan: 01
subsystem: api, ui
tags: [sparql, sharing, collaboration, sqlalchemy, alembic, lucide]

# Dependency graph
requires:
  - phase: 53-sparql-power-user
    provides: "SavedSparqlQuery model, saved query CRUD, SPARQL console UI"
provides:
  - "SharedQueryAccess and PromotedQueryView SQLAlchemy models"
  - "Migration 008 with shared_query_access and promoted_query_views tables"
  - "Share/unshare, list-users, fork, mark-viewed API endpoints"
  - "Saved dropdown with My Queries and Shared with Me sections"
  - "Inline share picker with instant checkbox toggle"
  - "Updated badge and fork action for shared queries"
affects: [54-02-promoted-views]

# Tech tracking
tech-stack:
  added: []
  patterns: ["share picker inline UI pattern", "include_shared backward-compatible query param"]

key-files:
  created:
    - "backend/migrations/versions/008_sharing_promotion.py"
  modified:
    - "backend/app/sparql/models.py"
    - "backend/app/sparql/schemas.py"
    - "backend/app/sparql/router.py"
    - "backend/migrations/env.py"
    - "backend/app/templates/browser/sparql_panel.html"
    - "frontend/static/js/sparql-console.js"
    - "frontend/static/css/workspace.css"

key-decisions:
  - "PromotedQueryView model created in same migration as SharedQueryAccess for migration efficiency"
  - "Share picker uses immediate PUT on checkbox change, no Apply button needed"
  - "include_shared=false default preserves backward compatibility for existing callers"
  - "Updated badge compares query.updated_at > access.last_viewed_at, null treated as always updated"

patterns-established:
  - "Inline picker pattern: toggle visibility on same button click, close on re-click"
  - "Backward-compatible list endpoint: query param switches between list and object response"

requirements-completed: [SPARQL-04]

# Metrics
duration: 4min
completed: 2026-03-10
---

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
