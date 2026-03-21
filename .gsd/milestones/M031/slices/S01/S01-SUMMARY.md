# S01 Summary: Carousel Removal + View Scope Binding

**Status:** Complete  
**Duration:** ~60min across 3 tasks  
**Risk realized:** None — high-risk carousel removal completed cleanly  

## What This Slice Delivered

The carousel tab bar — the in-view picker that let users switch between generic and model-declared views — has been completely removed from the codebase. Users now select views exclusively via the explorer sidebar. Model-declared view variants (e.g., "Projects Table") remain accessible through a new toolbar dropdown that appears when a type filter pill is active. A saved query scope dropdown lets users filter any generic view (table, cards, graph) by a saved SPARQL query.

### Carousel Removal (T01)
- Deleted `carousel_tab_bar.html` template
- Removed `{% include %}` and `.carousel-view-body` wrapper from table, cards, and graph view templates
- Removed `switchCarouselView()` (~65 lines), `restoreCarouselView()` (~20 lines), and their `window.*` exports from `workspace.js`
- Removed all carousel CSS (`.carousel-tab-bar`, `.carousel-tab`, `.carousel-view-body`, `.view-loading-indicator`, `.view-loading-spinner`, `@keyframes carousel-spin`) from `views.css`
- Removed `sempkm_carousel_view` localStorage references
- Replaced `all_specs` carousel-building logic in `views/router.py` `generic_view()` with focused `model_view_specs` that only contains model-declared specs for the active type

### Model-Declared Variant Dropdown (T01)
- Added `<select class="view-variant-select">` to `view_toolbar.html` — conditionally renders only when `model_view_specs` is non-empty
- Each option carries the spec IRI as value and renderer type as `data-renderer`
- `onchange` calls `openViewTab()` to navigate to the selected model-declared view's dedicated endpoint
- Dedicated view endpoints (`table_view()`, `cards_view()`, `graph_view()`) pass `model_view_specs: []` since they already serve a specific view

### Saved Query Scope Binding (T02)
- Added `scope_query: str = Query(default="")` parameter to `generic_view()` and `generic_graph_data()` endpoints
- When set, resolves the saved query via `QueryService.get_query()`, extracts the WHERE body via `extract_scope_where_body()`, and injects it as a `{ SELECT ?s WHERE { ... } }` sub-select into the dynamic query
- `build_dynamic_query()`, `_build_default_select()`, `_build_shacl_select()`, and `_build_graph_query()` all accept optional `scope_filter` parameter
- `extract_scope_where_body()` normalizes the saved query's primary SELECT variable to `?s` for consistent sub-select injection
- Scope persists across pagination via `pag_extra` alongside the `type` parameter
- Graph data URL includes `scope_query` when set so Cytoscape.js data fetch respects the scope
- Graceful degradation: invalid/deleted scope_query renders unfiltered with a warning log
- Scope dropdown (`<select class="view-scope-select">`) appears in toolbar with optgroups for "My Queries" and "Model Queries"
- `applyScopeQuery()` JS function triggers htmx GET with the selected scope

### Unit Tests (T03)
- 25 tests in `backend/tests/test_view_scope.py` covering:
  - `build_dynamic_query()` with/without scope filter (6 tests)
  - `extract_scope_where_body()` including variable renaming and edge cases (10 tests)
  - `get_view_specs_for_type()` type filtering (6 tests)
  - No-scope baselines (3 tests)

## Boundary Outputs (consumed by S02–S05)

| Output | Consumer | Description |
|--------|----------|-------------|
| `model_view_specs` template variable | S02 | Replaces `all_specs` — templates check `model_view_specs is defined and model_view_specs \| length > 0` |
| `scope_query` URL parameter | S02, S03 | Wired through all generic view endpoints + graph data |
| `build_dynamic_query(scope_filter=...)` | S02, S04 | Accepts optional SPARQL WHERE body for scope filtering |
| `extract_scope_where_body()` | S03 | Utility to extract and normalize WHERE body from saved queries |
| Carousel-free view templates | S05 | Clean CSS/JS foundation for full-height fixes |
| `applyScopeQuery()` JS function | S02, S03 | Client-side scope navigation |
| `openGenericViewTab(renderer, scopeQuery)` | S02 | Accepts optional scopeQuery parameter stored in panel params |

## Patterns Established

1. **Scope sub-select injection**: `{ SELECT ?s WHERE { <scope_filter> } }` pattern for constraining view results by a saved query — follows VFS `build_scope_filter()` but normalizes variable to `?s`
2. **Conditional toolbar dropdowns**: Template guards like `model_view_specs | length > 0` to show/hide toolbar elements
3. **Graceful degradation for missing scope**: Invalid scope_query renders unfiltered with `logger.warning` — no user-facing error

## Key Decisions

- **D284**: Model-declared view variant access after carousel removal — toolbar dropdown + Saved Views folder replaces carousel
- **D285**: M031 requirement IDs and numbering scheme (VIEW-08 through VIEW-14, SQ-01 through SQ-03, etc.)
- Variant dropdown uses existing `openViewTab()` to navigate rather than inline htmx swap
- Scope filter injected as sub-select in SPARQL, not as a JOIN or FILTER — consistent with VFS pattern
- Scope dropdown only renders on generic views (`is_generic` guard) since dedicated model views have fixed queries

## Observability

- `logger.info("generic_view: renderer=%s type=%s scope_query=%s", ...)` on every generic view request
- `logger.warning("generic_view: scope_query=%s not found — rendering unfiltered", ...)` for missing scopes
- Browser DevTools: `?scope_query=...` parameter visible on generic view network requests
- `.view-variant-select` element presence = model-declared ViewSpecs exist for active type
- `.view-scope-select` element presence = saved queries available

## Verification Results

| Check | Result |
|-------|--------|
| `grep -rn "carousel" backend/app/templates/ frontend/static/js/ frontend/static/css/views.css` | ✅ Zero results |
| `grep -rn "switchCarouselView\|restoreCarouselView\|sempkm_carousel_view" frontend/static/js/` | ✅ Zero results |
| `carousel_tab_bar.html` deleted | ✅ Confirmed |
| `grep -rn "all_specs" backend/app/templates/ backend/app/views/router.py` | ✅ Zero results |
| `python -m pytest tests/test_view_scope.py -v` | ✅ 25 passed |
| `router.py` syntax check | ✅ OK |
| `service.py` syntax check | ✅ OK |

## What the Next Slice Should Know

- **S02** depends on `openGenericViewTab(renderer, scopeQuery)` and `scope_query` URL parameter — both are wired and tested
- **S03** can reuse `extract_scope_where_body()` for saved query scope injection in other surfaces
- **S04** (Kanban) should follow the same `scope_filter` parameter pattern in its renderer
- **S05** (full-height CSS) benefits from carousel removal — no more `.carousel-view-body` wrapper to propagate height through
- The `is_generic` template variable gates scope dropdown visibility — dedicated model views don't show it
- `extract_scope_where_body()` returns empty for queries with LIMIT/ORDER BY after the closing WHERE brace — callers should strip those clauses first
