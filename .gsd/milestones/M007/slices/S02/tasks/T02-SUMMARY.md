---
id: T02
parent: S02
milestone: M007
provides:
  - scope_query field (renamed from saved_query_id) on MountDefinition with IRI storage
  - SCOPE_QUERY constant (renamed from SAVED_QUERY_ID) pointing to sempkm:scopeQuery predicate
  - Migration function migrate_saved_query_to_scope_query() for existing data
  - Frontend IRI construction for scope_query POST bodies
key_files:
  - backend/app/vfs/mount_service.py
  - backend/app/vfs/mount_router.py
  - backend/app/vfs/migrations.py
  - backend/app/browser/workspace.py
  - frontend/static/js/workspace.js
  - backend/tests/test_vfs_scope.py
key_decisions:
  - scope_query stores full IRI (urn:sempkm:query:{uuid}) as RDF IRI type, not xsd:string literal
  - Frontend constructs IRI by prefixing 'urn:sempkm:query:' to UUID from scope dropdown
  - Frontend strips IRI prefix when populating edit form to match dropdown option values
  - _resolve_scope_query_text simplified to accept full IRI directly (no more UUID vs IRI branching)
patterns_established:
  - VFS scope references use full IRIs (urn:sempkm:query:{uuid}) not bare UUID strings
observability_surfaces:
  - Migration function logs triple count at INFO level; grep for migrate_saved_query_to_scope_query
  - _resolve_scope_query_text logs WARNING on failed query resolution; grep for "Failed to resolve saved query"
  - Mount API responses include scope_query field with full IRI value
duration: 25min
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Rename savedQueryId to scopeQuery with IRI storage

**Renamed `savedQueryId` → `scopeQuery` across VFS backend, frontend, and browser workspace with IRI-typed storage and migration function.**

## What Happened

Renamed the `SAVED_QUERY_ID` constant to `SCOPE_QUERY` and `saved_query_id` field to `scope_query` across all VFS Python modules (mount_service, mount_router, strategies, mount_collections) and the browser workspace module. Changed SPARQL INSERT DATA from `"uuid"^^xsd:string` to `<urn:sempkm:query:uuid>` (IRI syntax). Updated frontend JS (`collectFormData`, `populateEditForm`) to construct/parse full IRIs. Removed stale async comment from mount_collections.py. Created migration module with SPARQL UPDATE that renames the predicate and wraps bare UUIDs as IRIs in one atomic operation. Updated tests to use renamed field.

Also discovered and updated `backend/app/browser/workspace.py` which was not listed in the task plan but contained `SAVED_QUERY_ID` imports, SPARQL queries with `?savedQueryId`, and the `_resolve_saved_query_text()` function — all renamed to match.

## Verification

- `python -m pytest tests/test_vfs_scope.py -v` — 16/16 passed
- `rg -rn "savedQueryId|SAVED_QUERY_ID|saved_query_id" backend/ frontend/ -g "*.py" -g "*.js" -g "*.html" | grep -v migration` — zero results
- `python3 -c "import ast; ast.parse(open(f).read())"` — all 6 modified Python files parse successfully
- Migration module `backend/app/vfs/migrations.py` syntactically valid

### Slice-level verification (partial — T02 is not final task):
- ✅ `cd backend && python -m pytest tests/test_vfs_scope.py -v` — 16 passed
- ⬜ `cd backend && python -m pytest tests/test_vfs_path_contract.py -v` — not yet created (T04 territory)
- ⬜ Manual/browser: mount form with type multi-select, preview with saved query — not testable without running app
- ✅ Grep confirms zero occurrences of `savedQueryId` in Python/template/JS (except migration)
- ⬜ Diagnostic: preview endpoint returns 404 for missing scope_query — T03 territory

## Diagnostics

- **Migration inspection:** Run `migrate_saved_query_to_scope_query()` with a SyncTriplestoreClient — logs count at INFO or "nothing to migrate"
- **RDF verification:** `SELECT * FROM <urn:sempkm:mounts> WHERE { ?m <urn:sempkm:scopeQuery> ?q }` — values should be IRIs
- **API verification:** `GET /api/vfs/mounts` response JSON includes `scope_query` field (full IRI or null)
- **Resolution failures:** Grep for `Failed to resolve saved query` in app logs

## Deviations

- `backend/app/browser/workspace.py` was not listed in the task plan but required identical renaming (import, SPARQL variables, binding extraction, function name). Updated as part of the rename sweep.
- `backend/app/vfs/strategies.py` had docstring references to `saved_query_id` — updated to `scope_query`.
- Simplified `_resolve_scope_query_text()` to remove the UUID-vs-IRI branching since scope_query values are now always full IRIs.

## Known Issues

None.

## Files Created/Modified

- `backend/app/vfs/mount_service.py` — Renamed constant, field, SPARQL vars, changed to IRI INSERT syntax
- `backend/app/vfs/mount_router.py` — Renamed imports, request models, SPARQL, IRI INSERT syntax
- `backend/app/vfs/mount_collections.py` — Removed stale saved_query_id async comment
- `backend/app/vfs/strategies.py` — Updated docstring references
- `backend/app/vfs/migrations.py` — New: migration function for predicate rename + value wrapping
- `backend/app/browser/workspace.py` — Renamed import, function, SPARQL vars, binding extraction
- `frontend/static/js/workspace.js` — scope_query in POST bodies with IRI construction, IRI parsing in edit form
- `backend/tests/test_vfs_scope.py` — Updated field names and docstring
