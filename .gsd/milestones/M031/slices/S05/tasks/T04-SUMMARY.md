---
id: T04
parent: S05
milestone: M031
provides:
  - Graph view fills available panel height via flex layout (no fragile calc)
  - Kanban view fills available panel height via flex layout
  - Graph popover renders above all chrome using fixed positioning on document.body
  - Popover cleanup on graph destroy prevents orphaned DOM nodes
key_files:
  - frontend/static/css/views.css
  - frontend/static/js/graph.js
  - backend/app/templates/browser/graph_view.html
  - backend/app/templates/browser/kanban_view.html
key_decisions:
  - Appended graph popovers to document.body with position:fixed instead of elevating z-index within the container — this fully escapes the stacking context created by graph-container's position:relative
  - Used a shared .view-flex-column wrapper class for both graph and kanban views rather than per-view flex rules — keeps CSS DRY for any future view that needs full-height layout
patterns_established:
  - Views that need to fill panel height should wrap content in .view-flex-column and use flex:1;min-height:0 on the expandable child — the parent .group-editor-area provides height:100%
  - Popovers that must render above dockview chrome should be appended to document.body with position:fixed and z-index:9999, using getBoundingClientRect() for viewport-relative positioning
observability_surfaces:
  - Graph/kanban layout is CSS-only — inspect computed styles on .graph-container (flex:1) and .kanban-board (flex:1;min-height:0)
  - Popover attachment can be verified by checking document.body.querySelectorAll('.graph-popover').length — should be 2 when a graph is active (node + edge popovers)
  - Popover cleanup can be verified by navigating away from graph view and checking the same query returns 0
duration: 12m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T04: Full-height views and graph popover z-index fix

**Fix graph and kanban views to fill panel height via flex layout, and move graph popovers to document.body with fixed positioning so they render above all dockview chrome**

## What Happened

Two layout fixes implemented across four files:

1. **Full-height graph and kanban views (VIEW-13):** Both graph_view.html and kanban_view.html templates are now wrapped in a `.view-flex-column` div that provides `display:flex; flex-direction:column; height:100%`. The `.graph-container` was changed from `height: calc(100% - 90px)` to `flex: 1; min-height: 0`, allowing it to fill whatever height remains after toolbars. The `.kanban-board` was changed from `height: 100%` to `flex: 1; min-height: 0; overflow-x: auto`, same pattern. Table and cards views were verified to not need changes — they use natural vertical scrolling handled by the `.group-editor-area` container.

2. **Graph popover z-index fix (VIEW-14):** Both node and edge popovers are now appended to `document.body` instead of inside `.graph-container`. CSS was changed from `position: absolute; z-index: 200` to `position: fixed; z-index: 9999`. Positioning math was updated to use `container.getBoundingClientRect()` to convert from container-relative Cytoscape coordinates to viewport-relative fixed coordinates. Overflow checks now compare against `window.innerWidth`/`window.innerHeight` instead of the container bounds. Cleanup was added to the existing `registerCleanup` handler to remove both popovers from body when the graph is destroyed.

## Verification

All 6 task-level checks and all 9 slice-level checks pass. Table and cards view templates were manually inspected and confirmed to not need changes.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -q "view-flex-column" frontend/static/css/views.css` | 0 | ✅ pass | <1s |
| 2 | `grep -q "view-flex-column" backend/app/templates/browser/graph_view.html` | 0 | ✅ pass | <1s |
| 3 | `grep -q "view-flex-column" backend/app/templates/browser/kanban_view.html` | 0 | ✅ pass | <1s |
| 4 | `! grep -q "calc(100% - 90px)" frontend/static/css/views.css` | 0 | ✅ pass | <1s |
| 5 | `grep -q "document\.body" frontend/static/js/graph.js` | 0 | ✅ pass | <1s |
| 6 | `grep -q "z-index.*9999" frontend/static/css/views.css` | 0 | ✅ pass | <1s |
| 7 | `python3 -c "import ast; ast.parse(open('backend/app/sparql/router.py').read())"` (slice) | 0 | ✅ pass | <1s |
| 8 | `python3 -c "import ast; ast.parse(open('backend/app/ontology/service.py').read())"` (slice) | 0 | ✅ pass | <1s |
| 9 | `python3 -c "import ast; ast.parse(open('backend/app/admin/router.py').read())"` (slice) | 0 | ✅ pass | <1s |
| 10 | `grep -q "sparql-vocab-pill" frontend/static/css/workspace.css` (slice) | 0 | ✅ pass | <1s |
| 11 | `grep -q "sparql-graph-tab\|sparql-result-tabs" frontend/static/js/sparql-console.js` (slice) | 0 | ✅ pass | <1s |
| 12 | `grep -q "propDescription\|title=.*description" backend/app/templates/browser/ontology/tbox_detail.html` (slice) | 0 | ✅ pass | <1s |
| 13 | `grep -q "calc(100vh\|flex.*1" frontend/static/css/style.css` (slice) | 0 | ✅ pass | <1s |
| 14 | `grep -q "z-index.*[3-9][0-9][0-9]" frontend/static/css/views.css` (slice) | 0 | ✅ pass | <1s |

## Diagnostics

- **Graph/kanban layout:** Inspect computed styles on `.graph-container` — should show `flex: 1` instead of old `height: calc(100% - 90px)`. Similarly `.kanban-board` should show `flex: 1; min-height: 0`.
- **Popover attachment:** In browser console, `document.body.querySelectorAll('.graph-popover').length` returns 2 when a graph view is active (node + edge popovers). Returns 0 after navigating away (cleanup fires).
- **Popover visibility:** Hover a node near the top of the graph — the popover should render above toolbars and dockview tabs without clipping. Inspect the popover element's computed `position: fixed` and `z-index: 9999`.

## Deviations

None. Implementation followed the task plan exactly.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/css/views.css` — Added `.view-flex-column` flex column wrapper; changed `.graph-container` from `height: calc(100% - 90px)` to `flex: 1; min-height: 0`; changed `.graph-popover` from `position: absolute; z-index: 200` to `position: fixed; z-index: 9999`; changed `.kanban-board` from `height: 100%` to `flex: 1; min-height: 0`
- `frontend/static/js/graph.js` — Moved popover/edgePopover creation from `container.appendChild` to `document.body.appendChild`; updated positioning to use viewport-relative coordinates via `getBoundingClientRect()`; added popover removal in `registerCleanup` handler
- `backend/app/templates/browser/graph_view.html` — Wrapped all template content in `<div class="view-flex-column">`
- `backend/app/templates/browser/kanban_view.html` — Wrapped all template content (excluding trailing script) in `<div class="view-flex-column">`
