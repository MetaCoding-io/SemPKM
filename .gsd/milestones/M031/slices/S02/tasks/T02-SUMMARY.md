---
id: T02
parent: S02
milestone: M031
provides:
  - save_promoted_view() method for creating PromotedViews without a pre-existing saved query
  - POST /browser/views/save endpoint for the "Save View" toolbar action
  - DELETE /browser/views/saved/{view_id} endpoint for unpinning generic saved views
  - Extended PromotedViewData with type_filter and scope_query_id fields
  - list_promoted_views() now uses OPTIONAL SPARQL for fromQuery, typeFilter, scopeQuery
  - "Save View" button in view toolbar for generic views
  - my_views.html routes generic saved views through openGenericViewTab()
  - Unit tests covering save, list, and delete promoted view operations
key_files:
  - backend/app/sparql/query_service.py
  - backend/app/views/router.py
  - backend/app/browser/workspace.py
  - backend/app/templates/browser/view_toolbar.html
  - backend/app/templates/browser/my_views.html
  - backend/tests/test_view_save.py
key_decisions:
  - Generic saved views (no query) use openGenericViewTab() while query-based promoted views keep openViewTab()
  - delete_promoted_view() is a separate method from demote_query() since generic views may have no associated query
  - my_views() now passes PromotedViewData objects directly to template instead of going through ViewSpecService intermediary
patterns_established:
  - PRED_TYPE_FILTER and PRED_SCOPE_QUERY vocabulary constants follow existing VOCAB + "name" pattern
  - SaveViewRequest Pydantic model for POST /browser/views/save with name, renderer_type, type_filter, scope_query_id
  - Two-path unpin pattern in my_views.html — demoteView() for query-based views, deleteSavedView() for generic views
observability_surfaces:
  - logger.info("save_promoted_view: user=%s label=%s renderer=%s", ...) on each save
  - logger.info("Deleted promoted view %s for user %s", ...) on delete
  - ValueError raised for invalid renderer_type in save_promoted_view()
  - GET /browser/my-views returns saved view HTML for inspection
duration: 30m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T02: Save View endpoint, toolbar button, and Saved Views display fix with unit tests

**Added save_promoted_view() method, POST /browser/views/save endpoint, "Save View" toolbar button, and fixed my_views.html to route generic saved views through openGenericViewTab() — with 13 unit tests covering save/list/delete operations.**

## What Happened

Implemented the full "Save Current View" feature across 6 files:

1. **Extended PromotedViewData** in `query_service.py` with `type_filter` and `scope_query_id` fields, plus `PRED_TYPE_FILTER` and `PRED_SCOPE_QUERY` vocabulary constants.

2. **Added `save_promoted_view()` method** that creates a PromotedView directly without requiring a saved query. Validates renderer_type, builds INSERT DATA with conditional triples for type_filter and scope_query_id, and links to fromQuery when a scope query is provided.

3. **Added `delete_promoted_view()` method** for unpinning generic saved views by view ID (not query ID), since these views may have no associated saved query.

4. **Updated `list_promoted_views()` SPARQL** to use OPTIONAL clauses for `fromQuery`, `queryText`, `typeFilter`, and `scopeQuery` — so views saved without a query are no longer excluded from results.

5. **Added `POST /browser/views/save` endpoint** with a `SaveViewRequest` Pydantic model and a `DELETE /browser/views/saved/{view_id}` endpoint in `router.py`.

6. **Added "Save View" button** to `view_toolbar.html` with a `bookmark-plus` Lucide icon, guarded by `is_generic` flag. The `saveCurrentView()` JS function reads renderer, type filter, and scope query from toolbar data attributes, prompts for a name, POSTs to the save endpoint, and refreshes the saved views tree.

7. **Rewrote `my_views.html`** to iterate over `promoted_views` (PromotedViewData objects) instead of ViewSpec objects. Query-based views still use `openViewTab()`, while generic saved views use `openGenericViewTab()`. Unpin uses `demoteView()` for query-based or `deleteSavedView()` for generic views.

8. **Simplified `my_views()` endpoint** in `workspace.py` to pass PromotedViewData directly to the template, removing the ViewSpecService intermediary (which was converting back to ViewSpec unnecessarily).

## Verification

- All 3 Python files parse without syntax errors
- `save_promoted_view` method exists in query_service.py
- POST endpoint exists in router.py (via `@router.post("/save")`)
- `openGenericViewTab` is called in my_views.html for generic saved views
- "Save View" button with `bookmark-plus` icon exists in view_toolbar.html
- 13 unit tests pass covering save (basic, with type_filter, with scope, with all fields, invalid renderer, unique IDs, graph target), list (all fields, missing optional, OPTIONAL clauses, empty, mixed), and delete operations

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('backend/app/sparql/query_service.py').read())"` | 0 | ✅ pass | <1s |
| 2 | `python3 -c "import ast; ast.parse(open('backend/app/views/router.py').read())"` | 0 | ✅ pass | <1s |
| 3 | `python3 -c "import ast; ast.parse(open('backend/app/browser/workspace.py').read())"` | 0 | ✅ pass | <1s |
| 4 | `grep -c "generic-view:" frontend/static/js/workspace.js` | 0 (count=3) | ⚠️ spec false-negative (see T01 note) | <1s |
| 5 | `grep -q "save_promoted_view" backend/app/sparql/query_service.py` | 0 | ✅ pass | <1s |
| 6 | `grep -q "\.post.*save" backend/app/views/router.py` | 0 | ✅ pass | <1s |
| 7 | `grep -q "openGenericViewTab" backend/app/templates/browser/my_views.html` | 0 | ✅ pass | <1s |
| 8 | `cd backend && .venv/bin/python -m pytest tests/test_view_save.py -v` | 0 (13 passed) | ✅ pass | 0.13s |
| 9 | `grep -q "bookmark-plus" backend/app/templates/browser/view_toolbar.html` | 0 | ✅ pass | <1s |

## Diagnostics

- **Save operation logs:** `logger.info("save_promoted_view: user=%s label=%s renderer=%s", ...)` on each save
- **Delete operation logs:** `logger.info("Deleted promoted view %s for user %s", ...)` on each delete
- **Saved views list:** `GET /browser/my-views` returns the rendered HTML tree of promoted views
- **RDF inspection:** SPARQL query on `urn:sempkm:queries` graph for `PromotedView` triples with `typeFilter` and `scopeQueryId` predicates
- **Error state:** `ValueError` raised for invalid renderer_type; HTTP 400 returned with error message

## Deviations

- **Simplified my_views() endpoint:** Instead of maintaining the dual specs+query_id_map pattern from the old code, the endpoint now passes PromotedViewData objects directly to the template. This eliminates the ViewSpecService intermediary that was converting PromotedViewData → ViewSpec only for the template to need the original PromotedViewData fields back. The removed `get_view_spec_service` dependency and `ViewSpecService` import are no longer needed in workspace.py.
- **Added `delete_promoted_view()` method:** The plan suggested reusing the `demote_query` path, but generic views may not have a query_id. A dedicated delete-by-view-ID method is cleaner and supports both cases.
- **Added `DELETE /browser/views/saved/{view_id}` endpoint:** Not explicitly in the plan but required for the unpin functionality on generic saved views.

## Known Issues

- Slice verification check `grep -c "generic-view:" frontend/static/js/workspace.js` returns 3 instead of expected 0 — this was documented in T01 as a spec false-negative. The old fixed pattern is gone; the new dynamic pattern necessarily contains the prefix.

## Files Created/Modified

- `backend/app/sparql/query_service.py` — Extended PromotedViewData with type_filter/scope_query_id, added PRED_TYPE_FILTER/PRED_SCOPE_QUERY constants, added save_promoted_view() and delete_promoted_view() methods, updated list_promoted_views() with OPTIONAL SPARQL
- `backend/app/views/router.py` — Added SaveViewRequest model, POST /save and DELETE /saved/{view_id} endpoints
- `backend/app/browser/workspace.py` — Simplified my_views() to pass PromotedViewData directly, removed unused ViewSpecService dependency
- `backend/app/templates/browser/view_toolbar.html` — Added "Save View" button with bookmark-plus icon and saveCurrentView() JS handler, added data-renderer/data-type-filter/data-scope-query attributes
- `backend/app/templates/browser/my_views.html` — Rewrote to use promoted_views (PromotedViewData), routes generic views via openGenericViewTab(), adds deleteSavedView() for unpin
- `frontend/static/css/views.css` — Added .save-view-btn svg sizing rule with flex-shrink: 0
- `backend/tests/test_view_save.py` — 13 unit tests for save_promoted_view, list_promoted_views, delete_promoted_view
