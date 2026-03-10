---
phase: 56-vfs-mountspec
plan: 01
subsystem: api
tags: [rdf, sparql, webdav, vfs, mount, crud, fastapi]

# Dependency graph
requires: []
provides:
  - MountSpec RDF vocabulary with all predicates for declarative directory structures
  - SyncMountService for CRUD on mount definitions (sync for WebDAV WSGI threads)
  - REST API endpoints for mount CRUD, preview, and SHACL property listing
  - Cache invalidation for mount changes propagating to WebDAV provider
affects: [56-02, 56-03, 56-04, 56-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dual sync/async SPARQL patterns: SyncMountService for WSGI, async helpers in mount_router for FastAPI"
    - "RDF CRUD via named graph: INSERT DATA / DELETE WHERE against urn:sempkm:mounts"
    - "Path validation with model ID conflict detection"

key-files:
  created:
    - backend/app/vfs/mount_service.py
    - backend/app/vfs/mount_router.py
  modified:
    - backend/app/vfs/cache.py
    - backend/app/triplestore/sync_client.py
    - backend/app/main.py

key-decisions:
  - "Async mount_router uses inline SPARQL (same patterns as SyncMountService) rather than wrapping sync service, avoiding sync/async bridge complexity"
  - "Preview endpoint caps at 100 objects per folder and 50 directory groups for responsive UI"
  - "SyncTriplestoreClient extended with update() method mirroring async client pattern"

patterns-established:
  - "Mount path validation: regex + reserved names + model ID conflicts + uniqueness"
  - "RDF CRUD pattern: delete-all-triples-then-reinsert for updates on named resources"

requirements-completed: [VFS-01]

# Metrics
duration: 4min
completed: 2026-03-10
---

# Phase 56 Plan 01: MountSpec Vocabulary and CRUD Summary

**MountSpec RDF vocabulary with sync CRUD service, 6 REST API endpoints for mount management, preview, and SHACL property listing**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-10T06:42:51Z
- **Completed:** 2026-03-10T06:47:44Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- MountSpec RDF vocabulary defined with 10 predicate constants under urn:sempkm: namespace
- SyncMountService with full CRUD: list (visibility-filtered), get by ID/prefix, create, update, delete
- REST API with 6 endpoints: GET/POST/PUT/DELETE mounts, POST preview, GET properties
- Path validation prevents model ID conflicts, reserved name collisions, and duplicate paths
- Preview endpoint generates directory tree structure for all 5 strategies (flat, by-type, by-date, by-tag, by-property)
- Properties endpoint extracts SHACL shape properties for strategy field dropdowns

## Task Commits

Each task was committed atomically:

1. **Task 1: Create MountService with RDF vocabulary and sync CRUD** - `e20d5b3` (feat)
2. **Task 2: Create mount CRUD and preview REST API endpoints** - `0123421` (feat)

## Files Created/Modified
- `backend/app/vfs/mount_service.py` - MountDefinition dataclass, SyncMountService, RDF vocabulary constants, path validation
- `backend/app/vfs/mount_router.py` - FastAPI router with 6 endpoints: list, create, update, delete, preview, properties
- `backend/app/vfs/cache.py` - Added clear_mount_cache() for post-CRUD cache invalidation
- `backend/app/triplestore/sync_client.py` - Added update() method for SPARQL INSERT/DELETE
- `backend/app/main.py` - Registered vfs_mount_router alongside existing VFS browser router

## Decisions Made
- Used async helpers in mount_router.py with the same SPARQL patterns as SyncMountService rather than wrapping the sync service, keeping the two contexts cleanly separated and avoiding sync/async bridge complexity
- Preview endpoint caps at 50 directory groups and 100 objects per folder for responsive UI
- Extended SyncTriplestoreClient with update() rather than creating a separate write client

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added SyncTriplestoreClient.update() method**
- **Found during:** Task 1 (MountService CRUD)
- **Issue:** SyncTriplestoreClient only had query() but MountService needs SPARQL UPDATE for INSERT/DELETE operations
- **Fix:** Added update() method mirroring the async TriplestoreClient.update() pattern (POST to /statements endpoint)
- **Files modified:** backend/app/triplestore/sync_client.py
- **Verification:** Docker import succeeds, method signature matches async client
- **Committed in:** e20d5b3 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential for SPARQL UPDATE operations. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Mount definitions can be created and managed via REST API
- SyncMountService ready for use by VFS provider dispatch (Plan 56-02/03)
- Preview endpoint ready for settings UI consumption (Plan 56-05)
- Properties endpoint ready for strategy field dropdown population

## Self-Check: PASSED

All files exist, all commits verified.

---
*Phase: 56-vfs-mountspec*
*Completed: 2026-03-10*
