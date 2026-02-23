---
phase: 09-provenance-and-redirect-micro-fixes
plan: 01
subsystem: api, auth
tags: [provenance, event-sourcing, redirect, auth]

# Dependency graph
requires:
  - phase: 07-route-protection-and-provenance
    provides: performed_by_role pattern in browser/router.py, ?next= redirect in auth.js
provides:
  - Full user provenance (performed_by + performed_by_role) on all write paths (browser and API)
  - Verified ?next= redirect consistency across all auth success flows
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "All EventStore.commit() calls include performed_by_role=user.role for complete provenance"

key-files:
  created: []
  modified:
    - backend/app/commands/router.py

key-decisions:
  - "AUTH-03-cosmetic already resolved by Phase 7 Plan 01 (commit 8af1e65) -- no code change needed"

patterns-established:
  - "All user-initiated EventStore.commit() calls must include both performed_by and performed_by_role kwargs"

requirements-completed: [PROV-02-partial, AUTH-03-cosmetic]

# Metrics
duration: 1min
completed: 2026-02-23
---

# Phase 9 Plan 01: Provenance and Redirect Micro-Fixes Summary

**Added performed_by_role to API command write path and verified ?next= redirect across all auth flows**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-23T05:39:11Z
- **Completed:** 2026-02-23T05:39:56Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- API command endpoint now passes performed_by_role=user.role to EventStore.commit(), achieving full parity with browser write path
- Verified all three auth success paths (login, magic link verify, invite accept) consistently use ?next= redirect pattern
- Closed both remaining v1.0 re-audit gaps: PROV-02-partial and AUTH-03-cosmetic

## Task Commits

Each task was committed atomically:

1. **Task 1: Add performed_by_role to API command EventStore.commit()** - `a5bfae6` (feat)
2. **Task 2: Verify invite acceptance ?next= redirect is functional** - no commit (verification-only, code already correct)

## Files Created/Modified
- `backend/app/commands/router.py` - Added performed_by_role=user.role kwarg to event_store.commit() call (line 124)

## Decisions Made
- AUTH-03-cosmetic was already resolved by Phase 7 Plan 01 (commit 8af1e65) which added ?next= redirect to all auth success paths including handleInviteAccept. No code change needed -- documented as already closed.

## Deviations from Plan

None - plan executed exactly as written. Task 2 followed the "already present" verification path as anticipated by the plan.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All v1.0 gap closure work is complete
- Both PROV-02-partial and AUTH-03-cosmetic gaps are closed
- No remaining items from the v1.0 milestone audit

## Self-Check: PASSED

- FOUND: 09-01-SUMMARY.md
- FOUND: a5bfae6 (Task 1 commit)

---
*Phase: 09-provenance-and-redirect-micro-fixes*
*Completed: 2026-02-23*
