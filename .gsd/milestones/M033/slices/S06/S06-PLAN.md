# S06: Graph View Icon Toggle

**Goal:** A toolbar toggle button on graph views switches nodes between abstract Cytoscape shapes and Lucide SVG icon rendering, with state persisted in localStorage.
**Demo:** User clicks the icon toggle button in the graph toolbar. Nodes switch from shape-only to Lucide icon overlays matching each type's configured icon. Clicking again reverts to shapes. Refreshing the page preserves the toggle state.

## Must-Haves

- Toolbar button in `.graph-toolbar` matching existing button style (`.graph-fit-btn` pattern)
- Active/inactive visual state on the toggle button
- SVG data URI construction from Lucide icons for each node type
- Icon styles injected into `buildSemanticStyle()` when toggle is active
- Isometric layer plane compound nodes (`_isometricLayer`) excluded from icon rendering
- Toggle state persisted in `localStorage` under `sempkm_graph_icons`
- Theme switch (`switchGraphTheme`) respects current icon toggle state

## Verification

- `grep -q "toggleGraphIcons" frontend/static/js/graph.js` — function exists
- `grep -q "sempkm_graph_icons" frontend/static/js/graph.js` — localStorage key used
- `grep -q "graph-icon-toggle-btn" backend/app/templates/browser/graph_view.html` — button in template
- `grep -q "graph-icon-toggle-btn" frontend/static/css/views.css` — button styled
- `grep -q "_isometricLayer" frontend/static/js/graph.js` — layer planes excluded from icons
- `grep -q "background-image" frontend/static/js/graph.js` — Cytoscape icon style property used
- `grep -q "console.warn" frontend/static/js/graph.js` — diagnostic logging present for icon failures

## Observability / Diagnostics

- `console.warn('[graph] ...')` emitted when `_buildIconDataUri()` fails for a specific icon name — surfaces Lucide lookup failures
- `console.warn('[graph] toggleGraphIcons called but no graph instance exists')` — diagnoses toggle attempts before graph init
- `localStorage.getItem('sempkm_graph_icons')` — inspectable via DevTools to verify persisted state
- `.graph-icon-toggle-btn.active` class presence — visual indicator of current toggle state, inspectable via DOM
- `_iconDataUriCache` is module-scoped but cache hits/misses are implicit; no failure state is silent — all failures return `null` and log warnings

## Tasks

- [x] **T01: Implement graph icon toggle button, SVG rendering, and localStorage persistence** `est:1h`
  - Why: This is the entire feature — a toolbar button, icon style injection via Cytoscape's `background-image`, and localStorage persistence. All changes are in 3 files with no backend work.
  - Files: `frontend/static/js/graph.js`, `backend/app/templates/browser/graph_view.html`, `frontend/static/css/views.css`
  - Do: (1) Add `toggleGraphIcons()` function to graph.js that builds SVG data URIs from Lucide icons via `lucide.createIcons()`, injects them as `background-image` styles per node type, and persists state to localStorage. (2) Extend `buildSemanticStyle()` to conditionally include icon background-image styles when toggle is active. (3) Add toggle button to graph_view.html toolbar. (4) Add button CSS with active state indicator. (5) Exclude `_isometricLayer` compound nodes from icon styles. (6) Fix missing comma between filtered-out and isometric style entries in the styles array (~line 123).
  - Verify: Open graph view in browser, click toggle button, verify icons appear on nodes and persist across reload
  - Done when: All 6 grep checks in Verification pass, icon toggle works visually, theme switching preserves icon state

## Files Likely Touched

- `frontend/static/js/graph.js`
- `backend/app/templates/browser/graph_view.html`
- `frontend/static/css/views.css`
