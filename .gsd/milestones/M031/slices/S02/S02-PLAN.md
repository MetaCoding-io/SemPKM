# S02: Multiple View Instances + Saved Views Fix

**Goal:** Users can open multiple instances of the same generic view type as independent dockview tabs with different scopes, and the Saved Views folder in the explorer loads/displays/creates/unpins views correctly.
**Demo:** Open "Table View" from explorer → table tab appears. Open "Table View" again from explorer → second table tab appears with a different tab ID. In a table view with a type filter and scope query active, click "Save View" → enter name → saved view appears in Saved Views folder. Click the saved view → it reopens with correct renderer, type filter, and scope query. Click unpin → entry disappears.

## Must-Haves

- `openGenericViewTab()` creates unique tab IDs so two instances of the same renderer can coexist as separate dockview panels
- Tab labels differentiate instances (append scope query name when set)
- "Save View" button in view toolbar calls a new backend endpoint to persist the current view configuration
- `PromotedViewData` extended with `type_filter` and `scope_query_id` fields stored as RDF triples
- New `POST /api/views/save` endpoint creates a PromotedView without requiring a pre-existing saved query
- `my_views.html` routes saved generic views through `openGenericViewTab(renderer, scopeQuery)` with type filter and scope metadata
- Saved Views folder shows correct renderer-type icons, labels, and unpin actions
- Unit tests cover save_promoted_view, list_promoted_views with new fields, and tab key uniqueness logic

## Proof Level

- This slice proves: contract + integration
- Real runtime required: no (unit tests verify data model and tab ID logic)
- Human/UAT required: yes (visual confirmation of multi-tab behavior and saved views folder)

## Verification

- `cd /home/james/Code/SemPKM && python3 -c "import ast; ast.parse(open('backend/app/sparql/query_service.py').read())"` — no syntax errors
- `cd /home/james/Code/SemPKM && python3 -c "import ast; ast.parse(open('backend/app/views/router.py').read())"` — no syntax errors
- `cd /home/james/Code/SemPKM && python3 -c "import ast; ast.parse(open('backend/app/browser/workspace.py').read())"` — no syntax errors
- `cd /home/james/Code/SemPKM && grep -c "generic-view:" frontend/static/js/workspace.js` — returns 0 (old fixed tab ID pattern replaced)
- `cd /home/james/Code/SemPKM && grep -q "save_promoted_view" backend/app/sparql/query_service.py` — new method exists
- `cd /home/james/Code/SemPKM && grep -q "POST.*views/save\|post.*views/save" backend/app/views/router.py` — new endpoint exists
- `cd /home/james/Code/SemPKM && grep -q "openGenericViewTab" backend/app/templates/browser/my_views.html` — saved views route through generic tab opener
- `cd /home/james/Code/SemPKM && python -m pytest backend/tests/test_view_save.py -v` — all tests pass

## Observability / Diagnostics

- Runtime signals: `logger.info("save_promoted_view: ...")` on save, `logger.info("generic_view: ...")` already logs renderer/type/scope_query on every generic view request
- Inspection surfaces: `/browser/my-views` endpoint returns saved view entries; browser DevTools shows tab panel IDs in dockview
- Failure visibility: `logger.warning(...)` for invalid save attempts; dockview console errors if duplicate tab IDs slip through

## Integration Closure

- Upstream surfaces consumed: `openGenericViewTab(renderer, scopeQuery)` from S01, `scope_query` URL parameter from S01, `PromotedViewData` and `list_promoted_views()` from `query_service.py`, `view_toolbar.html` scope dropdown pattern from S01
- New wiring introduced: `POST /api/views/save` endpoint, `save_promoted_view()` method, modified tab ID scheme in `openGenericViewTab()`
- What remains before the milestone is truly usable end-to-end: S07 E2E tests for multi-tab + saved views; user guide docs

## Tasks

- [ ] **T01: Enable multiple generic view instances as separate dockview tabs** `est:45m`
  - Why: Currently `openGenericViewTab()` uses a fixed tab ID `generic-view:{renderer}`, so clicking "Table View" twice just activates the existing tab. Multiple instances need unique IDs.
  - Files: `frontend/static/js/workspace.js`, `frontend/static/js/workspace-layout.js`
  - Do: Change `openGenericViewTab()` to generate unique tab IDs incorporating scope query and a counter for unscoped instances. Differentiate tab labels by appending scope query name when available. On second click from explorer with no scope, generate a fresh instance instead of deduplicating. Ensure `workspace-layout.js` special-panel init continues to extract renderer/selectedType/scopeQuery from params correctly.
  - Verify: `grep -c "generic-view:" frontend/static/js/workspace.js` returns 0 (no hardcoded fixed tab key); `node -e "..."` inline syntax check of modified JS functions
  - Done when: `openGenericViewTab('table')` called twice creates two separate dockview panels with distinct IDs and labels

- [ ] **T02: Save View endpoint, toolbar button, and Saved Views display fix with unit tests** `est:1h30m`
  - Why: Users need to save their current view configuration and reopen it later. The existing Saved Views folder routes through `openViewTab()` which goes to dedicated model-view endpoints, not generic views.
  - Files: `backend/app/sparql/query_service.py`, `backend/app/views/router.py`, `backend/app/browser/workspace.py`, `backend/app/templates/browser/view_toolbar.html`, `backend/app/templates/browser/my_views.html`, `frontend/static/css/views.css`, `backend/tests/test_view_save.py`
  - Do: (1) Extend `PromotedViewData` with `type_filter` and `scope_query_id` fields. Add `PRED_TYPE_FILTER` and `PRED_SCOPE_QUERY` vocabulary constants. (2) Add `save_promoted_view()` method that creates a PromotedView without requiring a saved query — `PRED_FROM_QUERY` becomes optional. (3) Update `list_promoted_views()` SPARQL to use OPTIONAL for new fields and for `fromQuery`. (4) Add `POST /api/views/save` endpoint in `router.py`. (5) Add "Save View" button to `view_toolbar.html` with JS prompt for name. (6) Fix `my_views.html` to call `openGenericViewTab(renderer, scopeQuery)` for generic saved views and pass type_filter/scope_query_id as data attributes. (7) Update `workspace.py` `my_views()` to pass extended PromotedViewData metadata. (8) Write unit tests in `test_view_save.py`.
  - Verify: `python -m pytest backend/tests/test_view_save.py -v` — all tests pass; `python3 -c "import ast; ast.parse(open('backend/app/sparql/query_service.py').read())"` — no errors
  - Done when: Save View button in toolbar creates a promoted view; Saved Views folder shows entries with correct icons; clicking a saved generic view opens via `openGenericViewTab` with correct params; unpin removes the entry

## Files Likely Touched

- `frontend/static/js/workspace.js`
- `frontend/static/js/workspace-layout.js`
- `backend/app/sparql/query_service.py`
- `backend/app/views/router.py`
- `backend/app/browser/workspace.py`
- `backend/app/templates/browser/view_toolbar.html`
- `backend/app/templates/browser/my_views.html`
- `frontend/static/css/views.css`
- `backend/tests/test_view_save.py`
