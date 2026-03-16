---
id: T02
parent: S01
milestone: M007
provides:
  - GET /browser/views/generic/{renderer} — table/card/graph endpoints with dynamic SHACL queries
  - GET /browser/views/generic/{renderer}/data — JSON data endpoint for generic graph view
  - GET /browser/views/type-pills — JSON endpoint returning available types with hrefs
  - pagination_base_url pattern — backward-compatible URL refactor for pagination, sort, filter
  - register_generic_views() called at startup in lifespan
key_files:
  - backend/app/views/router.py
  - backend/app/views/service.py
  - backend/app/main.py
  - backend/app/templates/browser/pagination.html
  - backend/app/templates/browser/view_toolbar.html
  - backend/app/templates/browser/table_view.html
  - backend/app/templates/browser/cards_view.html
  - backend/app/templates/browser/graph_view.html
  - frontend/static/js/graph.js
  - backend/tests/test_dynamic_query_builder.py
key_decisions:
  - Made rdf:type mandatory in default select query to ground ?s binding (was all-OPTIONAL causing empty results)
  - Used pag_extra approach for type param in pagination URLs (simpler than modifying pag_base with query string logic)
  - Added graph_data_url template variable + customDataUrl param to graph.js initGraph() for generic graph data endpoint
  - Generic graph uses separate /generic/graph/data endpoint rather than retrofitting existing /graph/{spec_iri}/data
patterns_established:
  - pagination_base_url | default() pattern in templates — all URL-generating templates now accept an override
  - pag_extra carries non-standard params (type, group_by) via & separator on pagination URLs
  - selected_type template variable propagated through hx-vals for filter toolbar type persistence
observability_surfaces:
  - INFO log "Registered 3 generic views" at startup
  - INFO log "generic_view: renderer=X type=Y" on each generic view request
  - 404 HTML for invalid renderer (not a 500 crash)
  - GET /browser/views/type-pills returns JSON type list
duration: ~60min
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: Generic view endpoints and pagination URL refactor

**Wired dynamic query builder to HTTP endpoints for table/card/graph generic views, refactored all pagination/sort/filter URLs to use `pagination_base_url` pattern, added type-pills endpoint, registered generic views at startup.**

## What Happened

1. **Startup registration**: Added `view_spec_service.register_generic_views()` call in `main.py` lifespan after ViewSpecService creation. ShapesService was already wired as constructor dependency from T01.

2. **Generic view endpoint** (`GET /browser/views/generic/{renderer}`): Validates renderer is table/card/graph, builds dynamic SPARQL via `build_dynamic_query()`, creates transient ViewSpec, delegates to `execute_table_query()`/`execute_cards_query()`/`execute_graph_query()`. Passes `pagination_base_url`, `pag_extra`, `selected_type`, and `is_generic` to template context. When `type` param is provided, SHACL-discovered columns appear and type label is resolved.

3. **Generic graph data endpoint** (`GET /browser/views/generic/{renderer}/data`): Separate JSON endpoint for graph renderer because generic specs have empty `sparql_query` — query is built dynamically per request. Updated `graph.js` `initGraph()` to accept optional `customDataUrl` parameter (5th arg, backward compatible). Template passes `graph_data_url` when in generic mode.

4. **Type pills endpoint** (`GET /browser/views/type-pills`): Returns JSON with type list from `shapes_service.get_types()`, including IRI, label, active state, and href for each pill.

5. **Pagination refactor**: Changed `pagination.html` line 3 from hardcoded URL to `pagination_base_url | default(old_pattern)`. Extended `pag_extra` to chain with existing group_by param via `| default("")`.

6. **View toolbar refactor**: Same `pagination_base_url | default()` pattern for `filter_base_url`. Added `selected_type` to `hx-vals` when present.

7. **Table sort header refactor**: Sort links now use `sort_base = pagination_base_url | default()` with `sort_extra = pag_extra | default("")`.

8. **Cards group-by refactor**: Group-by select `hx-get` now uses `pagination_base_url | default()` with type in `hx-vals`.

9. **Existing endpoint updates**: All three existing renderer endpoints (table, card, graph) now pass `pagination_base_url` in context for full backward compatibility.

10. **Default query fix**: Made `?s rdf:type ?type .` mandatory (non-OPTIONAL) in `_build_default_select()` — all-OPTIONAL patterns left `?s` unbound causing empty results. Updated corresponding test.

## Verification

- `python -m pytest tests/test_dynamic_query_builder.py -v` — **32/32 passed** (run in Docker container with worktree volume mounts)
- `curl /browser/views/generic/table` — 200, renders HTML with "All Objects" label, toolbar, filter input
- `curl /browser/views/generic/table?type=urn:sempkm:model:basic-pkm:Note` — 200, SHACL columns (title, body, noteType, isAbout, etc.), type in hx-vals
- `curl /browser/views/generic/card` — 200
- `curl /browser/views/generic/graph` — 200
- `curl /browser/views/generic/graph/data` — 200, returns JSON with 40 nodes and 25 edges
- `curl /browser/views/generic/invalid` — 404
- `curl /browser/views/type-pills?renderer=table` — 200, returns 5 types with correct hrefs
- `curl /browser/views/table/urn:sempkm:model:basic-pkm:view-note-table` — 200, sort headers use `/browser/views/table/{encoded_iri}`, backward compatible
- Existing model-declared view endpoints return identical URL patterns in sort/filter/pagination
- `register_generic_views()` logged at startup: "Registered 3 generic views"

### Slice-level verification status (intermediate task)
- ✅ Unit tests for `build_dynamic_query()` pass (32/32)
- ✅ `GET /browser/views/generic/table` returns HTML
- ✅ `GET /browser/views/generic/table?type=<iri>` returns filtered with SHACL columns
- ✅ `GET /browser/views/generic/invalid-renderer` returns 404
- ⏳ Browser: pagination controls work — verified via curl (pagination URLs are correct in rendered HTML); full browser pagination test deferred to T03 when data-populated views are tested
- ⏳ Browser: type pill click → table filters — type-pills endpoint works; UI integration in T03
- ⏳ Browser: carousel tab bar — pending T03
- ⏳ Browser: Saved Views folder — pending later task

## Diagnostics

- `curl /browser/views/generic/table` — renders HTML; check for `is_generic` in template context
- `curl /browser/views/type-pills?renderer=table` — returns JSON type list
- API logs: `grep "generic_view\|Registered.*generic" docker compose logs api`
- Invalid renderer: `curl /browser/views/generic/foobar` → 404 HTML
- Empty results: "No objects found for this view." message with correct toolbar

## Deviations

- Made `?s rdf:type ?type .` mandatory in `_build_default_select()` — the all-OPTIONAL pattern from T01 left `?s` unbound, causing empty results in generic views. Updated corresponding test assertion.
- Added `GET /browser/views/generic/{renderer}/data` endpoint (not in original plan) — needed because generic specs have empty `sparql_query` and build queries dynamically, so the existing `/graph/{spec_iri}/data` endpoint can't serve them.
- Modified `graph.js` `initGraph()` signature to accept optional 5th param `customDataUrl` — needed for generic graph to use the correct data endpoint.

## Known Issues

- Docker Compose for worktree (M007 directory) has RDF4J lock/startup issues on fresh volumes — used main project Docker for testing. Not a code issue.

## Files Created/Modified

- `backend/app/views/router.py` — added generic_view, generic_graph_data, type_pills endpoints; added pagination_base_url to existing endpoint contexts
- `backend/app/views/service.py` — fixed _build_default_select() to make rdf:type mandatory
- `backend/app/main.py` — added register_generic_views() call in lifespan
- `backend/app/templates/browser/pagination.html` — refactored pag_base to use pagination_base_url | default()
- `backend/app/templates/browser/view_toolbar.html` — refactored filter_base_url, added selected_type to hx-vals
- `backend/app/templates/browser/table_view.html` — refactored sort header URLs to use pagination_base_url
- `backend/app/templates/browser/cards_view.html` — refactored group-by select hx-get
- `backend/app/templates/browser/graph_view.html` — added graph_data_url and customDataUrl support
- `frontend/static/js/graph.js` — added optional customDataUrl parameter to initGraph()
- `backend/tests/test_dynamic_query_builder.py` — updated test for mandatory rdf:type in default select
