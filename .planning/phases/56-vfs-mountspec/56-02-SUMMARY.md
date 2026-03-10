---
phase: 56-vfs-mountspec
plan: 02
subsystem: api
tags: [webdav, vfs, mount, sparql, shacl, frontmatter, wsgidav]

# Dependency graph
requires:
  - phase: 56-01
    provides: MountSpec RDF vocabulary, SyncMountService CRUD, mount REST API
provides:
  - MountRootCollection and StrategyFolderCollection for 5 directory strategies
  - DirectoryStrategy enum and SPARQL query builders per strategy
  - MountedResourceFile with SHACL-aware frontmatter and property write-back
  - Provider mount prefix dispatch routing
  - Property write-back via object.patch through event store
affects: [56-03, 56-04, 56-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SHACL shape cache with TTLCache(ttl=300) for property metadata in sync VFS context"
    - "ETag from object IRI (not content hash) for cross-path concurrency on multi-folder objects"
    - "Frontmatter diff with predicate IRI mapping via sh:name reverse lookup"
    - "Strategy-specific SPARQL query builders with scope filter injection"

key-files:
  created:
    - backend/app/vfs/strategies.py
    - backend/app/vfs/mount_collections.py
    - backend/app/vfs/mount_resource.py
  modified:
    - backend/app/vfs/provider.py
    - backend/app/vfs/collections.py
    - backend/app/vfs/write.py

key-decisions:
  - "ETag derived from object IRI not content hash so duplicate files in multi-folder mounts share the same ETag"
  - "SHACL property shapes cached 5 minutes since shapes only change on model install"
  - "Object references rendered as {label, iri} dict in frontmatter for human-readable editing"
  - "By-date strategy uses two-level Year/Month hierarchy with MM-MonthName folder format"
  - "Uncategorized objects captured in _uncategorized folder via FILTER NOT EXISTS"

patterns-established:
  - "Strategy query builder pattern: separate SPARQL functions per strategy with scope filter parameter"
  - "Mount dispatch pattern: provider checks mount prefix before falling through to model hierarchy"
  - "_build_file_map_from_bindings: shared slug deduplication for mount file listings"

requirements-completed: [VFS-02, VFS-03, VFS-04]

# Metrics
duration: 5min
completed: 2026-03-10
---

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
