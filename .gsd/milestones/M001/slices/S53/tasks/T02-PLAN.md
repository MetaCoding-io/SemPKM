# T02: 53-sparql-power-user 02

**Slice:** S53 — **Milestone:** M001

## Description

Build the complete SPARQL console UI as a workspace bottom panel tab: CodeMirror 6 editor with syntax highlighting, toolbar with Run/Save/History/Saved buttons, result table with IRI pill rendering, session cell history, history/saved dropdowns with star-to-save, ontology-aware autocomplete, and admin page removal.

Purpose: This replaces Yasgui entirely with a native SemPKM SPARQL interface that matches the design language, supports all four SPARQL-02/03/05/06 requirements on the frontend, and eliminates the separate admin SPARQL page.

Output: New `sparql-console.js` module (CM6 editor + all UI logic), `sparql_panel.html` template, workspace.html modifications for tab registration, CSS for the panel, and removal of the admin SPARQL page.

## Must-Haves

- [ ] "SPARQL tab appears in the bottom panel for non-guest users"
- [ ] "CodeMirror 6 editor loads with SPARQL syntax highlighting when the tab is activated"
- [ ] "User can type a query, press Run (or Ctrl+Enter), and see results in a table"
- [ ] "Result cells containing object IRIs display as labeled pills with type icons"
- [ ] "Clicking an IRI pill opens a workspace tab for that object"
- [ ] "Previous query+result pairs appear as collapsible cells below the active editor"
- [ ] "History dropdown shows recent queries from server with timestamps"
- [ ] "Saved dropdown shows named queries; user can save current query with name+description"
- [ ] "Star icon in history dropdown promotes a history entry to saved"
- [ ] "Editor provides autocomplete suggestions for SPARQL keywords, prefixes, classes, and predicates"
- [ ] "Type badges (C/P/D/K) appear in autocomplete dropdown"
- [ ] "Admin /admin/sparql page is removed; sidebar link opens workspace with SPARQL panel"
- [ ] "Guest users do not see the SPARQL tab"

## Files

- `frontend/static/js/sparql-console.js`
- `frontend/static/css/workspace.css`
- `backend/app/templates/browser/workspace.html`
- `backend/app/templates/browser/sparql_panel.html`
- `frontend/static/js/workspace.js`
- `backend/app/admin/router.py`
- `backend/app/templates/components/_sidebar.html`
