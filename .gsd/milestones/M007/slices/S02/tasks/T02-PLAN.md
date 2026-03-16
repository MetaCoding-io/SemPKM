---
estimated_steps: 8
estimated_files: 5
---

# T02: Rename savedQueryId to scopeQuery with IRI storage

**Slice:** S02 — VFS Quick Wins — Type Filter, Query IRI, Preview
**Milestone:** M007

## Description

Rename the `sempkm:savedQueryId` predicate to `sempkm:scopeQuery` across the entire VFS codebase. Change value storage from bare UUID string literals (`"abc-def"^^xsd:string`) to full IRIs (`<urn:sempkm:query:abc-def>`). Write a migration SPARQL UPDATE that renames existing triples and wraps values. This aligns VFS with the Views Rethink pattern (D099).

## Steps

1. **Rename constant and field in `mount_service.py`:**
   - Rename `SAVED_QUERY_ID = f"{NS_SEMPKM}savedQueryId"` → `SCOPE_QUERY = f"{NS_SEMPKM}scopeQuery"`
   - Rename `saved_query_id` field on `MountDefinition` → `scope_query`
   - Update `to_dict()`: `"scope_query": self.scope_query`
   - Update all SPARQL queries in mount_service.py that reference `SAVED_QUERY_ID` → `SCOPE_QUERY`
   - Update all `?savedQueryId` SPARQL variable names → `?scopeQuery`
   - Update `_binding_to_mount()` and `_validate_mount_path()` references
   - Change INSERT DATA from `"{value}"^^xsd:string` to `<{value}>` (IRI syntax)
   - In binding parsing, extract IRI value: `b.get("scopeQuery", {}).get("value")` — this already returns the IRI string for IRI-typed values
   - Update `update_mount()` to handle `scope_query` in updates dict

2. **Rename in `mount_router.py`:**
   - Update import: `SAVED_QUERY_ID` → `SCOPE_QUERY`
   - Rename `saved_query_id` field on `MountCreateRequest`, `MountUpdateRequest`, `MountPreviewRequest` → `scope_query`
   - Update all SPARQL queries (OPTIONAL bindings, variable names)
   - Change INSERT DATA from string literal to IRI: `<{mount_iri}> <{SCOPE_QUERY}> <{body.scope_query}>` (no quotes, no xsd:string)
   - Update DELETE DATA similarly
   - Update async binding extraction

3. **Remove stale comment in `mount_collections.py`:**
   - Lines 117-120 have a comment about saved_query_id needing async. Remove it (T03 will wire the actual resolution).

4. **Update `frontend/static/js/workspace.js`:**
   - In `mountSubmitForm()`: change `saved_query_id` in POST body to `scope_query`. Change value from bare UUID to full IRI: when scope dropdown value starts with `query:`, construct `urn:sempkm:query:{uuid}` instead of just `{uuid}`.
   - In `populateEditForm()`: change `mount.saved_query_id` → `mount.scope_query`. Extract UUID from IRI for matching scope dropdown value: if scope_query starts with `urn:sempkm:query:`, strip prefix for `query:` option matching.
   - In `mountPreview()`: change `saved_query_id` → `scope_query` in preview POST body. Send full IRI.

5. **Update `backend/app/templates/browser/_vfs_settings.html`:**
   - Check for any hardcoded `saved_query_id` references (likely none — form uses JS).

6. **Write migration function:**
   - Create `backend/app/vfs/migrations.py` (or add to mount_service.py) with a function `migrate_saved_query_to_scope_query()` that:
     - Runs a SPARQL UPDATE on `urn:sempkm:mounts`:
       ```sparql
       DELETE { ?mount <urn:sempkm:vocab:savedQueryId> ?oldVal }
       INSERT { ?mount <urn:sempkm:vocab:scopeQuery> ?newIri }
       WHERE {
         GRAPH <urn:sempkm:mounts> {
           ?mount <urn:sempkm:vocab:savedQueryId> ?oldVal
           BIND(IRI(CONCAT("urn:sempkm:query:", STR(?oldVal))) AS ?newIri)
         }
       }
       ```
     - This handles bare UUIDs → full IRIs and predicate rename in one query

7. **Update test file `backend/tests/test_vfs_scope.py`:**
   - Change any `saved_query_id=` kwargs in `MountDefinition()` constructors to `scope_query=`
   - Verify tests still pass with renamed field

8. Run full test suite to confirm no regressions.

## Must-Haves

- [ ] Zero occurrences of `savedQueryId` in .py/.js/.html files (except migration code)
- [ ] `scope_query` stored as IRI (`<urn:sempkm:query:{uuid}>`) not string literal
- [ ] Migration SPARQL renames predicate AND wraps values
- [ ] JS constructs full IRI from scope dropdown UUID
- [ ] All existing tests pass with renamed field

## Verification

- `cd backend && python -m pytest tests/test_vfs_scope.py -v` — all pass
- `rg -rn "savedQueryId" backend/ frontend/ --include="*.py" --include="*.js" --include="*.html" | grep -v migration` — zero results
- Migration function exists and is syntactically correct

## Inputs

- `backend/app/vfs/mount_service.py` — `MountDefinition` with `type_filter` field from T01
- `backend/app/vfs/mount_router.py` — async REST endpoints with `saved_query_id` references
- `backend/app/vfs/mount_collections.py` — stale comment at lines 117-120
- `frontend/static/js/workspace.js` — `mountSubmitForm()` and `populateEditForm()` functions
- `backend/tests/test_vfs_scope.py` — tests referencing `saved_query_id`

## Expected Output

- `backend/app/vfs/mount_service.py` — `scope_query` field, `SCOPE_QUERY` constant, IRI storage
- `backend/app/vfs/mount_router.py` — all endpoints use `scope_query` with IRI values
- `backend/app/vfs/mount_collections.py` — stale comment removed
- `frontend/static/js/workspace.js` — `scope_query` in POST bodies with full IRI construction
- `backend/app/vfs/migrations.py` (new) — migration function
- `backend/tests/test_vfs_scope.py` — updated field references

## Observability Impact

- **API response shape change:** Mount API responses now include `scope_query` (full IRI string like `urn:sempkm:query:{uuid}`) instead of `saved_query_id` (bare UUID). Inspect via `GET /api/vfs/mounts` response JSON.
- **Migration logging:** `migrate_saved_query_to_scope_query()` logs at INFO: count of migrated triples, or "nothing to migrate" if none found. Grep for `migrate_saved_query_to_scope_query` in app logs.
- **RDF storage change:** `SCOPE_QUERY` triples are now IRI-typed (`<urn:sempkm:query:uuid>`) instead of `xsd:string`. Inspect via SPARQL on `urn:sempkm:mounts` graph: `SELECT * WHERE { ?m <urn:sempkm:scopeQuery> ?q }` — values should be IRIs.
- **Scope query resolution:** `_resolve_scope_query_text()` in workspace.py logs WARNING when a scope_query IRI fails to resolve. Grep for `Failed to resolve saved query` in app logs.
