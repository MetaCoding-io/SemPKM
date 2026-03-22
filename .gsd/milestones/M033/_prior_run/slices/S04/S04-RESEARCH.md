# S04 Research: Isometric 2.5D Graph View

**Slice:** Isometric 2.5D Graph View
**Calibration:** Targeted research — known technology (Cytoscape.js) with novel layout math, but well-documented extension API

---

## Summary

The isometric 2.5D graph view is a **custom Cytoscape.js layout extension** that stratifies nodes into horizontal z-layers based on RDF type, then projects them into 2D coordinates that create a visual depth effect. No external libraries are needed — this is ~200 lines of pure JS implementing the Cytoscape layout extension protocol. The backend needs a one-line addition to `available_layouts` in two places. The layer planes use Cytoscape's compound parent nodes with translucent background styling — no HTML overlays or canvas hacks.

---

## Recommendation

**Approach:** Register a custom discrete layout via `cytoscape('layout', 'isometric', IsometricLayout)` in a new `frontend/static/js/isometric-layout.js` file. The layout:

1. Groups nodes by `data('type')` into layers
2. Creates compound parent nodes per layer with translucent backgrounds (if not using compound nodes, draws layer planes via CSS overlay — but compound nodes are the Cytoscape-native approach)
3. Computes per-layer grid positions with isometric Y-offset per layer
4. Calls `eles.layoutPositions()` to set final positions

**Why not CSS 3D transforms:** The M033 roadmap explicitly rules this out — CSS 3D transforms on the Cytoscape container would break the coordinate system for mouse events, hit testing, and the canvas renderer. The correct approach is a 2D projection that *looks* isometric.

**Why compound parent nodes for layers:** Cytoscape natively supports compound nodes with background styling (`background-opacity`, `background-color`). Each layer becomes an invisible parent node whose children are the data nodes of that type. The parent auto-sizes to contain its children. This gives us translucent layer planes for free, with no z-index issues or DOM overlay positioning headaches.

---

## Implementation Landscape

### Files to Create

| File | Purpose |
|---|---|
| `frontend/static/js/isometric-layout.js` | Custom Cytoscape layout extension (~200 lines) |

### Files to Modify

| File | Change | Lines |
|---|---|---|
| `backend/app/templates/base.html` | Add `<script src="isometric-layout.js">` after graph.js (~line 149) | 1 |
| `backend/app/views/router.py` | Add `{"name": "isometric", "label": "Isometric"}` to `built_in_layouts` at lines ~431 and ~1093 | 2 |
| `frontend/static/js/graph.js` | Add `'isometric'` to `LAYOUT_REGISTRY` with empty config (line ~12). Handle compound node cleanup when switching away from isometric layout in `changeLayout()`. Add layer node styling in `buildSemanticStyle()`. | ~30 |
| `frontend/static/css/views.css` | Styles for isometric layer label badges (optional, compound parent labels handle this) | ~15 |

### No Backend SPARQL Changes

The node data already includes `type` (primary RDF type IRI) and `type_label` (resolved human-readable label) in the graph JSON response. The isometric layout stratifies by these existing fields — no new SPARQL queries needed.

---

## Cytoscape Custom Layout Extension Protocol

A Cytoscape layout extension requires:

```javascript
// Constructor — receives merged options
function IsometricLayout(options) {
  this.options = Object.assign({}, defaults, options);
}

// Run — compute positions and apply
IsometricLayout.prototype.run = function() {
  var options = this.options;
  var eles = options.eles;  // the collection to layout
  var nodes = eles.nodes().not(':parent');  // skip compound parents
  
  // Compute positions for each node
  eles.nodes().layoutPositions(this, options, function(node) {
    return { x: computedX, y: computedY };
  });
  
  return this;
};

// Stop — no-op for discrete layouts
IsometricLayout.prototype.stop = function() { return this; };

// Register
cytoscape('layout', 'isometric', IsometricLayout);
```

Key detail: `layoutPositions()` is the standard Cytoscape method that handles animation, fitting, padding, transform, and ready/stop callbacks. The layout only needs to provide the position function.

---

## Isometric Projection Math

The 2.5D illusion is created by:

1. **Layer separation:** Each type gets a Y-band. Layer 0 is at the bottom (highest Y), layer N at the top (lowest Y). The vertical spacing between layers creates the "stacking" visual.

2. **Isometric stagger:** Each layer is offset horizontally by a fraction of its layer index, creating the diagonal stacking effect:
   ```
   layer_offset_x = layer_index * STAGGER_X  // e.g., 40px per layer
   layer_offset_y = layer_index * LAYER_SPACING  // e.g., -200px per layer (upward)
   ```

3. **Within-layer arrangement:** Nodes within each layer use a grid layout (columns × rows) centered on the layer's anchor point:
   ```
   node_x = layer_offset_x + (col * NODE_SPACING_X) - (cols * NODE_SPACING_X / 2)
   node_y = layer_offset_y + (row * NODE_SPACING_Y) - (rows * NODE_SPACING_Y / 2)
   ```

4. **Constants (configurable via layout options):**
   - `layerSpacing`: 200 — vertical gap between layers
   - `staggerX`: 40 — horizontal offset per layer (creates depth illusion)
   - `nodeSpacingX`: 80 — horizontal gap between nodes in a layer
   - `nodeSpacingY`: 80 — vertical gap between nodes in a layer
   - `maxColumns`: 6 — max nodes per row within a layer

---

## Compound Parent Nodes for Layer Planes

Each RDF type layer gets a compound parent node:

```javascript
// Inject compound parent nodes for each type-layer
var layerNodes = [];
typeGroups.forEach(function(group, layerIndex) {
  var parentId = '__iso_layer_' + layerIndex;
  layerNodes.push({
    group: 'nodes',
    data: {
      id: parentId,
      label: group.typeLabel,
      _isometricLayer: true,
      _layerIndex: layerIndex
    }
  });
  // Re-parent actual nodes
  group.nodes.forEach(function(node) {
    node.move({ parent: parentId });
  });
});
```

Compound parent styling (added to `buildSemanticStyle`):
```javascript
{
  selector: 'node[_isometricLayer]',
  style: {
    'background-color': '#666',       // or per-type color
    'background-opacity': 0.08,       // translucent plane
    'border-width': 1,
    'border-color': '#999',
    'border-opacity': 0.3,
    'shape': 'round-rectangle',
    'label': 'data(label)',
    'text-valign': 'top',
    'text-halign': 'center',
    'font-size': '11px',
    'font-weight': 'bold',
    'padding': '20px',
    'compound-sizing-wrt-labels': 'include'
  }
}
```

### Cleanup on Layout Switch

When switching away from isometric to another layout (fcose, dagre, etc.), the compound layer nodes must be removed and child nodes un-parented. The `changeLayout()` function needs:

```javascript
function changeLayout(layoutName) {
  var cy = window._sempkmGraph;
  if (!cy) return;
  
  // Clean up isometric layer nodes if switching away
  var layerNodes = cy.nodes('[_isometricLayer]');
  if (layerNodes.length > 0 && layoutName !== 'isometric') {
    // Move children out of compound parents
    layerNodes.children().move({ parent: null });
    // Remove layer nodes
    cy.remove(layerNodes);
  }
  
  currentLayoutName = layoutName;
  // ... rest of existing logic
}
```

---

## Registration Flow

### Backend: Add to available_layouts

Two locations in `backend/app/views/router.py` define `built_in_layouts`:

1. **Line ~431** (generic_view endpoint for graph renderer):
   ```python
   "available_layouts": [
       {"name": "fcose", "label": "Force-Directed"},
       {"name": "dagre", "label": "Hierarchical"},
       {"name": "concentric", "label": "Radial"},
       {"name": "isometric", "label": "Isometric"},  # ADD
   ],
   ```

2. **Line ~1093** (graph_view endpoint):
   ```python
   built_in_layouts = [
       {"name": "fcose", "label": "Force-Directed"},
       {"name": "dagre", "label": "Hierarchical"},
       {"name": "concentric", "label": "Radial"},
       {"name": "isometric", "label": "Isometric"},  # ADD
   ]
   ```

### Frontend: Register layout extension

In `isometric-layout.js`, auto-register when Cytoscape is available:
```javascript
if (typeof cytoscape !== 'undefined') {
  cytoscape('layout', 'isometric', IsometricLayout);
}
```

Also add to `LAYOUT_REGISTRY` in `graph.js`:
```javascript
var LAYOUT_REGISTRY = {
  'fcose': { ... },
  'dagre': { ... },
  'concentric': { ... },
  'isometric': { name: 'isometric', animate: true, animationDuration: 500 }
};
```

### Template: Load the script

In `base.html`, after line 149 (`graph.js`):
```html
<script src="{{ 'isometric-layout.js' | asset_url }}"></script>
```

---

## Interaction with Existing Features

### Node Expansion (double-click)

When a user double-clicks a node to expand neighbors, new nodes are added via `_expandNode()`. If isometric layout is active, the new nodes need to be parented to the correct layer node (by matching their `type` data to existing layers) or a new layer created. The `_expandNode` function runs a sub-layout on new nodes — for isometric, this should re-run the full isometric layout or position new nodes within their layer.

**Approach:** After expansion, if `currentLayoutName === 'isometric'`, re-run the isometric layout on all nodes. This is cheap for a discrete layout.

### Filter

`filterGraph()` adds/removes the `filtered-out` class. Compound parent nodes should also get `filtered-out` if all their children are filtered. This can be handled in the filter function with a check after filtering children.

### Theme switching

`switchGraphTheme()` rebuilds styles via `buildSemanticStyle()`. The layer node styles must be included in the style builder output — they already will be since we add them to `buildSemanticStyle()`.

### Popovers

Popovers are positioned based on `renderedPosition()` and `container.getBoundingClientRect()`. Compound parent nodes will trigger popovers on hover — the isometric layer nodes should have `events: 'no'` or the popover handler should skip them (check `node.data('_isometricLayer')`).

---

## Edge Cases and Constraints

1. **Single-type graphs:** If all nodes have the same type, there's only one layer. The layout degenerates to a flat grid — which is fine, just not visually interesting. Could show a message "Isometric layout works best with multiple types."

2. **Unknown/missing types:** Nodes without a `type` field go into a fallback "Other" layer at the bottom.

3. **Large number of types:** With >6 types, layers become very spread out vertically. Cap at 8 layers, grouping remaining types into "Other."

4. **Compound node persistence:** Isometric compound parent nodes must be removed when switching to another layout. They have a sentinel `_isometricLayer` data flag for identification.

5. **Label readability:** Labels on data nodes positioned within compound parents render normally in 2D — no 3D transform means no readability issues. The `text-valign: 'bottom'` default works fine.

6. **User-created nodes during isometric view:** If a user creates a new object while isometric is active, the workspace fires `sempkm:tab-activated` but doesn't re-render the graph. The graph would need manual "Refresh" or the new node appears unpositioned until layout re-runs.

---

## Task Decomposition Guidance

### T01: Isometric Layout Extension (~200 lines JS)
- Create `frontend/static/js/isometric-layout.js`
- Implement `IsometricLayout` constructor, `run()`, `stop()`
- Layer grouping by `node.data('type')`
- Grid position computation within each layer
- Isometric stagger offset between layers
- Compound parent node injection for layer planes
- Compound parent node cleanup for layout switching
- Register via `cytoscape('layout', 'isometric', IsometricLayout)`

### T02: Integration & Wiring
- Add to `LAYOUT_REGISTRY` in `graph.js`
- Add compound parent node styles to `buildSemanticStyle()` 
- Add isometric cleanup to `changeLayout()` in `graph.js`
- Add `<script>` tag to `base.html`
- Add `{"name": "isometric", "label": "Isometric"}` to both `built_in_layouts` arrays in `router.py`
- Skip isometric layer nodes in popover handler
- Handle filter propagation to compound parents

### T03: Verification
- Manual testing: open any graph view, select "Isometric" from layout picker
- Verify nodes arrange on 3+ layers stratified by type
- Verify translucent layer planes visible behind nodes
- Verify edges connect across layers
- Verify switching back to fcose/dagre removes layer nodes
- Verify node expansion works in isometric mode
- Verify dark theme renders correctly
- Verify filter works (compound parents fade when all children filtered)

### Risk Assessment
- **No backend risk:** All changes are frontend JS + 2 one-liner Python additions
- **No vendor dependency risk:** Pure custom JS, no new libraries
- **Layout math is straightforward:** Grid within layers + linear vertical offset
- **Main risk:** Compound parent node lifecycle (injection/cleanup) must be clean — leaking layer nodes would corrupt the graph on layout switches

---

## Skill Discovery

The isometric 2.5D layout is pure custom JS on top of Cytoscape.js — no external frameworks beyond what's already loaded. No relevant skills found in `<available_skills>` for Cytoscape.js layout development. This is vanilla JS graph layout math with a well-documented extension API.
