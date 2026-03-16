---
estimated_steps: 8
estimated_files: 7
---

# T02: Generic view endpoints and pagination URL refactor

**Slice:** S01 — Generic Views & Explorer Consolidation
**Milestone:** M007

## Description

Wire the dynamic query builder to HTTP endpoints that produce rendered HTML for generic table, card, and graph views. Fix the hardcoded URL patterns in pagination, sort headers, and filter toolbar so generic views (which use `?type=` query params instead of spec IRI path segments) can paginate, sort, and filter correctly. Call `register_generic_views()` at startup.

## Steps

1. **Read T01 outputs**: check the methods added to `ViewSpecService` — `register_generic_views()`, `get_generic_spec()`, `build_dynamic_query()`, `get_generic_columns()`. Understand the return types and how the transient ViewSpec should be constructed.

2. **Add startup registration** in `backend/app/main.py`. In the `lifespan()` function, after `ViewSpecService` is created and stored in `app.state`, call `view_spec_service.register_generic_views()`. Also wire `ShapesService` into `ViewSpecService.__init__` if T01 added it as a dependency — check how `get_view_spec_service` dependency injection works in `backend/app/dependencies.py` and update accordingly.

3. **Add `GET /browser/views/generic/{renderer}` endpoint** in `backend/app/views/router.py`. Parameters: `renderer: str` (path), `type: str = Query(default="")`, plus standard pagination/sort/filter params matching existing `table_view` endpoint signature. Logic:
   - Validate `renderer` is one of `table`, `card`, `graph` — return 404 if not
   - Call `view_spec_service.build_dynamic_query(type_iri or None)` to get `(sparql_query, columns)`
   - Create a transient `ViewSpec` with the built query, renderer_type=renderer, and the well-known generic IRI
   - Set `pagination_base_url = f"/browser/views/generic/{renderer}" + (f"?type={quote(type, safe='')}" if type else "")`
   - For table renderer: delegate to `execute_table_query()` with the transient spec, render `table_view.html` with additional context: `is_generic=True`, `pagination_base_url`, `selected_type=type`
   - For card renderer: delegate to `execute_cards_query()`, render `cards_view.html`
   - For graph renderer: delegate to `execute_graph_query()`, render `graph_view.html`
   - Label resolution: call `label_service.resolve_batch()` for row IRIs (same as existing endpoints)
   - When `type` is provided, also fetch type label and pass `type_label` to context

4. **Add `GET /browser/views/type-pills` endpoint** in router. Calls `shapes_service.get_types()`, returns rendered `type_filter_pills.html` partial. Accept `selected_type` and `renderer` query params for active state and hrefs. (The actual template file will be created in T03 — for now, create a minimal placeholder that returns the type list as JSON or a simple HTML list so the endpoint is testable.)

5. **Refactor `pagination.html`**: Change line 3 from `{% set pag_base = "/browser/views/" ~ pag_view_type ~ "/" ~ spec_iri_encoded %}` to `{% set pag_base = pagination_base_url | default("/browser/views/" ~ pag_view_type ~ "/" ~ spec_iri_encoded) %}`. This makes it backward compatible — existing endpoints that don't pass `pagination_base_url` still work. **Important**: the generic view `pagination_base_url` already includes `?type=X`, so pagination params must use `&` not `?`. Check if `pag_base` is always used with `?page=` — if so, the generic URL needs to end without `?` and the template needs `{{ '&' if '?' in pag_base else '?' }}` before `page=`. Alternatively, have the generic URL use `pag_extra` for the type param: set `pag_extra = "&type=" ~ selected_type` in the endpoint context. The `pag_extra` variable is already appended to pagination URLs (visible in the template). **Use `pag_extra` approach** — simpler, no template logic changes needed beyond the pag_base default.

6. **Refactor `view_toolbar.html`**: Change the `filter_base_url` line from `{% set filter_base_url = "/browser/views/" ~ current_view_type ~ "/" ~ spec_iri_encoded %}` to `{% set filter_base_url = pagination_base_url | default("/browser/views/" ~ current_view_type ~ "/" ~ spec_iri_encoded) %}`. Same backward-compatible pattern.

7. **Refactor `table_view.html` sort headers**: The sort header links use a hardcoded `/browser/views/table/{{ spec_iri_encoded }}?sort=...` URL. Change to use `{{ pagination_base_url | default("/browser/views/table/" ~ spec_iri_encoded) }}`. Same `pag_extra` approach for type param. Similarly check `cards_view.html` for any hardcoded URLs.

8. **Update existing table/card/graph endpoints** to pass `pagination_base_url` in their template context. For existing endpoints: `pagination_base_url = f"/browser/views/{view_type}/{encoded_spec_iri}"`. This ensures backward compatibility while enabling the new pattern. Also pass `is_generic = False` (or simply don't pass it — template defaults to falsy).

## Must-Haves

- [ ] `GET /browser/views/generic/table` returns rendered table with all objects when no type specified
- [ ] `GET /browser/views/generic/table?type=<iri>` returns filtered table with SHACL columns
- [ ] Pagination works in generic views (next/prev/go-to-page all functional)
- [ ] Sort headers work in generic views
- [ ] Filter toolbar works in generic views
- [ ] Existing model-declared view endpoints unaffected (backward compatible)
- [ ] `register_generic_views()` called at startup
- [ ] Type pills endpoint returns type list

## Verification

- `cd backend && python -m pytest tests/test_dynamic_query_builder.py -v` — still passes (no regression)
- Docker up → `curl http://localhost:3000/browser/views/generic/table` returns HTML with table rows
- Browser: navigate to generic table → pagination controls work → filter input works → sort headers work
- Browser: navigate to existing model-declared view → still works as before

## Observability Impact

- Signals added/changed: Generic endpoint logs renderer and type at INFO level; 404 for invalid renderer
- How a future agent inspects this: `curl /browser/views/generic/table` returns HTML; check for `is_generic` in template context
- Failure state exposed: 404 HTML for invalid renderer; empty table with "No objects found" for empty results

## Inputs

- `backend/app/views/service.py` — T01 added `build_dynamic_query()`, `register_generic_views()`, `get_generic_spec()`, `get_generic_columns()`; `ShapesService` is now a constructor dependency
- `backend/app/dependencies.py` — DI factory for ViewSpecService (needs ShapesService wiring)
- `backend/app/main.py` — lifespan function where startup code runs
- `backend/app/templates/browser/pagination.html` — current hardcoded URL pattern on line 3
- `backend/app/templates/browser/view_toolbar.html` — current hardcoded filter URL
- `backend/app/templates/browser/table_view.html` — current hardcoded sort header URLs

## Expected Output

- `backend/app/views/router.py` — new `generic_view` and `type_pills` endpoints
- `backend/app/main.py` — `register_generic_views()` call in lifespan
- `backend/app/dependencies.py` — ShapesService wired into ViewSpecService factory
- `backend/app/templates/browser/pagination.html` — `pagination_base_url | default(...)` pattern
- `backend/app/templates/browser/view_toolbar.html` — same refactor
- `backend/app/templates/browser/table_view.html` — sort header URLs use pagination_base_url
- `backend/app/templates/browser/cards_view.html` — same if hardcoded URLs exist
