# T02: 35-owl2-rl-inference 02

**Slice:** S35 — **Milestone:** M001

## Description

Modify all SPARQL queries and UI templates to display inferred triples alongside user-created data. Relations panel shows inferred badge, object read view uses two-column layout, graph view uses dashed lines for inferred edges.

Purpose: Without this, inferred triples exist in the triplestore but are invisible to users. This plan makes inference results visible everywhere users look at their data.
Output: Modified SPARQL queries, updated templates with inferred badges, two-column object read layout, dashed graph edges.

## Must-Haves

- [ ] "Relations panel SPARQL queries use UNION to query both urn:sempkm:current and urn:sempkm:inferred, annotating results with source graph"
- [ ] "Inferred triples in relations panel show a subtle 'inferred' badge (small label or icon)"
- [ ] "Object read view shows inferred properties in a right-hand column, user-created on the left"
- [ ] "Graph view queries include urn:sempkm:inferred with dashed-line styling for inferred edges"
- [ ] "Labels service resolves labels from both current and inferred graphs"
- [ ] "scope_to_current_graph() gains an include_inferred parameter"
- [ ] "Inferred relation links are fully clickable/navigable"

## Files

- `backend/app/sparql/client.py`
- `backend/app/browser/router.py`
- `backend/app/views/service.py`
- `backend/app/services/labels.py`
- `backend/app/templates/browser/properties.html`
- `backend/app/templates/browser/object_read.html`
- `frontend/static/css/workspace.css`
