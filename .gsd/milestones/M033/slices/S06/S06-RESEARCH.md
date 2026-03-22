# S06 Research: Graph View Icon Toggle

**Depth:** Light — self-contained feature using established patterns (Cytoscape styling, Lucide icons, localStorage persistence).

---

## Summary

Add a toolbar toggle button to the graph view that switches nodes between abstract Cytoscape shapes (current behavior) and Lucide SVG icon rendering via Cytoscape's `background-image` property. Persist toggle state in localStorage.

## Recommendation

Single task. All changes are in 4 files with no backend work needed. The icon data (`window._sempkmIcons.graph`) and Lucide SVG data (`lucide.icons`) are already available at runtime.

---

## Implementation Landscape

### Files to Modify

| File | Change |
|---|---|
| `frontend/static/js/graph.js` | Add `toggleIcons()` function, SVG data URI builder, icon style injection into `buildSemanticStyle()`, localStorage read on init |
| `backend/app/templates/browser/graph_view.html` | Add icon toggle button to `.graph-toolbar` div |
| `frontend/static/css/views.css` | Style the toggle button (matches existing `.graph-fit-btn` pattern) |

### Data Already Available at Runtime

**`window._sempkmIcons.graph`** — fetched from `/browser/icons` on workspace load (workspace.js line 2826). Structure:
```js
{
  "http://example.org/ontology#Note": { icon: "file-text", color: "#4a90d9", size: null },
  "http://example.org/ontology#Person": { icon: "user", color: "#e6a23c", size: null },
  // ...per installed model type
}
```

**`lucide.icons`** — from the Lucide UMD bundle (`https://unpkg.com/lucide@0.575.0/dist/umd/lucide.min.js`), loaded in `base.html`. Maps PascalCase icon names to SVG element definitions. Each entry is `[attrs, children]` where children are SVG path elements.

### Cytoscape `background-image` on Nodes

Cytoscape.js supports `background-image` on nodes via data URIs. The approach:

1. Build an SVG string for each Lucide icon (24×24 viewBox, stroke-based paths)
2. Encode as `data:image/svg+xml;charset=utf-8,<encoded-svg>`
3. Apply as Cytoscape style: `{ 'background-image': dataUri, 'background-fit': 'contain', 'background-clip': 'none' }`

### SVG Data URI Construction

Lucide icons use a consistent SVG template:
```xml
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"
     fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  {paths from lucide.icons entry}
</svg>
```

The `lucide.icons` object uses PascalCase keys (`FileText`, `BookOpen`). The backend provides kebab-case names (`file-text`, `book-open`). Conversion:
```js
function kebabToPascal(s) {
  return s.split('-').map(function(w) { return w[0].toUpperCase() + w.slice(1); }).join('');
}
```

To extract SVG path content from `lucide.icons.FileText`:
- The UMD bundle stores `[tag, attrs, [...children]]` tuples
- Create a temporary `<i data-lucide="file-text">` element, call `lucide.createIcons({nodes: [el]})`, then read the resulting SVG's `innerHTML` for the path elements
- Alternatively, use `lucide.createElement(lucide.icons.FileText)` if available — this returns a DOM SVGElement directly

**Recommended approach:** Create a hidden container, insert `<i data-lucide="{name}">` elements, call `lucide.createIcons()` on the container, then extract the rendered SVG's `outerHTML` to build data URIs. This is the safest approach since `createIcons` is the proven API in this codebase. Cache the data URIs per icon name to avoid re-rendering.

### Toggle Behavior

- **Shapes mode (default):** Current behavior — `iconToShape` mapping sets node `shape` property (ellipse, rectangle, diamond, etc.). No `background-image`.
- **Icons mode:** Each node gets `background-image` with the Lucide SVG data URI, `background-fit: 'contain'`, `background-clip: 'none'`. Node shape stays but the icon overlay is the visual focus. Background color can be reduced to white/light to let the icon dominate.

### localStorage Persistence

Key: `sempkm_graph_icons` (matches existing `sempkm_*` pattern in workspace.js).
Value: `"true"` or `"false"` (string, matching `sempkm_fuzzy_enabled` pattern on line 1774).

Read on `initGraph()` start. Apply icon styles if enabled. Toggle button reflects current state.

### Toolbar Button Placement

The `.graph-toolbar` div (in `graph_view.html`) currently has:
- Layout picker `<select>` with label
- "Fit" button

The icon toggle button goes after "Fit":
```html
<button class="graph-icon-toggle-btn" onclick="toggleGraphIcons()" title="Toggle node icons">
  <i data-lucide="image"></i>
</button>
```

Style matches `.graph-fit-btn` in `views.css` (lines 534–548). Per CLAUDE.md rules:
- Size the SVG via CSS, not inline styles
- Add `flex-shrink: 0` since it's in a flex container
- Use `stroke: currentColor` for color inheritance

### Active State Indicator

When icons are enabled, the toggle button should have a visual "active" state — e.g., a highlighted background or border color. CSS class `.graph-icon-toggle-btn.active`.

### Theme Awareness

`switchGraphTheme(isDark)` rebuilds styles via `buildSemanticStyle()`. When icons are enabled, the SVG data URIs need icon colors from `_sempkmIcons.graph`. The `buildSemanticStyle` function already receives `typeColors` — icon styles should be injected conditionally based on the toggle state.

### Graph.js Integration Points

1. **`buildSemanticStyle(typeColors, isDark)`** (line 26): Add icon background-image styles when toggle is on. The icon styles are per-type-IRI selectors, same as existing shape selectors (lines 179-186).

2. **`initGraph(containerId, specIri, typeColors, availableLayouts, customDataUrl)`** (line 208): Read localStorage on init, set initial icon state.

3. **New `toggleGraphIcons()` function**: Toggle the state, rebuild styles with `cy.style().fromJson(styles).update()` (same pattern as `switchGraphTheme`), persist to localStorage.

4. **Export**: Add `window.toggleGraphIcons = toggleGraphIcons;` alongside existing exports (line 755-759).

### Edge Cases

- **Icons not loaded yet:** `window._sempkmIcons` is fetched async. If `initGraph` runs before the fetch completes, icon toggle should gracefully no-op or defer. Check: workspace.js fetches icons early in `_initWorkspace()`, and graph init happens later via `tryInit()` with a 50ms poll. Icons will almost certainly be loaded by then.
- **Unknown icon name:** If `lucide.icons[PascalCase]` is undefined, fall back to the default shape (no icon overlay).
- **Isometric layout compound nodes:** Layer plane nodes (`node[_isometricLayer]`) should NOT get icon overlays — they're structural containers. The icon style selector should exclude them: `node[type = "..."][!_isometricLayer]`.

---

## Verification

1. Open a graph view in the workspace
2. Click the icon toggle button — nodes should display Lucide SVG icons
3. Click again — nodes revert to abstract shapes
4. Reload the page — toggle state should persist
5. Switch between light/dark theme — icons should remain correct
6. Switch to isometric layout — layer plane nodes should NOT have icons
