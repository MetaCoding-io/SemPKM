---
phase: 08-integration-bug-fixes
plan: 01
subsystem: api
tags: [webhooks, validation, shacl, callback, url-consistency]

# Dependency graph
requires:
  - phase: 02-semantic-services
    provides: "AsyncValidationQueue and ValidationService"
  - phase: 04-admin-shell-and-object-creation
    provides: "WebhookService with fire-and-forget dispatch"
  - phase: 05-data-browsing-and-visualization
    provides: "Views router with /card/ endpoint and workspace.js URL routing"
provides:
  - "Validation completion callback mechanism on AsyncValidationQueue"
  - "validation.completed webhook dispatch wired in main.py lifespan"
  - "Verified cards view URL chain consistency (model -> router -> JS)"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Completion callback pattern: queue fires on_complete after processing for decoupled integration"

key-files:
  created: []
  modified:
    - "backend/app/validation/queue.py"
    - "backend/app/main.py"
    - "backend/app/commands/router.py"

key-decisions:
  - "on_complete callback is fire-and-forget (exception logged, never propagated) matching existing webhook dispatch semantics"
  - "webhook_service creation reordered before validation_queue in lifespan for dependency ordering"

patterns-established:
  - "Completion callback pattern: AsyncValidationQueue accepts optional on_complete callable for post-validation hooks"

requirements-completed: [ADMN-03, VIEW-02]

# Metrics
duration: 2min
completed: 2026-02-22
---

# Phase 8 Plan 1: Integration Bug Fixes Summary

**Validation.completed webhook dispatch wired via AsyncValidationQueue on_complete callback; cards view URL chain verified consistent**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-23T04:57:43Z
- **Completed:** 2026-02-23T04:59:22Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- AsyncValidationQueue now accepts an on_complete callback that fires after each validation run with report summary, event IRI, and timestamp
- main.py wires a callback that dispatches validation.completed webhooks with conforms status, violation count, and warning count
- Removed stale TODO comment in commands/router.py that documented the missing callback mechanism
- Verified the entire cards view URL chain is consistent: model data uses "card" (singular), router exposes /card/, workspace.js requests /card/, and view_toolbar.html switchViewType uses rendererType "card"

## Task Commits

Each task was committed atomically:

1. **Task 1: Add completion callback to AsyncValidationQueue and wire webhook dispatch** - `1ed6fca` (feat)
2. **Task 2: Verify cards view URL consistency across codebase** - verification only, no code changes needed

## Files Created/Modified
- `backend/app/validation/queue.py` - Added on_complete callback parameter, stored as _on_complete, invoked after report caching in _worker()
- `backend/app/main.py` - Reordered webhook_service creation before validation_queue, defined on_validation_complete callback, passed to queue constructor
- `backend/app/commands/router.py` - Removed 4-line TODO comment block about validation.completed webhook

## Decisions Made
- on_complete callback uses fire-and-forget semantics (exception logged via logger.warning, never propagated) to match existing webhook dispatch patterns throughout the codebase
- webhook_service creation moved above validation_queue in lifespan to satisfy dependency ordering

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All v1.0 integration gaps from the milestone audit are now closed
- ADMN-03 (validation.completed webhooks) and VIEW-02 (cards view URL) both verified complete
- No further phases planned

## Self-Check: PASSED

- All 3 modified files exist on disk
- Task 1 commit `1ed6fca` verified in git log
- SUMMARY.md created at expected path

---
*Phase: 08-integration-bug-fixes*
*Completed: 2026-02-22*
