---
id: S01
parent: M007
milestone: M007
provides:
  - 3 generic ViewSpec objects (Table/Cards/Graph) registered in-memory at startup with well-known IRIs
  - build_dynamic_query() — SHACL-to-SPARQL query builder with default column fallback
  - GET /browser/views/generic/{renderer} endpoints for table/card/graph with ?type= filter
  - GET /browser/views/generic/{renderer}/data — JSON data endpoint for generic graph
  - GET /browser/views/type-pills — JSON endpoint returning available types
  - type_filter_pills.html partial template with htmx pill buttons per RDF type
  - pagination_base_url template pattern — backward-compatible URL refactor for pagination/sort/filter
  - Carousel integration showing generic renderers + model-declared view specs when type selected
  - Explorer VIEWS section with flat entries (Spatial Canvas, Ontology Viewer, Table/Cards/Graph View, Saved Views folder)
  - openGenericViewTab() JS function using special-panel dockview component
  - generic-view specialType handler in workspace-layout.js
  - MY VIEWS section removed, merged into Saved Views folder
requires: []
affects:
  - S02
  - S03
key_files:
  - backend/app/views/service.py
  - backend/app/views/router.py
  - backend/app/main.py
  - backend/app/templates/browser/views_explorer.html
  - backend/app/templates/browser/type_filter_pills.html
  - backend/app/templates/browser/pagination.html
  - backend/app/templates/browser/view_toolbar.html
  - backend/app/templates/browser/table_view.html
  - backend/app/templates/browser/cards_view.html
  - backend/app/templates/browser/graph_view.html
  - frontend/static/js/workspace.js
  - frontend/static/js/workspace-layout.js
  - frontend/static/css/views.css
  - backend/tests/test_dynamic_query_builder.py
key_decisions:
  - D111 — Default SELECT uses mandatory rdf:type binding (all-OPTIONAL left ?s unbound)
  - D112 — Generic graph view uses separate data endpoint (generic specs have empty sparql_query)
  - D113 — pagination_base_url template variable with | default() for backward compatibility
  - D114 — Generic view tabs use special-panel dockview component, not view-panel
  - D115 — Saved Views replaces MY VIEWS as lazy-loaded folder inside VIEWS section
patterns_established:
  - _var_name_from_iri() for safe SPARQL variable names from property IRIs
  - get_generic_columns() as reusable column resolution with graceful degradation
  - pagination_base_url | default(old_pattern) in all URL-generating templates
  - pag_extra carries non-standard params (type, group_by) via & separator
  - type_filter_pills.html as htmx-driven filter partial with localStorage persistence
  - Generic IRI detection: indexOf('urn:sempkm:view:generic-') === 0
  - special-panel specialType pattern for tabs without spec IRIs
observability_surfaces:
  - logger.info("Registered %d generic views", count) at startup
  - logger.info("generic_view: renderer=%s type=%s", ...) on each request
  - logger.debug("build_dynamic_query: type=%s, columns=%d", ...) on query build
  - GET /browser/views/type-pills returns JSON type list for debugging
  - 404 HTML for invalid renderer (not 500 crash)
  - localStorage keys sempkm_generic_type_{renderer} store selected type
drill_down_paths:
  - .gsd/milestones/M007/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M007/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M007/slices/S01/tasks/T03-SUMMARY.md
  - .gsd/milestones/M007/slices/S01/tasks/T04-SUMMARY.md
duration: ~2.5h
verification_result: passed
completed_at: 2026-03-16
---

# S01: Generic Views & Explorer Consolidation

**Replaced per-model/per-type explorer tree with 3 generic views (Table/Cards/Graph) using SHACL-driven dynamic columns, type filter pills, carousel integration, and a consolidated Saved Views folder.**

## What Happened

Built the generic views infrastructure in four tasks:

**T01 — Query builder & registration (25min):** Added `build_dynamic_query()` to ViewSpecService, which uses ShapesService to discover SHACL PropertyShapes for a given type and builds SPARQL SELECT queries with OPTIONAL clauses per property. Falls back to 4 default columns (label, type, created, modified) when no type is selected, shapes are sparse (≤2 properties), or ShapesService fails. Graph renderer gets a CONSTRUCT query with LIMIT 200. Registered 3 generic ViewSpec objects in memory with well-known IRIs (`urn:sempkm:view:generic-table`, `generic-card`, `generic-graph`). 32 unit tests covering registration, column resolution, variable naming/dedup, and query building.

**T02 — Endpoints & pagination refactor (60min):** Wired endpoints at `GET /browser/views/generic/{renderer}` that build queries dynamically, create transient ViewSpec objects, and delegate to existing `execute_table_query()`/`execute_cards_query()`/`execute_graph_query()`. Added a separate `/generic/graph/data` JSON endpoint since generic specs have empty `sparql_query`. Refactored all pagination, sort-header, filter-toolbar, and group-by templates to use `pagination_base_url | default(old_pattern)` — generic views use `?type=` query params instead of spec IRI path segments, so the old hardcoded URL construction broke. All existing model-declared views pass the variable for backward compatibility. Added type-pills JSON endpoint.

**T03 — Type pills & carousel (35min):** Created `type_filter_pills.html` partial rendering "All Types" + one pill per RDF type, with htmx `hx-get` targeting the generic view endpoint. Active pill gets `.type-pill.active` styling. When a type is selected, the generic endpoint fetches model-declared ViewSpecs via `get_view_specs_for_type()` and combines them with 3 generic specs in `all_specs` — the carousel tab bar renders when `all_specs` has >1 entry. Updated `switchCarouselView()` and `loadViewContent()` in workspace.js to detect generic IRIs and route correctly. Added localStorage persistence of type selection per renderer.

**T04 — Explorer consolidation & JS wiring (45min):** Rewrote `views_explorer.html` from a per-model/per-type folder tree to 5 flat entries (Spatial Canvas, Ontology Viewer, Table View, Cards View, Graph View) plus a collapsible Saved Views folder that lazy-loads from `/browser/my-views`. Rewrote `openGenericViewTab()` to use the `special-panel` dockview pattern (like canvas/ontology/dashboard tabs). Removed the MY VIEWS sidebar section from `workspace.html`. Updated `my_views.html` and `sparql-console.js` to target `#saved-views-tree`.

## Verification

- **Unit tests:** 32/32 pass in `test_dynamic_query_builder.py` — covers registration (7), column resolution (7), variable naming (6), deduplication (1), query building (11)
- **No conflict markers** in backend/ or frontend/
- **Endpoint verification (curl):**
  - `GET /browser/views/generic/table` → 200, HTML with "All Objects" label, toolbar, filter
  - `GET /browser/views/generic/table?type=urn:sempkm:model:basic-pkm:Note` → 200, SHACL columns
  - `GET /browser/views/generic/card` → 200
  - `GET /browser/views/generic/graph` → 200
  - `GET /browser/views/generic/graph/data` → 200, JSON with nodes/edges
  - `GET /browser/views/generic/invalid` → 404 HTML
  - `GET /browser/views/type-pills?renderer=table` → 200, JSON with types
- **Browser verification:**
  - Explorer VIEWS shows exactly: Spatial Canvas (Beta), Ontology Viewer, Table View, Cards View, Graph View, Saved Views (7/7 assertions pass)
  - `openGenericViewTab('table')` / `('card')` / `('graph')` all open correct dockview tabs
  - Tab deduplication works (calling same renderer twice activates existing tab)
  - Spatial Canvas and Ontology Viewer tabs still work
  - Saved Views folder expands with lazy htmx load
  - No MY VIEWS section (`document.getElementById('section-my-views') === null`)
  - No per-model folders (`#section-views .tree-node[data-model-id]` count === 0)
- **Template verification:** pagination_base_url flows through pagination.html, view_toolbar.html, table_view.html, cards_view.html — backward compatible with existing model-declared views

## Requirements Advanced

- VIEW-01 — Generic table/card/graph endpoints serve all objects with common columns; 3 ViewSpec entries registered
- VIEW-02 — SHACL column discovery via ShapesService with fallback to defaults; proven by unit tests and typed endpoint responses
- VIEW-03 — Type filter pills render above generic views, filter by type, persist in localStorage
- VIEW-04 — Explorer VIEWS section consolidated: 5 flat entries + Saved Views folder, no per-model tree, no MY VIEWS section
- VIEW-05 — Carousel tab bar shows generic renderers + model-declared views when type pill is active

## Requirements Validated

- VIEW-01 — 3 generic ViewSpec entries in explorer, opening Table View shows all objects with common columns, no per-type folders
- VIEW-02 — SHACL columns discovered from ShapesService, fallback verified by unit test `test_sparse_shape_returns_defaults` and `test_shapes_service_exception_returns_defaults`
- VIEW-03 — Pills populated from ShapesService.get_types(), "All Types" default, type selection persists in localStorage, clicking pill filters view and changes columns
- VIEW-04 — Explorer shows Spatial Canvas, Ontology Viewer, Table View, Cards View, Graph View, Saved Views folder. No per-model/per-type tree. MY VIEWS section removed.
- VIEW-05 — When type pill active, all_specs populated with generic + model-declared specs, carousel renders with >1 entry

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- **T01:** Used renderer_type `"card"` instead of `"cards"` — matches existing ViewSpec convention used by all model-declared views
- **T02:** Made `rdf:type` mandatory (non-OPTIONAL) in `_build_default_select()` — all-OPTIONAL pattern caused empty results (recorded as D111)
- **T02:** Added `GET /browser/views/generic/{renderer}/data` endpoint not in original plan — needed for dynamic graph queries (D112)
- **T02:** Modified `graph.js` `initGraph()` to accept optional 5th param `customDataUrl` — backward compatible
- **T03:** CSS placed in `views.css` instead of `workspace.css` — better co-location with carousel styles
- **T03:** `openGenericViewTab()` added in T03 instead of T04 — natural alongside other JS changes
- **T04:** Used localStorage key `sempkm_generic_type_` (matching T03) instead of plan's `sempkm_generic_view_type_`
- **T04:** Updated `my_views.html` and `sparql-console.js` references from `#my-views-tree` to `#saved-views-tree`

## Known Limitations

- **Empty triplestore:** Browser verification of SHACL column changes on type pill click and carousel with model-declared views requires populated triplestore data — verified through code path analysis and template context propagation, not live rendering with data
- **Dead CSS:** `#section-my-views` rules in `workspace.css` are now dead code — harmless, cleanable in UI polish slice (S04)
- **Two code paths for generic URLs:** `loadViewContent()` (carousel switching within open tabs) and `openGenericViewTab()` (opening from explorer) both construct generic view URLs — the split is intentional but creates maintenance surface
- **Type pill count:** Type pills show all types without pagination — may need rethinking if type count exceeds ~15 (per D095)

## Follow-ups

- Clean up dead `#section-my-views` CSS rules in workspace.css (candidate for S04)
- Browser verification with populated triplestore to confirm SHACL column switching and carousel rendering end-to-end

## Files Created/Modified

- `backend/app/views/service.py` — Added build_dynamic_query(), register_generic_views(), get_generic_columns(), get_generic_spec(), _build_default_select(), _build_shacl_select(), _build_graph_query(), _var_name_from_iri(). ShapesService as optional constructor param.
- `backend/app/views/router.py` — Added generic_view, generic_graph_data, type_pills endpoints. Simplified views_explorer endpoint. Added pagination_base_url to existing endpoint contexts.
- `backend/app/main.py` — Added register_generic_views() call in lifespan, ShapesService wiring to ViewSpecService
- `backend/app/templates/browser/views_explorer.html` — Rewritten: flat generic entries + Saved Views folder (was per-model/per-type tree)
- `backend/app/templates/browser/type_filter_pills.html` — New partial for type filter pills with htmx
- `backend/app/templates/browser/pagination.html` — Refactored to pagination_base_url | default()
- `backend/app/templates/browser/view_toolbar.html` — Refactored filter URL, added selected_type to hx-vals
- `backend/app/templates/browser/table_view.html` — Refactored sort headers, added conditional type pills include
- `backend/app/templates/browser/cards_view.html` — Refactored group-by select, added conditional type pills include
- `backend/app/templates/browser/graph_view.html` — Added graph_data_url support, conditional type pills include
- `frontend/static/js/graph.js` — Added optional customDataUrl parameter to initGraph()
- `frontend/static/js/workspace.js` — Added openGenericViewTab(), loadViewContent() generic IRI handling, switchCarouselView() generic routing, localStorage persistence
- `frontend/static/js/workspace-layout.js` — Added generic-view specialType handler
- `frontend/static/css/views.css` — Added .type-filter-pills, .type-pill, .type-pill.active styles
- `backend/app/templates/browser/workspace.html` — Removed MY VIEWS section
- `backend/app/templates/browser/my_views.html` — Updated target IDs from #my-views-tree to #saved-views-tree
- `frontend/static/js/sparql-console.js` — Updated refreshMyViews() target from #my-views-tree to #saved-views-tree
- `backend/tests/test_dynamic_query_builder.py` — 32 unit tests across 6 test classes

## Forward Intelligence

### What the next slice should know
- Generic views use transient ViewSpec objects — `build_dynamic_query()` creates them per request. The 3 registered generic specs have empty `sparql_query` fields; queries are built dynamically.
- The `pagination_base_url` pattern is now the standard for all URL-generating templates. Any new view endpoints must pass it in template context.
- `get_view_specs_for_type(type_iri)` is the way to discover model-declared views for a given type — used by carousel integration.
- ShapesService is now a constructor dependency of ViewSpecService (optional, backward compatible).

### What's fragile
- `switchCarouselView()` in workspace.js has two branches: generic IRI detection does full innerHTML swap of `.group-editor-area`, non-generic does two-container body swap — the logic is correct but changes to either path must consider the other
- The `pag_extra` chaining in pagination templates concatenates with `&` — adding more non-standard params requires careful string concatenation or a proper URL builder

### Authoritative diagnostics
- `GET /browser/views/type-pills?renderer=table` returns the full type list from ShapesService — if types are missing here, they won't appear as pills
- `logger.info("generic_view: renderer=%s type=%s")` on each request — grep API logs for this
- Unit tests in `test_dynamic_query_builder.py` are the ground truth for query builder behavior — 32 tests, <1s runtime

### What assumptions changed
- Original plan assumed `_build_default_select()` could use all-OPTIONAL patterns — in practice, `?s` must be grounded by at least one mandatory triple pattern (rdf:type). D111 records this.
- Original plan assumed generic graph could use existing `/graph/{spec_iri}/data` endpoint — it can't because spec.sparql_query is empty for generic specs. D112 records the separate endpoint.
