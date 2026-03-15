# S02: Views Rethink & VFS Scope Fixes

**Goal:** Consolidate the explorer tree from 31+ flat entries to model-grouped folders, fix VFS scope dropdown (wrong URL + dead backend wiring), clean up 3 duplicate route definitions.

**Demo:** Explorer sidebar shows models as folders with types inside. VFS mount scope dropdown shows saved/model queries in optgroups. Creating a mount scoped to a saved query correctly filters objects.

## Must-Haves

- Explorer tree groups ViewSpecs by model, then by type (one entry per type, carousel handles renderers)
- 3 duplicate route definitions removed from views/router.py
- VFS scope dropdown fetches from correct URL (`/api/sparql/saved?include_shared=true`)
- VFS scope dropdown renders optgroups (My Queries, Model Queries, Shared)
- `build_scope_filter()` resolves `saved_query_id` → query text → SPARQL filter
- Saved Views folder merges MY VIEWS into VIEWS section
- All existing tests pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/ -x -q` — all tests pass
- Visual verification: explorer tree renders grouped by model
- VFS scope dropdown populated with queries (browser check)

## Tasks

- [ ] **T01: Remove duplicate routes and rewrite explorer endpoint** `est:45m`
  - Why: 3 duplicate routes are dead code; explorer needs model grouping
  - Files: `backend/app/views/router.py`, `backend/app/templates/browser/views_explorer.html`
  - Do:
    1. Delete duplicate route definitions at lines 468-594 (second `/explorer`, `/menu`, `/available`)
    2. Rewrite first `/explorer` endpoint to group by `source_model`, then by `target_class` within each model
    3. Resolve model display names via `label_service`
    4. Rewrite `views_explorer.html` template: model folders → type entries (one per type, default renderer)
    5. Add "Saved Views" folder at the bottom for promoted query views
  - Verify: app loads, explorer renders correctly
  - Done when: explorer shows model folders, no duplicate routes

- [ ] **T02: Fix VFS scope dropdown fetch URL** `est:20m`
  - Why: Frontend fetches `/api/sparql/queries` (404) instead of `/api/sparql/saved?include_shared=true`
  - Files: `frontend/static/js/workspace.js`
  - Do:
    1. Change fetch URL from `/api/sparql/queries` to `/api/sparql/saved?include_shared=true`
    2. Parse grouped response (`my_queries`, `shared_with_me`, `model_queries`)
    3. Render optgroups in the scope dropdown: My Queries, Model Queries (read-only), Shared
    4. Model queries use full IRI as value; user queries use `query:{uuid}` prefix
  - Verify: scope dropdown shows queries when creating/editing a mount
  - Done when: dropdown populated, correct values selected

- [ ] **T03: Wire `build_scope_filter()` to resolve saved queries** `est:30m`
  - Why: `build_scope_filter()` ignores `saved_query_id` entirely — mounts can't filter by query
  - Files: `backend/app/vfs/strategies.py`, `backend/app/vfs/mount_service.py`
  - Do:
    1. Add query resolution to `build_scope_filter()`: if `mount.saved_query_id` is set, look up the query text from SQLite (user queries) or RDF (model queries)
    2. Execute the saved query to get a set of IRIs
    3. Inject those IRIs as a `VALUES ?iri { ... }` clause
    4. Handle edge cases: query not found, query returns no results, query returns too many results
  - Verify: mount scoped to a saved query only shows matching objects
  - Done when: VFS mount filtering works end-to-end with saved queries

- [ ] **T04: Tests** `est:20m`
  - Why: Verify route cleanup and scope resolution
  - Files: `backend/tests/test_views_explorer.py` (new), `backend/tests/test_vfs_scope.py` (new)
  - Do:
    1. Test explorer endpoint returns model-grouped data
    2. Test `build_scope_filter()` with saved_query_id resolution
    3. Test edge cases (missing query, empty results)
  - Verify: `cd backend && .venv/bin/python -m pytest tests/ -x -q`
  - Done when: all tests pass including new ones

## Files Likely Touched

- `backend/app/views/router.py`
- `backend/app/templates/browser/views_explorer.html`
- `frontend/static/js/workspace.js`
- `backend/app/vfs/strategies.py`
- `backend/app/vfs/mount_service.py`
- `backend/tests/test_views_explorer.py` (new)
- `backend/tests/test_vfs_scope.py` (new)
