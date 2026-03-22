---
estimated_steps: 5
estimated_files: 3
skills_used: []
---

# T01: Implement graph icon toggle button, SVG rendering, and localStorage persistence

**Slice:** S06 — Graph View Icon Toggle
**Milestone:** M033

## Description

Add a toolbar toggle button to the graph view that switches nodes between abstract Cytoscape shapes (current behavior) and Lucide SVG icon overlays via Cytoscape's `background-image` property. Persist the toggle state in localStorage so it survives page reloads. Three files change: graph.js (logic), graph_view.html (button), views.css (button styling).

## Steps

1. **Add toggle button to `graph_view.html`** — Insert a button after the existing "Fit" button in `.graph-toolbar`:
   ```html
   <button class="graph-icon-toggle-btn" onclick="toggleGraphIcons()" title="Toggle node icons">
     <i data-lucide="image"></i>
   </button>
   ```

2. **Add button CSS to `views.css`** — Style `.graph-icon-toggle-btn` matching the existing `.graph-fit-btn` pattern. Add an `.active` state with highlighted background. Per CLAUDE.md rules: size SVG via CSS, add `flex-shrink: 0`, use `stroke: currentColor`.
   ```css
   .graph-icon-toggle-btn {
     /* Same padding/border/radius/font/transition as .graph-fit-btn */
     /* active state: background highlight */
   }
   .graph-icon-toggle-btn svg { width: 16px; height: 16px; flex-shrink: 0; stroke: currentColor; }
   .graph-icon-toggle-btn.active { background: var(--color-primary-muted, rgba(45, 90, 158, 0.15)); border-color: var(--color-primary); }
   ```

3. **Add SVG data URI builder to `graph.js`** — Create a `_buildIconDataUri(iconName, color)` function that:
   - Converts kebab-case icon name to PascalCase for Lucide lookup
   - Creates a temporary `<i data-lucide="{name}">` element, calls `lucide.createIcons({nodes: [container]})`, extracts the rendered SVG's `outerHTML`
   - Encodes the SVG as `data:image/svg+xml;charset=utf-8,{encodedSVG}`
   - Caches results in a module-level `_iconDataUriCache` object keyed by `iconName + color`
   - Returns the data URI string, or `null` if the icon name is unknown/Lucide doesn't have it

4. **Extend `buildSemanticStyle()` to inject icon styles** — After the existing per-type shape selectors (around line 183), add a conditional block:
   ```js
   if (_iconsEnabled && window._sempkmIcons && window._sempkmIcons.graph) {
     var graphIcons = window._sempkmIcons.graph;
     var typeIris = Object.keys(graphIcons);
     for (var k = 0; k < typeIris.length; k++) {
       var iri = typeIris[k];
       var iconInfo = graphIcons[iri];
       if (iconInfo && iconInfo.icon) {
         var dataUri = _buildIconDataUri(iconInfo.icon, iconInfo.color || '#333');
         if (dataUri) {
           styles.push({
             selector: 'node[type = "' + iri + '"][!_isometricLayer]',
             style: {
               'background-image': dataUri,
               'background-fit': 'contain',
               'background-clip': 'none',
               'background-opacity': 1,
               'background-color': isDark ? '#2c313a' : '#ffffff',
               'border-width': 2,
               'border-color': iconInfo.color || nodeBorder
             }
           });
         }
       }
     }
   }
   ```
   The `[!_isometricLayer]` selector ensures compound layer plane nodes don't get icon overlays.

5. **Implement `toggleGraphIcons()` and integrate with init/theme** —
   - Module-level variable `var _iconsEnabled = false;`
   - `toggleGraphIcons()`: flip `_iconsEnabled`, persist to `localStorage.setItem('sempkm_graph_icons', _iconsEnabled ? 'true' : 'false')`, rebuild styles with `cy.style().fromJson(buildSemanticStyle(...)).update()`, toggle `.active` class on the button
   - In `initGraph()` or `_renderGraph()`: read `localStorage.getItem('sempkm_graph_icons') === 'true'` to set initial `_iconsEnabled`, and if true, add `.active` class to the button
   - In `switchGraphTheme()`: icon state already flows through `buildSemanticStyle()` via the module-level `_iconsEnabled` variable — no extra work needed
   - Export: `window.toggleGraphIcons = toggleGraphIcons;`

**Important pre-existing bug to fix:** Line 123 of graph.js has a missing comma between the `filtered-out` style entry closing `}` and the isometric layer plane style entry `{`. Add the comma: `},` instead of `}`.

## Must-Haves

- [ ] `toggleGraphIcons()` function exported on `window`
- [ ] SVG data URIs built from Lucide icons at runtime, cached per icon+color
- [ ] `_isometricLayer` compound nodes excluded from icon styles via `[!_isometricLayer]` selector
- [ ] Toggle state read from/written to `localStorage` key `sempkm_graph_icons`
- [ ] Button has `.active` class when icons are enabled
- [ ] `switchGraphTheme()` preserves icon state (icons still show after theme toggle)
- [ ] Missing comma on line ~123 of graph.js fixed

## Verification

- `grep -q "toggleGraphIcons" frontend/static/js/graph.js` — function defined
- `grep -q "sempkm_graph_icons" frontend/static/js/graph.js` — localStorage key
- `grep -q "graph-icon-toggle-btn" backend/app/templates/browser/graph_view.html` — button exists
- `grep -q "graph-icon-toggle-btn" frontend/static/css/views.css` — CSS rule exists
- `grep -q "background-image" frontend/static/js/graph.js` — Cytoscape icon style property used
- `grep -q "_isometricLayer" frontend/static/js/graph.js` — layer plane exclusion present (pre-existing, but confirm still there)
- `node -e "var fs=require('fs'); var code=fs.readFileSync('frontend/static/js/graph.js','utf8'); try { new Function(code); console.log('SYNTAX OK'); } catch(e) { console.error('SYNTAX ERROR:', e.message); process.exit(1); }"` — JS parses without syntax errors

## Inputs

- `frontend/static/js/graph.js` — existing graph visualization module (761 lines), contains `buildSemanticStyle()`, `initGraph()`, `switchGraphTheme()`, `filterGraph()`, exports on `window`
- `backend/app/templates/browser/graph_view.html` — graph view template with `.graph-toolbar` containing layout picker and Fit button
- `frontend/static/css/views.css` — view styles, `.graph-fit-btn` at line 534 is the reference for button styling
- `frontend/static/js/workspace.js` — context only: fetches `window._sempkmIcons` from `/browser/icons` at workspace init (~line 2829)

## Expected Output

- `frontend/static/js/graph.js` — modified: `_buildIconDataUri()`, `toggleGraphIcons()`, icon style injection in `buildSemanticStyle()`, localStorage read in init, window export, comma fix
- `backend/app/templates/browser/graph_view.html` — modified: icon toggle button added to `.graph-toolbar`
- `frontend/static/css/views.css` — modified: `.graph-icon-toggle-btn` and `.graph-icon-toggle-btn.active` styles added
