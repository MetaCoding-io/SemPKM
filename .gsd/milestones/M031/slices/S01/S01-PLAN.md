# S01: Carousel Removal + View Scope Binding

**Goal:** The carousel tab bar is completely removed from all view templates and JS. Model-declared view variants are accessible via a toolbar dropdown when a type filter pill is active. A saved query scope dropdown lets users filter any generic view by a saved SPARQL query.

**Demo:** User clicks "Table View" in the explorer → table view opens with type filter pills, no carousel visible. User clicks a type pill (e.g., "Project") → the view toolbar shows a "View Variant" dropdown listing model-declared views for that type (e.g., "Projects Table"). Selecting a variant navigates to that model-declared view. A "Scope" dropdown in the toolbar lists saved queries; selecting one re-fetches the view filtered to objects matching that query.

## Must-Haves

- Carousel tab bar (`carousel_tab_bar.html`) is removed from all view templates — no `{% include "browser/carousel_tab_bar.html" %}` anywhere
- `.carousel-view-body` wrapper div removed from table, cards, and graph view templates
- `switchCarouselView()`, `restoreCarouselView()` functions removed from `workspace.js` and their `window.*` exports deleted
- Carousel CSS (`.carousel-tab-bar`, `.carousel-tab`, `.carousel-view-body`, `.view-loading-indicator`, `.view-loading-spinner`, `@keyframes carousel-spin`) removed from `views.css`
- `localStorage.getItem('sempkm_carousel_view')` references removed
- When a type filter pill is active in a generic view, the view toolbar shows a dropdown listing model-declared ViewSpecs for that type (from `get_view_specs_for_type()`)
- Selecting a model-declared variant from the dropdown navigates to its dedicated view endpoint (e.g., `/browser/views/table/{spec_iri}`)
- A "Scope" dropdown appears in the view toolbar listing the user's saved SPARQL queries
- Selecting a saved query scope re-fetches the generic view with `scope_query={query_id}` parameter, filtering results to objects matching that query
- The `scope_query` parameter is wired through all three generic view renderers (table, card, graph)
- The router's `all_specs` carousel-building logic is removed from the generic view endpoint

## Proof Level

- This slice proves: integration
- Real runtime required: yes (Docker stack for E2E-style verification)
- Human/UAT required: no

## Verification

- `cd backend && python -m pytest tests/test_view_scope.py -v` — unit tests for scope query filtering in generic views
- `grep -rn "carousel" backend/app/templates/ frontend/static/js/ frontend/static/css/` — must return zero results (except possibly in unrelated contexts)
- `grep -rn "switchCarouselView\|restoreCarouselView\|sempkm_carousel_view" frontend/static/js/` — must return zero results
- Docker stack manual check: open Table View from explorer → no carousel visible → click a type pill → variant dropdown appears in toolbar → select a variant → correct view renders → select a scope query → view re-fetches with filtered data
- Diagnostic check: open a generic view with a type pill active that has NO model-declared ViewSpecs → verify the variant dropdown does NOT render (no empty/broken dropdown). Check browser console for JS errors — must be zero carousel-related errors.

## Observability / Diagnostics

- Runtime signals: `logger.info("generic_view: renderer=%s type=%s scope_query=%s", ...)` in views/router.py
- Inspection surfaces: Browser DevTools network tab shows `?scope_query=...` parameter on generic view requests
- Failure visibility: If scope_query references a nonexistent saved query, the view renders unfiltered (graceful degradation, no error)
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `ViewSpecService.get_view_specs_for_type()`, `ViewSpecService.build_dynamic_query()`, `/api/sparql/saved` endpoint for saved query list
- New wiring introduced in this slice: `scope_query` URL parameter on `/browser/views/generic/{renderer}`, model-declared variant dropdown in view toolbar, scope dropdown in view toolbar
- What remains before the milestone is truly usable end-to-end: S02 (multiple view instances + saved views CRUD), S03 (saved queries everywhere), S04 (kanban), S05-S07 (polish + tests + docs)

## Tasks

- [x] **T01: Remove carousel tab bar and add model-declared variant dropdown** `est:2h`
  - Why: The carousel is the core removal target (VIEW-08). Model-declared view variants must remain accessible via the toolbar dropdown (D284). This is the highest-risk change.
  - Files: `backend/app/templates/browser/carousel_tab_bar.html`, `backend/app/templates/browser/table_view.html`, `backend/app/templates/browser/cards_view.html`, `backend/app/templates/browser/graph_view.html`, `backend/app/templates/browser/view_toolbar.html`, `backend/app/views/router.py`, `frontend/static/js/workspace.js`, `frontend/static/css/views.css`
  - Do:
    1. Remove `{% include "browser/carousel_tab_bar.html" %}` from all three view templates (table, cards, graph).
    2. Remove the `<div class="carousel-view-body">` wrapper and its closing `</div>` from all three templates — the content should render directly without a carousel wrapper.
    3. In `views/router.py` `generic_view()`, remove the `all_specs` carousel-building block (the `if type_iri:` block that appends generic specs + model specs). Instead, pass `model_view_specs` (just the model-declared specs for the active type) to the template context.
    4. Add a new endpoint `GET /browser/views/generic/{renderer}/variants?type={type_iri}` that returns JSON list of model-declared ViewSpecs for a type (spec_iri, label, renderer_type). Or alternatively, pass these directly in the template context — simpler since we already have the data.
    5. In `view_toolbar.html`, add a "View Variant" `<select>` dropdown that appears only when `model_view_specs` is non-empty. The dropdown lists model-declared view labels. `onchange` navigates to the selected spec's dedicated endpoint URL (`/browser/views/{renderer}/{spec_iri}`).
    6. In `workspace.js`, remove `switchCarouselView()` function (~50 lines), `restoreCarouselView()` function (~20 lines), their `window.*` exports, and `loadViewContent()`'s reference to "carousel".
    7. Remove carousel CSS from `views.css`: `.carousel-tab-bar`, `.carousel-tab`, `.carousel-tab:hover`, `.carousel-tab.active`, `.carousel-view-body`, `.view-loading-indicator`, `.view-loading-spinner`, `@keyframes carousel-spin`.
    8. Remove `sempkm_carousel_view` localStorage references from `workspace.js`.
    9. Delete `carousel_tab_bar.html` template file.
  - Verify: `grep -rn "carousel" backend/app/templates/ frontend/static/js/ frontend/static/css/views.css` returns zero results. `grep -rn "switchCarouselView\|restoreCarouselView" frontend/static/js/` returns zero results.
  - Done when: No carousel UI anywhere. Model-declared variant dropdown appears in toolbar when a type with model-declared views is selected. Selecting a variant navigates correctly.

- [ ] **T02: Add saved query scope dropdown and wire scope_query parameter** `est:2h`
  - Why: VIEW-09 requires saved query scope binding on all view types. This adds the scope dropdown to the toolbar and wires the `scope_query` URL parameter through all three generic view renderers (table, card, graph).
  - Files: `backend/app/views/router.py`, `backend/app/views/service.py`, `backend/app/templates/browser/view_toolbar.html`, `frontend/static/js/workspace.js`, `frontend/static/js/workspace-layout.js`
  - Do:
    1. In `views/router.py` `generic_view()`, add `scope_query: str = Query(default="")` parameter.
    2. When `scope_query` is set, resolve the saved query text: fetch it via the query service (import and inject `QueryService` dependency), extract the WHERE body from the query text using `_extract_where_body()` from `service.py`, and inject it as a sub-select filter into the dynamic query.
    3. Modify `ViewSpecService.build_dynamic_query()` to accept an optional `scope_filter: str` parameter. When provided, add `{ SELECT ?s WHERE { <scope_filter> } }` as an additional WHERE clause constraining which objects appear.
    4. Pass `scope_query` through pagination URLs — add it to `pag_extra` alongside the `type` parameter so pagination, sorting, and filtering preserve the scope.
    5. Fetch saved queries for the scope dropdown: in `generic_view()`, call the saved query list API (or directly query via `QueryService`) to get the user's saved queries. Pass them to the template context as `saved_queries`.
    6. In `view_toolbar.html`, add a "Scope" `<select>` dropdown that lists saved queries (optgroup: My Queries / Model Queries if available). Default option is "All Objects". `onchange` triggers an htmx GET to the current generic view URL with the selected `scope_query` value appended.
    7. In `workspace-layout.js`, update the `generic-view` special panel init to pass `scopeQuery` from panel params to the URL.
    8. In `workspace.js` `openGenericViewTab()`, accept an optional `scopeQuery` parameter and store it in panel params.
    9. Pass `scope_query` value back to the template context so the dropdown shows the currently selected scope on re-render.
    10. In `generic_graph_data()`, also accept and apply the `scope_query` parameter so graph data respects the scope filter.
  - Verify: Start Docker stack, open Table View, select a scope query from dropdown → view re-renders showing only objects matching the query. Pagination preserves the scope. Switching type pills preserves the scope.
  - Done when: All three renderers (table, card, graph) accept and apply `scope_query`. The scope dropdown appears in the toolbar. Scope selection persists across pagination and type switching.

- [ ] **T03: Unit tests for scope query filtering and variant dropdown data** `est:1h`
  - Why: Proves the scope_query filtering logic works correctly and the variant dropdown data is populated. This is the contract verification for S01's boundary outputs (consumed by S02, S03, S04).
  - Files: `backend/tests/test_view_scope.py`
  - Do:
    1. Create `backend/tests/test_view_scope.py` with tests covering:
       - `build_dynamic_query()` with no scope filter returns unscoped query
       - `build_dynamic_query()` with a scope filter adds the sub-select constraint
       - `build_dynamic_query()` with both type_iri and scope_filter produces correct combined query
       - Scope filter extraction from saved query text (`_extract_where_body()` on a representative SELECT query)
       - `get_view_specs_for_type()` returns only specs matching the target class
       - `get_view_specs_for_type()` returns empty list for types with no model-declared specs
    2. Use existing test patterns from `backend/tests/conftest.py` for fixtures.
    3. Test that the scope sub-select correctly narrows results (mock SPARQL execution).
  - Verify: `cd backend && python -m pytest tests/test_view_scope.py -v` — all tests pass
  - Done when: All tests pass. `build_dynamic_query()` with scope filter produces correct SPARQL. `get_view_specs_for_type()` returns correct filtered specs.

## Files Likely Touched

- `backend/app/templates/browser/carousel_tab_bar.html` (deleted)
- `backend/app/templates/browser/table_view.html`
- `backend/app/templates/browser/cards_view.html`
- `backend/app/templates/browser/graph_view.html`
- `backend/app/templates/browser/view_toolbar.html`
- `backend/app/views/router.py`
- `backend/app/views/service.py`
- `frontend/static/js/workspace.js`
- `frontend/static/js/workspace-layout.js`
- `frontend/static/css/views.css`
- `backend/tests/test_view_scope.py` (new)
