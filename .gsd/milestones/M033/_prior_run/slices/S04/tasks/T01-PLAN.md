---
estimated_steps: 5
estimated_files: 1
skills_used: []
---

# T01: Create isometric layout extension

**Slice:** S04 — Isometric 2.5D Graph View
**Milestone:** M033

## Description

Create `frontend/static/js/isometric-layout.js` — a custom Cytoscape.js layout extension (~200 lines) that stratifies graph nodes into horizontal z-layers by RDF type, positions them in a grid within each layer, applies isometric stagger between layers for visual depth, and injects compound parent nodes to create translucent layer planes.

This is a standalone file with no dependencies beyond Cytoscape.js (already loaded globally). It registers itself via `cytoscape('layout', 'isometric', IsometricLayout)`.

## Steps

1. **Implement the layout constructor and defaults.** The `IsometricLayout` function receives `options` (merged with defaults). Store `this.options`. Defaults:
   - `layerSpacing: 200` — vertical gap between layers
   - `staggerX: 40` — horizontal offset per layer (depth illusion)
   - `nodeSpacingX: 80` — horizontal gap within a layer grid
   - `nodeSpacingY: 80` — vertical gap within a layer grid
   - `maxColumns: 6` — max nodes per row in a layer
   - `maxLayers: 8` — cap on number of distinct layers (excess grouped into "Other")
   - `animate: true, animationDuration: 500`

2. **Implement `run()` — the core layout logic:**
   a. Get all non-parent nodes via `options.eles.nodes().not(':parent')`.
   b. Group nodes by `node.data('type')`. Nodes without a type go into an "Other" group. If there are more than `maxLayers` distinct types, keep the top N-1 by node count and merge the rest into "Other".
   c. Sort layers by node count descending (largest type at bottom/layer 0) so the most populated layer is visually prominent.
   d. **Inject compound parent nodes** for each layer. For each type group, create a parent node with `data: { id: '__iso_layer_' + index, label: typeLabel, _isometricLayer: true, _layerIndex: index }`. Move each node in the group to be a child of this parent via `node.move({ parent: parentId })`. Add the parent node to the Cytoscape instance via `cy.add()`.
   e. **Compute positions** for each non-parent node using `eles.nodes().not(':parent').layoutPositions(this, options, positionFn)`. The position function:
      - Look up the node's layer index from its parent's `_layerIndex`
      - Compute column/row within the layer's grid: `col = nodeIndexInLayer % maxColumns`, `row = Math.floor(nodeIndexInLayer / maxColumns)`
      - `x = staggerX * layerIndex + col * nodeSpacingX - (numCols * nodeSpacingX / 2)`
      - `y = -layerIndex * layerSpacing + row * nodeSpacingY - (numRows * nodeSpacingY / 2)`
      - The negative Y puts higher layers at the top of the viewport

3. **Implement `stop()` — no-op for discrete layouts.** Return `this`.

4. **Register the layout** at the bottom of the file:
   ```javascript
   if (typeof cytoscape !== 'undefined') {
     cytoscape('layout', 'isometric', IsometricLayout);
   }
   ```

5. **Handle edge cases:**
   - **Single-type graph:** Degenerates to a flat grid — fine, just one layer.
   - **No nodes:** `run()` returns immediately.
   - **Existing isometric layer nodes:** Before injecting new compound parents, remove any existing `[_isometricLayer]` nodes (handles re-layout scenarios).
   - Use `typeLabel` from `node.data('typeLabel')` for the layer label. Fall back to a shortened version of the type IRI (after last `/` or `#`) if typeLabel is empty.

## Must-Haves

- [ ] Layout registered via `cytoscape('layout', 'isometric', IsometricLayout)`
- [ ] Nodes grouped by `data('type')` into layers
- [ ] Compound parent nodes injected with `_isometricLayer: true` sentinel
- [ ] Grid positioning within each layer
- [ ] Isometric vertical stagger between layers
- [ ] Layer count capped at 8 with "Other" fallback
- [ ] Type label resolution for compound parent labels (typeLabel → IRI suffix fallback)
- [ ] Cleanup of existing layer nodes before re-layout

## Verification

- `test -f frontend/static/js/isometric-layout.js` — file exists
- `node -e "const fs=require('fs'); const src=fs.readFileSync('frontend/static/js/isometric-layout.js','utf8'); if(!src.includes('layoutPositions')) process.exit(1); if(!src.includes(\"cytoscape('layout'\")) process.exit(1); if(!src.includes('_isometricLayer')) process.exit(1); console.log('OK')"` — correct protocol, sentinel flag
- `grep -c "function IsometricLayout" frontend/static/js/isometric-layout.js` returns 1

## Inputs

- `frontend/static/js/graph.js` — reference for Cytoscape patterns (LAYOUT_REGISTRY, initGraph, node data schema: `type`, `typeLabel`, `label`)

## Expected Output

- `frontend/static/js/isometric-layout.js` — new file (~200 lines), self-contained Cytoscape layout extension

## Observability Impact

- **New signals:** `console.debug('[isometric] Layout computed: N layers, M nodes')` on each run. `window._sempkmIsometricState` object for browser console inspection of layer metadata.
- **Inspection:** Run `window._sempkmIsometricState` in DevTools to see last layout run. Query `cy.nodes('[_isometricLayer]')` to inspect injected compound parents.
- **Failure state:** If the extension fails to register, `cytoscape('layout', 'isometric', ...)` won't fire and the layout name won't appear in Cytoscape's internal registry. The `window._sempkmIsometricState` will be `undefined` if `run()` was never called.
