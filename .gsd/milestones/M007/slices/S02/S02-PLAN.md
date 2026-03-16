# S02: VFS Quick Wins — Type Filter, Query IRI, Preview

**Goal:** VFS mounts support type filter (VALUES clause, AND-composed with scope), scopeQuery predicate with full IRI, preview resolves saved query scope, path contract documented and tested.
**Demo:** Create a mount with type_filter → WebDAV shows only matching types. Create a mount with saved query scope → preview shows correct filtered counts. Existing mounts with savedQueryId still work after migration.

## Must-Haves

- `type_filter` field on MountDefinition accepting list of type IRIs
- `build_scope_filter()` generates VALUES clause for type_filter, AND-composed with scope
- `sempkm:savedQueryId` renamed to `sempkm:scopeQuery` everywhere
- `scopeQuery` stored as full IRI (`<urn:sempkm:query:{uuid}>`), not bare UUID string
- Migration SPARQL UPDATE renames predicate and wraps existing values
- WebDAV collections resolve saved query text via SyncTriplestoreClient
- Preview endpoint resolves saved query scope via async TriplestoreClient
- Type multi-select UI in mount form
- Path contract documentation with forward/reverse mapping examples
- Unit tests for type_filter VALUES, slug generation, collision dedup

## Proof Level

- This slice proves: contract + integration
- Real runtime required: yes (preview endpoint, WebDAV collections use triplestore)
- Human/UAT required: no

## Verification

- `cd backend && python -m pytest tests/test_vfs_scope.py -v` — all existing + new type_filter tests pass
- `cd backend && python -m pytest tests/test_vfs_path_contract.py -v` — slug/dedup tests pass
- Manual/browser: mount form shows type multi-select, preview with saved query returns filtered counts
- Grep confirms zero occurrences of `savedQueryId` in Python/template/JS files (except migration script)
- Diagnostic: `build_scope_filter()` with a type_filter mount that has an invalid IRI returns a VALUES clause containing the raw string (no silent swallow) — verifiable by inspecting SPARQL output
- Diagnostic: preview endpoint returns HTTP 404 with `{"error": "Saved query not found"}` when `scope_query` IRI doesn't resolve

## Observability / Diagnostics

- Runtime signals: `build_scope_filter()` logs when type_filter VALUES clause is generated; preview endpoint logs resolved query IRI
- Inspection surfaces: mount API response includes `type_filter` and `scope_query` fields; preview endpoint returns filtered counts
- Failure visibility: preview endpoint returns clear error when saved query IRI not found in triplestore
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `SyncTriplestoreClient` (existing), `TriplestoreClient` (existing), `QUERIES_GRAPH` + `PRED_QUERY_TEXT` from `query_service.py`
- New wiring introduced: `build_scope_filter()` accepts `sync_client` parameter for query resolution; `MountRootCollection`/`StrategyFolderCollection` pass `self._client` to scope filter
- What remains before milestone is truly usable end-to-end: S03 (composable chains + filename templates), S04 (UI polish), S05 (docs)

## Tasks

- [x] **T01: Add type_filter to MountDefinition and build_scope_filter** `est:1h`
  - Why: VFS-07 core — type filter VALUES clause in SPARQL scope, AND-composed with existing scope
  - Files: `backend/app/vfs/mount_service.py`, `backend/app/vfs/strategies.py`, `backend/tests/test_vfs_scope.py`
  - Do: Add `type_filter: list[str] | None = None` field to `MountDefinition`. Add `TYPE_FILTER` vocab constant. Extend `build_scope_filter()` to emit `VALUES ?type { <iri1> <iri2> }` when type_filter is set. Compose type filter AND scope (both clauses in WHERE). Update `to_dict()`. Write unit tests for type_filter alone, with scope, empty list, and AND composition.
  - Verify: `cd backend && python -m pytest tests/test_vfs_scope.py -v` — all tests pass
  - Done when: `build_scope_filter(mount_with_type_filter)` returns SPARQL with VALUES clause; existing tests still pass

- [x] **T02: Rename savedQueryId to scopeQuery with IRI storage** `est:1.5h`
  - Why: VFS-08 — align predicate naming and store full IRIs per D099
  - Files: `backend/app/vfs/mount_service.py`, `backend/app/vfs/mount_router.py`, `backend/app/vfs/mount_collections.py`, `frontend/static/js/workspace.js`, `backend/app/templates/browser/_vfs_settings.html`
  - Do: Rename `SAVED_QUERY_ID` constant to `SCOPE_QUERY` with value `sempkm:scopeQuery`. Rename `saved_query_id` field to `scope_query` on `MountDefinition` and Pydantic models. Change INSERT DATA to store as IRI (`<urn:sempkm:query:{uuid}>`) not string literal. Update all SPARQL queries (OPTIONAL bindings, variable names). Update `_binding_to_mount()` / async equivalent to parse IRI values. Update JS `populateEditForm()` and `mountSubmitForm()` to use `scope_query`. Write migration function (SPARQL UPDATE: DELETE old triples, INSERT with new predicate + IRI wrapper). Remove stale comment in mount_collections.py line 117-120.
  - Verify: `cd backend && python -m pytest tests/test_vfs_scope.py -v`; grep for `savedQueryId` returns zero hits in .py/.js/.html (except migration)
  - Done when: All mount CRUD uses `sempkm:scopeQuery` with IRI values; migration script exists

- [x] **T03: Wire saved query resolution into WebDAV and fix preview** `est:1.5h`
  - Why: VFS-09 — make saved query scope actually work in WebDAV and preview (currently dead code)
  - Files: `backend/app/vfs/strategies.py`, `backend/app/vfs/mount_collections.py`, `backend/app/vfs/mount_router.py`, `backend/app/vfs/cache.py`, `backend/tests/test_vfs_scope.py`
  - Do: Add `sync_client` parameter to `build_scope_filter()`. When `mount.scope_query` is set and no `resolved_query_text` provided, query `urn:sempkm:queries` graph via sync_client to get query text (using `PRED_QUERY_TEXT` vocab). Cache resolved text in `listing_cache` with `query_text:{id}` key. Update `clear_mount_cache()` to also clear `query_text:*` keys. Update `MountRootCollection.__init__` and `StrategyFolderCollection.__init__` to pass `self._client` to `build_scope_filter()`. Fix preview endpoint: when `scope_query` is set, query async `TriplestoreClient` for query text, pass to `build_scope_filter()` as `resolved_query_text`. Remove stale SQLite comment from preview endpoint. Write unit tests with mocked sync_client for query resolution.
  - Verify: `cd backend && python -m pytest tests/test_vfs_scope.py -v` — query resolution tests pass; preview endpoint code path no longer has dead scope block
  - Done when: WebDAV collections resolve saved query scope at runtime; preview returns filtered counts for mounts with saved queries

- [x] **T04: Type multi-select UI in mount form** `est:1h`
  - Why: VFS-07 UI — users need to select type filters without writing SPARQL
  - Files: `backend/app/templates/browser/_vfs_settings.html`, `frontend/static/js/workspace.js`, `backend/app/vfs/mount_router.py`
  - Do: Add type multi-select checkbox group to mount form template (below strategy fields). Populate from `/browser/views/type-pills` endpoint (or new `/api/vfs/mounts/types` endpoint returning available types). Update `mountSubmitForm()` to collect checked type IRIs into `type_filter` array in POST body. Update `populateEditForm()` to pre-check types from mount data. Update `MountCreateRequest`/`MountUpdateRequest` to include `type_filter: list[str] | None = None`. Update mount create/update INSERT DATA in `mount_router.py` to store multi-valued `sempkm:typeFilter` triples. Update async mount query to collect type_filter via GROUP_CONCAT. Update preview endpoint to accept and apply type_filter.
  - Verify: Browser: open Settings → VFS → create mount → type checkboxes visible and selectable; preview reflects type filter
  - Done when: Full round-trip: create mount with type_filter via UI → API stores triples → edit form pre-selects → WebDAV filters by type

- [x] **T05: Path contract documentation and slug/dedup tests** `est:45m`
  - Why: VFS-10 — document bidirectional path mapping and test edge cases
  - Files: `docs/guide/23-vfs.md` (or new `docs/vfs-path-contract.md`), `backend/tests/test_vfs_path_contract.py`, `backend/app/vfs/mount_collections.py`
  - Do: Document forward (IRI → filename via slugify + dedup) and reverse (filename → IRI via file_map lookup) mapping. Document filename instability caveat (label changes = filename changes). Add examples. Write unit tests for `_slugify_label()` edge cases (unicode, special chars, empty, very long). Write unit tests for collision dedup logic (same label → suffix numbering). Identify and test the actual slug/dedup functions in mount_collections.py or strategies.py.
  - Verify: `cd backend && python -m pytest tests/test_vfs_path_contract.py -v` — all tests pass; docs file exists with examples
  - Done when: Path contract documented with forward/reverse examples; slug edge cases have test coverage

## Files Likely Touched

- `backend/app/vfs/mount_service.py`
- `backend/app/vfs/strategies.py`
- `backend/app/vfs/mount_collections.py`
- `backend/app/vfs/mount_router.py`
- `backend/app/vfs/cache.py`
- `backend/app/templates/browser/_vfs_settings.html`
- `frontend/static/js/workspace.js`
- `backend/tests/test_vfs_scope.py`
- `backend/tests/test_vfs_path_contract.py` (new)
- `docs/guide/23-vfs.md`
