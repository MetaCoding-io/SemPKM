# S03: Saved Queries Everywhere — Summary

**Status:** Complete  
**Duration:** ~25 minutes across 2 tasks  
**Risk materialized:** None (low-risk slice delivered cleanly)

## What This Slice Delivered

Saved queries are now surfaced as a first-class explorer section — users see their SPARQL saved queries in the sidebar, can click them to open scoped Table View tabs, and can drag them onto the spatial canvas to create embedded view widgets. VFS mount scope with saved queries was verified as already working.

### Concrete Deliverables

1. **QUERIES explorer section** — New `section-queries` block in `workspace.html` between VIEWS and DASHBOARDS, following the established explorer section pattern with htmx lazy-loading via `hx-trigger="load, queriesRefreshed from:body"`.

2. **Saved queries partial template** (`saved_queries_explorer.html`) — Renders queries as `.tree-leaf` entries grouped into "My Queries" (user-created, `database` icon) and "Model Queries" (from loaded models, `book-open` icon). Each entry has:
   - `onclick` → `openGenericViewTab('table', queryId, queryName)` — opens a scoped Table View tab
   - `ondragstart` → sets `window.__canvasDragPayload = {type:'query', id, url:'/browser/sparql-result/{id}?embed=1', label}` — canvas embed support
   - Empty state: "No saved queries" message

3. **Explorer endpoint** (`GET /browser/views/saved-queries/explorer`) — Calls `QueryService.list_all_queries(user.id)`, renders the partial. Error handling: exceptions logged via `logger.exception()`, endpoint degrades to empty list.

4. **28 unit tests** (`test_saved_queries_explorer.py`) — Three test classes:
   - `TestSavedQueriesExplorerTemplate` (18 tests): real Jinja2 rendering of the partial template
   - `TestSavedQueriesExplorerEndpoint` (5 tests): endpoint behavior with mocked dependencies
   - `TestSQ03VFSScopeQueryVerification` (5 tests): confirms SQ-03 VFS scope already works

### Requirement Status

| Requirement | Status | Evidence |
|------------|--------|----------|
| SQ-01 (Saved queries in explorer sidebar) | **Validated** | QUERIES section with click-to-view, 18 template tests + 5 endpoint tests |
| SQ-02 (Saved queries as canvas embed source) | **Validated** | `__canvasDragPayload` with `{type:'query', ...}` format matching existing canvas embed pattern |
| SQ-03 (Saved queries in object browser dropdown / VFS scope) | **Validated** | VFS `build_scope_filter()` + `_resolve_scope_query_sync()` already handle saved query scope. 5 verification tests confirm. |

## Patterns Established

- **Explorer section with htmx lazy-load + custom event refresh**: The QUERIES section follows the same pattern as DASHBOARDS and WORKFLOWS — `hx-trigger="load, queriesRefreshed from:body"` on a `div[hx-get]`. This is now the canonical pattern for any new explorer section.
- **Grouped tree-leaf template with mixed sources**: The partial groups entries by source (user vs. model) with section headers, collapsing headers when a group is empty. Reusable for any mixed-source listing.
- **Template rendering tests via standalone Jinja2**: T02 renders real templates via `jinja2.Environment(FileSystemLoader(...))` rather than mocking template output — catches template syntax errors that mock-based tests miss.

## Deviation from Plan

- **URL path**: Plan specified `/browser/saved-queries/explorer` but views router prefix is `/browser/views`, so actual URL is `/browser/views/saved-queries/explorer`. htmx attribute updated accordingly. Non-breaking — purely a routing convention alignment.

## What Next Slices Should Know

- **S04 (Kanban)**: No direct dependency on S03. The explorer section pattern established here can be referenced if kanban needs an explorer entry.
- **S07 (E2E + Docs)**: Needs E2E tests for the QUERIES explorer section — clicking a query to open a table view tab, verifying drag payload shape. User docs should mention the QUERIES section in the explorer sidebar guide.
- The `queriesRefreshed` custom event should be fired after saving or deleting a query to keep the explorer in sync — this needs to be wired in the SPARQL console save/delete handlers if not already present.
