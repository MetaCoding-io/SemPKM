---
estimated_steps: 9
estimated_files: 2
---

# T02: Frontend Flip Button, Property Table Rendering, Serialization, and CSS

**Slice:** S02 — Property Flip on Object Nodes
**Milestone:** M008

## Description

Add the flip button to canvas object node headers, implement the click handler that fetches and caches properties from the T01 endpoint, render a compact property table replacing the markdown body when flipped, serialize `showProperties` for save/load persistence, and add all CSS styling.

## Steps

1. **Add `propertyCache` to canvas state object** (line ~11 in `canvas.js`):
   - Add `propertyCache: {}` to the `state` object alongside existing properties like `nodeData`, `layer`, etc.

2. **Add `SVG_FLIP` icon constant** (~line 42, among other SVG constants):
   - Define inline SVG matching existing icon pattern (16×16 viewBox, `class="spatial-icon"`, stroke-based)
   - Use a rotate/swap icon (two curved arrows like Lucide `repeat` or `arrow-left-right`)
   - Example: `var SVG_FLIP = '<svg class="spatial-icon" ...>...</svg>';`

3. **Add flip button to `renderNodes()` header** (line ~857):
   - Insert between the expand button and delete button in the header HTML array:
     ```
     '<button class="spatial-node-flip', (node.showProperties ? ' is-flipped' : ''), '" type="button" title="Toggle properties">', SVG_FLIP, '</button>',
     ```
   - The `is-flipped` class drives CSS active state

4. **Add conditional property table vs markdown in `renderNodes()` body section**:
   - Find the existing line that renders the markdown div (after the collapsed check):
     ```javascript
     (node.collapsed ? '' : '<div class="spatial-node-markdown">' + renderMarkdown(node.markdown || '') + '</div>')
     ```
   - Replace with conditional:
     ```javascript
     node.collapsed ? '' :
       (node.showProperties && state.propertyCache[node.id]
         ? buildPropertyTable(state.propertyCache[node.id])
         : '<div class="spatial-node-markdown">' + renderMarkdown(node.markdown || '') + '</div>')
     ```

5. **Implement `buildPropertyTable(data)` function**:
   - Returns HTML string wrapped in `<div class="spatial-node-properties">`
   - If `data.type_label`: render `<div class="prop-type-header">{type_label}</div>`
   - For each property in `data.properties`:
     - `<div class="prop-row{source === 'inferred' ? ' prop-inferred' : ''}">` 
     - `<span class="prop-label">{name}</span>`
     - `<span class="prop-value">{formatted values}</span>`
     - `</div>`
   - Value formatting:
     - Multiple values: join with `, ` or render each in a `<span class="prop-pill">`
     - IRI values with `ref_label`: show the label
     - Boolean: `✓` / `✗`
     - Tag-like values (from tag properties): `<span class="prop-pill">#{value}</span>`
   - Inferred properties get a subtle `(inferred)` suffix or `.prop-inferred` class

6. **Add flip click handler to `onLayerClick()`**:
   - In the early-exit guard (line ~459), add `.spatial-node-flip` to the list of selectors that get `return` treatment:
     ```javascript
     event.target.closest('.spatial-node-flip')
     ```
   - After the expand button handler (line ~547), add:
     ```javascript
     var flipBtn = event.target.closest('.spatial-node-flip');
     if (flipBtn) {
       var flipNode = flipBtn.closest('.spatial-node');
       if (!flipNode) return;
       var nodeId = flipNode.dataset.nodeId;
       var model = findNode(nodeId);
       if (!model) return;
       model.showProperties = !model.showProperties;
       if (model.showProperties && !state.propertyCache[nodeId]) {
         fetchNodeProperties(nodeId, model.uri);
       } else {
         renderNodes();
       }
       return;
     }
     ```

7. **Implement `fetchNodeProperties(nodeId, iri)` function**:
   - Follow the `fetchNodeBody` pattern (line ~276):
     ```javascript
     function fetchNodeProperties(nodeId, iri) {
       fetch('/api/canvas/properties?iri=' + encodeURIComponent(iri))
         .then(function(r) { return r.ok ? r.json() : null; })
         .then(function(data) {
           if (data) {
             state.propertyCache[nodeId] = data;
           }
           renderNodes();
         })
         .catch(function() { renderNodes(); });
     }
     ```

8. **Add serialization in `getDocument()` and `applyDocument()`**:
   - In `getDocument()` (line ~1142), inside the node serialization loop, add:
     ```javascript
     if (n.showProperties) serialized.showProperties = true;
     ```
   - In `applyDocument()` (line ~1167), inside the node restoration loop, add:
     ```javascript
     if (n.showProperties) node.showProperties = true;
     ```
   - Note: `propertyCache` is NOT serialized — it's re-fetched when the flipped node is next viewed. The cache is memory-only.

9. **Add CSS styles to `workspace.css`**:
   - Add `.spatial-node-flip` to the existing button group (lines 4907-4909):
     ```css
     .spatial-node-chevron,
     .spatial-node-expand,
     .spatial-node-flip,
     .spatial-node-delete {
     ```
   - Add to hover rule (lines 4924-4926):
     ```css
     .spatial-node-chevron:hover,
     .spatial-node-expand:hover,
     .spatial-node-flip:hover,
     .spatial-node-delete:hover {
     ```
   - Add flip-specific active state:
     ```css
     .spatial-node-flip.is-flipped {
       color: var(--color-accent);
     }
     .spatial-node-flip.is-flipped svg {
       stroke: var(--color-accent);
     }
     ```
   - Add property table styles:
     ```css
     .spatial-node-properties {
       overflow-y: auto;
       max-height: 100%;
       padding: 8px 12px;
       font-size: 12px;
     }
     .prop-type-header {
       font-weight: 600;
       font-size: 11px;
       text-transform: uppercase;
       letter-spacing: 0.05em;
       color: var(--color-text-muted);
       margin-bottom: 8px;
       padding-bottom: 4px;
       border-bottom: 1px solid var(--color-border);
     }
     .prop-row {
       display: flex;
       gap: 8px;
       padding: 3px 0;
       border-bottom: 1px solid var(--color-border-subtle, rgba(255,255,255,0.05));
     }
     .prop-label {
       flex-shrink: 0;
       width: 90px;
       font-weight: 500;
       color: var(--color-text-muted);
       overflow: hidden;
       text-overflow: ellipsis;
       white-space: nowrap;
     }
     .prop-value {
       flex-grow: 1;
       word-break: break-word;
       min-width: 0;
     }
     .prop-inferred {
       opacity: 0.7;
     }
     .prop-pill {
       display: inline-block;
       background: var(--color-surface-raised, rgba(255,255,255,0.08));
       padding: 1px 6px;
       border-radius: 3px;
       margin-right: 4px;
       font-size: 11px;
     }
     ```
   - Per project convention, add `flex-shrink: 0` for the flip button SVG:
     ```css
     .spatial-node-flip svg {
       flex-shrink: 0;
     }
     ```

## Must-Haves

- [ ] Flip button visible in node header between expand and delete
- [ ] Click toggles between markdown body and property table
- [ ] Properties fetched from `/api/canvas/properties?iri=<IRI>` and cached per-node
- [ ] Property table shows name/value rows with type label header
- [ ] Body properties not shown in table (handled by endpoint)
- [ ] Multi-value properties displayed (comma-separated or pills)
- [ ] Inferred properties visually distinguished
- [ ] `showProperties` persists across save/load via `getDocument()`/`applyDocument()`
- [ ] Flip button shows active state (accent color) when flipped
- [ ] Property table scrolls within node bounds (overflow-y: auto)
- [ ] Old canvas sessions (no `showProperties`) load without errors
- [ ] SVG icon follows project convention (CSS-sized, flex-shrink: 0, stroke: currentColor)

## Verification

- Docker Compose up → open workspace → Spatial Canvas → drag typed object → click flip button → property table visible with SHACL-ordered values
- Click flip again → markdown body returns
- Drag untyped object → flip → shows properties with local-name labels
- Save canvas → reload page → flipped node still shows properties (after cache re-fetch)
- Open old saved canvas session → loads without JS errors, no `showProperties` field → all nodes default to markdown view
- Inspect `state.propertyCache` in browser console → has entry for flipped node

## Observability Impact

- **`state.propertyCache`** — inspectable via `window.SemPKMCanvas.exportState()` won't include cache (memory-only), but browser console can access the IIFE's `state.propertyCache` via debugger breakpoints
- **Flip button visual indicator** — `.is-flipped` class on the button provides immediate visual feedback; accent color shows which nodes are in property view
- **Network requests** — `GET /api/canvas/properties?iri=<IRI>` visible in browser Network tab; errors silently caught and node re-renders (no user-facing error, just stays on markdown)
- **Serialization** — `showProperties: true` present in saved session JSON; absent (falsy) for unflipped nodes
- **Future agent inspection** — `document.querySelectorAll('.spatial-node-flip.is-flipped').length` shows count of flipped nodes; `document.querySelectorAll('.prop-row').length` shows visible property rows

## Inputs

- `frontend/static/js/canvas.js` — current canvas implementation (1399 LOC) with `state` object, `renderNodes()`, `onLayerClick()`, `getDocument()`, `applyDocument()`, `fetchNodeBody` as reference pattern
- `frontend/static/css/workspace.css` — existing spatial node button styles at lines 4907-4949
- T01 output: `GET /api/canvas/properties?iri=<IRI>` endpoint returning `{type_label, properties: [...]}`

## Expected Output

- `frontend/static/js/canvas.js` — extended with `propertyCache` state, `SVG_FLIP` icon, flip button in `renderNodes()`, conditional property table rendering, `buildPropertyTable()`, flip click handler in `onLayerClick()`, `fetchNodeProperties()`, `showProperties` serialization in `getDocument()`/`applyDocument()`
- `frontend/static/css/workspace.css` — extended with `.spatial-node-flip` button styles, `.is-flipped` active state, `.spatial-node-properties` table layout, `.prop-row/.prop-label/.prop-value/.prop-inferred/.prop-pill/.prop-type-header` styles
