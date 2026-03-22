# S02 Research: Isometric 2.5D Graph Layout & Icon Toggle

## Summary

This slice adds two features to the existing Cytoscape.js graph view: (1) an "Isometric" layout option that applies a CSS 3D perspective transform to simulate a 2.5D tilted view, and (2) a toolbar toggle button that switches graph nodes between shape-only display and Lucide SVG icon-on-node display. The isometric layout involves novel CSS 3D transform + Cytoscape coordinate correction. The icon toggle is straightforward Cytoscape `background-image` styling. Both features are scoped entirely to `frontend/static/js/graph.js`, `frontend/static/css/views.css`, and `backend/app/templates/browser/graph_view.html`.

## Requirements

| ID | Requirement | Status | Notes |
|----|------------|--------|-------|
| ISO-01 | Graph view has a selectable "Isometric" layout that applies CSS 3D perspective with correct click/drag/popover interaction | Active | Highest risk — coordinate correction needed |
| ISO-02 | Isometric layout is visually distinct (tilted plane, perspective depth cue) | Active | CSS `perspective()` + `rotateX()` |
| ICON-01 | Graph view toolbar has a toggle button switching nodes between shape-only and Lucide SVG icon display | Active | `background-image` with SVG data URIs |

## Recommendation

**Approach:** Apply the CSS 3D transform to a **wrapper div** around the Cytoscape container (not the container itself). Monkey-patch Cytoscape's `findContainerClientCoords()` to use `DOMMatrix.inverse()` for coordinate correction when the isometric transform is active. This keeps Cytoscape's event system working while the wrapper handles the visual tilt.

**Why a wrapper, not the container:** Cytoscape's canvas renderer size is coupled to the container's `clientWidth`/`clientHeight`. Applying a 3D transform directly changes `getBoundingClientRect()` but not `clientWidth`, creating a scale mismatch inside `findContainerClientCoords()`. A wrapper avoids this — the container's logical dimensions stay correct.

**Icon toggle:** Use Cytoscape's `background-image` property with SVG data URIs from Lucide's global `lucide.icons` object. Toggle by applying/removing a style override to all nodes via `cy.style().fromJson()`. Persist preference in `localStorage` key `sempkm_graph_icon_mode`.

**Build order:** Icon toggle first (low risk, validates Lucide SVG→Cytoscape pipeline), then isometric layout (higher risk, can fail fast).

## Implementation Landscape

### Files to Modify

| File | Change |
|------|--------|
| `frontend/static/js/graph.js` | Add `_applyIsometricTransform()`, `_removeIsometricTransform()`, `_setIconMode()`, icon toggle handler, isometric layout entry in `LAYOUT_REGISTRY` |
| `frontend/static/css/views.css` | Add `.graph-isometric-wrapper` styles (perspective, rotateX, transform-style), icon toggle button styling |
| `backend/app/templates/browser/graph_view.html` | Add icon toggle button to `.graph-toolbar`, add "Isometric" to available_layouts (if hardcoded in template) |
| `backend/app/views/router.py` (lines 431-436) | Add `{"name": "isometric", "label": "Isometric 2.5D"}` to the `available_layouts` list |

### Files to Read (reference only)

| File | Why |
|------|-----|
| `e2e/tests/02-views/graph-view.spec.ts` | Existing E2E patterns for graph view testing |
| `e2e/helpers/selectors.ts` | Add new selectors for icon toggle button |

### No Backend Logic Changes

Both features are purely frontend. No SPARQL changes, no new endpoints, no model changes.

## Technical Analysis

### 1. Isometric CSS 3D Transform

**Transform chain:** `perspective(800px) rotateX(55deg) rotateZ(-45deg)` on the wrapper div. The `perspective` provides depth scaling. `rotateX(55deg)` tilts the plane toward the viewer (true isometric would be ~54.74°, rounding to 55°). `rotateZ(-45deg)` rotates the view diamond-wise.

**Container architecture:**
```
<div class="graph-isometric-wrapper" style="perspective: 800px">  <!-- NEW wrapper -->
  <div id="cy-container" class="graph-container">                 <!-- existing -->
    <canvas>...</canvas>                                           <!-- Cytoscape renders here -->
  </div>
</div>
```

When isometric is not active, the wrapper has `transform: none` and is invisible to layout.

**Coordinate correction approach:**

Cytoscape's `findContainerClientCoords()` (v3.33.1) does:
```js
var rect = container.getBoundingClientRect();  // affected by 3D transform
var scale = rect.width / (clientWidth + borderHor);  // wrong scale
var left = rect.left + padding.left + border.left;   // wrong position
```

Fix: Override the renderer's `findContainerClientCoords` method when isometric is active. Use `DOMMatrix` to compute the untransformed container bounds:

```js
function _getUntransformedRect(container, wrapperEl) {
    // Get the wrapper's computed transform matrix
    var style = getComputedStyle(wrapperEl);
    var matrixStr = style.transform;
    if (!matrixStr || matrixStr === 'none') {
        return container.getBoundingClientRect();
    }
    var matrix = new DOMMatrix(matrixStr);
    var inverse = matrix.inverse();

    // Get the transformed rect
    var rect = container.getBoundingClientRect();

    // Apply inverse to the rect corners to find untransformed bounds
    // For the offset calculation, we need the top-left corner in viewport coords
    // corrected for the transform
    var wrapperRect = wrapperEl.getBoundingClientRect();
    var wrapperCenter = {
        x: wrapperRect.left + wrapperRect.width / 2,
        y: wrapperRect.top + wrapperRect.height / 2
    };

    // The transform origin is center of wrapper
    // Untransformed left/top = center - (clientWidth/2), center - (clientHeight/2)
    return {
        left: wrapperCenter.x - container.clientWidth / 2,
        top: wrapperCenter.y - container.clientHeight / 2,
        width: container.clientWidth,
        height: container.clientHeight
    };
}
```

**Alternative simpler approach:** Instead of monkey-patching `findContainerClientCoords`, cache the untransformed `getBoundingClientRect()` values *before* applying the CSS transform, and use `cy.invalidateSize()` sparingly. The problem is this breaks on window resize, scroll, or panel resize.

**Best approach: transparent overlay with event relay.** Place a `pointer-events: auto` overlay div that sits on top of the transformed wrapper. It receives mouse events in un-transformed viewport space. Intercept `mousedown`, `mousemove`, `mouseup`, `wheel`, `click`, `dblclick`, convert coordinates to where they would land on the untransformed container, and dispatch new events to the container. This completely isolates Cytoscape from the CSS transform.

**Recommended approach (simplest reliable):** Monkey-patch `cy.renderer().findContainerClientCoords` to return `[left, top, width, height, 1]` computed from the known untransformed container dimensions. When isometric mode is activated, capture the container's true position and store it. On window resize or panel resize, recalculate. This avoids the overlay complexity and gives Cytoscape correct coordinates directly.

### 2. Popover Positioning Under Isometric Transform

The existing popover code (lines 407-421 in graph.js) uses:
```js
var pos = evt.renderedPosition || nodeEl.renderedPosition();
var cRect = container.getBoundingClientRect();
var left = cRect.left + pos.x + 16;
```

Under the isometric transform, `cRect` is the *transformed* bounding box, and `pos` is Cytoscape's rendered position (which is correct relative to the untransformed canvas). The popover will appear at the wrong location.

**Fix:** When isometric mode is active, convert the popover position through the forward CSS transform matrix:
```js
var matrix = new DOMMatrix(getComputedStyle(wrapperEl).transform);
var point = matrix.transformPoint(new DOMPoint(pos.x - cw/2, pos.y - ch/2, 0));
// Add wrapper center offset
var left = wrapperCenter.x + point.x + 16;
var top = wrapperCenter.y + point.y - 12;
```

### 3. Lucide SVG → Cytoscape `background-image`

The Lucide UMD bundle (v0.575.0) exposes a global `lucide` object. Key APIs:
- `lucide.createElement(IconDefinition, attrs)` → returns an HTMLElement (SVG)
- Individual icon definitions are accessible as `lucide.FileText`, `lucide.Lightbulb`, etc.

For Cytoscape `background-image`, we need SVG data URIs:
```js
function _lucideSvgDataUri(iconName) {
    // Lucide UMD exposes icons by PascalCase name
    // Convert kebab-case to PascalCase: 'file-text' → 'FileText'
    var pascalName = iconName.replace(/(^|-)(\w)/g, function(_, __, c) { return c.toUpperCase(); });
    var iconDef = lucide[pascalName];
    if (!iconDef) return null;

    var el = lucide.createElement(iconDef, {
        width: 20, height: 20,
        stroke: 'currentColor',
        'stroke-width': 1.5
    });
    var svgStr = el.outerHTML;
    return 'data:image/svg+xml;utf8,' + encodeURIComponent(svgStr);
}
```

**Performance note:** Cytoscape docs warn that `background-image` is expensive. Memoize the SVG data URI generation per icon name.

**Icon mapping:** The existing `iconToShape` map (line 141 in graph.js) maps icon names to shapes:
```js
var iconToShape = {
    'file-text': 'rectangle',
    'lightbulb': 'diamond',
    'book-open': 'round-rectangle',
    'tag': 'ellipse',
    'folder-kanban': 'round-rectangle',
    'user': 'ellipse',
};
```

The icon toggle will use this same map as a data source — for each type with an icon entry in `window._sempkmIcons.graph`, generate the SVG data URI and apply it as `background-image`.

**Style application:** Toggle between two styles:
- **Shape mode (default):** Current behavior — `shape` varies by type, no `background-image`
- **Icon mode:** All nodes get `shape: 'ellipse'` (uniform), plus `background-image: <svg-data-uri>`, `background-fit: 'contain'`, `background-opacity: 1`

Toggle via `cy.style().fromJson(buildSemanticStyle(colors, isDark, iconMode)).update()`.

### 4. Layout Selector Integration

The backend (router.py line 431-436) hardcodes three layouts:
```python
"available_layouts": [
    {"name": "fcose", "label": "Force-Directed"},
    {"name": "dagre", "label": "Hierarchical"},
    {"name": "concentric", "label": "Radial"},
],
```

Add `{"name": "isometric", "label": "Isometric 2.5D"}` to this list. On the frontend, `changeLayout('isometric')` will:
1. Run the fcose layout first (to position nodes)
2. Apply the CSS 3D transform to the wrapper
3. Set up coordinate correction

Switching away from isometric will remove the transform and coordinate correction.

The isometric "layout" is really a *view transform*, not a node-positioning algorithm. It takes whatever layout is currently applied and adds a 3D perspective tilt. But from the user's perspective, it appears in the layout picker dropdown, which is the simplest UI.

**Alternative:** Separate the isometric toggle from the layout picker — have a dedicated "3D" toggle button. This allows isometric + any layout combination. Cleaner conceptually but more UI surface. The roadmap boundary map says "isometric entry in LAYOUT_REGISTRY", so treat it as a layout.

### 5. `DOMMatrix` Browser Support

`DOMMatrix` is supported in Chrome 61+, Firefox 33+, Safari 11+, Edge 79+. All modern browsers used for this app. No polyfill needed.

### 6. Cytoscape `containerBB` Cache

`findContainerClientCoords()` caches its result in `this.containerBB`. The cache is invalidated by `invalidateContainerClientCoordsCache()` which is called on scroll, resize, and `cy.invalidateSize()`. When switching to/from isometric mode, call `cy.invalidateSize()` to flush this cache and force recalculation with the patched method.

## Pitfalls & Risks

### P1: Canvas Rendering Quality Under CSS 3D
CSS 3D transforms are applied by the GPU compositor *after* the canvas has been rasterized. This means the canvas content will be bilinearly filtered when tilted, potentially appearing slightly blurry. Mitigated by using `cy.renderer().pixelRatio` to render at higher resolution, but may not be worth the performance cost. Accept slight blur as a visual characteristic of the isometric view.

### P2: Cytoscape's `findContainerClientCoords` Cache
The method caches results in `this.containerBB`. When we monkey-patch it, we must ensure the cache invalidation path (`invalidateContainerClientCoordsCache`) still works correctly. Best: override the method rather than modifying the cache.

### P3: Popover Z-Index Under 3D Transform
CSS 3D transforms create a new stacking context. Popovers are already appended to `document.body` (D293 pattern), so they're outside the transform's stacking context. No issue expected.

### P4: Panel Resize Invalidation
When a dockview panel is resized, the container dimensions change. The isometric transform correction must recalculate. Cytoscape already calls `cy.resize()` on container resize observation. The monkey-patched `findContainerClientCoords` will pick up the new dimensions.

### P5: Lucide Icon Discovery at Runtime
`window._sempkmIcons` (referenced in graph.js line 140) is populated by some external mechanism (likely `/browser/icons` endpoint). If it's empty or undefined, the icon toggle silently falls back to shape-only mode. The toggle button should still appear but show a tooltip "No icons configured for current types" if no icons are available.

### P6: `lucide.createElement` Returns HTMLElement, Not String
Cytoscape needs a string for `background-image` data URI. Use `el.outerHTML` to serialize. Must include the XML namespace (`xmlns="http://www.w3.org/2000/svg"`) — Lucide's `createElement` should include it, but verify. Without xmlns, the data URI won't render.

### P7: Isometric Zoom/Pan Behavior
Cytoscape's zoom (mousewheel) and pan (drag) still operate in the untransformed canvas space. Under the 3D tilt, zooming looks correct (canvas zooms, then the tilt is applied by CSS). But panning direction may feel "off" because the visual axes are rotated. User drags "right" but the graph moves along the rotated axis. This is inherent to CSS post-compositing transforms and acceptable for v1. Could be improved later by rotating the pan vector.

## Task Decomposition Guidance

### T01: Lucide SVG Icon Toggle (~2h est)
- Add `_lucideSvgDataUri(iconName)` memoized helper to graph.js
- Add `iconMode` parameter to `buildSemanticStyle()` — when true, add `background-image` styles per type
- Add icon toggle button to `.graph-toolbar` in `graph_view.html`
- Add `_setIconMode(cy, mode)` that toggles localStorage and rebuilds stylesheet
- Add CSS for the toggle button in views.css
- Verify: icon toggle button appears, clicking switches between shapes and SVG icons on nodes

### T02: Isometric 2.5D Layout (~3h est)
- Add `.graph-isometric-wrapper` div around `#cy-container` in template
- Add `_applyIsometricTransform(cy, container)` — applies CSS 3D transform to wrapper, patches `findContainerClientCoords`, fixes popover positioning
- Add `_removeIsometricTransform(cy, container)` — removes transform, restores original methods
- Wire `changeLayout('isometric')` to run fcose first, then apply transform
- Wire layout switch away from isometric to call remove
- Add `{"name": "isometric", "label": "Isometric 2.5D"}` to backend `available_layouts`
- CSS: `.graph-isometric-wrapper` with `perspective`, `transform-style: preserve-3d`, transition

### T03: Verification & Edge Cases (~1h est)
- Test isometric mode: click node (tap event fires), double-click (expand works), hover (popover positions correctly), layout switch (transform applies/removes cleanly)
- Test icon toggle: shapes visible in shape mode, SVGs visible in icon mode, localStorage persists across page reload
- Test isometric + icon toggle combined
- E2E: Add test for layout picker having "Isometric 2.5D" option, icon toggle button presence

## Don't Hand-Roll

| Need | Existing solution |
|------|-------------------|
| SVG icon generation | `lucide.createElement()` — global Lucide UMD API |
| 3D matrix math | `DOMMatrix` — native browser API, inverse(), transformPoint() |
| Node positioning | Cytoscape's existing layout algorithms (fcose, dagre, concentric) |
| Popover positioning | Existing `_showNodePopover()` / `_showEdgePopover()` — just needs coordinate adjustment |

## Sources

- Cytoscape.js v3.33.1 source: `findContainerClientCoords()` uses `getBoundingClientRect()` + `clientWidth` for scale computation
- Cytoscape.js issue #1756: CSS transform on container causes coordinate mismatch (fixed for 2D in v3.2.0, 3D transforms still affected)
- MDN `DOMMatrix`: inverse(), transformPoint() — browser-native 4x4 matrix operations
- Lucide UMD: `lucide.createElement(IconDef, attrs)` returns SVG HTMLElement
- Cytoscape.js docs: `background-image` supports SVG data URIs via `encodeURIComponent()`
