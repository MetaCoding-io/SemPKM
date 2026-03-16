---
estimated_steps: 7
estimated_files: 5
---

# T03: Wire saved query resolution into WebDAV and fix preview

**Slice:** S02 — VFS Quick Wins — Type Filter, Query IRI, Preview
**Milestone:** M007

## Description

Make `scope_query` actually work. Currently `build_scope_filter()` only uses `scope_query` when the caller manually passes `resolved_query_text` — but no caller does. WebDAV collections call `build_scope_filter(mount)` without resolving the query text, so saved query scope is silently ignored.

This task wires `SyncTriplestoreClient` into `build_scope_filter()` for WebDAV (sync context) and fixes the preview endpoint to resolve queries via async `TriplestoreClient`.

**Critical sync/async boundary:** WebDAV runs in sync WSGI threads via wsgidav — must use `SyncTriplestoreClient`. Preview endpoint runs in async FastAPI — uses `TriplestoreClient`. Never mix these.

## Steps

1. **Extend `build_scope_filter()` in `strategies.py`:**
   - Add optional `sync_client: SyncTriplestoreClient | None = None` parameter
   - When `mount.scope_query` is set and `resolved_query_text` is not provided and `sync_client` is provided:
     - Extract UUID from IRI: `mount.scope_query` is `urn:sempkm:query:{uuid}` — parse it
     - Check cache first: `listing_cache.get(f"query_text:{uuid}")`
     - If not cached, query the triplestore:
       ```sparql
       SELECT ?text FROM <urn:sempkm:queries> WHERE {
         <{mount.scope_query}> <urn:sempkm:vocab:queryText> ?text
       }
       ```
     - Cache the result: `listing_cache[f"query_text:{uuid}"] = text`
     - If query text found, process it through `_extract_where_body()` and compose as scope
   - Import `listing_cache` and `_cache_lock` from `cache.py`
   - Import vocab constants: `QUERIES_GRAPH = "urn:sempkm:queries"`, `PRED_QUERY_TEXT = "urn:sempkm:vocab:queryText"`

2. **Update callers in `mount_collections.py`:**
   - `MountRootCollection.__init__`: change `build_scope_filter(mount)` → `build_scope_filter(mount, sync_client=client)`
   - `StrategyFolderCollection.__init__`: same change, use `self._client`
   - Both classes already receive `client: SyncTriplestoreClient` in `__init__`

3. **Update `cache.py`:**
   - In `clear_mount_cache()`, extend the key filter to also clear keys starting with `"query_text:"`:
     ```python
     if k.startswith("mount:") or k.startswith("root:") or k.startswith("query_text:")
     ```

4. **Fix preview endpoint in `mount_router.py`:**
   - In `preview_mount()` function (line ~488), replace the dead scope block (lines ~509-514):
     ```python
     # OLD (dead code):
     if body.sparql_scope and body.sparql_scope != "all" and body.saved_query_id:
         scope_filter = ""  # dead
     ```
   - New implementation:
     - If `body.scope_query` is set: query `urn:sempkm:queries` via async `client` for query text, then call `build_scope_filter()` with `resolved_query_text=query_text`
     - If `body.sparql_scope` is set and not "all": create a temp `MountDefinition` and call `build_scope_filter()`
     - If `body.type_filter` is set: create/update temp `MountDefinition` with type_filter and call `build_scope_filter()`
     - The preview should compose all filters just like real WebDAV does
   - Remove the stale comment about "loading from SQLite"

5. **Add logging:**
   - In `build_scope_filter()`: log at DEBUG level when resolving a scope_query via sync_client
   - In `preview_mount()`: log at DEBUG when resolving scope_query

6. **Write unit tests in `test_vfs_scope.py`:**
   - Add `TestQueryResolution` class:
     - `test_scope_query_resolved_via_sync_client` — mock sync_client returns query text → build_scope_filter uses it
     - `test_scope_query_not_found_returns_empty` — mock sync_client returns no results → no scope filter
     - `test_scope_query_without_client_ignored` — scope_query set but no sync_client → falls back to sparql_scope
     - `test_scope_query_cached_on_second_call` — call twice, sync_client.query called only once
   - Use `unittest.mock.MagicMock` for `SyncTriplestoreClient`

7. Run full test suite.

## Must-Haves

- [ ] `build_scope_filter()` resolves `scope_query` via `sync_client` when provided
- [ ] Query text is cached with `query_text:{uuid}` key in listing_cache
- [ ] `clear_mount_cache()` clears query_text cache keys
- [ ] WebDAV collections pass `sync_client` to `build_scope_filter()`
- [ ] Preview endpoint resolves scope_query via async client (no dead code, no SQLite comment)
- [ ] Unit tests with mocked client verify resolution behavior

## Verification

- `cd backend && python -m pytest tests/test_vfs_scope.py -v` — all tests pass including query resolution tests
- Read preview_mount() and confirm no dead scope block remains
- Read mount_collections.py and confirm both callers pass sync_client

## Observability Impact

- Signals added: DEBUG log in `build_scope_filter()` when resolving scope_query
- How a future agent inspects this: grep logs for "scope_query" or "query_text"
- Failure state exposed: if query IRI not found in triplestore, scope filter silently returns empty (fallback to unscoped) — logged at WARNING

## Inputs

- `backend/app/vfs/strategies.py` — `build_scope_filter()` with type_filter support from T01
- `backend/app/vfs/mount_service.py` — `MountDefinition` with `scope_query` field from T02
- `backend/app/vfs/mount_router.py` — preview endpoint with `scope_query` from T02
- `backend/app/vfs/mount_collections.py` — stale comment removed by T02
- `backend/app/vfs/cache.py` — existing `clear_mount_cache()` and `listing_cache`
- Query text is stored in `urn:sempkm:queries` graph at predicate `urn:sempkm:vocab:queryText` (from `backend/app/sparql/query_service.py` lines 26, 41)

## Expected Output

- `backend/app/vfs/strategies.py` — `build_scope_filter()` resolves scope_query via sync_client with caching
- `backend/app/vfs/mount_collections.py` — both collection classes pass sync_client to build_scope_filter
- `backend/app/vfs/mount_router.py` — preview endpoint resolves scope_query via async client
- `backend/app/vfs/cache.py` — clear_mount_cache clears query_text keys
- `backend/tests/test_vfs_scope.py` — 4+ new query resolution tests with mocked client
