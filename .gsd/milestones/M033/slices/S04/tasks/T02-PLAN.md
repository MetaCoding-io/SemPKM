---
estimated_steps: 5
estimated_files: 3
skills_used: []
---

# T02: Wire isometric layout into graph system and verify

**Slice:** S04 — Isometric 2.5D Graph View
**Milestone:** M033

## Description

Connect the `isometric-layout.js` extension to the rest of the graph system: load the script, register the layout in the picker dropdown, add compound parent node styles, add cleanup logic when switching away from isometric, skip layer nodes in popovers, propagate filter state to compound parents, and handle node expansion while isometric is active. Then verify the full integration.

## Steps

1. **Load the script in `base.html`.** Add a `<script>` tag for `isometric-layout.js` immediately after the line loading `graph.js` (line 149). The layout extension must load after `graph.js` but the order relative to other view scripts (kanban, calendar, map) doesn't matter since it self-registers with Cytoscape.

   In `backend/app/templates/base.html`, after line 149 (`graph.js`):
   ```html
   <script src="{{ 'isometric-layout.js' | asset_url }}"></script>
   ```

2. **Register the layout in the backend layout lists.** In `backend/app/views/router.py`:
   - At ~line 431, add `{"name": "isometric", "label": "Isometric"}` to the `available_layouts` list (the inline list in the generic_view graph branch).
   - At ~line 1090, add `{"name": "isometric", "label": "Isometric"}` to the `built_in_layouts` list (the graph_view endpoint).

3. **Integrate into `graph.js`.** Four changes:

   a. **LAYOUT_REGISTRY** (~line 15): Add `'isometric': { name: 'isometric', animate: true, animationDuration: 500 }` entry.

   b. **buildSemanticStyle()** — Add compound parent node styles at the end of the `styles` array (before the per-type color loop, ~line 126). These styles make the layer planes visible:
   ```javascript
   // Isometric layer plane compound parent nodes
   {
     selector: 'node[_isometricLayer]',
     style: {
       'background-color': '#666',
       'background-opacity': 0.08,
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
       'compound-sizing-wrt-labels': 'include',
       'events': 'no'
     }
   }
   ```
   For dark theme, use lighter colors: `'background-color': '#aaa'`, `'border-color': '#666'`. Use the `isDark` parameter to choose. Setting `'events': 'no'` also prevents popovers from firing on layer nodes, but the mouseover handler should also guard.

   c. **changeLayout()** (~line 631): Before setting `currentLayoutName`, check for existing isometric layer nodes and clean them up if switching away from isometric:
   ```javascript
   function changeLayout(layoutName) {
     var cy = window._sempkmGraph;
     if (!cy) return;
     
     // Clean up isometric compound layer nodes when switching away
     if (layoutName !== 'isometric') {
       var layerNodes = cy.nodes('[_isometricLayer]');
       if (layerNodes.length > 0) {
         layerNodes.children().move({ parent: null });
         cy.remove(layerNodes);
       }
     }
     
     currentLayoutName = layoutName;
     // ... rest unchanged
   ```

   d. **mouseover handler** (~line 496): Add an early return for isometric layer nodes:
   ```javascript
   cy.on('mouseover', 'node', function (evt) {
     if (evt.target.data('_isometricLayer')) return;  // skip layer planes
     evt.target.addClass('hovered');
     // ... rest unchanged
   ```

   e. **filterGraph()** (~line 651): After filtering data nodes, also update compound parent visibility — if all children of a layer node are filtered out, add `filtered-out` to the parent:
   ```javascript
   // After the existing node/edge filter loop:
   cy.nodes('[_isometricLayer]').forEach(function(parent) {
     var children = parent.children();
     var allFiltered = children.length > 0 && children.every(function(c) {
       return c.hasClass('filtered-out');
     });
     if (allFiltered) {
       parent.addClass('filtered-out');
     } else {
       parent.removeClass('filtered-out');
     }
   });
   ```

   f. **_expandNode()** (~line 600 area): After adding new elements and running the sub-layout, if `currentLayoutName === 'isometric'`, re-run the full isometric layout instead of the positional sub-layout. New nodes need to be parented to the correct layer:
   ```javascript
   if (currentLayoutName === 'isometric') {
     cy.layout({ name: 'isometric', animate: true, animationDuration: 500 }).run();
   } else {
     // existing sub-layout logic
   }
   ```

4. **Also skip layer nodes in tap/dbltap handlers.** Add early returns in the `cy.on('tap', 'node', ...)` and `cy.on('dbltap', 'node', ...)` handlers (~lines 317, 326) if `evt.target.data('_isometricLayer')`.

5. **Verify end-to-end:** Run all slice-level verification commands:
   - `test -f frontend/static/js/isometric-layout.js`
   - `grep -q "isometric" backend/app/views/router.py`
   - `grep -q "isometric-layout.js" backend/app/templates/base.html`
   - `grep -q "'isometric'" frontend/static/js/graph.js`
   - `grep -q "_isometricLayer" frontend/static/js/graph.js`

## Must-Haves

- [ ] Script tag added to base.html after graph.js
- [ ] "Isometric" appears in both `available_layouts` arrays in router.py
- [ ] `'isometric'` entry in LAYOUT_REGISTRY in graph.js
- [ ] Compound parent node styles in `buildSemanticStyle()` (both light and dark themes)
- [ ] Isometric cleanup in `changeLayout()` — un-parent children, remove layer nodes
- [ ] Layer nodes skipped in mouseover, tap, and dbltap handlers
- [ ] Filter propagation to compound parent nodes
- [ ] Expansion re-runs full isometric layout when active

## Verification

- `grep -q "isometric-layout.js" backend/app/templates/base.html` — script loaded
- `grep -q "isometric" backend/app/views/router.py` — backend registers layout
- `grep -q "'isometric'" frontend/static/js/graph.js` — in LAYOUT_REGISTRY
- `grep -q "_isometricLayer" frontend/static/js/graph.js` — compound parent handling
- `grep -c "isometric" backend/app/views/router.py` returns >= 2 — both layout lists updated

## Inputs

- `frontend/static/js/isometric-layout.js` — the layout extension from T01
- `frontend/static/js/graph.js` — existing graph system to integrate into
- `backend/app/views/router.py` — both `available_layouts` / `built_in_layouts` arrays
- `backend/app/templates/base.html` — script loading order

## Expected Output

- `frontend/static/js/graph.js` — modified with LAYOUT_REGISTRY entry, compound parent styles, cleanup, popover skip, filter propagation, expansion handling
- `backend/app/views/router.py` — modified with "Isometric" in both layout lists
- `backend/app/templates/base.html` — modified with isometric-layout.js script tag

## Observability Impact

- **LAYOUT_REGISTRY:** `'isometric'` key now registered — `Object.keys(LAYOUT_REGISTRY)` in browser console shows all available layouts including isometric.
- **Compound parent styles:** `node[_isometricLayer]` selector in Cytoscape stylesheet makes layer planes visible with translucent backgrounds. `events: 'no'` prevents click/hover interaction on layers.
- **Cleanup visibility:** After switching away from isometric, `cy.nodes('[_isometricLayer]').length === 0` confirms cleanup. If non-zero, cleanup failed.
- **Filter propagation:** When filtering with isometric active, `cy.nodes('[_isometricLayer].filtered-out')` shows which layer planes were hidden because all children were filtered.
- **Failure mode:** If `isometric-layout.js` fails to load, `LAYOUT_REGISTRY['isometric']` exists but `cytoscape('layout', 'isometric')` is unregistered — the layout will be treated as unknown by Cytoscape and produce no visible change. Check browser network tab for 404 on the script.
