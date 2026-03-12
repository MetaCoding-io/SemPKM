---
id: S56
parent: M001
milestone: M001
provides:
  - MountSpec RDF vocabulary with all predicates for declarative directory structures
  - SyncMountService for CRUD on mount definitions (sync for WebDAV WSGI threads)
  - REST API endpoints for mount CRUD, preview, and SHACL property listing
  - Cache invalidation for mount changes propagating to WebDAV provider
  - MountRootCollection and StrategyFolderCollection for 5 directory strategies
  - DirectoryStrategy enum and SPARQL query builders per strategy
  - MountedResourceFile with SHACL-aware frontmatter and property write-back
  - Provider mount prefix dispatch routing
  - Property write-back via object.patch through event store
  - Mount management UI form in VFS settings with create/edit/delete
  - Strategy-specific dynamic fields for 5 mount strategies
  - Live directory preview from preview endpoint
  - Active mounts list with inline edit/delete actions
  - Custom SPARQL scope integration via saved queries dropdown
requires: []
affects: []
key_files: []
key_decisions:
  - "Async mount_router uses inline SPARQL (same patterns as SyncMountService) rather than wrapping sync service, avoiding sync/async bridge complexity"
  - "Preview endpoint caps at 100 objects per folder and 50 directory groups for responsive UI"
  - "SyncTriplestoreClient extended with update() method mirroring async client pattern"
  - "ETag derived from object IRI not content hash so duplicate files in multi-folder mounts share the same ETag"
  - "SHACL property shapes cached 5 minutes since shapes only change on model install"
  - "Object references rendered as {label, iri} dict in frontmatter for human-readable editing"
  - "By-date strategy uses two-level Year/Month hierarchy with MM-MonthName folder format"
  - "Uncategorized objects captured in _uncategorized folder via FILTER NOT EXISTS"
  - "Mount JS in separate IIFE after main workspace IIFE; functions exposed via window for inline onclick handlers"
  - "Scope dropdown uses query: prefix for saved query IDs to distinguish from special values (all, custom)"
  - "Auto-slug from mount name generates path prefix on blur only when path field is empty"
patterns_established:
  - "Mount path validation: regex + reserved names + model ID conflicts + uniqueness"
  - "RDF CRUD pattern: delete-all-triples-then-reinsert for updates on named resources"
  - "Strategy query builder pattern: separate SPARQL functions per strategy with scope filter parameter"
  - "Mount dispatch pattern: provider checks mount prefix before falling through to model hierarchy"
  - "_build_file_map_from_bindings: shared slug deduplication for mount file listings"
  - "VFS settings form pattern: inline form with fetch() CRUD, error display in mount-form-error div, list rendering via renderMountList"
observability_surfaces: []
drill_down_paths: []
duration: 3min
verification_result: passed
completed_at: 2026-03-10
blocker_discovered: false
---
# S56: Vfs Mountspec

**# Phase 56 Plan 01: MountSpec Vocabulary and CRUD Summary**

## What Happened

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

# Phase 56 Plan 02: Strategy Collections and Mount Dispatch Summary

**WebDAV mount directory hierarchy with 5 SPARQL-driven strategies, SHACL-aware frontmatter rendering, and property write-back through object.patch**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-10T06:51:10Z
- **Completed:** 2026-03-10T06:57:03Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- All 5 directory strategies (flat, by-type, by-date, by-tag, by-property) produce SPARQL-driven folder listings
- MountedResourceFile renders frontmatter from SHACL shapes with human-readable property names
- Property write-back diffs old vs new frontmatter and commits changes via object.patch
- Provider dispatches mount paths to correct strategy collections with model hierarchy fallthrough
- By-date uses Year/Month hierarchy, _uncategorized captures objects missing grouping property
- Multi-valued properties produce files in multiple folders with shared IRI-based ETags

## Task Commits

Each task was committed atomically:

1. **Task 1: Strategy query builders, mount collections, and provider dispatch** - `a55014a` (feat)
2. **Task 2: MountedResourceFile with SHACL frontmatter and property write-back** - `919f2b5` (feat)

## Files Created/Modified
- `backend/app/vfs/strategies.py` - DirectoryStrategy enum and SPARQL query builders for all 5 strategies plus _uncategorized
- `backend/app/vfs/mount_collections.py` - MountRootCollection (dispatches by strategy) and StrategyFolderCollection (type/date/tag/property folders)
- `backend/app/vfs/mount_resource.py` - MountedResourceFile with SHACL shape cache, frontmatter rendering, and property write-back
- `backend/app/vfs/provider.py` - Extended with mount prefix dispatch in _resolve_mount_path before model hierarchy
- `backend/app/vfs/collections.py` - RootCollection lists mount directories alongside models, get_member returns MountRootCollection
- `backend/app/vfs/write.py` - Added write_properties_via_event_store and _frontmatter_to_rdf_properties diff helper

## Decisions Made
- ETag derived from object IRI (not content hash) so all paths to the same object share the same ETag for cross-path concurrency control
- SHACL property shapes cached with 5-minute TTL since shapes only change on model install
- Object references in frontmatter use {label, iri} dict format for human-readable editing with IRI preservation
- By-date strategy uses two-level hierarchy with year folders at mount root and MM-MonthName folders within (e.g., "01-January")
- _uncategorized folder uses FILTER NOT EXISTS to capture objects missing the grouping property
- Frontmatter diff maps sh:name keys back to predicate IRIs for precise property patching

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Mount collections ready for end-to-end WebDAV browsing (Plan 56-03 integration testing)
- Property write-back ready for testing via WebDAV PUT
- Settings UI can consume mount management endpoints (Plan 56-05)

## Self-Check: PASSED

All files exist, all commits verified.

# Phase 56 Plan 03: Mount Management UI Summary

**Settings page mount form with 5-strategy dropdown, dynamic fields, live preview, SPARQL scope integration, and CRUD list management**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-10T06:51:32Z
- **Completed:** 2026-03-10T06:54:44Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Mount management section added to VFS settings below existing API token management
- Form supports all 5 strategies (flat, by-type, by-date, by-tag, by-property) with dynamic field toggling
- Scope dropdown populated from saved SPARQL queries API with "Custom SPARQL..." inline entry option
- Live directory preview calls preview endpoint and renders tree structure with file counts
- Active mounts list with Edit (pre-fills form) and Delete (confirm dialog) actions
- Auto-slug generation: mount name auto-populates path prefix on blur

## Task Commits

Each task was committed atomically:

1. **Task 1: Add mount management HTML form and CSS** - `edf3ca6` (feat)
2. **Task 2: Add mount form JavaScript for dynamic fields, preview, and CRUD** - `a405923` (feat)

## Files Created/Modified
- `backend/app/templates/browser/_vfs_settings.html` - Extended with mount form, strategy-specific fields, preview area, and active mounts list
- `frontend/static/css/workspace.css` - Mount management styles: form rows, preview tree, list items, btn-secondary-sm class
- `frontend/static/js/workspace.js` - Mount management IIFE with 10 functions: init, strategy toggle, scope toggle, CRUD, preview, edit/cancel, delete

## Decisions Made
- Placed mount JS in a separate IIFE after the main workspace IIFE rather than inside it, since inline onclick handlers require global scope (exposed via window assignments)
- Used `query:` prefix for saved query option values in scope dropdown to distinguish from special values (all, custom)
- Auto-slug on name blur only fires when path is empty, preventing overwrite of manually entered paths
- Added btn-secondary-sm class to workspace.css for mount list edit buttons (did not exist previously)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Mount management UI is complete and ready for end-to-end testing
- Preview and CRUD calls target endpoints created in Plan 56-01
- Saved queries scope integration ready (depends on Phase 53 queries existing)

## Self-Check: PASSED

All files exist, all commits verified.

---
*Phase: 56-vfs-mountspec*
*Completed: 2026-03-10*
