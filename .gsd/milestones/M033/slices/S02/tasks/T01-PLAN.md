---
estimated_steps: 5
estimated_files: 3
skills_used: []
---

# T01: Add Lucide SVG icon toggle to graph nodes

**Slice:** S02 — Isometric 2.5D Graph Layout & Icon Toggle
**Milestone:** M033

## Description

Add a toolbar toggle button to the graph view that switches node rendering between shape-only mode (current default) and Lucide SVG icon mode. In icon mode, each node type's Lucide icon (from `window._sempkmIcons.graph`) is rendered as a `background-image` SVG data URI inside the node. The user's preference is persisted in `localStorage` key `sempkm_graph_icon_mode`.

The Lucide UMD bundle is already loaded globally from `base.html` (line 47: `lucide@0.575.0`). The graph icons mapping (`window._sempkmIcons.graph`) is populated by workspace.js on load (line ~2807) with structure `{ typeIri: { icon: 'kebab-case-name' } }`.

## Steps

1. **Add `_lucideSvgDataUri(iconName)` to `graph.js`** — Memoized helper that converts a kebab-case Lucide icon name to an SVG data URI. Convert to PascalCase for lookup in `lucide` global. Use `lucide.createElement(iconDef, { width: 20, height: 20, stroke: 'currentColor', 'stroke-width': 1.5 })`. Serialize via `el.outerHTML`. Wrap in `data:image/svg+xml;utf8,` + `encodeURIComponent()`. Cache in a module-level `_svgUriCache` object. Return `null` if icon definition not found.

2. **Modify `buildSemanticStyle()` to accept `iconMode` parameter** — Add optional third parameter `iconMode` (boolean, default `false`). When `true` AND `window._sempkmIcons.graph` has entries, for each type entry: (a) look up the SVG data URI via `_lucideSvgDataUri(iconInfo.icon)`, (b) if found, push an additional style rule with `selector: 'node[type = "' + iri + '"]'` and style: `{ 'background-image': dataUri, 'background-fit': 'contain', 'background-clip': 'none', 'background-width': '60%', 'background-height': '60%' }`. In icon mode, override all node shapes to `'ellipse'` for uniformity (add a `'node'` selector rule with `'shape': 'ellipse'` when iconMode is true). Replace `#333`/dark-mode stroke color in the SVG by passing the color as the `stroke` attribute to `lucide.createElement()` — use the node's text color (isDark ? '#abb2bf' : '#333').

3. **Add icon toggle button to graph toolbar in `graph_view.html`** — After the "Fit" button in `.graph-toolbar`, add: `<button class="graph-icon-toggle-btn" id="graph-icon-toggle" onclick="window._toggleGraphIcons()" title="Toggle node icons"><i data-lucide="shapes"></i> <span>Icons</span></button>`. The Lucide `shapes` icon visually represents the feature.

4. **Add `_setIconMode()` and `_toggleGraphIcons()` to `graph.js`** — `_setIconMode(mode)`: write mode ('shape' or 'icon') to `localStorage.setItem('sempkm_graph_icon_mode', mode)`, rebuild stylesheet with `cy.style().fromJson(buildSemanticStyle(currentColors, isDark, mode === 'icon')).update()`, update button text/class. Expose `window._toggleGraphIcons` that reads current mode, flips it, calls `_setIconMode()`. On graph init (`initGraph`), read localStorage and apply if 'icon'. Update `switchGraphTheme()` and post-expand style rebuild to pass current icon mode.

5. **Add CSS for icon toggle button in `views.css`** — Style `.graph-icon-toggle-btn` matching existing `.graph-fit-btn` (same padding, border, border-radius, font-size). Add `.graph-icon-toggle-btn.active` with background highlight. Per CLAUDE.md: `.graph-icon-toggle-btn svg { width: 14px; height: 14px; flex-shrink: 0; stroke: currentColor; }`.

## Must-Haves

- [ ] `_lucideSvgDataUri()` correctly generates SVG data URIs from Lucide icon names
- [ ] `buildSemanticStyle()` adds `background-image` styles when `iconMode` is true
- [ ] Icon toggle button appears in graph toolbar
- [ ] Clicking toggle switches between shape-only and icon modes
- [ ] localStorage `sempkm_graph_icon_mode` persists preference across page reload
- [ ] Theme switch and node expansion preserve current icon mode

## Verification

- `rg -c '_lucideSvgDataUri' frontend/static/js/graph.js` returns ≥ 1
- `rg -c '_setIconMode\|_toggleGraphIcons' frontend/static/js/graph.js` returns ≥ 2
- `rg -c 'sempkm_graph_icon_mode' frontend/static/js/graph.js` returns ≥ 2
- `rg -c 'graph-icon-toggle' backend/app/templates/browser/graph_view.html` returns ≥ 1
- `rg -c 'graph-icon-toggle-btn' frontend/static/css/views.css` returns ≥ 1

## Inputs

- `frontend/static/js/graph.js` — existing graph initialization, `buildSemanticStyle()`, `changeLayout()`, theme switching, `window._sempkmIcons.graph` consumption
- `frontend/static/css/views.css` — existing `.graph-toolbar`, `.graph-fit-btn` styles
- `backend/app/templates/browser/graph_view.html` — existing toolbar HTML with layout picker and fit button

## Expected Output

- `frontend/static/js/graph.js` — modified with `_lucideSvgDataUri()`, updated `buildSemanticStyle(typeColors, isDark, iconMode)`, `_setIconMode()`, `_toggleGraphIcons()`, localStorage read on init
- `frontend/static/css/views.css` — modified with `.graph-icon-toggle-btn` styles
- `backend/app/templates/browser/graph_view.html` — modified with icon toggle button in toolbar
