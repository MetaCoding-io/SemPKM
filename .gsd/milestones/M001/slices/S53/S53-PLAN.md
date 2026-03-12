# S53: Sparql Power User

**Goal:** Build the backend data layer and API endpoints for SPARQL query history, saved queries, result enrichment, and ontology vocabulary.
**Demo:** Build the backend data layer and API endpoints for SPARQL query history, saved queries, result enrichment, and ontology vocabulary.

## Must-Haves


## Tasks

- [x] **T01: 53-sparql-power-user 01** `est:4min`
  - Build the backend data layer and API endpoints for SPARQL query history, saved queries, result enrichment, and ontology vocabulary.

Purpose: All four Phase 53 features (history, saved queries, IRI pills, autocomplete) depend on backend API endpoints. Building these first lets the UI plan (Plan 02) consume real APIs without stubs.

Output: Two new SQLAlchemy models, one Alembic migration, Pydantic schemas, and 7+ new API endpoints on the SPARQL router. The existing SPARQL POST endpoint is enhanced with optional result enrichment.
- [x] **T02: 53-sparql-power-user 02** `est:5min`
  - Build the complete SPARQL console UI as a workspace bottom panel tab: CodeMirror 6 editor with syntax highlighting, toolbar with Run/Save/History/Saved buttons, result table with IRI pill rendering, session cell history, history/saved dropdowns with star-to-save, ontology-aware autocomplete, and admin page removal.

Purpose: This replaces Yasgui entirely with a native SemPKM SPARQL interface that matches the design language, supports all four SPARQL-02/03/05/06 requirements on the frontend, and eliminates the separate admin SPARQL page.

Output: New `sparql-console.js` module (CM6 editor + all UI logic), `sparql_panel.html` template, workspace.html modifications for tab registration, CSS for the panel, and removal of the admin SPARQL page.

## Files Likely Touched

- `backend/app/sparql/models.py`
- `backend/app/sparql/schemas.py`
- `backend/app/sparql/router.py`
- `backend/migrations/versions/007_sparql_tables.py`
- `frontend/static/js/sparql-console.js`
- `frontend/static/css/workspace.css`
- `backend/app/templates/browser/workspace.html`
- `backend/app/templates/browser/sparql_panel.html`
- `frontend/static/js/workspace.js`
- `backend/app/admin/router.py`
- `backend/app/templates/components/_sidebar.html`
