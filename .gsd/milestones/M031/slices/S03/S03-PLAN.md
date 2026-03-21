# S03: Saved Queries Everywhere

**Goal:** Saved queries are surfaced in the explorer sidebar, draggable onto the spatial canvas, and usable as VFS mount scope — making them a first-class navigation and scoping primitive across the entire UI.
**Demo:** User expands "QUERIES" section in explorer, sees their saved queries listed. Clicking a query opens a Table View tab scoped to that query's results. Dragging a query entry onto the spatial canvas creates an embedded view widget. VFS mount settings already allow selecting a saved query as scope (verified working).

## Must-Haves

- Explorer sidebar has a "QUERIES" section between VIEWS and DASHBOARDS, lazy-loaded via htmx
- Each query entry is clickable (opens scoped Table View tab) and draggable (canvas embed)
- New endpoint `GET /browser/views/saved-queries/explorer` returns the partial HTML listing
- Canvas drag payload matches existing `buildEmbedConfig('queries', item)` format: `{type:'query', id, url, label}`
- VFS mount scope dropdown confirmed working with saved queries (SQ-03 verification)

## Verification

- `python3 -c "import ast; ast.parse(open('backend/app/views/router.py').read())"` — syntax OK
- `python3 -c "import ast; ast.parse(open('backend/app/sparql/router.py').read())"` — syntax OK
- `python3 -m pytest backend/tests/test_saved_queries_explorer.py -v` — all pass
- `grep -q 'section-queries' backend/app/templates/browser/workspace.html` — section exists
- `test -f backend/app/templates/browser/saved_queries_explorer.html` — template exists
- `grep -q '__canvasDragPayload' backend/app/templates/browser/saved_queries_explorer.html` — drag support
- `grep -q 'openGenericViewTab' backend/app/templates/browser/saved_queries_explorer.html` — click opens view tab
- `grep -q 'logger.exception' backend/app/views/router.py` — error logging present in explorer endpoint

## Tasks

- [x] **T01: Add Saved Queries explorer section, endpoint, and template** `est:30m`
  - Why: SQ-01 requires saved queries in the explorer sidebar; SQ-02 (canvas embed) is free once entries have `ondragstart` drag attributes matching the existing canvas payload format.
  - Files: `backend/app/templates/browser/workspace.html`, `backend/app/templates/browser/saved_queries_explorer.html`, `backend/app/views/router.py`
  - Do: (1) Add `section-queries` explorer section to `workspace.html` between VIEWS and DASHBOARDS, following the dashboards section pattern with htmx lazy-load from `/browser/saved-queries/explorer`. (2) Create `saved_queries_explorer.html` partial template listing queries as `.tree-leaf` entries with click (`openGenericViewTab('table', queryId, queryName)`) and drag (`__canvasDragPayload = {type:'query', id, url:'/browser/sparql-result/{id}?embed=1', label}`) handlers. Group into "My Queries" and "Model Queries" using optgroup-style headers. (3) Add `GET /browser/saved-queries/explorer` endpoint to `views/router.py` using `QueryService.list_all_queries()`.
  - Verify: `python3 -c "import ast; ast.parse(open('backend/app/views/router.py').read())"` succeeds; `grep -q 'section-queries' backend/app/templates/browser/workspace.html`; `grep -q '__canvasDragPayload' backend/app/templates/browser/saved_queries_explorer.html`
  - Done when: Explorer sidebar has a QUERIES section that lazy-loads query entries with click-to-view and drag-to-canvas support

- [x] **T02: Unit test for explorer endpoint + SQ-03 VFS verification** `est:20m`
  - Why: Slice verification requires a test for the new endpoint (contract) and confirmation that SQ-03 (VFS mount scope) already works end-to-end.
  - Files: `backend/tests/test_saved_queries_explorer.py`, `backend/app/vfs/strategies.py`
  - Do: (1) Write `test_saved_queries_explorer.py` with tests for the new endpoint: returns HTML with `.tree-leaf` entries, includes drag attributes, handles empty query list, includes both user and model queries. Mock `QueryService.list_all_queries()`. (2) Verify SQ-03 by reading VFS `build_scope_filter()` and `_resolve_scope_query_sync()` — confirm saved query scope resolution already works. Add a brief comment in the test file documenting SQ-03 verification.
  - Verify: `python3 -m pytest backend/tests/test_saved_queries_explorer.py -v` — all pass
  - Done when: All tests pass; SQ-03 documented as already-implemented

## Files Likely Touched

- `backend/app/templates/browser/workspace.html`
- `backend/app/templates/browser/saved_queries_explorer.html`
- `backend/app/views/router.py`
- `backend/tests/test_saved_queries_explorer.py`

## Observability / Diagnostics

- **Endpoint logging:** `saved_queries_explorer` endpoint logs an exception with full traceback if `list_all_queries()` fails, then returns an empty list (graceful degradation — the section renders "No saved queries" instead of crashing).
- **htmx trigger observability:** The `queriesRefreshed` custom event on `document.body` triggers a re-fetch of the queries tree, making post-save/delete refresh inspectable via browser dev-tools event listener panel.
- **Failure visibility:** If the endpoint errors, the htmx swap replaces the loading placeholder with the empty-state message — no broken UI state. Backend logs surface the root cause.
- **Drag payload inspection:** `window.__canvasDragPayload` is set as a global on dragstart, inspectable via browser console during drag operations.
