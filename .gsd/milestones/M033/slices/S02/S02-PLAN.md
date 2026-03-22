# S02: Isometric 2.5D Graph Layout & Icon Toggle

**Goal:** Graph view has a selectable "Isometric" layout with CSS 3D perspective + correct click/drag/popover interaction, and a toolbar toggle switching nodes between shape-only and Lucide SVG icon display.
**Demo:** Open a graph view → select "Isometric 2.5D" from the layout picker → graph tilts into 2.5D perspective → click a node → popover appears at the correct position. Toggle the icon button → nodes show Lucide SVG icons inside them → toggle off → shapes return. Refresh → icon preference persists.

## Must-Haves

- "Isometric 2.5D" option appears in the layout picker dropdown in both generic and model-spec graph views
- Selecting isometric applies CSS 3D perspective transform (`perspective(800px) rotateX(55deg) rotateZ(-45deg)`) to a wrapper div around the Cytoscape container
- Node click (tap) events fire on the correct node under isometric transform (coordinate correction via monkey-patching `findContainerClientCoords`)
- Node popovers position correctly under isometric transform (forward-transform coordinate conversion)
- Switching away from isometric cleanly removes the transform and restores normal interaction
- Icon toggle button appears in the graph toolbar
- Clicking icon toggle switches all nodes to show Lucide SVG icons via `background-image` data URIs
- Icon mode preference persists in `localStorage` key `sempkm_graph_icon_mode`
- Icon toggle works in both normal and isometric layout modes

## Proof Level

- This slice proves: integration (CSS 3D transform + Cytoscape event system coordination)
- Real runtime required: yes (browser rendering of CSS 3D transforms + Cytoscape canvas)
- Human/UAT required: yes (visual quality of isometric tilt, icon rendering clarity)

## Verification

- Layout picker has 4+ options including "Isometric 2.5D": `cd e2e && npx playwright test tests/02-views/graph-isometric.spec.ts --reporter=list`
- Icon toggle button is present and functional: same E2E spec covers icon toggle
- Manual verification: open graph view in browser, select Isometric, click nodes, check popover positions, toggle icons

## Integration Closure

- Upstream surfaces consumed: `frontend/static/js/graph.js` (LAYOUT_REGISTRY, buildSemanticStyle, changeLayout, popover code), `backend/app/views/router.py` (available_layouts lists), `backend/app/templates/browser/graph_view.html` (toolbar HTML)
- New wiring introduced in this slice: isometric wrapper div in template, monkey-patch of `cy.renderer().findContainerClientCoords`, Lucide→SVG data URI pipeline
- What remains before the milestone is truly usable end-to-end: S03-S06 (calendar, map, federated SPARQL, app catalog) — no dependency on this slice

## Tasks

- [x] **T01: Add Lucide SVG icon toggle to graph nodes** `est:1.5h`
  - Why: Delivers ICON-01 — a toolbar button that switches graph nodes between shape-only and Lucide SVG icon display, with localStorage persistence
  - Files: `frontend/static/js/graph.js`, `frontend/static/css/views.css`, `backend/app/templates/browser/graph_view.html`
  - Do: Add memoized `_lucideSvgDataUri(iconName)` helper using `lucide.createElement()`. Add `iconMode` parameter to `buildSemanticStyle()` — when true, push `background-image` styles per type. Add icon toggle button to `.graph-toolbar` in template. Add `_setIconMode(cy, mode)` that writes to localStorage and rebuilds stylesheet. Wire theme changes to preserve icon mode. CSS: style the toggle button with flex-shrink:0 for the SVG icon per CLAUDE.md rules.
  - Verify: `rg -c '_lucideSvgDataUri\|_setIconMode\|sempkm_graph_icon_mode' frontend/static/js/graph.js` returns ≥ 3
  - Done when: Icon toggle button visible in graph toolbar; clicking it switches nodes between shapes and SVG icons; preference persists across page reload via localStorage

- [ ] **T02: Implement isometric 2.5D CSS transform layout with coordinate correction** `est:2.5h`
  - Why: Delivers ISO-01 and ISO-02 — the isometric layout with CSS 3D perspective and correct click/popover interaction
  - Files: `frontend/static/js/graph.js`, `frontend/static/css/views.css`, `backend/app/templates/browser/graph_view.html`, `backend/app/views/router.py`
  - Do: Add `.graph-isometric-wrapper` div around `#cy-container` in template. Add `_applyIsometricTransform(cy, container)` — wraps container, applies CSS 3D, monkey-patches `cy.renderer().findContainerClientCoords` to return untransformed coords via container's `clientWidth`/`clientHeight` and wrapper center. Add `_removeIsometricTransform(cy, container)` — removes CSS, restores original method. Add isometric entry to `LAYOUT_REGISTRY` that runs fcose first then applies transform. Fix `_showNodePopover` and `_showEdgePopover` to forward-transform coordinates through wrapper's CSS matrix when isometric is active. Add `{"name": "isometric", "label": "Isometric 2.5D"}` to BOTH `available_layouts` lists in router.py (line ~431 and line ~971). CSS: `.graph-isometric-wrapper` with perspective, transform-style, transition.
  - Verify: `rg -c '_applyIsometricTransform\|_removeIsometricTransform\|graph-isometric-wrapper' frontend/static/js/graph.js frontend/static/css/views.css` returns matches in both files; `rg -c 'isometric' backend/app/views/router.py` returns ≥ 2
  - Done when: Selecting "Isometric 2.5D" in layout picker tilts the graph into 3D perspective; clicking a node fires the correct tap event; popovers appear near the clicked node; switching to another layout removes the tilt cleanly

- [ ] **T03: E2E tests for isometric layout and icon toggle** `est:1h`
  - Why: Automated verification that both features are wired up and functional — covers layout picker option presence, icon toggle button presence, and basic interaction
  - Files: `e2e/tests/02-views/graph-isometric.spec.ts`, `e2e/helpers/selectors.ts`
  - Do: Add `iconToggle` and `isometricLayout` selectors to `SEL.views`. Write E2E spec: (1) graph view has "Isometric 2.5D" in layout picker options, (2) selecting isometric applies the CSS transform class, (3) icon toggle button is present, (4) clicking icon toggle applies background-image to nodes, (5) isometric + icon toggle combined. Follow existing graph-view.spec.ts patterns for opening a graph panel.
  - Verify: `cd e2e && npx playwright test tests/02-views/graph-isometric.spec.ts --reporter=list` — all tests pass or skip gracefully when no graph spec exists
  - Done when: E2E spec file exists with 4+ test cases; tests pass against running test stack

## Observability / Diagnostics

- **Console warnings:** `_lucideSvgDataUri()` logs `[graph] Lucide icon not found: <name>` when the lucide UMD doesn't have a matching PascalCase export, and `[graph] lucide UMD not loaded` if the CDN script failed. Both are console.warn — visible in browser DevTools.
- **Icon mode state inspection:** `localStorage.getItem('sempkm_graph_icon_mode')` returns `'icon'` or `'shape'` (or null for default). The toggle button has `.active` class when icon mode is on.
- **Isometric transform inspection (T02):** The wrapper div `.graph-isometric-wrapper` presence in DOM indicates isometric is active. CSS `transform` property is inspectable via DevTools.
- **Failure-path verification:** Open graph view with lucide CDN blocked → console shows `[graph] lucide UMD not loaded` warning → graph renders with shapes only (graceful degradation, no crash).

## Files Likely Touched

- `frontend/static/js/graph.js`
- `frontend/static/css/views.css`
- `backend/app/templates/browser/graph_view.html`
- `backend/app/views/router.py`
- `e2e/tests/02-views/graph-isometric.spec.ts`
- `e2e/helpers/selectors.ts`
