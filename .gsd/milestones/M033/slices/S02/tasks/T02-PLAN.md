---
estimated_steps: 5
estimated_files: 4
skills_used: []
---

# T02: Implement isometric 2.5D CSS transform layout with coordinate correction

**Slice:** S02 — Isometric 2.5D Graph Layout & Icon Toggle
**Milestone:** M033

## Description

Add an "Isometric 2.5D" layout option to the graph view that applies a CSS 3D perspective transform to a wrapper div around the Cytoscape container, creating a tilted 2.5D visual effect. The core challenge is that CSS 3D transforms break Cytoscape's event coordinate system — `getBoundingClientRect()` returns the *transformed* bounding box while `clientWidth`/`clientHeight` remain untransformed, causing click events to land on wrong nodes.

The fix: monkey-patch `cy.renderer().findContainerClientCoords` to return coordinates computed from the untransformed container dimensions and the wrapper's center point. Popover positioning must also be corrected by forward-transforming Cytoscape's rendered positions through the wrapper's CSS matrix.

**Important architectural detail:** The wrapper div is added in the template around the existing `#cy-container`. When isometric is NOT active, the wrapper has no transform and is invisible to layout (just a pass-through div). When isometric IS active, CSS applies `perspective(800px) rotateX(55deg) rotateZ(-45deg)` to the inner container via a `.isometric-active` class.

There are TWO `available_layouts` definitions in `backend/app/views/router.py` — one at line ~431 (generic graph view) and one at line ~971 (model-spec graph view). Both must include the isometric entry.

## Steps

1. **Add wrapper div in `graph_view.html`** — Wrap the existing `<div id="cy-container" class="graph-container" ...>` inside `<div class="graph-isometric-wrapper">`. The wrapper is a simple pass-through container — no transform by default. Template becomes:
   ```html
   <div class="graph-isometric-wrapper" id="cy-wrapper">
     <div id="cy-container" class="graph-container" data-testid="graph-view"></div>
   </div>
   ```

2. **Add `_applyIsometricTransform()` to `graph.js`** — Function takes `(cy, container)`. Gets wrapper via `container.parentElement` (the `.graph-isometric-wrapper`). Steps: (a) Run fcose layout first to position nodes, waiting for `layoutstop` event. (b) Add `.isometric-active` class to wrapper, which triggers the CSS 3D transform. (c) Store the original `findContainerClientCoords` method: `var origFindCoords = cy.renderer().findContainerClientCoords`. (d) Monkey-patch `cy.renderer().findContainerClientCoords`: compute wrapper center from `wrapper.getBoundingClientRect()`, return `[wrapperCenter.x - container.clientWidth/2, wrapperCenter.y - container.clientHeight/2, container.clientWidth, container.clientHeight, 1]` (the 5-element array that Cytoscape expects). (e) Call `cy.invalidateSize()`. (f) Store `origFindCoords` on the cy instance for later restore: `cy._origFindCoords = origFindCoords`. (g) Set a flag `cy._isometricActive = true`.

3. **Add `_removeIsometricTransform()` to `graph.js`** — Function takes `(cy, container)`. Steps: (a) Get wrapper. (b) Remove `.isometric-active` class from wrapper. (c) Restore original: `cy.renderer().findContainerClientCoords = cy._origFindCoords`. (d) Call `cy.invalidateSize()`. (e) Clear flag: `cy._isometricActive = false`.

4. **Wire isometric into layout switching** — In `changeLayout()`: before running any layout, check if isometric is currently active (`cy._isometricActive`) and remove it via `_removeIsometricTransform()`. If the new layout is `'isometric'`, call `_applyIsometricTransform()` instead of `cy.layout(config).run()`. Update popover positioning: in `_showNodePopover` and `_showEdgePopover`, after computing `left`/`top`, check `cy._isometricActive`. If active, get wrapper's computed transform via `new DOMMatrix(getComputedStyle(wrapper).transform)`, transform the rendered position point through it, and use the transformed coordinates plus wrapper center offset for popover placement. Add a `ResizeObserver` or hook into the existing panel resize path to call `cy.invalidateSize()` when the wrapper resizes during isometric mode.

5. **Backend and CSS** — Add `{"name": "isometric", "label": "Isometric 2.5D"}` to BOTH `available_layouts` lists in `backend/app/views/router.py` (generic graph view at ~line 431, and model-spec view built_in_layouts at ~line 971). CSS in `views.css`: `.graph-isometric-wrapper` with `position: relative; width: 100%; flex: 1; min-height: 0; transform-style: preserve-3d;`. `.graph-isometric-wrapper.isometric-active` with `perspective: 800px;`. `.graph-isometric-wrapper.isometric-active .graph-container` with `transform: rotateX(55deg) rotateZ(-45deg); transition: transform 0.6s ease;`. The grid background on `.graph-container` naturally enhances the isometric visual.

## Must-Haves

- [ ] `.graph-isometric-wrapper` div wraps `#cy-container` in template
- [ ] Selecting "Isometric 2.5D" in layout picker applies CSS 3D perspective transform
- [ ] `findContainerClientCoords` is monkey-patched to return untransformed coordinates
- [ ] Node click (tap) events fire on the correct node under transform
- [ ] Node/edge popovers position correctly near the clicked element under transform
- [ ] Switching from isometric to another layout cleanly removes the transform
- [ ] Both `available_layouts` lists in router.py include the isometric entry

## Verification

- `rg -c '_applyIsometricTransform\|_removeIsometricTransform' frontend/static/js/graph.js` returns ≥ 2
- `rg -c 'isometric-active' frontend/static/css/views.css` returns ≥ 2
- `rg -c 'graph-isometric-wrapper' backend/app/templates/browser/graph_view.html` returns ≥ 1
- `rg 'isometric' backend/app/views/router.py` returns 2 matches (both layout lists)

## Inputs

- `frontend/static/js/graph.js` — existing `changeLayout()`, `LAYOUT_REGISTRY`, `_showNodePopover()`, `_showEdgePopover()`, `initGraph()` (T01 will have modified `buildSemanticStyle` but T02's changes are orthogonal)
- `frontend/static/css/views.css` — existing `.graph-container`, `.view-flex-column` styles
- `backend/app/templates/browser/graph_view.html` — existing template (T01 will have added icon toggle button)
- `backend/app/views/router.py` — the two `available_layouts` definitions at ~line 431 and ~line 971

## Expected Output

- `frontend/static/js/graph.js` — modified with `_applyIsometricTransform()`, `_removeIsometricTransform()`, isometric entry in LAYOUT_REGISTRY conceptually, modified `changeLayout()`, modified popover functions
- `frontend/static/css/views.css` — modified with `.graph-isometric-wrapper` and `.isometric-active` styles
- `backend/app/templates/browser/graph_view.html` — modified with wrapper div around cy-container
- `backend/app/views/router.py` — modified with isometric entry in both available_layouts lists
