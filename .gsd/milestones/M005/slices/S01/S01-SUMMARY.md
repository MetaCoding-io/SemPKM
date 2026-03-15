---
id: S01
parent: M005
milestone: M005
provides:
  - QueryService (RDF-backed SPARQL query management)
  - Migration script SQL→RDF for saved queries
  - Model-shipped named queries
requires: []
affects:
  - S07  # Views rethink will reference query IRIs
  - S08  # VFS v2 will use saved queries as scope primitive
key_files:
  - backend/app/sparql/query_service.py
  - backend/app/sparql/router.py
  - backend/app/sparql/migrate_queries.py
  - backend/app/views/service.py
  - backend/migrations/versions/010_drop_query_sql_tables.py
  - models/basic-pkm/views/basic-pkm.jsonld
key_decisions:
  - Single-quoted SPARQL literals with _esc() helper to avoid f-string quoting hell
  - ViewSpecService takes QueryService in constructor (optional param for backward compat)
  - SQL models kept in sparql/models.py for migration script only
  - Model queries use sempkm:source predicate to mark as read-only
  - Query IRIs use urn:sempkm:query:{uuid} pattern for URL stability
patterns_established:
  - String concatenation for SPARQL construction (not f-string triple-quotes)
  - _lit() and _dt() helpers for typed literals
  - ASK query for idempotent migration checks
observability_surfaces:
  - logger.info on query save/delete/share operations with query IRI
  - SPARQL query against urn:sempkm:queries graph shows all stored data
  - Admin endpoint POST /admin/migrate-queries with counts
drill_down_paths: []
duration: 2h
verification_result: passed
completed_at: 2026-03-14
---

# S01: Query Storage SQL→RDF Migration

**All saved queries, history, sharing, and promotions now stored as RDF in the triplestore instead of SQL tables. Model-shipped named queries enabled.**

## What Happened

Built QueryService (query_service.py) backed by SPARQL INSERT/DELETE/SELECT against urn:sempkm:queries named graph. Covers full CRUD for saved queries, history with dedup and pruning at 100 entries, sharing (get/update/fork), and promotion/demotion to named views. 31 unit tests verify all operations against mock TriplestoreClient.

Rewired all 15 SQL-backed endpoints in sparql/router.py to use QueryService. Removed 295 lines of SQLAlchemy code, replaced with 137 lines of clean service calls. Updated ViewSpecService and workspace.py to use QueryService for promoted view resolution (removed db session parameter from get_view_spec_by_iri and get_user_promoted_view_specs).

Created data migration script (migrate_queries.py) that reads all 4 SQL tables and writes equivalent RDF triples. Idempotent via ASK check. Added admin endpoint POST /admin/migrate-queries. Created Alembic migration 010 to drop the SQL tables after migration.

Added 3 model-shipped named queries to basic-pkm (Active Projects, Recent Notes, Concept Hierarchy) with sempkm:source marking them read-only. Updated saved query list endpoint to include model queries in response.

## Verification

- 417 tests passing (386 existing + 31 new QueryService tests)
- Zero SQL model imports in router, views/service, or browser/workspace
- sparql/models.py retained only for migration script (not imported by app code)
- All 7 tasks complete per plan

## Deviations

Triple-quoted f-strings with SPARQL literals caused Python syntax errors (nested quotes). Switched to string concatenation with _lit()/_dt() helpers — cleaner and avoids the quoting problem entirely.

## Known Limitations

- Runtime verification against live triplestore deferred (needs Docker stack running)
- The `mark_viewed` endpoint is a no-op — the is_updated tracking was fragile in SQL too
- History entries have UUID IDs from urn:sempkm:query-exec:{uuid} — not the original SQL UUIDs

## Follow-ups

- Run POST /admin/migrate-queries on live stack before applying migration 010
- Frontend SPARQL console needs update to show model queries section (T07 added API, not UI)
- S07/S08 design docs can now reference query IRIs as scope primitive

## Files Created/Modified

- `backend/app/sparql/query_service.py` — new: complete RDF-backed query management service
- `backend/app/sparql/migrate_queries.py` — new: SQL→RDF data migration
- `backend/app/sparql/router.py` — rewired 15 endpoints from SQL to QueryService
- `backend/app/views/service.py` — removed SQL deps, uses QueryService for promoted views
- `backend/app/views/router.py` — removed db parameter from 4 endpoints
- `backend/app/browser/workspace.py` — removed SQL deps, uses QueryService for my-views
- `backend/app/main.py` — passes query_service to ViewSpecService constructor
- `backend/app/dependencies.py` — added get_query_service dependency
- `backend/tests/test_query_service.py` — 31 unit tests
- `backend/migrations/versions/010_drop_query_sql_tables.py` — drops 4 SQL tables
- `backend/migrations/env.py` — removed sparql model imports
- `models/basic-pkm/views/basic-pkm.jsonld` — added 3 named queries

## Forward Intelligence

### What the next slice should know
- QueryService is available via `get_query_service` dependency — use it for any query-related operations
- Model queries use `sempkm:source` predicate — look for this when filtering user vs model queries
- The `urn:sempkm:queries` graph holds ALL query data (saved, history, shares, promotions)

### What's fragile
- SPARQL literal escaping uses single quotes — if query text contains unescaped single quotes, _esc() handles it but complex edge cases may surface
- ViewSpecService's query_service param is optional (None default) for backward compat — if not passed, user views silently return empty

### Authoritative diagnostics
- `SELECT * FROM <urn:sempkm:queries> WHERE { ?s ?p ?o }` — shows all query data in triplestore
- `backend/tests/test_query_service.py` — 31 tests verify all QueryService paths
- `grep -rn 'from app.sparql.models' backend/app/` — should only match migrate_queries.py

### What assumptions changed
- Originally planned to use f-string triple-quotes for SPARQL — discovered Python can't nest quote styles reliably in f-strings, switched to string concatenation with helpers
