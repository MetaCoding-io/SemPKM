# S04 UAT: Isometric 2.5D Graph View

## Preconditions

- SemPKM running with at least one Mental Model installed (basic-pkm recommended — provides multiple types)
- At least 5-10 objects of 2+ different types exist (e.g., Notes, Tasks, Events, Projects)
- Graph view accessible from the workspace

---

## Test Cases

### TC1: Isometric layout appears in picker

1. Open the workspace and navigate to a graph view (VIEWS → Graph, or open a type's graph view)
2. Locate the layout picker dropdown in the graph toolbar
3. **Expected:** "Isometric" appears as one of the layout options alongside existing layouts (fcose, cose, etc.)

### TC2: Basic isometric layout renders

1. From a graph view with nodes of 2+ types, select "Isometric" from the layout picker
2. **Expected:** Nodes rearrange into horizontal layers stratified by RDF type
3. **Expected:** Each layer has a translucent background plane (compound parent node)
4. **Expected:** Layers are vertically staggered with horizontal offset creating a 2.5D depth effect
5. **Expected:** Edges connect nodes across layers normally
6. **Expected:** Layer planes have labels showing the type name (e.g., "Note", "Task")

### TC3: Layer ordering

1. With isometric layout active on a graph with unequal type counts
2. **Expected:** The type with the most nodes is at the bottom (layer 0)
3. **Expected:** Types with fewer nodes are stacked above

### TC4: Single-type graph

1. Open a graph view filtered to a single type (e.g., only Notes)
2. Select "Isometric" layout
3. **Expected:** All nodes appear in a single layer with one translucent plane. No errors.

### TC5: No-type fallback

1. If any graph nodes lack a `type` data field
2. **Expected:** Those nodes are grouped into an "Other" layer

### TC6: Layer plane non-interactivity

1. With isometric layout active, hover over a translucent layer plane background
2. **Expected:** No tooltip/popover appears on the layer plane
3. Click on a layer plane background area (not on a node)
4. **Expected:** No object tab opens. No selection highlight on the layer plane.
5. Double-click on a layer plane background
6. **Expected:** No node expansion triggered

### TC7: Node interaction preserved

1. With isometric layout active, click on an actual node (not the layer plane)
2. **Expected:** The node's object tab opens in the workspace
3. Hover over a node
4. **Expected:** Normal tooltip/popover appears with node info

### TC8: Switch away — cleanup

1. With isometric layout active and compound layer planes visible
2. Switch to a different layout (e.g., "fcose" or "cose")
3. **Expected:** All translucent layer planes disappear
4. **Expected:** All nodes remain visible — none orphaned or missing
5. **Expected:** No `_isometricLayer` compound parent nodes remain (`cy.nodes('[_isometricLayer]').length` === 0 in browser console)

### TC9: Switch back — re-layout

1. After switching away from isometric (TC8), switch back to "Isometric"
2. **Expected:** Layer planes re-created, nodes re-stratified by type
3. **Expected:** Layout looks identical to the first time

### TC10: Text filter propagation

1. With isometric layout active, type a filter string that matches nodes in only one layer
2. **Expected:** Nodes in other layers fade out (filtered)
3. **Expected:** Layer planes with all children filtered out also fade or hide
4. Clear the filter
5. **Expected:** All nodes and layers return to normal visibility

### TC11: Node expansion with isometric

1. With isometric layout active, expand a node (double-click or expand action)
2. **Expected:** New nodes appear and the entire isometric layout re-runs
3. **Expected:** New nodes are correctly assigned to their type layers
4. **Expected:** Console shows `[isometric] Layout computed: N layers, M nodes` with updated counts

### TC12: Theme compatibility

1. Switch to dark theme with isometric layout active
2. **Expected:** Layer plane backgrounds use appropriate colors for dark theme (lighter translucent tones)
3. Switch to light theme
4. **Expected:** Layer plane backgrounds use appropriate colors for light theme (darker translucent tones)

### TC13: Observability diagnostic

1. Open browser DevTools console with isometric layout active
2. Type `window._sempkmIsometricState`
3. **Expected:** Object with `{ layers: [...], totalNodes: N, timestamp }`. Each layer entry shows parentId, label, nodeCount, layerIndex.
4. Type `cy.nodes('[_isometricLayer]').length`
5. **Expected:** Number equal to the count of distinct type layers currently displayed

### TC14: Max 8 layers cap

1. If a graph has objects of 9+ distinct types (may need to install additional models or create varied objects)
2. Select "Isometric" layout
3. **Expected:** At most 8 layers displayed. Excess types merged into an "Other" layer.

---

## Edge Cases

- **Empty graph:** Selecting isometric on a graph with 0 nodes should not error — layout completes with 0 layers.
- **Layout extension not loaded:** If `isometric-layout.js` fails to load (404), selecting "Isometric" from the picker should silently do nothing — no JS errors, no broken graph. Verify by checking `LAYOUT_REGISTRY` keys in console.
- **Rapid layout switching:** Quickly toggling between isometric and other layouts should not leave orphaned compound parents or produce duplicate layer planes.
