# S03 Research: Saved Queries Everywhere

**Date:** 2026-03-21  
**Depth:** Light research — straightforward feature work wiring existing APIs and patterns to new UI surfaces  

## Summary

S03 surfaces saved queries in three new locations beyond the view toolbar (already done in S01): (1) a dedicated "Saved Queries" section in the explorer sidebar, (2) drag-to-canvas for saved query embeds, and (3) VFS browser scope integration. The codebase already has all the backend APIs, data models, and rendering infrastructure needed. This is purely UI wiring work — no new endpoints, no new data models, no architectural changes.

**Requirements targeted:** SQ-01 (explorer sidebar), SQ-02 (canvas embed), SQ-03 (object browser dropdown / VFS scope)

## Recommendation

Three independent tasks, parallelizable:

1. **Explorer sidebar "Saved Queries" section** (SQ-01) — Add a new collapsible `explorer-section` to `workspace.html` between VIEWS and DASHBOARDS. Lazy-load via htmx from a new endpoint `/browser/saved-queries/explorer` that returns a partial template listing saved queries. Each entry is clickable (loads query in SPARQL console) and draggable (sets `__canvasDragPayload` for canvas embed).

2. **Canvas drag-drop for saved queries** (SQ-02) — Already 95% done. The canvas `onDrop` handler already accepts `type:'query'` payloads. The embed picker already has a "Queries" tab that fetches from `/api/sparql/saved` and builds correct embed configs. The drag payload from the new explorer entries just needs to set `{type:'query', id: queryId, url: '/browser/sparql-result/{id}?embed=1', label: name}` — matching the existing `buildEmbedConfig('queries', item)` pattern. Essentially free once T01 explorer entries have `ondragstart` attributes.

3. **VFS browser scope by saved query** (SQ-03) — VFS mounts already support `scope_query` as a field on `MountDefinition`. The mount settings form in `workspace.js` already has a scope dropdown (`#mount-scope`) populated from `/api/sparql/saved?include_shared=true`. The `build_scope_filter()` in `vfs/strategies.py` already resolves scope queries. This requirement is essentially already implemented — the user can create/edit a mount and select a saved query as its scope. The "object browser dropdown" mentioned in CONTEXT likely refers to this existing VFS mount scope dropdown. **Validate** that the current implementation works correctly end-to-end; if it does, SQ-03 is already satisfied and just needs verification.

## Implementation Landscape

### Key Files to Change

| File | Change | Task |
|------|--------|------|
| `backend/app/templates/browser/workspace.html` | Add `section-queries` explorer section with htmx lazy-load | T01 |
| `backend/app/templates/browser/saved_queries_explorer.html` | **New file** — partial template listing saved queries as tree leaves | T01 |
| `backend/app/views/router.py` (or new route in `sparql/router.py`) | New endpoint `GET /browser/saved-queries/explorer` returning the partial | T01 |
| `frontend/static/css/workspace.css` | Minor: tree-leaf icon styling for query entries (reuse existing `.view-leaf` pattern) | T01 |

### Key Files — Already Working (verify only)

| File | What exists |
|------|-------------|
| `frontend/static/js/canvas.js` | `onDrop` accepts `type:'query'`; `buildEmbedConfig('queries', item)` builds correct URL; embed picker has "Queries" tab |
| `backend/app/browser/sparql_result.py` | `GET /browser/sparql-result/{query_id}?embed=1` renders query results as embeddable HTML |
| `backend/app/vfs/strategies.py` | `build_scope_filter()` resolves `scope_query` IRI to SPARQL WHERE body |
| `backend/app/vfs/mount_service.py` | `MountDefinition.scope_query` field, CRUD operations persist scope_query |
| `frontend/static/js/workspace.js` | Mount settings form populates `#mount-scope` dropdown from `/api/sparql/saved` |
| `backend/app/sparql/query_service.py` | Full CRUD: `list_user_queries()`, `list_model_queries()`, `list_all_queries()`, `get_query()` |
| `backend/app/sparql/router.py` | `GET /api/sparql/saved` returns user + model + shared queries |

### Patterns to Follow

1. **Explorer section pattern** — Copy the structure from `section-dashboards` or `section-workflows` in `workspace.html`: a `div.explorer-section` with a header (chevron + title + optional action button) and a body div with `hx-get` + `hx-trigger="load"` + `hx-swap="innerHTML"`.

2. **Tree leaf with drag support** — Copy from `views_explorer.html` generic view entries: `<a class="tree-leaf">` with `draggable="true"` and `ondragstart` setting `__canvasDragPayload`.

3. **Canvas drag payload format** — `{type:'query', id:'<query-uuid>', url:'/browser/sparql-result/<query-uuid>?embed=1', label:'<query-name>'}` — matches `buildEmbedConfig('queries', item)` in `canvas.js`.

4. **Endpoint pattern for explorer partial** — Follow `views_explorer()` in `views/router.py`: receives `Request` + `User`, calls `QueryService`, renders a Jinja2 partial template.

### Endpoint for Explorer Partial

The new endpoint needs to:
- Call `query_service.list_all_queries(user.id)` to get both user and model queries
- Render a partial template with tree-leaf entries for each query
- Each entry needs: icon (lucide `database` or `search`), label (query name), click handler (load in SPARQL panel), drag handler (canvas embed payload)
- Click behavior: open the SPARQL bottom panel with the query loaded. This can use `toggleBottomPanel()` + set the editor content, OR simply open a scoped generic view tab via `openGenericViewTab('table', queryId, queryName)`.

### Click Behavior Decision

Two reasonable options for what happens when a user clicks a saved query in the explorer:
- **Option A:** Open a generic Table View tab scoped to that query — `openGenericViewTab('table', queryId, queryName)`. This is the most useful default since it immediately shows the query results in a browseable view.
- **Option B:** Open the SPARQL console with the query loaded — useful for editing/re-running but requires the bottom panel which is a secondary surface.

**Recommend Option A** — it's more natural in the explorer context (explorer = browse data) and the SPARQL console already has its own "Saved" dropdown for loading queries to edit.

### What's NOT Needed

- No new backend data model — `QueryService` already has all CRUD
- No new API endpoints for queries themselves — `GET /api/sparql/saved` already exists
- No canvas.js changes — drag-drop and embed picker already handle `type:'query'`
- No VFS changes — `scope_query` already works on mounts
- No workspace.js scope changes — `applyScopeQuery()` and `openGenericViewTab(renderer, scopeQuery, scopeLabel)` already exist from S01

### Build Order

1. **T01: Explorer sidebar section + endpoint + template** — The only real new code. Add the explorer section, create the endpoint, create the partial template. Includes dragstart for canvas integration (SQ-02 is free).
2. **T02: Verification** — Verify canvas embed picker queries tab works, verify VFS mount scope dropdown works, verify explorer section renders correctly. Write any needed unit tests for the new endpoint.

### Verification Strategy

- **Explorer section:** `GET /browser/saved-queries/explorer` returns HTML with `.tree-leaf` entries for each saved query
- **Click behavior:** Clicking a query entry opens a scoped Table View tab
- **Canvas drag:** Dragging a query entry onto the canvas creates an embed node with iframe pointing to `/browser/sparql-result/{id}?embed=1`
- **Canvas embed picker:** The "Queries" tab in the embed picker already works — verify it lists queries and clicking one creates an embed
- **VFS scope:** Creating a mount with a scope query filters the mount's contents — already tested by existing VFS tests
- Syntax check all modified Python files
- `grep -rn "saved.queries\|saved_queries" backend/app/templates/` confirms new template exists
