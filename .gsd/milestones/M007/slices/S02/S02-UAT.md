# S02: VFS Quick Wins — Type Filter, Query IRI, Preview — UAT

**Milestone:** M007
**Written:** 2026-03-16

## UAT Type

- UAT mode: mixed (artifact-driven for tests/grep, live-runtime for mount form and preview)
- Why this mode is sufficient: Unit tests verify SPARQL generation and path contract logic; browser verification confirms UI round-trip. No human judgment needed.

## Preconditions

- Docker stack running (`docker compose up -d`)
- At least one Mental Model installed (basic-pkm) so types exist for type filter
- At least one saved SPARQL query exists (for scope_query testing)
- Backend logs accessible (`docker compose logs -f api`)

## Smoke Test

Run `cd backend && python -m pytest tests/test_vfs_scope.py tests/test_vfs_path_contract.py -v` — expect 47/47 passed.

## Test Cases

### 1. Type filter VALUES clause generation

1. Open Python shell in backend venv
2. Create a `MountDefinition` with `type_filter=["urn:ex:Note", "urn:ex:Person"]`
3. Call `build_scope_filter(mount)`
4. **Expected:** Output contains `VALUES ?type { <urn:ex:Note> <urn:ex:Person> }` and `?iri a ?type .`

### 2. Type filter AND-composes with scope

1. Create a `MountDefinition` with both `sparql_scope="SELECT ?s WHERE { ?s a <urn:ex:Foo> }"` and `type_filter=["urn:ex:Note"]`
2. Call `build_scope_filter(mount)`
3. **Expected:** Output contains both the VALUES clause and the scope subquery — both filter constraints present

### 3. Mount form shows type checkboxes

1. Navigate to Settings → VFS in the workspace
2. Click "New Mount" (or equivalent)
3. **Expected:** A "Type Filter" section appears with checkboxes for each type (Person, Note, Project, Concept, etc.)
4. Check 2 types (e.g., Note and Person)
5. Click Preview
6. **Expected:** Preview returns a count reflecting only objects of those two types

### 4. Type filter persists on create and pre-selects on edit

1. Create a mount with name "UAT Type Test", strategy "by-type", and 2 types checked
2. Mount card appears in list showing "· 2 types" in the meta line
3. Click Edit on the mount
4. **Expected:** The 2 previously selected types are pre-checked; others are unchecked
5. Uncheck one type and save
6. Click Edit again
7. **Expected:** Only the 1 remaining type is checked

### 5. savedQueryId fully renamed to scopeQuery

1. Run: `rg -rn "savedQueryId|SAVED_QUERY_ID|saved_query_id" backend/ frontend/ -g "*.py" -g "*.js" -g "*.html" | grep -v migration`
2. **Expected:** Zero results

### 6. scope_query stores as IRI in mount create

1. Create a mount with a saved query selected in the scope dropdown
2. Query the triplestore: `SELECT * FROM <urn:sempkm:mounts> WHERE { ?m <urn:sempkm:scopeQuery> ?q }`
3. **Expected:** `?q` value is an IRI (`<urn:sempkm:query:{uuid}>`), not a string literal

### 7. scope_query populates edit form correctly

1. Edit a mount that has a scope_query set
2. **Expected:** The scope dropdown shows the correct saved query selected (not blank)

### 8. Preview with scope_query resolves saved query

1. Create or select a mount with scope_query pointing to a valid saved query
2. Click Preview
3. **Expected:** Preview returns filtered results matching the saved query scope
4. Check backend logs for `Resolving scope_query` DEBUG message

### 9. Preview returns 404 for invalid scope_query

1. Via API (curl/httpie), POST to preview endpoint with `scope_query` set to `urn:sempkm:query:nonexistent-uuid`
2. **Expected:** HTTP 404 response with `{"detail": "Saved query not found"}`

### 10. Path contract — slug generation

1. Run `cd backend && python -m pytest tests/test_vfs_path_contract.py::TestSlugify -v`
2. **Expected:** 15/15 passed — covers normal, unicode, special chars, empty, whitespace, long labels

### 11. Path contract — collision dedup

1. Run `cd backend && python -m pytest tests/test_vfs_path_contract.py::TestBuildFileMap -v`
2. **Expected:** 11/11 passed — covers hash suffix on collision, isolation of non-colliding, reverse lookup

### 12. Path contract documentation

1. Open `docs/guide/23-vfs.md`
2. **Expected:** Contains "Path Contract" section with:
   - Forward mapping (label → slug → filename.md)
   - Reverse mapping (filename → IRI via file_map lookup)
   - Collision dedup explanation (IRI SHA-256 hash prefix)
   - Filename instability caveat

## Edge Cases

### Empty type_filter treated as no filter

1. Create a `MountDefinition` with `type_filter=[]`
2. Call `build_scope_filter(mount)`
3. **Expected:** No VALUES clause — empty list is a no-op, same as `None`

### scope_query without sync_client in WebDAV

1. Call `build_scope_filter(mount_with_scope_query)` without passing `sync_client`
2. **Expected:** scope_query is silently ignored, no crash — scope_filter based on other fields only

### Type filter with nonexistent type IRI

1. Create mount with `type_filter=["urn:ex:NonexistentType"]`
2. WebDAV listing for that mount
3. **Expected:** Empty directory (VALUES matches zero objects) — no error, no crash

### Unicode in slug

1. `_slugify("Über Alles")` → `"ber-alles"` (non-ASCII stripped)
2. `_slugify("日本語")` → `"untitled"` (all chars stripped, empty fallback)

## Failure Signals

- Any test in `test_vfs_scope.py` or `test_vfs_path_contract.py` fails
- `rg savedQueryId` finds results outside migration files
- Mount form has no type checkbox section
- Preview with scope_query returns empty/null when query exists
- Preview with invalid scope_query returns 200 instead of 404
- Mount edit form doesn't pre-select saved types
- Mount list cards don't show type count

## Requirements Proved By This UAT

- VFS-07 — type_filter VALUES clause, AND composition, type multi-select UI (tests 1-4)
- VFS-08 — savedQueryId renamed, IRI storage (tests 5-7)
- VFS-09 — preview resolves scope, 404 on missing (tests 8-9)
- VFS-10 — path contract documented and tested (tests 10-12)

## Not Proven By This UAT

- Migration function execution on real data with existing mounts (no existing mounts with savedQueryId in test environment)
- WebDAV listing with live triplestore confirming type_filter restricts file listing (requires mounted client)
- Performance with large type_filter lists (>10 types)

## Notes for Tester

- The M007 worktree Docker stack may have a LuceneSail locking issue (`RepositoryLockedException`). If so, run browser tests against the main project stack by copying worktree files.
- Migration function exists at `backend/app/vfs/migrations.py` but has no automatic trigger yet — it's meant to be called once when upgrading from pre-S02 data.
- Type checkboxes fetch from the same endpoint as type filter pills in generic views (`/browser/views/type-pills`). If no models are installed, no types appear.
