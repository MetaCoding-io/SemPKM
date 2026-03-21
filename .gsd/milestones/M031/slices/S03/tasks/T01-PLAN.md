---
estimated_steps: 4
estimated_files: 3
skills_used: []
---

# T01: Add Saved Queries explorer section, endpoint, and template

**Slice:** S03 — Saved Queries Everywhere
**Milestone:** M031

## Description

Add a "QUERIES" section to the explorer sidebar that lists the user's saved SPARQL queries. Each entry is clickable (opens a Table View tab scoped to that query) and draggable (creates a canvas embed widget). This single task covers requirements SQ-01 (explorer sidebar) and SQ-02 (canvas embed via drag attributes).

The implementation touches three files: workspace.html (new section), a new partial template, and the views router (new endpoint). All backend APIs (`QueryService.list_all_queries()`) and frontend handlers (`openGenericViewTab()`, canvas `__canvasDragPayload` handler) already exist.

## Steps

1. **Add explorer section to `workspace.html`** — Insert a `div.explorer-section#section-queries` between the existing `section-views` and `section-dashboards` blocks. Follow the dashboards section pattern:
   - Header with `data-panel-name="queries"`, grip icon, chevron, title "QUERIES"
   - Body div `id="queries-tree"` with `hx-get="/browser/saved-queries/explorer"` + `hx-trigger="load, queriesRefreshed from:body"` + `hx-swap="innerHTML"`
   - Loading placeholder text

2. **Create `saved_queries_explorer.html` partial template** — New file at `backend/app/templates/browser/saved_queries_explorer.html`. Follow the `dashboard_explorer.html` pattern:
   - Iterate over `queries` context variable (list of `SavedQueryData` objects)
   - Separate user queries (`query.source != 'model'`) from model queries (`query.source == 'model'`) using group headers
   - Each entry is a `div.tree-leaf` with:
     - `draggable="true"` and `ondragstart` setting `__canvasDragPayload = {type:'query', id:'<query.id>', url:'/browser/sparql-result/<query.id>?embed=1', label:'<query.name>'}`
     - `onclick="openGenericViewTab('table', '<query.id>', '<query.name>')"` to open a scoped Table View
     - Lucide icon (`database` for user queries, `book-open` for model queries)
     - Label span with the query name
   - Empty state: `<div class="tree-empty">No saved queries</div>`

3. **Add endpoint to `views/router.py`** — New route `GET /browser/saved-queries/explorer`:
   - Depends on `get_current_user` and `get_query_service`
   - Calls `await query_service.list_all_queries(user.id)` to get both user and model queries
   - Passes the full list as `queries` to the template
   - Returns `templates.TemplateResponse(request, "browser/saved_queries_explorer.html", context)`

4. **Verify syntax and integration** — Run Python syntax check on `router.py`. Verify the new section appears in workspace.html with correct htmx attributes. Verify drag payload format matches canvas expectations.

## Must-Haves

- [ ] `workspace.html` has `section-queries` between `section-views` and `section-dashboards`
- [ ] `saved_queries_explorer.html` renders `.tree-leaf` entries for each saved query
- [ ] Each entry has `ondragstart` with `__canvasDragPayload` in the correct format: `{type:'query', id, url:'/browser/sparql-result/{id}?embed=1', label}`
- [ ] Each entry has `onclick` calling `openGenericViewTab('table', queryId, queryName)`
- [ ] Endpoint `/browser/saved-queries/explorer` exists and uses `QueryService.list_all_queries()`
- [ ] Empty state handled (no queries → "No saved queries" message)

## Verification

- `python3 -c "import ast; ast.parse(open('backend/app/views/router.py').read())"` — no syntax errors
- `grep -q 'section-queries' backend/app/templates/browser/workspace.html` — section exists
- `grep -q '__canvasDragPayload' backend/app/templates/browser/saved_queries_explorer.html` — drag support present
- `grep -q 'openGenericViewTab' backend/app/templates/browser/saved_queries_explorer.html` — click handler present
- `grep -q 'saved-queries/explorer' backend/app/views/router.py` — endpoint registered
- `grep -q 'saved-queries/explorer' backend/app/templates/browser/workspace.html` — htmx wired

## Inputs

- `backend/app/templates/browser/workspace.html` — existing explorer sidebar to add new section to
- `backend/app/templates/browser/dashboard_explorer.html` — reference pattern for the partial template
- `backend/app/views/router.py` — router to add the new endpoint to
- `backend/app/sparql/query_service.py` — `QueryService.list_all_queries()` API to call

## Expected Output

- `backend/app/templates/browser/workspace.html` — modified with new `section-queries` block
- `backend/app/templates/browser/saved_queries_explorer.html` — new partial template
- `backend/app/views/router.py` — modified with new `/saved-queries/explorer` endpoint

## Observability Impact

- **New signal:** `saved_queries_explorer` endpoint logs exception traces on `list_all_queries()` failure, then degrades gracefully to empty list.
- **Inspection surface:** `window.__canvasDragPayload` global is set during drag, inspectable in browser console. htmx `queriesRefreshed` event on `document.body` triggers re-fetch.
- **Failure visibility:** Error path renders "No saved queries" empty state instead of crashing — broken backend surfaces in server logs, not broken UI.
