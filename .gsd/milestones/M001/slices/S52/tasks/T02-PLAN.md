# T02: 52-bug-fixes-security 02

**Slice:** S52 — **Milestone:** M001

## Description

Gate SPARQL query access by user role: guests get no access (403 + hidden UI), members can only query the current graph (no all_graphs, no FROM/GRAPH clauses), owners get unrestricted access.

Purpose: Close the SPARQL-01 security requirement — prevent unauthorized data access via SPARQL queries.
Output: Three-layer access control (API enforcement, query clause detection, UI hiding).

## Must-Haves

- [ ] "Guest users receive HTTP 403 when calling /api/sparql and the SPARQL console tab is hidden from the bottom panel"
- [ ] "Member users can execute SPARQL queries against the current graph but cannot use all_graphs=true, FROM clauses, or GRAPH clauses"
- [ ] "Owner users have unrestricted SPARQL access including all_graphs=true"
- [ ] "Admin SPARQL page (/admin/sparql) sidebar link is hidden from guests; page still accessible to members and owners"

## Files

- `backend/app/sparql/router.py`
- `backend/app/sparql/client.py`
- `backend/app/admin/router.py`
- `backend/app/templates/browser/workspace.html`
- `backend/app/templates/components/_sidebar.html`
