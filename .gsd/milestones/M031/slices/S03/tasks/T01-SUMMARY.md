---
id: T01
parent: S03
milestone: M031
provides:
  - QUERIES explorer section in sidebar
  - saved_queries_explorer.html partial template
  - GET /browser/views/saved-queries/explorer endpoint
key_files:
  - backend/app/templates/browser/workspace.html
  - backend/app/templates/browser/saved_queries_explorer.html
  - backend/app/views/router.py
key_decisions:
  - Endpoint placed in views/router.py (prefix /browser/views) so actual URL is /browser/views/saved-queries/explorer, not /browser/saved-queries/explorer as original plan stated
patterns_established:
  - Explorer partial template with grouped tree-leaf entries, drag payload, and click handler following dashboard_explorer.html pattern
observability_surfaces:
  - logger.exception in saved_queries_explorer endpoint on list_all_queries failure
  - Graceful degradation to empty-state message on error
  - window.__canvasDragPayload global inspectable during drag
  - queriesRefreshed custom event triggers re-fetch
duration: 15m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T01: Add Saved Queries explorer section, endpoint, and template

**Added QUERIES explorer section to sidebar with htmx-loaded saved query listing, click-to-open-table-view, and drag-to-canvas support**

## What Happened

Added a "QUERIES" explorer section to `workspace.html` between the VIEWS and DASHBOARDS sections, following the dashboards section pattern with htmx lazy-loading via `hx-trigger="load, queriesRefreshed from:body"`.

Created `saved_queries_explorer.html` partial template that renders saved queries as `.tree-leaf` entries, grouped into "My Queries" (user-created) and "Model Queries" (from loaded models). Each entry has:
- `ondragstart` setting `window.__canvasDragPayload` with `{type:'query', id, url:'/browser/sparql-result/{id}?embed=1', label}` — matching the existing canvas embed format
- `onclick` calling `openGenericViewTab('table', queryId, queryName)` to open a scoped Table View tab
- Lucide icons: `database` for user queries, `book-open` for model queries
- Empty state: "No saved queries" when no queries exist

Added `GET /browser/views/saved-queries/explorer` endpoint to `views/router.py` that calls `QueryService.list_all_queries(user.id)` and renders the partial template. The endpoint includes error handling — exceptions are logged and the endpoint degrades gracefully to an empty list.

## Verification

All 8 task-level verification checks pass. Slice-level checks that apply to T01 all pass; the pytest check is expected to fail until T02 creates the test file.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('backend/app/views/router.py').read())"` | 0 | ✅ pass | <1s |
| 2 | `python3 -c "import ast; ast.parse(open('backend/app/sparql/router.py').read())"` | 0 | ✅ pass | <1s |
| 3 | `grep -q 'section-queries' backend/app/templates/browser/workspace.html` | 0 | ✅ pass | <1s |
| 4 | `test -f backend/app/templates/browser/saved_queries_explorer.html` | 0 | ✅ pass | <1s |
| 5 | `grep -q '__canvasDragPayload' backend/app/templates/browser/saved_queries_explorer.html` | 0 | ✅ pass | <1s |
| 6 | `grep -q 'openGenericViewTab' backend/app/templates/browser/saved_queries_explorer.html` | 0 | ✅ pass | <1s |
| 7 | `grep -q 'saved-queries/explorer' backend/app/views/router.py` | 0 | ✅ pass | <1s |
| 8 | `grep -q 'saved-queries/explorer' backend/app/templates/browser/workspace.html` | 0 | ✅ pass | <1s |
| 9 | `grep -q 'logger.exception' backend/app/views/router.py` | 0 | ✅ pass | <1s |
| 10 | `python3 -m pytest backend/tests/test_saved_queries_explorer.py -v` | — | ⏳ deferred (T02) | — |

## Diagnostics

- **Endpoint errors:** Check server logs for `saved_queries_explorer: failed to load queries` — the endpoint catches exceptions, logs the traceback, and returns an empty list.
- **Drag payload:** During a drag operation from the QUERIES section, inspect `window.__canvasDragPayload` in the browser console to verify the payload shape.
- **htmx refresh:** Fire `htmx.trigger(document.body, 'queriesRefreshed')` in the console to force a re-fetch of the queries tree.

## Deviations

- **URL path adjusted:** The plan specified `/browser/saved-queries/explorer` but the views router has prefix `/browser/views`, so the actual URL is `/browser/views/saved-queries/explorer`. The htmx attribute in workspace.html was updated accordingly. This is a minor path adaptation, not an architectural change.

## Known Issues

None.

## Files Created/Modified

- `backend/app/templates/browser/workspace.html` — Added `section-queries` explorer section between VIEWS and DASHBOARDS
- `backend/app/templates/browser/saved_queries_explorer.html` — New partial template for rendering saved query tree entries
- `backend/app/views/router.py` — Added `GET /saved-queries/explorer` endpoint using QueryService.list_all_queries()
- `.gsd/milestones/M031/slices/S03/S03-PLAN.md` — Added Observability/Diagnostics section, diagnostic verification check, and URL correction
- `.gsd/milestones/M031/slices/S03/tasks/T01-PLAN.md` — Added Observability Impact section
