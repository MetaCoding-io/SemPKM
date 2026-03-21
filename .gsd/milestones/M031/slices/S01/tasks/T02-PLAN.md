---
estimated_steps: 10
estimated_files: 5
---

# T02: Add saved query scope dropdown and wire scope_query parameter

**Slice:** S01 — Carousel Removal + View Scope Binding
**Milestone:** M031

## Description

Add a saved query scope dropdown to the view toolbar and wire the `scope_query` URL parameter through all three generic view renderers (table, card, graph). This delivers VIEW-09 (saved query scope binding on all view types).

The scope dropdown lists the user's saved SPARQL queries (from the existing `/api/sparql/saved` endpoint). Selecting one re-fetches the generic view with `?scope_query={query_id}`, which filters results to only objects that match the saved query's WHERE clause. The scope persists across pagination, sorting, filtering, and type switching.

The saved query list endpoint already exists at `GET /api/sparql/saved` and returns `SavedQueryOut` objects with `id`, `name`, `query_text`. Model-shipped queries are also available. The VFS system already has a working `build_scope_filter()` pattern in `backend/app/vfs/strategies.py` that extracts WHERE bodies from saved queries — we follow a similar approach.

**Depends on:** T01 (carousel removed, `model_view_specs` in template context, clean toolbar template)

## Steps

1. **Add scope_query parameter to generic_view endpoint.** In `backend/app/views/router.py`:
   - Add `scope_query: str = Query(default="")` parameter to `generic_view()`.
   - Import `QueryService` from the sparql module and add it as a dependency: `query_service: QueryService = Depends(get_query_service)` (check existing imports/dependencies in `dependencies.py`).
   - Also add `db: AsyncSession = Depends(get_db_session)` if needed for QueryService.

2. **Resolve saved query text when scope_query is set.** In `generic_view()`:
   - When `scope_query` is non-empty, look up the saved query by ID using `query_service.get_query(scope_query, user.id)` (or an appropriate method — check `QueryService` API).
   - Extract the query text from the result.
   - Pass the query text to `build_dynamic_query()` as a new `scope_filter` parameter.
   - If the query ID doesn't resolve (e.g., deleted query), gracefully degrade — log a warning and render unfiltered.

3. **Modify build_dynamic_query to accept scope_filter.** In `backend/app/views/service.py`:
   - Add `scope_filter: str | None = None` parameter to `build_dynamic_query()`.
   - When `scope_filter` is provided, extract its WHERE body using `_extract_where_body()` and inject it as a sub-select into the generated SPARQL query.
   - For SELECT queries (table/card): add `{ SELECT ?s WHERE { <extracted_where_body> } }` to the WHERE clause. The variable name may need mapping — the scope query likely uses `?s` or `?iri` for the subject. Check `_extract_where_body()` and adapt if the variable name differs.
   - For CONSTRUCT queries (graph): add the sub-select as a constraint on `?s` in the WHERE clause.
   - The pattern follows VFS's `build_scope_filter()` approach.

4. **Pass scope_query through pagination/filter URLs.** In `generic_view()`:
   - Add `scope_query` to `pag_extra`: `if scope_query: pag_extra += f"&scope_query={quote(scope_query, safe='')}"`.
   - This ensures pagination, sorting, and filtering preserve the active scope.
   - Pass `scope_query` value to the template context as `"scope_query": scope_query`.

5. **Fetch saved queries for the dropdown.** In `generic_view()`:
   - Call `query_service.list_user_queries(user.id)` to get the user's saved queries.
   - Also call `query_service.list_model_queries()` to get model-shipped queries.
   - Pass both to the template context as `"user_saved_queries"` and `"model_saved_queries"`.

6. **Add scope dropdown to view_toolbar.html.** In `backend/app/templates/browser/view_toolbar.html`:
   - Inside the `.view-toolbar-right` div, before the filter input, add:
   ```html
   <select class="view-scope-select"
           onchange="applyScopeQuery(this.value, '{{ renderer | default('table') }}', '{{ selected_type | default('') }}')">
       <option value="">All Objects</option>
       {% if user_saved_queries is defined and user_saved_queries %}
       <optgroup label="My Queries">
           {% for q in user_saved_queries %}
           <option value="{{ q.id }}"{% if scope_query is defined and scope_query == q.id|string %} selected{% endif %}>{{ q.name }}</option>
           {% endfor %}
       </optgroup>
       {% endif %}
       {% if model_saved_queries is defined and model_saved_queries %}
       <optgroup label="Model Queries">
           {% for q in model_saved_queries %}
           <option value="{{ q.id }}"{% if scope_query is defined and scope_query == q.id|string %} selected{% endif %}>{{ q.name }}</option>
           {% endfor %}
       </optgroup>
       {% endif %}
   </select>
   ```

7. **Add applyScopeQuery JS function.** In `frontend/static/js/workspace.js`:
   - Add a function `applyScopeQuery(queryId, renderer, selectedType)` that constructs the URL `/browser/views/generic/{renderer}?scope_query={queryId}&type={selectedType}` and triggers an htmx swap into `.group-editor-area`.
   - Export it via `window.applyScopeQuery = applyScopeQuery;`.

8. **Wire scope_query in workspace-layout.js.** In `frontend/static/js/workspace-layout.js`:
   - In the `generic-view` special panel init block, read `params.params.scopeQuery` and append it to the URL if present.
   - In `workspace.js` `openGenericViewTab()`, accept an optional `scopeQuery` parameter and include it in the panel params.

9. **Wire scope_query in generic_graph_data endpoint.** In `views/router.py`:
   - Add `scope_query: str = Query(default="")` to `generic_graph_data()`.
   - When set, resolve the query and pass the scope filter to `build_dynamic_query()`.
   - This ensures graph data respects the scope filter.

10. **Add CSS for scope dropdown.** In `frontend/static/css/views.css`:
    ```css
    .view-scope-select {
        padding: 4px 8px;
        font-size: 0.8rem;
        border: 1px solid var(--color-border);
        border-radius: 4px;
        background: var(--color-surface);
        color: var(--color-text);
        cursor: pointer;
        max-width: 200px;
    }
    ```

## Must-Haves

- [ ] `scope_query` URL parameter accepted by all three generic view endpoints (table, card, graph)
- [ ] `scope_query` accepted by `generic_graph_data()` endpoint
- [ ] `build_dynamic_query()` accepts and applies scope_filter parameter
- [ ] Scope persists across pagination, sorting, and filtering via pag_extra
- [ ] Scope dropdown shows saved queries in the view toolbar
- [ ] Selecting "All Objects" clears the scope filter
- [ ] Selecting a saved query re-fetches the view with filtered results
- [ ] Graceful degradation when scope_query references nonexistent query

## Verification

- Start Docker stack, navigate to Table View
- Select a type pill, then select a saved query from scope dropdown → view shows filtered results
- Paginate → scope persists (URL still has `scope_query=...`)
- Change type pill → scope persists
- Select "All Objects" in scope dropdown → view shows all objects again
- Open Graph View → scope dropdown is present and functional
- Open Cards View → scope dropdown is present and functional

## Inputs

- `backend/app/views/router.py` — from T01: no carousel logic, `model_view_specs` in context
- `backend/app/views/service.py` — `build_dynamic_query()` to be extended with scope_filter
- `backend/app/templates/browser/view_toolbar.html` — from T01: has variant dropdown, clean layout
- `backend/app/sparql/router.py` — existing saved query API endpoints (reference for query service patterns)
- `backend/app/vfs/strategies.py` — reference for `build_scope_filter()` and `_extract_where_body()` patterns

## Expected Output

- `backend/app/views/router.py` — `scope_query` param on generic_view + generic_graph_data, saved queries fetched for dropdown
- `backend/app/views/service.py` — `build_dynamic_query()` accepts `scope_filter`, injects sub-select
- `backend/app/templates/browser/view_toolbar.html` — scope dropdown with saved queries
- `frontend/static/js/workspace.js` — `applyScopeQuery()` function, `openGenericViewTab()` accepts scopeQuery
- `frontend/static/js/workspace-layout.js` — generic-view panel init passes scopeQuery to URL
- `frontend/static/css/views.css` — `.view-scope-select` style
