---
id: S02
parent: M033
milestone: M033
provides:
  - Isometric 2.5D layout option in graph view with CSS 3D perspective transform
  - Monkey-patched Cytoscape coordinate system for correct click targeting under isometric transform
  - DOMMatrix-based popover positioning correction under transform
  - Lucide SVG icon toggle for graph nodes with localStorage persistence
  - Memoized Lucide-to-data-URI pipeline for node background images
  - 5 Playwright E2E tests for isometric layout and icon toggle
requires: []
affects: []
key_files:
  - frontend/static/js/graph.js
  - frontend/static/css/views.css
  - backend/app/templates/browser/graph_view.html
  - backend/app/views/router.py
  - e2e/tests/02-views/graph-isometric.spec.ts
key_decisions: []
patterns_established:
  - "Monkey-patch cy.renderer().findContainerClientCoords for CSS 3D coordinate correction"
  - "DOMMatrix forward-transform for popover positioning under CSS 3D perspective"
  - "Memoized _lucideSvgDataUri() for Lucide SVG → data URI conversion"
observability_surfaces:
  - "Console warning '[graph] Isometric wrapper #cy-wrapper not found' when wrapper div missing"
  - "localStorage key sempkm_graph_icon_mode persists icon toggle state"
drill_down_paths:
  - .gsd/milestones/M033/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M033/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M033/slices/S02/tasks/T03-SUMMARY.md
duration: 48m
verification_result: passed
completed_at: 2026-03-22
---

# S02: Isometric 2.5D Graph Layout & Icon Toggle

**Added isometric 2.5D perspective layout with coordinate-corrected interaction and Lucide SVG icon toggle to graph view — 5 E2E tests passing**

## What Happened

T01 added a Lucide SVG icon toggle to graph nodes: a memoized `_lucideSvgDataUri()` pipeline converts Lucide icon names to data URIs injected as Cytoscape node `background-image`. Toolbar toggle button with localStorage persistence (`sempkm_graph_icon_mode`). Theme-aware stroke colors.

T02 added the isometric 2.5D layout: CSS 3D perspective transform (`perspective(800px) rotateX(55deg) rotateZ(-45deg)`) on a `#cy-wrapper` div, monkey-patched Cytoscape coordinate system for correct click targeting, and DOMMatrix-based popover positioning correction. Added "Isometric 2.5D" to the layout picker in both frontend and backend.

T03 wrote 5 Playwright E2E tests covering layout selection, CSS 3D transform activation, icon toggle presence and node background-image injection, and combined isometric+icon interaction.

## Verification

5 E2E tests pass. Manual verification: isometric perspective renders, click targeting works under transform, popovers position correctly, icon toggle switches node display, preference persists across page loads.

## Deviations

None.

## Known Limitations

- Isometric layout uses a fixed perspective angle — not user-adjustable.
- Icon mode uses Lucide icons only; nodes without a matching icon get a fallback shape.

## Follow-ups

None.

## Files Created/Modified

- `frontend/static/js/graph.js` — Lucide SVG data URI pipeline, icon toggle, isometric layout, coordinate correction
- `frontend/static/css/views.css` — Isometric wrapper styles, icon toggle button styles
- `backend/app/templates/browser/graph_view.html` — cy-wrapper div, icon toggle toolbar button
- `backend/app/views/router.py` — Isometric layout in available_layouts
- `e2e/tests/02-views/graph-isometric.spec.ts` — 5 E2E tests
- `e2e/helpers/selectors.ts` — Icon toggle and isometric wrapper selectors

## Forward Intelligence

### What the next slice should know
- The isometric coordinate correction is a monkey-patch on `cy.renderer().findContainerClientCoords` — it must be reapplied after layout changes.

### What's fragile
- The DOMMatrix-based popover positioning assumes the transform is on `#cy-wrapper`. If the DOM hierarchy changes, popover positions will be wrong.

### Authoritative diagnostics
- Console warning `[graph] Isometric wrapper #cy-wrapper not found` indicates the template is missing the wrapper div.
- `localStorage.getItem('sempkm_graph_icon_mode')` shows current icon state.

### What assumptions changed
- None.
