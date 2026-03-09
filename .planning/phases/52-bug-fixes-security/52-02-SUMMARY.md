---
phase: 52-bug-fixes-security
plan: 02
subsystem: api
tags: [sparql, rbac, security, fastapi, jinja2]

# Dependency graph
requires: []
provides:
  - "Role-based SPARQL access control (guest=denied, member=current-graph-only, owner=unrestricted)"
  - "check_member_query_safety() function for FROM/GRAPH clause detection"
  - "UI defense-in-depth: SPARQL Console hidden from guests in sidebar"
affects: [53-sparql-core, 54-sparql-advanced]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Inline role checks via _enforce_sparql_role() helper instead of require_role() dependency (enables per-role differentiated behavior)"
    - "Jinja2 conditional UI hiding as defense-in-depth layer behind API enforcement"

key-files:
  created: []
  modified:
    - backend/app/sparql/router.py
    - backend/app/sparql/client.py
    - backend/app/admin/router.py
    - backend/app/templates/components/_sidebar.html

key-decisions:
  - "Used inline role checks in _enforce_sparql_role() rather than require_role() dependency injection, because different roles need different behavior (guest=deny, member=restricted, owner=pass)"
  - "No workspace bottom panel changes needed -- SPARQL tab does not exist yet (CONTEXT.md reference is anticipatory for Phase 53+)"
  - "No all_graphs UI toggle exists in admin SPARQL template (Yasgui sends queries via /api/sparql POST which now has API-level enforcement)"

patterns-established:
  - "SPARQL role gating: _enforce_sparql_role() called before _execute_sparql() in both GET and POST endpoints"
  - "Member query safety: check_member_query_safety() rejects FROM/GRAPH clause attempts with 403"

requirements-completed: [SPARQL-01]

# Metrics
duration: 3min
completed: 2026-03-09
---

# Phase 52 Plan 02: SPARQL Role Gating Summary

**Three-tier SPARQL access control: guest denial (403), member current-graph restriction (no FROM/GRAPH/all_graphs), owner unrestricted access**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-09T07:19:45Z
- **Completed:** 2026-03-09T07:22:45Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Guest users now receive HTTP 403 from both GET and POST /api/sparql endpoints
- Member users can execute SPARQL queries against the current graph but are blocked from all_graphs=true, FROM clauses, and GRAPH clauses (all return 403)
- Owner users retain full unrestricted SPARQL access
- Admin SPARQL page (/admin/sparql) now requires at least member role via require_role("owner", "member")
- SPARQL Console sidebar link hidden from guest users via Jinja2 conditional

## Task Commits

Each task was committed atomically:

1. **Task 1: Add SPARQL role gating to API endpoints and query safety check** - `1734de9` (feat)
2. **Task 2: Hide SPARQL UI elements based on user role** - `54db4be` (feat)

## Files Created/Modified
- `backend/app/sparql/client.py` - Added check_member_query_safety() function that detects FROM/GRAPH clauses
- `backend/app/sparql/router.py` - Added _enforce_sparql_role() helper and calls in both GET/POST endpoints
- `backend/app/admin/router.py` - Changed admin SPARQL endpoint from get_current_user to require_role("owner", "member")
- `backend/app/templates/components/_sidebar.html` - Wrapped SPARQL Console link in {% if user.role != 'guest' %}

## Decisions Made
- Used inline role checks (_enforce_sparql_role) rather than require_role dependency injection because different roles need different behavior (guest=deny, member=restricted, owner=pass)
- No workspace bottom panel changes -- SPARQL tab does not exist yet (anticipatory for Phase 53+)
- No admin SPARQL all_graphs toggle exists in the template -- API enforcement is sufficient

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- SPARQL-01 requirement complete: three-tier access control enforced at API and UI layers
- Phase 53 (SPARQL core) can build on this foundation knowing role gating is in place
- E2E tests not run (Docker stack not active) -- should be verified when stack is next started

## Self-Check: PASSED

- All 4 modified files exist on disk
- Both task commits verified (1734de9, 54db4be)
- Python syntax validated for all 3 backend files

---
*Phase: 52-bug-fixes-security*
*Completed: 2026-03-09*
