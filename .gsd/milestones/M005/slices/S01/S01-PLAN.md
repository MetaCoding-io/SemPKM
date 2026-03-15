# S01: Query Storage SQL→RDF Migration

**Goal:** Move saved queries, query history, sharing, and promoted views from SQL tables to RDF in the triplestore, enabling model-shipped named queries and IRI-addressable query resources for views and VFS scoping.

**Demo:** Open SPARQL console → save a query → share it → promote to view → all works identically. SPARQL query against `urn:sempkm:queries` shows the saved query as RDF triples. SQL tables are gone.

## Must-Haves

- All 4 SQL tables migrated: `SavedSparqlQuery`, `SharedQueryAccess`, `PromotedQueryView`, `SparqlQueryHistory`
- `QueryService` backed by RDF with clean interface (no SQLAlchemy in SPARQL router)
- All existing SPARQL console endpoints work identically (save, load, update, delete, share, unshare, fork, promote, demote, history)
- Data migration path for existing saved queries (SQL → RDF)
- Alembic migration to drop SQL tables
- Model-shipped named queries loadable from model views graphs
- Unit tests for QueryService CRUD operations

## Proof Level

- This slice proves: integration (full SPARQL console round-trip against RDF storage)
- Real runtime required: yes (triplestore must be running)
- Human/UAT required: yes (SPARQL console UX should feel identical)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_query_service.py -q` — unit tests for QueryService CRUD
- Browser: SPARQL console save/load/share/promote cycle works
- SPARQL query `SELECT * FROM <urn:sempkm:queries> WHERE { ?s a <urn:sempkm:vocab:SavedQuery> }` returns saved queries
- E2E: `e2e/tests/05-admin/sparql-console.spec.ts` and `sparql-workspace.spec.ts` still pass
- No references to `SavedSparqlQuery`, `SharedQueryAccess`, `PromotedQueryView`, or `SparqlQueryHistory` remain in app code (only in migration files)

## Observability / Diagnostics

- Runtime signals: logger.info on query save/delete/share operations with query IRI
- Inspection surfaces: SPARQL query against `urn:sempkm:queries` graph shows all stored queries
- Failure visibility: QueryService methods raise explicit exceptions with context (query not found, permission denied, etc.)
- Redaction constraints: query text is not a secret but user IDs should use IRIs not raw UUIDs in logs

## Integration Closure

- Upstream surfaces consumed: `TriplestoreClient` for SPARQL queries/updates, `User` model for owner mapping
- New wiring introduced: `QueryService` injected via FastAPI dependency, replaces `get_db_session` in SPARQL router
- What remains: S07/S08 design docs will reference query IRIs for view/VFS scoping (not built in this slice)

## Tasks

- [x] **T01: Build QueryService with RDF backend** `est:2h`
  - Why: Core service that replaces all SQLAlchemy query operations with SPARQL/RDF
  - Files: `backend/app/sparql/query_service.py` (new), `backend/app/rdf/namespaces.py`
  - Do: Create `QueryService` class with methods: `save_query()`, `get_query()`, `list_user_queries()`, `update_query()`, `delete_query()`, `save_history()`, `get_history()`, `clear_history()`, `share_query()`, `unshare_query()`, `get_shares()`, `fork_query()`, `promote_query()`, `demote_query()`, `get_promotion_status()`, `list_promoted_views()`. All backed by SPARQL INSERT/DELETE/SELECT against `urn:sempkm:queries` graph. Add `SEMPKM_QUERIES_GRAPH` constant to namespaces. History entries capped at 50 per user (matching current SQL behavior). Query IRIs: `urn:sempkm:query:{uuid}`. History IRIs: `urn:sempkm:query-exec:{uuid}`. Promotion IRIs: `urn:sempkm:query-view:{uuid}`.
  - Verify: Unit tests in `test_query_service.py` covering CRUD, sharing, promotion
  - Done when: All QueryService methods have unit tests that pass

- [x] **T02: Unit tests for QueryService** `est:1h`
  - Why: Verify the service works correctly before wiring it into routes
  - Files: `backend/tests/test_query_service.py` (new)
  - Do: Test save/get/list/update/delete for queries. Test history save/list/clear with cap enforcement. Test share/unshare/get_shares. Test promote/demote/get_promotion_status. Test fork creates independent copy. Use mock TriplestoreClient or test against SPARQL result fixtures. Test permission checks (can't delete someone else's query).
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_query_service.py -v`
  - Done when: All tests pass, covering happy path and key error cases

- [x] **T03: Rewire SPARQL router to use QueryService** `est:2h`
  - Why: Replace ~65 SQLAlchemy references in sparql/router.py with QueryService calls
  - Files: `backend/app/sparql/router.py`, `backend/app/dependencies.py`
  - Do: Add `get_query_service` dependency. Replace every `db.execute(select(SavedSparqlQuery)...)` with `query_service.get_query(...)` etc. Remove `get_db_session` dependency from all query-related endpoints (keep it for any non-query endpoints if they exist). Keep Pydantic response schemas — they still define the API contract, just populated from RDF instead of ORM. Remove imports of SQL models. The 17 query-related endpoints must maintain identical HTTP behavior (same paths, same request/response shapes, same status codes).
  - Verify: Start the stack, open SPARQL console, save a query, reload page, query appears. Share with another user if multi-user, promote to view, verify view appears in MY VIEWS.
  - Done when: Zero references to SQL query models in `sparql/router.py`

- [x] **T04: Update ViewSpecService for RDF-backed promoted views** `est:45m`
  - Why: `ViewSpecService.get_user_promoted_view_specs()` and `get_view_spec_by_iri()` currently join SQL tables
  - Files: `backend/app/views/service.py`, `backend/app/browser/workspace.py`
  - Do: Replace SQL queries in `get_user_promoted_view_specs()` and the `urn:sempkm:user-view:` branch of `get_view_spec_by_iri()` with calls to `QueryService.list_promoted_views()` and `QueryService.get_promoted_view()`. Update `workspace.py` demote button query (line ~925) to use QueryService. Remove SQL model imports from both files.
  - Verify: Promoted views still appear in MY VIEWS explorer section. Clicking a promoted view opens it in a tab.
  - Done when: No SQL query model imports in `views/service.py` or `browser/workspace.py`

- [x] **T05: Data migration script** `est:1h`
  - Why: Existing users have saved queries in SQL that need to move to RDF
  - Files: `backend/app/sparql/migrate_queries.py` (new), `backend/app/admin/router.py`
  - Do: Create async migration function that reads all rows from `SavedSparqlQuery`, `SharedQueryAccess`, `PromotedQueryView`, `SparqlQueryHistory` and writes equivalent RDF triples to `urn:sempkm:queries` graph. Map user UUIDs to user IRIs (`urn:sempkm:user:{uuid}`). Preserve original UUIDs as query IRIs for URL stability. Add an admin endpoint `POST /admin/migrate-queries` (same pattern as `/admin/migrate-tags`). Log counts: queries migrated, shares, promotions, history entries. Idempotent: skip if triples already exist.
  - Verify: Run migration against stack with existing saved queries. SPARQL console shows same queries before and after.
  - Done when: Migration endpoint works, all existing data preserved in RDF

- [x] **T06: Alembic migration to drop SQL tables** `est:30m`
  - Why: Clean up SQL tables after data is in RDF
  - Files: `backend/migrations/versions/` (new migration file)
  - Do: Generate Alembic migration that drops `sparql_query_history`, `saved_sparql_queries`, `shared_query_access`, `promoted_query_views` tables. The migration should check that the RDF migration has been run (or print a warning). Remove model imports from `migrations/env.py` if they were only needed for these tables.
  - Verify: `cd backend && alembic upgrade head` runs cleanly
  - Done when: SQL tables dropped, Alembic history clean

- [x] **T07: Model-shipped named queries support** `est:1h`
  - Why: Enable Mental Models to ship named queries that appear alongside user queries (read-only)
  - Files: `backend/app/sparql/query_service.py`, `models/basic-pkm/views/basic-pkm.jsonld`
  - Do: Add `list_model_queries()` to QueryService — queries model views graphs for `sempkm:SavedQuery` entries with `sempkm:source` set to a model ID. Add `list_all_queries()` that merges user + model queries, marking model queries as `readonly: true`. Add 2-3 example named queries to basic-pkm views.jsonld (e.g. "Active Projects", "Recent Notes"). Update the SPARQL console saved queries list endpoint to include model queries in the response.
  - Verify: SPARQL console shows model-shipped queries with a read-only indicator. User cannot edit/delete them. User can fork (copy) a model query.
  - Done when: Model queries visible in SPARQL console, fork works, edit/delete blocked

## Files Likely Touched

- `backend/app/sparql/query_service.py` (new)
- `backend/app/sparql/router.py`
- `backend/app/sparql/models.py` (eventually removed or emptied)
- `backend/app/sparql/schemas.py` (kept — API contract unchanged)
- `backend/app/sparql/migrate_queries.py` (new)
- `backend/app/views/service.py`
- `backend/app/browser/workspace.py`
- `backend/app/dependencies.py`
- `backend/app/rdf/namespaces.py`
- `backend/tests/test_query_service.py` (new)
- `backend/migrations/versions/` (new migration)
- `models/basic-pkm/views/basic-pkm.jsonld`
