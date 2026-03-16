# S01: Generic Views & Explorer Consolidation — Research

**Date:** 2026-03-15
**Depth:** Targeted — known patterns in existing codebase, moderate integration complexity

## Summary

This slice delivers 5 requirements (VIEW-01 through VIEW-05) by adding generic cross-type views, SHACL-driven dynamic columns, type filter pills, explorer tree consolidation, and carousel integration for model-declared views.

The codebase has strong existing infrastructure: `ViewSpecService` with `execute_table_query()` / `execute_cards_query()` / `execute_graph_query()` already handle pagination, sorting, filtering, and label resolution. `ShapesService.get_form_for_type()` returns `PropertyShape` objects with `path`, `name`, `order`, and `datatype` — everything needed for dynamic column discovery. The carousel tab bar and localStorage persistence are production-tested. The dockview tab system has both `view-panel` (renders via `/browser/views/{type}/{iri}`) and `special-panel` (renders via `/browser/{specialType}`) components.

The main work is: (1) a `build_dynamic_query()` function that converts SHACL property shapes into SPARQL SELECT queries, (2) new generic view endpoints, (3) type filter pills as an htmx partial, (4) rewriting `views_explorer.html` to show generic entries + Saved Views, and (5) wiring the carousel to appear when a type is selected within a generic view.

## Recommendation

**Use the existing `view-panel` dockview component** for generic views, not `special-panel`. Generic views are fundamentally views (table/card/graph rendering with pagination) — they just build their query dynamically instead of reading it from a ViewSpec SPARQL string. The `openViewTab()` / `loadViewContent()` JS path already maps renderer types to `/browser/views/{type}/{iri}` URLs.

**Register 3 in-memory ViewSpec objects at startup** (D093) with well-known IRIs (`urn:sempkm:view:generic-table`, etc.). These have empty `sparql_query` and empty `target_class`. The generic view endpoint detects them by IRI prefix, builds the query dynamically, and delegates to the same `execute_table_query()` / `execute_cards_query()` / `execute_graph_query()` methods.

**Implement Phase 1+2 together** — the design doc separated them for safety, but Phase 1 alone (generic views alongside existing per-type folders) would leave a confusing double-navigation UX. The roadmap's acceptance criteria explicitly say "no per-type folders in explorer tree." The risk is low because model-declared ViewSpecs remain in memory and accessible via carousel — only the explorer tree changes.

## Implementation Landscape

### Key Files

- `backend/app/views/service.py` (1319 lines) — `ViewSpecService` class. Add `build_dynamic_query()` method that takes a type IRI (optional) and returns a dynamically-built SPARQL SELECT using SHACL shapes. Add `register_generic_views()` startup method that creates 3 in-memory ViewSpec objects. Add `get_generic_columns(type_iri)` that calls `ShapesService.get_form_for_type()` and maps `PropertyShape` → column list.
- `backend/app/views/router.py` (552 lines) — View endpoints. Add `GET /browser/views/generic/{renderer}` endpoint with `?type=` filter parameter. This endpoint builds the dynamic query, creates a transient ViewSpec, and delegates to existing `execute_*_query()` methods. Add `GET /browser/views/type-pills` endpoint returning the type pills HTML partial.
- `backend/app/services/shapes.py` (405 lines) — `ShapesService`. Already has `get_form_for_type(type_iri)` → `NodeShapeForm` with `properties: list[PropertyShape]` and `get_types()` → `list[dict]`. No changes needed — consumed as-is.
- `backend/app/templates/browser/views_explorer.html` — Complete rewrite. Replace per-model/per-type tree with: Spatial Canvas, Ontology Viewer, 3 generic view entries, Saved Views collapsible folder.
- `backend/app/templates/browser/my_views.html` — Rename to `saved_views.html` conceptually (or fold into views_explorer.html as a nested section). The `/browser/my-views` endpoint stays but renders inside the Saved Views folder.
- New: `backend/app/templates/browser/type_filter_pills.html` — Partial template for type pills. Receives `types` list from `ShapesService.get_types()`, current `selected_type`, and renders pill buttons with htmx wiring.
- `backend/app/templates/browser/table_view.html` — Needs modification: when rendering a generic view, include type pills above the carousel bar. The `carousel_tab_bar.html` include should be conditional — only shown when a type is selected (pills active).
- `backend/app/templates/browser/pagination.html` — URL pattern is hardcoded as `/browser/views/{view_type}/{spec_iri_encoded}`. Generic view pagination needs to use `/browser/views/generic/{renderer}?type={type}` instead. Pass a `pagination_base_url` variable rather than constructing it in the template.
- `backend/app/templates/browser/view_toolbar.html` — Same issue: filter URL pattern is hardcoded. Needs the same `pagination_base_url` fix.
- `frontend/static/js/workspace.js` — Add `openGenericViewTab(renderer)` function. The `loadViewContent()` already handles `viewType` → URL mapping — add `'generic-table'`, `'generic-cards'`, `'generic-graph'` cases pointing to `/browser/views/generic/{renderer}`.
- `frontend/static/js/workspace-layout.js` — The `view-panel` init handler maps `viewType` → URL. Extend for generic types: when `viewType` starts with `generic-`, use `/browser/views/generic/{renderer}`.
- `backend/app/templates/browser/workspace.html` — Remove `section-my-views` div (MY VIEWS section). The Saved Views folder becomes part of the VIEWS section tree.
- `backend/app/browser/workspace.py` — The `/browser/my-views` endpoint stays as-is but may need to be referenced from the new views_explorer template.

### Build Order

1. **Dynamic query builder (service layer)** — `build_dynamic_query()` in `ViewSpecService`. This is the riskiest piece — SPARQL must be correct for all types, handle the "All Types" case (no filter), and produce valid column lists. Test this in isolation with unit tests before wiring to endpoints. Proves VIEW-02.

2. **Generic view endpoint** — `GET /browser/views/generic/{renderer}` route. Uses the dynamic query builder, creates a transient ViewSpec, delegates to existing execute methods. Proves VIEW-01.

3. **Type filter pills** — `type_filter_pills.html` partial + `GET /browser/views/type-pills` endpoint. htmx wiring: clicking a pill re-fetches the generic view with `?type=` parameter. localStorage persistence for selected type. Proves VIEW-03.

4. **Carousel integration** — When a type pill is active, fetch model-declared ViewSpecs for that type via `get_view_specs_for_type()` and render the carousel tab bar. Switching carousel tabs loads the model-declared view. Proves VIEW-05.

5. **Explorer tree rewrite** — Rewrite `views_explorer.html` to show fixed generic entries + Saved Views folder. Remove MY VIEWS section from workspace.html. Proves VIEW-04.

6. **Pagination/toolbar URL fix** — Refactor `pagination.html` and `view_toolbar.html` to use a passed-in base URL instead of constructing it from `spec_iri_encoded`. Required because generic views use a different URL pattern.

### Verification Approach

**Unit tests** (no Docker required):
- `test_dynamic_query_builder.py`: Test `build_dynamic_query()` with various type IRIs, verify SPARQL structure (correct SELECT vars, OPTIONAL clauses, FROM clause, type filter). Test fallback to default columns for sparse types. Test "All Types" query (no type filter).
- Tests are pure-function — mock `ShapesService.get_form_for_type()` to return known `NodeShapeForm` objects.

**Browser verification** (Docker required):
- Open Table View from explorer → all objects shown with common columns (label, type, created, modified)
- Click a type pill → table filters to that type, columns change to SHACL-discovered properties
- Click a different type pill → columns change again
- Click "All Types" pill → back to common columns, all objects shown
- With a type selected, carousel tab bar appears showing model-declared view variants
- Switch carousel tab → model-declared view loads
- Saved Views folder shows promoted query views
- No per-type/per-model folders in explorer tree
- Pagination works in generic views
- Filter works in generic views

## Constraints

- **Pagination template is coupled to URL pattern.** `pagination.html` and `view_toolbar.html` construct URLs as `/browser/views/{view_type}/{spec_iri_encoded}`. Generic views use a different URL pattern (`/browser/views/generic/{renderer}?type={type}`). Must refactor both templates to accept a base URL parameter, or the generic view won't paginate/filter correctly.
- **`execute_table_query()` requires `spec.sparql_query` to be non-empty.** The early return on empty query (returns empty rows) means generic views must set the dynamically-built query on a transient ViewSpec before calling execute. Can't pass query separately.
- **Carousel tab bar expects `all_specs` (model-declared specs for a type).** When no type is selected (All Types), there are no model specs — the carousel should not render. When a type is selected, the carousel needs both the generic renderers AND the model-declared renderers listed as tabs.
- **`scope_to_current_graph()` is mandatory.** All dynamically-built queries must pass through it. The function injects `FROM <urn:sempkm:current>` — without it, queries scan all named graphs.

## Common Pitfalls

- **Double-encoding spec IRIs in URLs.** The `spec_iri_encoded` variable uses `quote(iri, safe="")` in the router, and templates use `{{ spec_iri_encoded }}` in href URLs. Generic views don't have a spec IRI in the URL — they use `?type=` query params. If the pagination template tries to URL-encode a type IRI into the path segment, it will double-encode.
- **Column order instability.** `PropertyShape.order` is a float from `sh:order`. If multiple properties have the same `sh:order` (or 0.0 default), column order is undefined. The dynamic query builder should sort by `(order, name)` for determinism.
- **Graph view without type filter.** Rendering an all-types graph could pull thousands of nodes. The CONSTRUCT query for generic graph view needs a LIMIT (200 nodes default) and should encourage type selection first. The design doc flags this as an open question — recommend requiring type selection for graph view or applying a hard limit.
- **Type pills rendering before ShapesService cache is warm.** First request after startup may be slow. `ShapesService` calls `_fetch_shapes_graph()` which does a CONSTRUCT across all model shapes graphs. This is already the case for existing views — not new, but worth noting.

## Open Risks

- **SHACL shapes may have deeply nested property paths.** `sh:path` could theoretically be a SHACL property path (sequence, alternative, inverse). The current `_extract_property_shape()` extracts `sh:path` as a simple IRI. If any model uses complex paths, the dynamic query builder will produce invalid SPARQL. Low risk — all current models use simple IRI paths.
- **Generic graph view CONSTRUCT query.** Existing graph ViewSpecs ship custom CONSTRUCT queries. The generic graph view needs to build a CONSTRUCT dynamically. This is less straightforward than SELECT — need to decide what triples to construct (all properties? all relationships? just typed subjects?). Recommend building a standard CONSTRUCT that gets all relationships between typed objects, mirroring the pattern in `models/basic-pkm/views/basic-pkm.jsonld`.
