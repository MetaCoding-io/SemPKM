# S01: Generic Views & Explorer Consolidation

**Goal:** Replace the per-model/per-type explorer tree with 3 generic views (Table/Cards/Graph) that use SHACL-driven dynamic columns, type filter pills, and carousel integration for model-declared views. Consolidate MY VIEWS into a Saved Views folder under VIEWS.
**Demo:** Open Table View from explorer → all objects with common columns → click a type pill → columns change to SHACL-discovered properties → carousel shows model-declared views → Saved Views folder lists promoted queries → no per-type folders in explorer.

## Must-Haves

- 3 generic ViewSpec objects registered in-memory at startup (D093) with well-known IRIs `urn:sempkm:view:generic-table`, `urn:sempkm:view:generic-cards`, `urn:sempkm:view:generic-graph`
- `build_dynamic_query()` method on ViewSpecService that builds SPARQL SELECT from SHACL property shapes, falling back to default columns (label, type, created, modified) for types with ≤2 properties or when no type is selected
- `GET /browser/views/generic/{renderer}` endpoint with `?type=` filter parameter
- Type filter pills partial template + `GET /browser/views/type-pills` endpoint
- Pagination, sort headers, and filter toolbar use a `pagination_base_url` template variable instead of hardcoded `/browser/views/{type}/{iri}` path construction
- Carousel tab bar appears when a type pill is active, showing model-declared views alongside generic renderers
- Explorer VIEWS section shows: Spatial Canvas, Ontology Viewer, Table View, Cards View, Graph View, Saved Views folder
- MY VIEWS section removed from workspace.html; saved/promoted views folded into Saved Views folder
- `openGenericViewTab(renderer)` JS function added to workspace.js

## Proof Level

- This slice proves: integration (endpoints, templates, JS, SHACL query builder all compose into working generic views)
- Real runtime required: yes (Docker with triplestore for browser verification)
- Human/UAT required: no (browser assertions sufficient)

## Verification

- `cd backend && python -m pytest tests/test_dynamic_query_builder.py -v` — unit tests for `build_dynamic_query()` with mocked ShapesService, verifying SPARQL structure, column lists, default fallback, type-filtered queries, and sort determinism
- Browser: open Table View from explorer → all objects shown with common columns (label, type, created, modified)
- Browser: click a type pill → table filters to that type, columns change to SHACL-discovered properties
- Browser: with type selected, carousel tab bar appears with model-declared view tabs
- Browser: pagination and filter work in generic table view
- Browser: Saved Views folder visible in VIEWS section
- Browser: no per-model/per-type folder tree in explorer, no MY VIEWS section
- Diagnostic: `build_dynamic_query()` with invalid/missing type gracefully returns default columns — no exception propagated (verified via unit test `test_shapes_service_exception_returns_defaults`)
- Diagnostic: `GET /browser/views/generic/invalid-renderer` returns 404 HTML (not a 500 crash)

## Observability / Diagnostics

- Runtime signals: `logger.info("Registered %d generic views", count)` at startup; `logger.debug("build_dynamic_query: type=%s, columns=%d", ...)` on each query build
- Inspection surfaces: `GET /browser/views/available` JSON endpoint includes generic views; `GET /browser/views/type-pills` returns current type list
- Failure visibility: 404 HTML response from generic endpoint if renderer is invalid; empty table with "No objects found" if SPARQL returns nothing; generic views log SPARQL query at DEBUG level
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `ShapesService.get_form_for_type()`, `ShapesService.get_types()`, `ViewSpecService.execute_table_query()` / `execute_cards_query()` / `execute_graph_query()`, `scope_to_current_graph()`, `carousel_tab_bar.html`, `switchCarouselView()`, `/browser/my-views` endpoint
- New wiring introduced in this slice: `register_generic_views()` called in `main.py` lifespan; generic view endpoints in `views/router.py`; `openGenericViewTab()` exposed on window in `workspace.js`; rewritten `views_explorer.html` template
- What remains before the milestone is truly usable end-to-end: VFS enhancements (S02/S03), UI polish (S04), docs (S05)

## Tasks

- [x] **T01: Dynamic query builder and generic view registration with unit tests** `est:2h`
  - Why: The SHACL-to-SPARQL query builder is the riskiest piece — it must produce correct SPARQL for all types, handle the "All Types" case, and produce stable column lists. Unit tests validate correctness before wiring to endpoints. Also registers 3 generic ViewSpec objects in memory. Proves VIEW-02 at contract level.
  - Files: `backend/app/views/service.py`, `backend/tests/test_dynamic_query_builder.py`
  - Do: Add `build_dynamic_query(type_iri: str | None) -> tuple[str, list[str]]` to ViewSpecService. Uses `ShapesService.get_form_for_type()` to discover PropertyShape objects, extracts `path`/`name`/`order`, builds SPARQL SELECT with OPTIONAL clauses for each property, sorts by `(order, name)` for determinism. Default columns: `label`, `type`, `created`, `modified` when no type or ≤2 properties. Also add `get_generic_columns(type_iri)` helper. Add `register_generic_views()` class method creating 3 in-memory ViewSpec with well-known IRIs and empty `sparql_query`/`target_class`. Graph view query: build a standard CONSTRUCT mirroring `models/basic-pkm/views/basic-pkm.jsonld` pattern. All queries pass through `scope_to_current_graph()`. Write comprehensive unit tests mocking ShapesService — test with various types, sparse shapes (≤2 props), empty shapes, All Types case, column order stability.
  - Verify: `cd backend && python -m pytest tests/test_dynamic_query_builder.py -v` — all tests pass
  - Done when: `build_dynamic_query()` produces valid SPARQL for typed and untyped cases, unit tests cover ≥8 scenarios, `register_generic_views()` creates 3 ViewSpec objects with correct well-known IRIs

- [x] **T02: Generic view endpoints and pagination URL refactor** `est:2h`
  - Why: Wires the dynamic query builder to HTTP endpoints that produce rendered HTML. Fixes the hardcoded URL pattern in pagination/toolbar/sort-headers so generic views (which use `?type=` query params instead of spec IRI path segments) can paginate and filter. Proves VIEW-01.
  - Files: `backend/app/views/router.py`, `backend/app/templates/browser/pagination.html`, `backend/app/templates/browser/view_toolbar.html`, `backend/app/templates/browser/table_view.html`, `backend/app/templates/browser/cards_view.html`, `backend/app/main.py`
  - Do: (1) Add `GET /browser/views/generic/{renderer}` endpoint in `views/router.py`. Accepts `renderer` path param (table/card/graph) and `type` query param. Detects generic ViewSpec by IRI prefix `urn:sempkm:view:generic-`. Calls `build_dynamic_query(type_iri)`, creates transient ViewSpec with the built query, delegates to `execute_table_query()`/`execute_cards_query()`/`execute_graph_query()`. Passes `pagination_base_url` to template context. (2) Refactor `pagination.html`: replace `{% set pag_base = "/browser/views/" ~ pag_view_type ~ "/" ~ spec_iri_encoded %}` with `{% set pag_base = pagination_base_url | default("/browser/views/" ~ pag_view_type ~ "/" ~ spec_iri_encoded) %}`. Same for `view_toolbar.html` filter URL and `table_view.html` sort headers. (3) Existing table/card/graph endpoints pass `pagination_base_url` in context using their existing URL pattern (backward compatible). (4) Add `register_generic_views()` call in `main.py` lifespan after ViewSpecService creation. (5) Add type pills endpoint: `GET /browser/views/type-pills` returning rendered `type_filter_pills.html` partial.
  - Verify: Docker up → navigate to `/browser/views/generic/table` → all objects shown with common columns → pagination works → filter works
  - Done when: Generic table/card/graph endpoints return rendered HTML with working pagination and filtering; existing model-declared views unaffected

- [x] **T03: Type filter pills and carousel integration** `est:1.5h`
  - Why: Type pills let users filter generic views by type. When a type is selected, SHACL columns appear and the carousel tab bar shows model-declared views for that type. Proves VIEW-03 and VIEW-05.
  - Files: `backend/app/templates/browser/type_filter_pills.html` (new), `backend/app/views/router.py`, `backend/app/templates/browser/table_view.html`, `backend/app/templates/browser/cards_view.html`, `backend/app/templates/browser/graph_view.html`, `frontend/static/js/workspace.js`, `frontend/static/css/workspace.css`
  - Do: (1) Create `type_filter_pills.html` partial — renders pill buttons from `types` list (each with `type_iri` and `label`), plus an "All Types" pill. Active pill has `.active` class. Each pill uses htmx: `hx-get="/browser/views/generic/{renderer}?type={type_iri}"` targeting `closest .group-editor-area`. (2) In the generic view endpoint, pass `types` (from `ShapesService.get_types()`), `selected_type`, and `is_generic=True` to template context. (3) In `table_view.html` / `cards_view.html` / `graph_view.html`, include `type_filter_pills.html` above carousel bar when `is_generic` is true. (4) Carousel integration: when a type is selected in a generic view, fetch model-declared ViewSpecs for that type via `get_view_specs_for_type()` and pass as `all_specs` to the carousel template. Generic renderers (table/card/graph) should also appear as carousel tabs. (5) Add CSS for `.type-filter-pills` container and `.type-pill` buttons (`.active` state) in workspace.css. (6) localStorage persistence: store selected type per renderer in `sempkm_generic_view_type_{renderer}`, read on page load via JS.
  - Verify: Browser: open generic Table View → type pills visible → click a type pill → table filters, columns change → carousel appears with model-declared views → click "All Types" → back to common columns, carousel hidden
  - Done when: Type pills filter generic views, SHACL columns appear for typed views, carousel shows model-declared views when type is selected, type selection persists in localStorage

- [x] **T04: Explorer tree consolidation and JS wiring** `est:1.5h`
  - Why: Replaces the per-model folder tree with flat generic view entries and a Saved Views folder. Removes MY VIEWS section. Adds `openGenericViewTab()` JS function. Proves VIEW-04 and completes the slice.
  - Files: `backend/app/templates/browser/views_explorer.html`, `backend/app/templates/browser/workspace.html`, `backend/app/views/router.py`, `frontend/static/js/workspace.js`
  - Do: (1) Rewrite `views_explorer.html` to show flat entries: Spatial Canvas (existing), Ontology Viewer (existing), Table View, Cards View, Graph View — each calling `openGenericViewTab(renderer)`. Below these, a collapsible "Saved Views" folder that loads content via htmx from `/browser/my-views` (the existing endpoint, unchanged). (2) In `workspace.js`, add `openGenericViewTab(renderer)` function. Uses dockview `special-panel` component with `specialType: 'generic-view'` and `renderer` param. The `workspace-layout.js` special-panel init handler maps `generic-view` → `/browser/views/generic/{renderer}`. (3) Remove `section-my-views` div from `workspace.html` — the MY VIEWS section is now folded into the VIEWS tree as "Saved Views". (4) Update the `views_explorer` endpoint in `router.py` to pass saved views data alongside generic view entries (or keep the saved views as a lazy htmx load inside the template). (5) Browser verification: explorer shows 5 fixed entries + Saved Views folder, no per-model folders, clicking Table View opens generic table, saved views are accessible.
  - Verify: Browser: explorer VIEWS section shows Spatial Canvas, Ontology Viewer, Table View, Cards View, Graph View, Saved Views folder → clicking Table View opens generic table → Saved Views folder expands to show promoted queries → no per-model/per-type folders → no MY VIEWS section in sidebar
  - Done when: Explorer tree matches acceptance criteria (VIEW-04), all generic views openable from explorer, saved views accessible, MY VIEWS section gone

## Files Likely Touched

- `backend/app/views/service.py` — build_dynamic_query(), register_generic_views(), get_generic_columns()
- `backend/app/views/router.py` — generic view endpoints, type pills endpoint, views_explorer updates
- `backend/app/main.py` — register_generic_views() call in lifespan
- `backend/app/templates/browser/views_explorer.html` — complete rewrite
- `backend/app/templates/browser/type_filter_pills.html` — new partial
- `backend/app/templates/browser/table_view.html` — type pills include, pagination_base_url for sort headers
- `backend/app/templates/browser/cards_view.html` — type pills include, pagination_base_url
- `backend/app/templates/browser/graph_view.html` — type pills include
- `backend/app/templates/browser/pagination.html` — pagination_base_url refactor
- `backend/app/templates/browser/view_toolbar.html` — filter URL refactor
- `backend/app/templates/browser/workspace.html` — remove MY VIEWS section
- `frontend/static/js/workspace.js` — openGenericViewTab(), type pill localStorage
- `frontend/static/js/workspace-layout.js` — generic-view special-panel handler
- `frontend/static/css/workspace.css` — type pill styles
- `backend/tests/test_dynamic_query_builder.py` — new unit test file
