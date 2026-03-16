---
id: S02
parent: M007
milestone: M007
provides:
  - type_filter field on MountDefinition with VALUES clause in build_scope_filter, AND-composed with scope
  - sempkm:scopeQuery predicate (renamed from savedQueryId) with full IRI storage and migration
  - build_scope_filter resolves scope_query via SyncTriplestoreClient with TTL cache for WebDAV
  - Preview endpoint resolves scope_query via async TriplestoreClient with HTTP 404 on missing
  - Type multi-select checkbox UI in mount form with full CRUD round-trip
  - Path contract documentation and 26 unit tests for slug/dedup logic
requires: []
affects:
  - S03
key_files:
  - backend/app/vfs/mount_service.py
  - backend/app/vfs/mount_router.py
  - backend/app/vfs/strategies.py
  - backend/app/vfs/mount_collections.py
  - backend/app/vfs/cache.py
  - backend/app/vfs/migrations.py
  - backend/app/browser/workspace.py
  - backend/app/templates/browser/_vfs_settings.html
  - frontend/static/js/workspace.js
  - frontend/static/css/workspace.css
  - backend/tests/test_vfs_scope.py
  - backend/tests/test_vfs_path_contract.py
  - docs/guide/23-vfs.md
key_decisions:
  - type_filter VALUES clause uses ?iri a ?type binding to connect to object pattern
  - scope_query stores full IRI (urn:sempkm:query:{uuid}) as RDF IRI type, not string literal
  - Frontend constructs IRI by prefixing urn:sempkm:query: to UUID; strips prefix on edit populate
  - Two-query approach for list_mounts type_filter (separate SELECT merged in Python) — more portable than GROUP_CONCAT subquery
  - build_scope_filter gets optional sync_client param for WebDAV; async callers pre-resolve and pass resolved_query_text
  - Preview returns HTTP 404 with clear error when scope_query IRI doesn't resolve (fail-fast)
  - Cache key format query_text:{uuid} for resolved scope queries in listing_cache
  - Collision dedup uses IRI SHA-256 hash prefix (--{hash[:6]}), not sequential numbering
patterns_established:
  - Multi-valued RDF predicate CRUD: store as individual triples, read via separate query + Python merge for lists, GROUP_CONCAT for single-resource queries
  - VFS scope references use full IRIs (urn:sempkm:query:{uuid}) not bare UUID strings
  - build_scope_filter returns concatenated filter parts joined by newline+indent — composable fragments
observability_surfaces:
  - DEBUG log in build_scope_filter when type_filter VALUES clause generated (grep "type_filter VALUES")
  - DEBUG log when resolving scope_query via sync client (grep "Resolving scope_query")
  - DEBUG log when scope_query resolved from cache (grep "resolved from cache")
  - WARNING log when scope_query IRI not found in triplestore (grep "not found in triplestore")
  - Migration function logs triple count at INFO (grep "migrate_saved_query_to_scope_query")
  - Mount API responses include type_filter and scope_query fields
  - Preview endpoint returns HTTP 404 with {"detail": "Saved query not found"} on missing scope_query
drill_down_paths:
  - .gsd/milestones/M007/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M007/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M007/slices/S02/tasks/T03-SUMMARY.md
  - .gsd/milestones/M007/slices/S02/tasks/T04-SUMMARY.md
  - .gsd/milestones/M007/slices/S02/tasks/T05-SUMMARY.md
duration: ~2.5h
verification_result: passed
completed_at: 2026-03-16
---

# S02: VFS Quick Wins — Type Filter, Query IRI, Preview

**VFS mounts now support type filtering via VALUES clause (AND-composed with scope), scopeQuery predicate with full IRI storage and migration, live saved query resolution in both WebDAV and preview, type multi-select UI, and a documented+tested path contract.**

## What Happened

Five tasks built incrementally on the VFS infrastructure:

**T01** added `type_filter: list[str] | None` to `MountDefinition` and refactored `build_scope_filter()` from sequential if/elif to a composable parts-list. When type_filter is set, it generates `VALUES ?type { <iri1> <iri2> }` with `?iri a ?type .` binding. Type filter and scope compose via AND — both appear in the returned SPARQL fragment. 6 new tests.

**T02** renamed `savedQueryId` → `scopeQuery` across all VFS backend, frontend, and browser workspace code. Changed SPARQL storage from `"uuid"^^xsd:string` to `<urn:sempkm:query:uuid>` IRI syntax. Created `backend/app/vfs/migrations.py` with a SPARQL UPDATE that atomically renames the predicate and wraps bare UUIDs. Frontend JS constructs/parses full IRIs. Also discovered and updated `workspace.py` (not in original plan) which had the old imports and function names.

**T03** wired live saved query resolution into `build_scope_filter()` via optional `sync_client` parameter. WebDAV collections pass their existing client; resolved text is TTL-cached in `listing_cache` with `query_text:{uuid}` keys. Replaced the dead scope block in the preview endpoint (which had a stale SQLite comment and always returned empty scope) with real async resolution that returns HTTP 404 when the query IRI doesn't exist. 5 new tests.

**T04** completed the full type_filter CRUD loop. Added `type_filter` to Pydantic request models, async create/update endpoints store individual `sempkm:typeFilter` triples, list endpoint uses a two-query merge approach for portability. Mirrored in sync `mount_service.py`. Mount form UI fetches types from the existing `/browser/views/type-pills` endpoint and renders checkboxes. Edit form pre-checks saved types. Mount list cards show type count inline.

**T05** wrote 26 unit tests covering `_slugify()` edge cases (15 tests: unicode, special chars, empty, long labels) and `_build_file_map_from_bindings()` collision dedup (11 tests: hash suffix, isolation, reverse lookup). Documented the VFS path contract in `docs/guide/23-vfs.md` with forward/reverse mapping, collision dedup explanation, and filename instability caveat.

## Verification

- `python -m pytest tests/test_vfs_scope.py -v` — **21/21 passed** (10 existing + 6 type_filter + 5 query resolution)
- `python -m pytest tests/test_vfs_path_contract.py -v` — **26/26 passed** (15 slugify + 11 file map)
- `rg savedQueryId backend/ frontend/ -g "*.py" -g "*.js" -g "*.html" | grep -v migration` — zero results
- Browser: mount form type checkboxes visible and functional, preview reflects type filter, edit form pre-selects saved types
- API: mount list and get responses include `type_filter` and `scope_query` fields with correct values

## Requirements Advanced

- VFS-07 — type_filter field on MountDefinition, VALUES clause generation, AND-composition with scope, type multi-select UI with full CRUD round-trip
- VFS-08 — savedQueryId renamed to scopeQuery across all code, IRI storage, migration function
- VFS-09 — preview endpoint resolves saved query scope via async TriplestoreClient, returns 404 on missing; WebDAV resolves via sync client with cache
- VFS-10 — path contract documented with forward/reverse examples, filename instability caveat, slug/dedup test coverage

## Requirements Validated

- VFS-07 — type_filter VALUES clause tested (6 unit tests), UI verified in browser, full CRUD round-trip confirmed
- VFS-08 — zero occurrences of savedQueryId outside migration confirmed by grep, IRI storage verified in tests
- VFS-09 — 5 unit tests for query resolution, preview endpoint 404 verified, dead SQLite comment removed
- VFS-10 — 26 unit tests for slug/dedup, docs/guide/23-vfs.md has Path Contract section with examples

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- T02 discovered `backend/app/browser/workspace.py` needed the same savedQueryId→scopeQuery rename — it had imports, SPARQL variables, binding extraction, and a function name referencing the old convention. Updated in the same sweep.
- T05 found collision dedup uses IRI SHA-256 hash prefix (`--{hash[:6]}`), not sequential numbering as the plan assumed. Tests and docs written against actual behavior.
- T04 used a two-query approach for list_mounts type_filter instead of GROUP_CONCAT subquery — more portable across SPARQL 1.1 stores.

## Known Limitations

- `_slugify` does not truncate long labels (300+ char slugs possible). Could hit filesystem path length limits on deeply nested mounts.
- Unicode handling is lossy — strips all non-ASCII to hyphens (e.g., "Über" → "ber"). Safe for filesystems but loses information.
- Migration function (`migrate_saved_query_to_scope_query`) exists but has no automatic trigger — must be called manually or wired into a startup hook.
- Browser-level verification of preview with saved query scope required main project stack (worktree triplestore has a LuceneSail locking issue).

## Follow-ups

- Wire `migrate_saved_query_to_scope_query()` into startup or provide an admin endpoint to trigger it.
- Consider adding `_slugify` truncation for very long labels if deeply nested mounts become a real use case.

## Files Created/Modified

- `backend/app/vfs/mount_service.py` — TYPE_FILTER constant, type_filter field, to_dict, sync CRUD for type_filter
- `backend/app/vfs/mount_router.py` — type_filter in Pydantic models, async CRUD, preview scope resolution
- `backend/app/vfs/strategies.py` — build_scope_filter refactored to parts-list, type_filter VALUES, sync_client param, query resolution helper
- `backend/app/vfs/mount_collections.py` — sync_client passthrough, stale comment removed
- `backend/app/vfs/cache.py` — clear_mount_cache clears query_text: keys
- `backend/app/vfs/migrations.py` — new: savedQueryId→scopeQuery migration function
- `backend/app/browser/workspace.py` — renamed imports, function, SPARQL vars
- `backend/app/templates/browser/_vfs_settings.html` — type filter checkbox container
- `frontend/static/js/workspace.js` — scope_query IRI construction/parsing, type filter fetch/populate/collect/reset
- `frontend/static/css/workspace.css` — type filter container styles
- `backend/tests/test_vfs_scope.py` — 11 new tests (6 type_filter + 5 query resolution)
- `backend/tests/test_vfs_path_contract.py` — new: 26 tests for slug/dedup
- `docs/guide/23-vfs.md` — Path Contract section with forward/reverse mapping docs

## Forward Intelligence

### What the next slice should know
- `build_scope_filter()` now uses a parts-list pattern — each filter concern (scope, type_filter, resolved query) adds to a list, joined at the end. S03's composable chains should follow the same pattern.
- `MountDefinition` has `strategy: str` — S03 needs to change this to `str | list[str]` for chains. The `to_dict()` method and all SPARQL read/write paths will need updates.
- `_build_file_map_from_bindings()` is the function that S03's filename templates will modify — it already does slugify + dedup, and S03 needs to add template expansion before the slugify step.

### What's fragile
- The two-query merge in `mount_router.py` `list_mounts` for type_filter — if the mount IRI format changes, the Python merge logic (matching by URI key) would break. S03 adding strategy chains as multi-valued triples should follow the same two-query pattern or validate the merge works with additional predicates.
- Preview endpoint scope resolution creates a temporary MountDefinition just to call `build_scope_filter()` — this is a bit of a hack but works. If MountDefinition grows required fields in S03, preview will need updating.

### Authoritative diagnostics
- `cd backend && python -m pytest tests/test_vfs_scope.py tests/test_vfs_path_contract.py -v` — 47 tests covering all VFS scope and path contract behavior
- Grep `savedQueryId` across backend/frontend (excluding migration) — must be zero
- Mount API response JSON — inspect `type_filter` and `scope_query` fields directly

### What assumptions changed
- Plan assumed collision dedup used sequential numbering — actual implementation uses IRI SHA-256 hash prefix. Tests and docs reflect reality.
- Plan assumed `workspace.py` didn't reference savedQueryId — it did, and was updated.
