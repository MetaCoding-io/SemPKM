---
estimated_steps: 8
estimated_files: 8
skills_used:
  - test
---

# T02: Save View endpoint, toolbar button, and Saved Views display fix with unit tests

**Slice:** S02 — Multiple View Instances + Saved Views Fix
**Milestone:** M031

## Description

This task delivers the "Save Current View" feature and fixes the Saved Views folder display. Currently, promoted views can only be created by promoting an existing saved SPARQL query. This task adds a direct save path for generic views (table/cards/graph) that captures the current renderer, type filter, and scope query as a named saved view. It also fixes the Saved Views folder so clicking a saved generic view opens via `openGenericViewTab()` with the correct scope/type, instead of routing through the model-view `openViewTab()` endpoint.

## Steps

1. **Extend `PromotedViewData` in `backend/app/sparql/query_service.py`** (~line 132):
   - Add two new fields: `type_filter: str = ""` and `scope_query_id: str = ""`
   - Add two vocabulary constants after `PRED_RENDERER_TYPE` (~line 44):
     ```python
     PRED_TYPE_FILTER = VOCAB + "typeFilter"
     PRED_SCOPE_QUERY = VOCAB + "scopeQueryId"
     ```

2. **Add `save_promoted_view()` method** to `QueryService` class (after `promote_query()` ~line 623):
   - Signature: `async def save_promoted_view(self, user_id: uuid.UUID, display_label: str, renderer_type: str, type_filter: str = "", scope_query_id: str = "") -> PromotedViewData`
   - Validate `renderer_type` against `VALID_RENDERERS`
   - Generate a new view UUID and IRI
   - Build INSERT DATA with: `a PromotedView`, `owner`, `rdfs:label`, `rendererType`, `dcterms:created`
   - Conditionally add `typeFilter` triple if `type_filter` is non-empty
   - Conditionally add `scopeQueryId` triple if `scope_query_id` is non-empty
   - Conditionally add `fromQuery` triple if `scope_query_id` is non-empty (linking to the saved query)
   - Return `PromotedViewData` with all fields populated
   - Key difference from `promote_query()`: does NOT require an existing saved query

3. **Update `list_promoted_views()` SPARQL** (~line 672):
   - Make `PRED_FROM_QUERY` OPTIONAL (currently it's required, which would exclude views saved without a query)
   - Add OPTIONAL clauses for `PRED_TYPE_FILTER` and `PRED_SCOPE_QUERY`
   - Update the `PromotedViewData` construction to populate the new fields from bindings (with fallback to empty string)
   - Also update `PRED_QUERY_TEXT` to be OPTIONAL (views saved without a query won't have query text)

4. **Add `POST /api/views/save` endpoint** in `backend/app/views/router.py`:
   - Add a Pydantic model `SaveViewRequest` with fields: `name: str`, `renderer_type: str`, `type_filter: str = ""`, `scope_query_id: str = ""`
   - Route: `@router.post("/save")`
   - Call `query_service.save_promoted_view()` with the request data
   - Return `JSONResponse` with `{"id": view_id, "label": name, "renderer": renderer_type}`
   - The views router is mounted at `/browser/views` (check `backend/app/views/router.py` for the prefix), so the endpoint will be at `/browser/views/save`

5. **Add "Save View" button to `backend/app/templates/browser/view_toolbar.html`**:
   - Add a button in `.view-toolbar-right`, before the scope dropdown, guarded by `{% if is_generic is defined and is_generic %}`
   - Use Lucide `bookmark-plus` icon
   - `onclick` calls a new JS function `saveCurrentView()` that:
     - Reads current renderer from a data attribute on `.view-toolbar`
     - Reads current type filter from the `data-current-filter` or from localStorage `sempkm_generic_type_{renderer}`
     - Reads current scope query from `.view-scope-select` value
     - Prompts user for a view name via `prompt()`
     - POSTs to `/browser/views/save` with fetch
     - On success, refreshes the saved views tree via `htmx.ajax('GET', '/browser/my-views', '#saved-views-tree')`
     - Shows toast notification
   - Add `data-renderer="{{ renderer | default('table') }}"` and `data-type-filter="{{ selected_type | default('') }}"` attributes to `.view-toolbar` div
   - Style the button via existing `.panel-btn` class in `frontend/static/css/views.css`

6. **Fix `backend/app/templates/browser/my_views.html`**:
   - Currently `onclick` calls `openViewTab('{{ spec.spec_iri }}', '{{ spec.label }}', '{{ spec.renderer_type }}')` — this routes to `/browser/views/{viewType}/{encodedViewId}` which is for model-declared views
   - For saved generic views (those created via "Save View"), change to call `openGenericViewTab('{{ spec.renderer_type }}', '{{ spec.scope_query_id | default("") }}', '{{ spec.label }}')`
   - Distinguish between model-declared views and generic saved views: add a `is_generic` flag to each spec in the template context. Generic saved views have no `sparql_query` (or have a `scope_query_id` set).
   - Add `data-type-filter="{{ spec.type_filter | default('') }}"` and `data-scope-query="{{ spec.scope_query_id | default('') }}"` attributes to each view entry
   - Keep the existing unpin/demote button but use the view ID for unpinning generic views (need a `delete_promoted_view()` method or reuse `demote_query` path)

7. **Update `backend/app/browser/workspace.py` `my_views()` endpoint** (~line 1192):
   - The current code fetches `specs` from `view_spec_service.get_user_promoted_view_specs()` and `promoted` from `query_service.list_promoted_views()`
   - Pass the full `promoted` list to the template so each entry has `type_filter`, `scope_query_id`, `renderer_type`, and `query_id`
   - Update the template context to include `promoted_views` alongside or replacing `specs`
   - Each promoted view entry in the template needs: `display_label`, `renderer_type`, `type_filter`, `scope_query_id`, `id` (for unpin), `query_id` (for demote, may be empty)

8. **Write unit tests in `backend/tests/test_view_save.py`**:
   - Test `save_promoted_view()` creates correct RDF triples (mock triplestore client, verify SPARQL INSERT contains expected predicates)
   - Test `save_promoted_view()` with type_filter and scope_query_id
   - Test `save_promoted_view()` without optional fields (no type_filter, no scope)
   - Test `save_promoted_view()` rejects invalid renderer_type
   - Test `list_promoted_views()` returns new fields from SPARQL bindings
   - Test `list_promoted_views()` handles missing optional fields gracefully
   - Follow the pattern in `backend/tests/test_view_scope.py` for mock setup

## Must-Haves

- [ ] `PromotedViewData` has `type_filter` and `scope_query_id` fields
- [ ] `save_promoted_view()` method creates a PromotedView without requiring a saved query
- [ ] `list_promoted_views()` returns `type_filter` and `scope_query_id` from OPTIONAL SPARQL bindings
- [ ] `POST /browser/views/save` endpoint accepts name, renderer, type_filter, scope_query_id
- [ ] "Save View" button appears in view toolbar for generic views
- [ ] `my_views.html` calls `openGenericViewTab()` for generic saved views (not `openViewTab()`)
- [ ] Unpin works for views created via Save View
- [ ] Unit tests in `test_view_save.py` pass

## Verification

- `python3 -c "import ast; ast.parse(open('backend/app/sparql/query_service.py').read())"` — no syntax errors
- `python3 -c "import ast; ast.parse(open('backend/app/views/router.py').read())"` — no syntax errors
- `python3 -c "import ast; ast.parse(open('backend/app/browser/workspace.py').read())"` — no syntax errors
- `python -m pytest backend/tests/test_view_save.py -v` — all tests pass
- `grep -q "save_promoted_view" backend/app/sparql/query_service.py` — method exists
- `grep -q "openGenericViewTab" backend/app/templates/browser/my_views.html` — saved views use generic tab opener
- `grep -q "bookmark-plus\|save.*view\|Save View" backend/app/templates/browser/view_toolbar.html` — save button exists

## Observability Impact

- Signals added/changed: `logger.info("save_promoted_view: user=%s label=%s renderer=%s", ...)` on each save
- How a future agent inspects this: `GET /browser/my-views` returns the saved views HTML; SPARQL query on `urn:sempkm:queries` graph for `PromotedView` triples
- Failure state exposed: `ValueError` raised for invalid renderer_type; `logger.warning` if scope query ID doesn't resolve

## Inputs

- `backend/app/sparql/query_service.py` — `PromotedViewData` at ~line 132, `promote_query()` at ~line 588, `list_promoted_views()` at ~line 672, vocabulary constants at ~line 40
- `backend/app/views/router.py` — `generic_view()` at ~line 132, `_VALID_RENDERERS` at ~line 128
- `backend/app/browser/workspace.py` — `my_views()` at ~line 1192
- `backend/app/templates/browser/view_toolbar.html` — toolbar with scope dropdown
- `backend/app/templates/browser/my_views.html` — saved views rendering with `openViewTab()` onclick
- `backend/tests/test_view_scope.py` — reference for test patterns (mock setup, async test structure)
- `frontend/static/js/workspace.js` — `openGenericViewTab()` updated in T01 with 3-param signature (renderer, scopeQuery, scopeLabel)

## Expected Output

- `backend/app/sparql/query_service.py` — extended `PromotedViewData`, new `save_promoted_view()` method, updated `list_promoted_views()` with OPTIONAL fields
- `backend/app/views/router.py` — new `POST /browser/views/save` endpoint with `SaveViewRequest` model
- `backend/app/browser/workspace.py` — `my_views()` passes promoted view metadata to template
- `backend/app/templates/browser/view_toolbar.html` — "Save View" button with `saveCurrentView()` JS handler
- `backend/app/templates/browser/my_views.html` — uses `openGenericViewTab()` for generic saved views, passes scope/type
- `frontend/static/css/views.css` — minor styling for save button if needed
- `backend/tests/test_view_save.py` — unit tests for save_promoted_view, list_promoted_views with new fields
