---
id: T02
parent: S01
milestone: M031
provides:
  - scope_query URL parameter on all three generic view endpoints (table, card, graph)
  - scope_query on generic_graph_data endpoint
  - build_dynamic_query() accepts and applies scope_filter parameter
  - Scope persists across pagination, sorting, and filtering via pag_extra
  - Scope dropdown in view toolbar showing saved queries
  - extract_scope_where_body() helper for scope sub-select generation
  - applyScopeQuery JS function for client-side scope navigation
key_files:
  - backend/app/views/router.py
  - backend/app/views/service.py
  - backend/app/templates/browser/view_toolbar.html
  - frontend/static/js/workspace.js
  - frontend/static/js/workspace-layout.js
  - frontend/static/css/views.css
key_decisions:
  - Scope filter injected as { SELECT ?s WHERE { ... } } sub-select in SPARQL — follows VFS build_scope_filter() pattern but normalizes variable to ?s for views
  - Scope dropdown only renders on generic views (is_generic guard) since dedicated model views have their own fixed queries
  - Saved query resolution uses uuid.UUID validation with graceful fallback to unfiltered on any error
patterns_established:
  - extract_scope_where_body() normalizes saved query SELECT variable to ?s via regex replacement
  - scope_query preserved in pag_extra alongside type param for pagination/filter persistence
  - Graph data URL includes scope_query when set so Cytoscape.js data fetch respects scope
observability_surfaces:
  - logger.info("generic_view: renderer=%s type=%s scope_query=%s", ...) in views/router.py
  - Browser DevTools network tab shows ?scope_query=... parameter on generic view requests
  - .view-scope-select element presence indicates saved queries are available
  - Graceful degradation: nonexistent scope_query renders unfiltered with logger.warning
duration: 25m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T02: Add saved query scope dropdown and wire scope_query parameter

**Added scope dropdown to view toolbar and wired scope_query parameter through all three generic view renderers (table, card, graph) with saved query WHERE body injection.**

## What Happened

Implemented the full scope query filtering pipeline across 6 files:

1. **service.py** — Added `scope_filter: str | None` parameter to `build_dynamic_query()`, `_build_default_select()`, `_build_shacl_select()`, and `_build_graph_query()`. When scope_filter is provided, a `{ SELECT ?s WHERE { <scope_filter> } }` sub-select is injected into the generated SPARQL, constraining which subjects appear. Added `extract_scope_where_body()` helper that extracts the WHERE body from a saved query and normalizes the primary SELECT variable to `?s`.

2. **router.py** — Added `scope_query: str = Query(default="")` to both `generic_view()` and `generic_graph_data()`. When set, resolves the saved query via `QueryService.get_query(uuid, user_id)`, extracts the WHERE body, and passes it as `scope_filter` to `build_dynamic_query()`. Gracefully degrades (renders unfiltered + logs warning) if the query ID is invalid, deleted, or extraction fails. Added `QueryService` dependency. Fetches `user_saved_queries` and `model_saved_queries` for the dropdown and passes them to all three renderer template contexts. Appends `scope_query` to `pag_extra` for pagination persistence. Passes `scope_query` to graph data URL params.

3. **view_toolbar.html** — Added a `<select class="view-scope-select">` dropdown that appears only on generic views when saved queries exist. Uses optgroups for "My Queries" and "Model Queries". Preserves `scope_query` in the filter input's `hx-vals` for filter persistence. `onchange` calls `applyScopeQuery()`.

4. **workspace.js** — Added `applyScopeQuery(queryId, renderer, selectedType)` function that constructs the URL and triggers an htmx GET swap. Updated `openGenericViewTab()` to accept optional `scopeQuery` parameter and pass it in panel params. Exported `applyScopeQuery` on window.

5. **workspace-layout.js** — Updated the `generic-view` panel init to read `params.params.scopeQuery` and include it in the URL query string.

6. **views.css** — Added `.view-scope-select` styling matching `.view-variant-select` with `max-width: 200px` and right margin.

## Verification

Syntax validation passes on all Python files. Carousel removal checks still pass. Scope query WHERE body extraction tested with 4 test cases (simple ?s, ?iri→?s rename, bad input, DISTINCT).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('backend/app/views/router.py').read())"` | 0 | ✅ pass | <1s |
| 2 | `python3 -c "import ast; ast.parse(open('backend/app/views/service.py').read())"` | 0 | ✅ pass | <1s |
| 3 | `grep -rn "carousel" backend/app/templates/ frontend/static/js/ frontend/static/css/` | 1 | ✅ pass (no matches) | <1s |
| 4 | `grep -rn "switchCarouselView\|restoreCarouselView\|sempkm_carousel_view" frontend/static/js/` | 1 | ✅ pass (no matches) | <1s |
| 5 | extract_scope_where_body unit tests (4 cases) | 0 | ✅ pass | <1s |
| 6 | Generated SPARQL structure validation (3 cases: no scope, with scope, no type + scope) | 0 | ✅ pass | <1s |

### Slice-level verification (partial — T02 is task 2 of 3)

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 1 | `cd backend && python -m pytest tests/test_view_scope.py -v` | ⬜ not yet | Test file created by T03 |
| 2 | `grep -rn "carousel" ...` | ✅ pass | Zero results |
| 3 | `grep -rn "switchCarouselView\|restoreCarouselView\|sempkm_carousel_view" ...` | ✅ pass | Zero results |
| 4 | Docker stack manual check | ⬜ deferred | Will verify in final task |

## Diagnostics

- **Scope dropdown presence:** `document.querySelector('.view-scope-select')` in browser DevTools — non-null when saved queries exist and the view is generic.
- **Scope parameter in URL:** Check network tab for `scope_query=<uuid>` parameter on generic view requests.
- **Missing scope filtering:** If scope doesn't filter, check that `extract_scope_where_body()` returns non-empty for the saved query's text (test with the query text in a Python shell).
- **Graceful degradation:** If scope_query references a deleted query, the view renders unfiltered and the server logs `generic_view: scope_query=<id> not found — rendering unfiltered`.

## Deviations

- Added `import uuid` to router.py (needed for `uuid.UUID()` conversion of scope_query string) — not mentioned in plan but required.
- Scope dropdown is guarded by `is_generic` template variable so it only appears on generic views, not on dedicated model views that have fixed queries.
- Used `QueryService` from ViewSpecService's existing injection path rather than a separate dependency for the service.py helper — the router injects QueryService directly via `Depends(get_query_service)`.

## Known Issues

None.

## Files Created/Modified

- `backend/app/views/router.py` — Added scope_query param to generic_view + generic_graph_data, QueryService dependency, saved query resolution, scope in pag_extra + template contexts
- `backend/app/views/service.py` — Added scope_filter param to build_dynamic_query + all three query builders, added extract_scope_where_body() helper
- `backend/app/templates/browser/view_toolbar.html` — Added scope dropdown with optgroups, scope_query in filter hx-vals
- `frontend/static/js/workspace.js` — Added applyScopeQuery() function, scopeQuery param in openGenericViewTab()
- `frontend/static/js/workspace-layout.js` — generic-view panel init passes scopeQuery to URL
- `frontend/static/css/views.css` — Added .view-scope-select styling
