# S52: Bug Fixes Security

**Goal:** Fix two known regressions: (1) lint dashboard filter controls overflow on narrow viewports, and (2) event log fails to render badges, diffs, and undo for compound operation types like "body.
**Demo:** Fix two known regressions: (1) lint dashboard filter controls overflow on narrow viewports, and (2) event log fails to render badges, diffs, and undo for compound operation types like "body.

## Must-Haves


## Tasks

- [x] **T01: 52-bug-fixes-security 01** `est:6min`
  - Fix two known regressions: (1) lint dashboard filter controls overflow on narrow viewports, and (2) event log fails to render badges, diffs, and undo for compound operation types like "body.set,object.create". Also implement undo for object.create events via compensating event (soft-archive).

Purpose: Close FIX-01 and FIX-02 requirements — known bugs that degrade the event log and lint dashboard UX.
Output: Responsive lint filters, compound event display, and object.create undo.
- [x] **T02: 52-bug-fixes-security 02** `est:3min`
  - Gate SPARQL query access by user role: guests get no access (403 + hidden UI), members can only query the current graph (no all_graphs, no FROM/GRAPH clauses), owners get unrestricted access.

Purpose: Close the SPARQL-01 security requirement — prevent unauthorized data access via SPARQL queries.
Output: Three-layer access control (API enforcement, query clause detection, UI hiding).

## Files Likely Touched

- `frontend/static/css/workspace.css`
- `backend/app/events/query.py`
- `backend/app/templates/browser/event_log.html`
- `backend/app/templates/browser/event_detail.html`
- `backend/app/browser/router.py`
- `backend/app/sparql/router.py`
- `backend/app/sparql/client.py`
- `backend/app/admin/router.py`
- `backend/app/templates/browser/workspace.html`
- `backend/app/templates/components/_sidebar.html`
