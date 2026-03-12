# T01: 53-sparql-power-user 01

**Slice:** S53 — **Milestone:** M001

## Description

Build the backend data layer and API endpoints for SPARQL query history, saved queries, result enrichment, and ontology vocabulary.

Purpose: All four Phase 53 features (history, saved queries, IRI pills, autocomplete) depend on backend API endpoints. Building these first lets the UI plan (Plan 02) consume real APIs without stubs.

Output: Two new SQLAlchemy models, one Alembic migration, Pydantic schemas, and 7+ new API endpoints on the SPARQL router. The existing SPARQL POST endpoint is enhanced with optional result enrichment.

## Must-Haves

- [ ] "Query history is persisted to SQLite and scoped per user"
- [ ] "Saved queries are persisted with name, description, and query text per user"
- [ ] "SPARQL POST endpoint returns enriched results with labels, types, and icons for object IRIs"
- [ ] "Vocabulary endpoint returns classes, predicates, and prefixes from installed Mental Model ontology graphs"
- [ ] "History CRUD supports list, create-on-execute, and prune-to-100"
- [ ] "Saved query CRUD supports list, create, update, and delete"

## Files

- `backend/app/sparql/models.py`
- `backend/app/sparql/schemas.py`
- `backend/app/sparql/router.py`
- `backend/migrations/versions/007_sparql_tables.py`
