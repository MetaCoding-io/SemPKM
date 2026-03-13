---
id: T01
parent: S02
milestone: M003
provides:
  - _handle_hierarchy handler with real SPARQL query for root objects (FILTER NOT EXISTS dcterms:isPartOf)
  - GET /browser/explorer/children endpoint for lazy child expansion
  - hierarchy_tree.html template for root hierarchy nodes
  - hierarchy_children.html template for child nodes
  - label_service wired into explorer_tree dispatcher
key_files:
  - backend/app/browser/workspace.py
  - backend/app/templates/browser/hierarchy_tree.html
  - backend/app/templates/browser/hierarchy_children.html
key_decisions:
  - Added **_kwargs to _handle_by_type to absorb the new label_service param passed by explorer_tree dispatcher
  - Hierarchy nodes render as .tree-node (not .tree-leaf) since any node could have children — recursive expansion pattern
  - Label click uses event.stopPropagation() on the span to prevent triggering the htmx click-once expansion on the parent node
patterns_established:
  - Hierarchy handler signature: async fn(request, label_service, icon_svc, **_kwargs) — accepts label_service directly
  - explorer_tree dispatcher passes label_service=label_service to all handlers; handlers that don't need it absorb via **_kwargs
  - Both hierarchy templates share identical node structure for recursive expansion consistency
observability_surfaces:
  - DEBUG log "Hierarchy roots query returned %d objects" in app.browser.workspace logger
  - DEBUG log "Hierarchy children query for %s returned %d objects" in app.browser.workspace logger
  - HTTP 400 {"detail": "Invalid IRI"} for invalid parent param on children endpoint
  - SPARQL query errors logged with exc_info=True, fallback to empty results
duration: 20m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T01: SPARQL queries, hierarchy handler, and children endpoint

**Replaced hierarchy placeholder with real SPARQL-driven tree of root objects and added lazy children endpoint.**

## What Happened

Replaced the `_handle_hierarchy` placeholder handler with a real implementation that queries the RDF4J triplestore for root objects (those without `dcterms:isPartOf`) using `FILTER NOT EXISTS`. Added a new `GET /browser/explorer/children?parent={iri}` endpoint for lazy child expansion. Created two templates (`hierarchy_tree.html`, `hierarchy_children.html`) reusing existing `.tree-node`/`.tree-toggle`/`.tree-children` CSS classes with htmx lazy-loading. Wired `label_service` into the `explorer_tree` dispatcher and added `**_kwargs` to `_handle_by_type` to absorb the extra parameter.

## Verification

- `GET /browser/explorer/tree?mode=hierarchy` → 200, returns real tree nodes with `data-testid="hierarchy-node"` ✅
- `GET /browser/explorer/children?parent=http://example.org/valid` → 200, empty children HTML ✅
- `GET /browser/explorer/children?parent=not-a-valid-iri` → 400 `{"detail":"Invalid IRI"}` ✅
- `GET /browser/explorer/tree?mode=by-type` → 200 (no regression) ✅
- `GET /browser/nav-tree` → 200 (backwards compat) ✅
- `cd backend && python -m pytest tests/test_explorer_modes.py -v` → 8/8 passed ✅

## Diagnostics

- `GET /browser/explorer/tree?mode=hierarchy` — directly testable, returns tree HTML or empty state
- `GET /browser/explorer/children?parent={iri}` — directly testable, returns children or empty state
- DEBUG logs visible with `LOG_LEVEL=DEBUG`: "Hierarchy roots query returned %d objects" and "Hierarchy children query for %s returned %d objects"
- SPARQL failures logged with `exc_info=True` and fall back to empty results

## Deviations

- Added `**_kwargs` to `_handle_by_type` — necessary because the dispatcher now passes `label_service` to all handlers, and `_handle_by_type` didn't accept extra kwargs. The task plan mentioned `_handle_by_type` and `_handle_by_tag` accept `**_kwargs` (which was true for `_handle_by_tag` but not `_handle_by_type`).

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/workspace.py` — replaced `_handle_hierarchy` with real SPARQL handler; added `explorer_children` endpoint; wired `label_service` into `explorer_tree` dispatcher; added `**_kwargs` to `_handle_by_type`
- `backend/app/templates/browser/hierarchy_tree.html` — new template for root hierarchy nodes with htmx lazy-loading
- `backend/app/templates/browser/hierarchy_children.html` — new template for child nodes with recursive expansion pattern
