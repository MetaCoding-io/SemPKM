---
id: T02
parent: S02
milestone: M033
provides:
  - Isometric 2.5D layout option in graph view layout picker
  - CSS 3D perspective transform with coordinate-corrected click targeting
  - Popover positioning correction under isometric transform via DOMMatrix forward-transform
key_files:
  - frontend/static/js/graph.js
  - frontend/static/css/views.css
  - backend/app/templates/browser/graph_view.html
  - backend/app/views/router.py
key_decisions:
  - Used wrapper div + .isometric-active class toggle rather than inline style manipulation for cleaner CSS transition control
  - Monkey-patched cy.renderer().findContainerClientCoords with wrapper-center-based untransformed coordinates for click targeting
  - Used DOMMatrix.transformPoint() to forward-transform Cytoscape rendered positions through the CSS 3D matrix for popover placement
  - Bumped template separator index from 3 to 4 to account for 4th built-in layout
patterns_established:
  - _popoverViewportCoords(cy, container, pos) as reusable coordinate transformer that handles both normal and isometric modes
  - _applyIsometricTransform/_removeIsometricTransform as paired activation/deactivation with flag + method restore
observability_surfaces:
  - "console.log '[graph] Isometric 2.5D transform applied' on activation"
  - "console.log '[graph] Isometric 2.5D transform removed' on deactivation"
  - "console.warn '[graph] Isometric wrapper #cy-wrapper not found' when wrapper div is missing"
  - "window._sempkmGraph._isometricActive boolean flag inspectable in DevTools"
duration: 18m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T02: Implement isometric 2.5D CSS transform layout with coordinate correction

**Added isometric 2.5D layout with CSS 3D perspective transform, monkey-patched Cytoscape coordinate system for correct click targeting, and DOMMatrix-based popover positioning correction.**

## What Happened

Implemented the isometric layout in four files:

1. **graph_view.html** — Wrapped `#cy-container` inside a new `<div class="graph-isometric-wrapper" id="cy-wrapper">` pass-through div. Bumped the model-layout separator threshold from `loop.index0 == 3` to `loop.index0 == 4` since isometric is the 4th built-in layout.

2. **graph.js** — Added three new functions:
   - `_applyIsometricTransform(cy, container)`: Runs fcose layout first (via `layoutstop` event listener), then applies `.isometric-active` class to the wrapper. Monkey-patches `cy.renderer().findContainerClientCoords` to return coordinates based on the wrapper's visual center and the container's untransformed `clientWidth`/`clientHeight`, fixing the coordinate mismatch that CSS 3D transforms cause.
   - `_removeIsometricTransform(cy, container)`: Removes the class, restores the original `findContainerClientCoords`, and clears the `_isometricActive` flag.
   - `_popoverViewportCoords(cy, container, renderedPos)`: When isometric is active, forward-transforms Cytoscape rendered positions through the container's CSS matrix via `DOMMatrix.transformPoint()` and maps to viewport coordinates using the wrapper center. Falls back to standard `getBoundingClientRect()` positioning when isometric is inactive.
   
   Modified `changeLayout()` to detect and remove isometric transform before switching layouts, and to call `_applyIsometricTransform()` instead of running a standard layout when isometric is selected.
   
   Updated both `_showNodePopover()` and `_showEdgePopover()` to use `_popoverViewportCoords()` for all positioning.

3. **views.css** — Added `.graph-isometric-wrapper` (pass-through flex container with `transform-style: preserve-3d`), `.isometric-active` (with `perspective: 800px`), `.isometric-active .graph-container` (with `rotateX(55deg) rotateZ(-45deg)` + 0.6s transition), and `:not(.isometric-active) .graph-container` (transition: none for instant reset).

4. **router.py** — Added `{"name": "isometric", "label": "Isometric 2.5D"}` to both `available_layouts` lists (generic graph view at line ~432 and model-spec built_in_layouts at line ~975).

## Verification

All five task-level checks passed:

- `_applyIsometricTransform` and `_removeIsometricTransform` present in graph.js (4 occurrences)
- `isometric-active` present in views.css (3 occurrences)
- `graph-isometric-wrapper` present in graph_view.html (1 occurrence)
- `isometric` present in both router.py layout lists (2 matches)
- JavaScript syntax validation passed (`node -c`)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg -c '_applyIsometricTransform\|_removeIsometricTransform' frontend/static/js/graph.js` | 0 | ✅ pass (4) | <1s |
| 2 | `rg -c 'isometric-active' frontend/static/css/views.css` | 0 | ✅ pass (3) | <1s |
| 3 | `rg -c 'graph-isometric-wrapper' backend/app/templates/browser/graph_view.html` | 0 | ✅ pass (1) | <1s |
| 4 | `rg 'isometric' backend/app/views/router.py` | 0 | ✅ pass (2 lines) | <1s |
| 5 | `node -c frontend/static/js/graph.js` | 0 | ✅ pass | <1s |

## Diagnostics

- **Isometric active state:** `window._sempkmGraph._isometricActive` returns `true` when isometric is on
- **Wrapper class inspection:** `document.getElementById('cy-wrapper').classList.contains('isometric-active')` 
- **Coordinate patch verification:** `typeof window._sempkmGraph._origFindCoords === 'function'` is `true` when patched
- **Console signals:** `[graph] Isometric 2.5D transform applied/removed` logged on layout switches
- **Failure path:** If `#cy-wrapper` is missing, console.warn fires and graph stays in previous layout

## Deviations

- Bumped template model-layout separator from `loop.index0 == 3` to `loop.index0 == 4` — not in plan but necessary because isometric is the 4th built-in layout and the old threshold would incorrectly show "Model Layouts" before it.
- Added `:not(.isometric-active) .graph-container { transition: none }` rule — ensures instant reset when switching away from isometric instead of a 0.6s reverse animation.
- Used `DOMMatrix.transformPoint()` for popover coordinate transformation instead of manually multiplying through the matrix — cleaner API, same result.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/graph.js` — Added `_applyIsometricTransform()`, `_removeIsometricTransform()`, `_popoverViewportCoords()`; modified `changeLayout()` for isometric handling; updated `_showNodePopover()` and `_showEdgePopover()` to use coordinate transformer
- `frontend/static/css/views.css` — Added `.graph-isometric-wrapper`, `.isometric-active`, `.isometric-active .graph-container`, and `:not(.isometric-active)` transition reset rules; added `height: 100%` to `.graph-container`
- `backend/app/templates/browser/graph_view.html` — Added `#cy-wrapper` div around `#cy-container`; bumped model-layout separator index
- `backend/app/views/router.py` — Added isometric entry to both `available_layouts` lists
- `.gsd/milestones/M033/slices/S02/S02-PLAN.md` — Added failure-path verification step
- `.gsd/milestones/M033/slices/S02/tasks/T02-PLAN.md` — Added Observability Impact section
