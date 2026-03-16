# S02: VFS Quick Wins — Type Filter, Query IRI, Preview — Research

**Date:** 2026-03-15

## Summary

This slice covers four VFS requirements (VFS-07 through VFS-10) — all low-complexity extensions to well-established VFS infrastructure. The codebase is clean and the patterns are clear: `MountDefinition` dataclass holds mount config, `build_scope_filter()` in `strategies.py` builds SPARQL WHERE fragments, `mount_service.py` does RDF CRUD in `urn:sempkm:mounts`, `mount_router.py` provides async REST endpoints, and `mount_collections.py` consumes scope filters in WebDAV collections.

The main gap is that `saved_query_id` is stored on mounts but completely ignored by `build_scope_filter()` — callers in `MountRootCollection.__init__` and `StrategyFolderCollection.__init__` call `build_scope_filter(mount)` without resolving the query text. The comment at `mount_collections.py:75` confirms: *"WebDAV falls back to sparql_scope only."* This is the core wiring task.

The secondary changes — `type_filter` field, `scopeQuery` predicate rename, preview fix, path contract docs — all follow established patterns and touch known files.

## Recommendation

Build in order: (1) `type_filter` on `MountDefinition` + `build_scope_filter()` VALUES clause, (2) `scopeQuery` IRI alignment with migration SPARQL, (3) saved query resolution in WebDAV + preview fix, (4) path contract docs + slug/dedup tests. This order lets each piece be independently testable and avoids coupling.

## Implementation Landscape

### Key Files

- **`backend/app/vfs/mount_service.py`** — `MountDefinition` dataclass, RDF CRUD, vocab constants. Add `type_filter: list[str] | None = None` field. Add `TYPE_FILTER = f"{NS_SEMPKM}typeFilter"` and `SCOPE_QUERY = f"{NS_SEMPKM}scopeQuery"` constants. Rename `SAVED_QUERY_ID` → `SCOPE_QUERY` throughout. Update `create_mount()`, `update_mount()`, `get_mount_by_id()`, `get_mount_by_prefix()`, `list_mounts()`, `_binding_to_mount()` to handle `type_filter` (multi-valued) and `scopeQuery` (IRI value, not string literal).

- **`backend/app/vfs/strategies.py`** — `build_scope_filter()` currently takes `(mount, resolved_query_text=None)`. Extend to: (a) resolve saved query text from RDF via `SyncTriplestoreClient` when `mount.saved_query_id` is set (using cached lookup), (b) add `type_filter` VALUES clause. Both compose via AND. The `SyncTriplestoreClient` needs to be passed in (callers have it as `self._client`). The query text lives in `urn:sempkm:queries` graph at predicate `urn:sempkm:vocab:queryText` on IRI `urn:sempkm:query:{uuid}` (from `backend/app/sparql/query_service.py`).

- **`backend/app/vfs/mount_collections.py`** — `MountRootCollection.__init__` and `StrategyFolderCollection.__init__` both call `build_scope_filter(mount)`. Update to pass `self._client` so the function can resolve saved queries. Remove the stale comment at line 75.

- **`backend/app/vfs/mount_router.py`** — Async REST endpoints. Update `MountCreateRequest`/`MountUpdateRequest` Pydantic models to include `type_filter: list[str] | None = None`. Update create/update INSERT DATA to store multi-valued `sempkm:typeFilter` triples and `sempkm:scopeQuery` as IRI (not string literal). Update async `_get_mount_by_id_async()` and list endpoints to query new predicates. Fix preview endpoint (`preview_mount()`) — replace the dead scope filter block at ~line 509 with actual query resolution via async `TriplestoreClient`.

- **`backend/app/vfs/cache.py`** — Extend `clear_mount_cache()` to also clear `query_text:*` cache keys. Add `query_text:{id}` caching pattern for resolved query text.

- **`backend/app/templates/browser/_vfs_settings.html`** — Add type multi-select UI element (checkboxes or multi-select) populated from `/browser/views/type-pills` or a similar types endpoint. Wire into `collectFormData()`.

- **`frontend/static/js/workspace.js`** — Update `collectFormData()` to collect selected type IRIs. Update `initMountForm()` to fetch and populate type options. Update `populateEditForm()` to pre-select types. Update `mountPreview()` to send `type_filter`.

- **`backend/app/vfs/provider.py`** — No changes needed for this slice (path dispatch extension is S03).

- **`backend/tests/test_vfs_scope.py`** — Existing 10 tests for `build_scope_filter` and `_extract_where_body`. Extend with: type_filter VALUES clause tests, type_filter + scope composition tests, scopeQuery IRI resolution tests.

- **Path contract docs** — New file `docs/vfs-path-contract.md` (or section in existing docs). Document `_slugify()` → `_build_file_map_from_bindings()` → dedup suffix pipeline. Add unit tests for slug generation edge cases and collision dedup.

### Build Order

1. **Type filter + build_scope_filter extension** — Add `type_filter` field to `MountDefinition`, extend `build_scope_filter()` with VALUES clause, write unit tests. This is independent and immediately testable without Docker.

2. **scopeQuery IRI alignment + migration** — Rename predicate from `sempkm:savedQueryId` to `sempkm:scopeQuery`, store as IRI not string, write migration SPARQL UPDATE. Update all mount_service.py and mount_router.py references. This is a rename with no behavior change (yet).

3. **Saved query resolution in WebDAV + preview fix** — Wire `SyncTriplestoreClient` into `build_scope_filter()` for query text resolution. Update `MountRootCollection` and `StrategyFolderCollection` callers to pass `sync_client`. Fix preview endpoint to resolve saved queries via async `TriplestoreClient`. This is the core behavior change — makes `saved_query_id` actually work.

4. **Type multi-select UI** — Add UI element to mount form, update JS `collectFormData()` and `initMountForm()`. Populate from same types data source as generic view type pills.

5. **Path contract docs + tests** — Document forward/reverse mapping. Add unit tests for `_slugify()` and `_build_file_map_from_bindings()` edge cases.

### Verification Approach

- **Unit tests (pytest, no Docker):** `build_scope_filter()` with type_filter, with resolved_query_text, with both composed. `_slugify()` edge cases. `_build_file_map_from_bindings()` collision dedup. Can mock `SyncTriplestoreClient` for query resolution tests.
- **Integration (Docker):** Create a mount with type_filter via API → verify WebDAV listing only shows filtered types. Create a mount with saved query scope → verify WebDAV listing reflects query scope. Preview endpoint returns correct counts with scope applied.
- **Migration:** Run scopeQuery migration SPARQL → verify existing mounts still load correctly (no bare UUID values remain as `savedQueryId` triples).

## Constraints

- **Sync/async boundary:** WebDAV runs in sync WSGI threads — must use `SyncTriplestoreClient`, not `QueryService` (async). Preview endpoint runs in async FastAPI context — can use `TriplestoreClient` directly.
- **Multi-valued RDF field:** `type_filter` is a list of type IRIs. RDF stores this as multiple `sempkm:typeFilter` triples on the same subject. SPARQL queries need `GROUP_CONCAT` or multiple `OPTIONAL` blocks to collect them. The cleanest pattern is a separate query or a sub-select with `GROUP_CONCAT`.
- **scopeQuery stores full IRI:** `sempkm:scopeQuery` value must be `<urn:sempkm:query:{uuid}>` (IRI), not `"uuid"` (string literal). This means INSERT DATA uses `<{iri}>` not `"{value}"`. Existing `saved_query_id` values are bare UUIDs stored as string literals — migration must wrap them.
- **Query text predicate:** The vocab is `urn:sempkm:vocab:queryText` on graph `urn:sempkm:queries` (from `query_service.py` lines 40-41).

## Common Pitfalls

- **Multi-valued SPARQL binding explosion** — If `type_filter` has 3 IRIs and we query them with multiple `OPTIONAL` blocks, the result set multiplies. Use `GROUP_CONCAT` with `GROUP BY ?mount` to aggregate type filter values into a single binding, then split in Python.
- **IRI vs literal mismatch** — `scopeQuery` must be stored as an IRI (`<urn:...>`) not a string literal (`"urn:..."`). Mixing these causes silent query failures where FILTER/JOIN conditions don't match. Verify in the INSERT DATA statements.
- **Cache key prefix for query text** — Use `query_text:{id}` prefix and add to `clear_mount_cache()` cleanup. Without this, updated saved queries won't be reflected in mounts until TTL expires AND the mount cache is cleared.
