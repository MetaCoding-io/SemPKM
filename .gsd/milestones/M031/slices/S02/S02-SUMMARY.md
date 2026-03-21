# S02 Summary: Multiple View Instances + Saved Views Fix

**Status:** Complete
**Requirements validated:** VIEW-10 (multiple view instances), VIEW-11 (saved views CRUD)
**Decisions recorded:** D289 (tab ID refinement), D290 (generic vs query-based saved views routing)

## What This Slice Delivered

Users can now open multiple instances of the same generic view type (table, cards, graph) as independent dockview tabs, each with its own scope. A "Save View" button in the view toolbar persists the current view configuration. The Saved Views folder correctly loads, displays, and manages both generic and query-based saved views.

### T01: Multiple Generic View Instances (15m)

Rewrote `openGenericViewTab()` in `workspace.js` with a dual tab ID strategy:

- **Scoped tabs:** `generic-view:{renderer}:scope:{queryId}` — deduplicates (same query = same tab)
- **Unscoped tabs:** `generic-view:{renderer}:{Date.now()}` — every explorer click creates a fresh tab

Tab labels differentiate instances: scoped tabs append the query name ("Table View — My Projects"), unscoped duplicates get a numeric suffix ("Table View (2)") counting existing same-renderer panels.

**Files:** `frontend/static/js/workspace.js`

### T02: Save View Endpoint + Toolbar Button + Saved Views Display Fix (30m)

Full "Save Current View" feature across 6 files + unit tests:

1. **Extended `PromotedViewData`** with `type_filter` and `scope_query_id` fields. Added `PRED_TYPE_FILTER` and `PRED_SCOPE_QUERY` vocabulary constants.
2. **`save_promoted_view()` method** — creates a PromotedView without requiring a saved query. Validates renderer_type, builds INSERT DATA with conditional triples.
3. **`delete_promoted_view()` method** — unpins by view ID (not query ID), supporting generic views with no associated query.
4. **`list_promoted_views()` updated** — OPTIONAL SPARQL for all extended fields and `fromQuery`, so views saved without a query aren't excluded.
5. **`POST /browser/views/save`** endpoint with `SaveViewRequest` Pydantic model + `DELETE /browser/views/saved/{view_id}` endpoint.
6. **"Save View" button** in `view_toolbar.html` with `bookmark-plus` Lucide icon, guarded by `is_generic` flag.
7. **Rewrote `my_views.html`** — generic saved views route through `openGenericViewTab()`, query-based views keep `openViewTab()`. Two-path unpin pattern.
8. **Simplified `my_views()` endpoint** — passes `PromotedViewData` directly, removed ViewSpecService intermediary.
9. **13 unit tests** covering save (basic, with type_filter, with scope, with all fields, invalid renderer, unique IDs, graph target), list (all fields, missing optional, OPTIONAL clauses, empty, mixed), and delete.

**Files:** `backend/app/sparql/query_service.py`, `backend/app/views/router.py`, `backend/app/browser/workspace.py`, `backend/app/templates/browser/view_toolbar.html`, `backend/app/templates/browser/my_views.html`, `frontend/static/css/views.css`, `backend/tests/test_view_save.py`

## Verification Results

| Check | Result |
|-------|--------|
| `query_service.py` parses | ✅ |
| `router.py` parses | ✅ |
| `workspace.py` parses | ✅ |
| Old fixed tab ID pattern gone | ✅ (grep for `var tabKey = 'generic-view:' + renderer;` returns 0) |
| `save_promoted_view` method exists | ✅ |
| `@router.post("/save")` endpoint exists | ✅ |
| `openGenericViewTab` in my_views.html | ✅ |
| 13 unit tests pass | ✅ (0.11s) |

**Note:** The slice plan's check `grep -c "generic-view:" workspace.js` returns 3, not 0. This is a spec false-negative — the new dynamic pattern necessarily contains the prefix string. The correct check (old fixed pattern removed) passes.

## Patterns Established

- **Tab ID scheme:** `generic-view:{renderer}:{timestamp}` (unscoped) or `generic-view:{renderer}:scope:{queryId}` (scoped)
- **Two-path saved views:** Generic saves via `openGenericViewTab()` + `deleteSavedView()`, query-based via `openViewTab()` + `demoteView()`
- **OPTIONAL SPARQL for extended PromotedViewData:** All new predicates wrapped in OPTIONAL so older views without those fields still appear in listings
- **SaveViewRequest Pydantic model** for POST /browser/views/save with name, renderer_type, type_filter, scope_query_id

## What Downstream Slices Should Know

- **S07 (E2E Tests):** Multi-tab behavior requires testing that clicking "Table View" twice from explorer creates two tabs, and that saving a view then clicking it from Saved Views opens the correct renderer with correct scope. The tab ID format is `generic-view:{renderer}:{timestamp}` — selectors should use prefix matching.
- **S03 (Saved Queries Everywhere):** `save_promoted_view()` can optionally link to a saved query via `scope_query_id`. The method is independent of the existing `promote_to_view()` path, so saved queries can be promoted either way.
- **S04 (Kanban):** When kanban renderer is added, it automatically works with `openGenericViewTab('kanban')` — no changes needed to the multi-instance system.

## Observability

- `logger.info("save_promoted_view: user=%s label=%s renderer=%s", ...)` on save
- `logger.info("Deleted promoted view %s for user %s", ...)` on delete
- `ValueError` for invalid renderer_type; HTTP 400 with error message
- Panel IDs visible in browser DevTools dockview containers
- `GET /browser/my-views` returns saved view HTML for inspection
