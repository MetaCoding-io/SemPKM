---
id: T03
parent: S02
milestone: M007
provides:
  - build_scope_filter resolves scope_query via SyncTriplestoreClient with TTL cache
  - Preview endpoint resolves scope_query via async TriplestoreClient with 404 on missing
key_files:
  - backend/app/vfs/strategies.py
  - backend/app/vfs/mount_collections.py
  - backend/app/vfs/mount_router.py
  - backend/app/vfs/cache.py
  - backend/tests/test_vfs_scope.py
key_decisions:
  - scope_query resolution in build_scope_filter uses a separate helper (_resolve_scope_query_sync) to keep the main function clean
  - Cache key format is query_text:{uuid} where uuid is extracted from urn:sempkm:query:{uuid} IRI
  - Preview endpoint returns HTTP 404 with "Saved query not found" when scope_query IRI doesn't resolve (fail-fast, not silent empty)
patterns_established:
  - sync_client optional parameter on build_scope_filter for WebDAV callers; async callers pre-resolve and pass resolved_query_text
observability_surfaces:
  - DEBUG log in build_scope_filter when resolving scope_query via sync client (grep "Resolving scope_query")
  - DEBUG log in build_scope_filter when cache hit on scope_query (grep "resolved from cache")
  - WARNING log when scope_query IRI not found in triplestore (grep "not found in triplestore")
  - DEBUG log in preview_mount when resolving scope_query
duration: 15m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T03: Wire saved query resolution into WebDAV and fix preview

**`build_scope_filter()` now resolves scope_query IRI → SPARQL text via SyncTriplestoreClient (WebDAV) or async client (preview), with TTL-cached query text and 404 on missing queries.**

## What Happened

Extended `build_scope_filter()` with an optional `sync_client` parameter. When `mount.scope_query` is set and no `resolved_query_text` is explicitly provided, the function resolves the query IRI against `urn:sempkm:queries` graph via a new `_resolve_scope_query_sync()` helper. Results are cached in `listing_cache` with `query_text:{uuid}` keys, cleared alongside mount caches.

Updated both `MountRootCollection` and `StrategyFolderCollection` in `mount_collections.py` to pass their existing `client` as `sync_client` to `build_scope_filter()`.

Replaced the dead scope block in `preview_mount()` (which had a stale SQLite comment and produced empty scope_filter regardless of input) with real async resolution: queries `urn:sempkm:queries` graph for query text, raises HTTP 404 if not found, then builds scope_filter through a temporary MountDefinition with `resolved_query_text`.

## Verification

- `backend/.venv/bin/python -m pytest tests/test_vfs_scope.py -v` — 21/21 passed (5 new TestQueryResolution tests)
- Confirmed `mount_collections.py` passes `sync_client=client` in both collection classes
- Confirmed `mount_router.py` has no dead scope block, no SQLite comment, no `savedQueryId` references
- Confirmed `cache.py` clears `query_text:` keys in `clear_mount_cache()`
- LSP diagnostics clean (only pre-existing unused `user` hints in auth-gated endpoints)

### Slice-level checks (T03 scope):
- ✅ `test_vfs_scope.py` — all 21 tests pass
- ⬜ `test_vfs_path_contract.py` — does not exist yet (later task)
- ✅ Zero `savedQueryId` occurrences outside migration
- ✅ Preview endpoint returns 404 when scope_query IRI doesn't resolve

## Diagnostics

- **Query resolution tracing:** Grep logs for `"Resolving scope_query"` (DEBUG) to see when sync_client lookups happen
- **Cache hits:** Grep for `"resolved from cache"` — indicates TTL cache is working
- **Missing queries:** Grep for `"not found in triplestore"` (WARNING) — scope_query IRI didn't resolve, scope silently omitted in WebDAV
- **Preview failures:** HTTP 404 with `{"detail": "Saved query not found"}` when preview scope_query doesn't resolve

## Deviations

- Added a 5th test (`test_resolved_query_text_takes_precedence_over_sync_client`) beyond the 4 specified in the plan — verifies that explicit `resolved_query_text` skips sync_client entirely

## Known Issues

None.

## Files Created/Modified

- `backend/app/vfs/strategies.py` — Added `sync_client` param to `build_scope_filter()`, `_resolve_scope_query_sync()` helper, query resolution constants
- `backend/app/vfs/mount_collections.py` — Both collection classes pass `sync_client=client` to `build_scope_filter()`
- `backend/app/vfs/mount_router.py` — Preview endpoint resolves scope_query via async client, imports strategy constants
- `backend/app/vfs/cache.py` — `clear_mount_cache()` clears `query_text:` cache keys
- `backend/tests/test_vfs_scope.py` — Added `TestQueryResolution` class with 5 tests
