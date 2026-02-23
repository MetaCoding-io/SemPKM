---
phase: 06-user-and-team-management-for-multi-tenant-cloud-readiness
plan: 03
subsystem: auth
tags: [rbac, fastapi-depends, route-protection, event-provenance, performedBy]

# Dependency graph
requires:
  - phase: 06-user-and-team-management-for-multi-tenant-cloud-readiness
    provides: "Auth dependencies (get_current_user, require_role) and User model"
provides:
  - "RBAC enforcement on all API endpoints: owner (full), member (read+write), guest (read-only)"
  - "Event provenance: sempkm:performedBy triple in every user-initiated event"
  - "Health endpoint explicitly documented as public (no auth)"
affects: [06-04]

# Tech tracking
tech-stack:
  added: []
  patterns: [route-level-rbac, event-provenance-tracking, optional-performed-by]

key-files:
  created: []
  modified:
    - backend/app/events/models.py
    - backend/app/events/store.py
    - backend/app/commands/router.py
    - backend/app/sparql/router.py
    - backend/app/models/router.py
    - backend/app/validation/router.py
    - backend/app/health/router.py

key-decisions:
  - "EVENT_PERFORMED_BY is optional in EventStore.commit() for backward compatibility with system operations"
  - "User IRI constructed as urn:sempkm:user:{uuid} by the calling router, not by EventStore"

patterns-established:
  - "Route-level RBAC: Depends(require_role('owner', 'member')) for write, Depends(get_current_user) for read-only auth"
  - "Event provenance: performed_by=URIRef(f'urn:sempkm:user:{user.id}') passed to EventStore.commit()"
  - "Health endpoint intentionally public: no auth dependency, documented in module docstring"

requirements-completed: [RBAC-01, RBAC-02, RBAC-03, PROV-01, PROV-02]

# Metrics
duration: 4min
completed: 2026-02-22
---

# Phase 6 Plan 03: Endpoint Auth Retrofit and Event Provenance Summary

**RBAC enforcement across all API endpoints with owner/member/guest role hierarchy and sempkm:performedBy event provenance tracking**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-22T06:55:45Z
- **Completed:** 2026-02-22T06:59:49Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- EVENT_PERFORMED_BY constant and optional performed_by parameter added to EventStore.commit() for user attribution in events
- RBAC enforcement: commands require owner/member, model install/remove require owner, all read endpoints require authentication
- Health endpoint documented as intentionally public for Docker healthchecks
- Full RBAC hierarchy verified: owner (full access), member (read + write data), guest (read-only), unauthenticated (401)

## Task Commits

Each task was committed atomically:

1. **Task 1: Event provenance enrichment** - `523b316` (feat)
2. **Task 2: Route protection with auth dependencies** - `23a01a0` (feat)

## Files Created/Modified
- `backend/app/events/models.py` - Added EVENT_PERFORMED_BY constant (sempkm:performedBy)
- `backend/app/events/store.py` - Extended commit() with optional performed_by URIRef parameter
- `backend/app/commands/router.py` - Auth-protected with require_role("owner", "member"), passes user IRI to EventStore
- `backend/app/sparql/router.py` - Auth-protected with get_current_user (any authenticated role)
- `backend/app/models/router.py` - Install/remove require owner role, list requires authentication
- `backend/app/validation/router.py` - Auth-protected with get_current_user (any authenticated role)
- `backend/app/health/router.py` - Documented as intentionally public (no auth added)

## Decisions Made
- EVENT_PERFORMED_BY is optional in EventStore.commit() -- system operations (model auto-install at startup) produce events without user attribution, fulfilling the backward compatibility requirement
- User IRI is constructed as `urn:sempkm:user:{uuid}` by the calling router, not by EventStore -- keeps EventStore agnostic to user identity format

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- API container needed manual restart to pick up code changes (dev volume mount + uvicorn reload didn't trigger on file save from host). Restarted with `docker compose restart api` and all verifications passed.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All API endpoints enforce RBAC: ready for production use with authenticated sessions
- Event provenance tracking active: every user command records the actor for audit trail
- Plan 04 (invitation management endpoints) can build on the auth infrastructure

## Self-Check: PASSED

All 7 modified files verified on disk. Both task commits (523b316, 23a01a0) verified in git log.

---
*Phase: 06-user-and-team-management-for-multi-tenant-cloud-readiness*
*Completed: 2026-02-22*
