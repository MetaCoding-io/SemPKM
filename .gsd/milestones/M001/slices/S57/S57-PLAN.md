# S57: Spatial Canvas

**Goal:** Snap-to-grid alignment, edge label polish, and keyboard navigation for the spatial canvas.
**Demo:** Snap-to-grid alignment, edge label polish, and keyboard navigation for the spatial canvas.

## Must-Haves


## Tasks

- [x] **T01: 57-spatial-canvas 01** `est:4min`
  - Snap-to-grid alignment, edge label polish, and keyboard navigation for the spatial canvas.

Purpose: Make the canvas feel precise and keyboard-accessible -- nodes align cleanly to the 24px grid, edge labels are readable, and users can navigate/manipulate nodes without a mouse.
Output: Modified canvas.js with snapToGrid function, keyboard handler, and selection state; updated workspace.css with focus ring and edge label background styling; Wave 0 E2E test stubs for all phase requirements.
- [x] **T02: 57-spatial-canvas 02** `est:4min`
  - Wiki-link edge rendering with distinct styling and ghost nodes for unresolved targets.

Purpose: Parse `[[wiki-link]]` syntax in node markdown bodies and render them as visually distinct edges (dashed green) on the canvas. When a wiki-link target is not on the canvas, show a ghost node stub that can be clicked to add the full node.
Output: Modified canvas.js with wiki-link pre-processing and ghost node logic, new backend endpoint for title-to-IRI resolution, CSS for dashed green edges and ghost node styling.
- [x] **T03: 57-spatial-canvas 03** `est:3min`
  - Bulk drag-drop from nav tree to spatial canvas with auto-edge discovery.

Purpose: Enable users to select multiple objects in the nav tree and drop them onto the canvas as a group, automatically discovering and rendering the relationships between them. This is the key "drop a bunch of notes and instantly see how they connect" workflow.
Output: Modified workspace.js with getSelectedIris export, modified tree_children.html for multi-item drag payloads, new backend batch-edges endpoint, modified canvas.js with bulk drop handler and grid placement.

## Files Likely Touched

- `frontend/static/js/canvas.js`
- `frontend/static/css/workspace.css`
- `e2e/tests/17-spatial-canvas/snap-to-grid.spec.ts`
- `e2e/tests/17-spatial-canvas/edge-labels.spec.ts`
- `e2e/tests/17-spatial-canvas/keyboard-nav.spec.ts`
- `e2e/tests/17-spatial-canvas/bulk-drop.spec.ts`
- `e2e/tests/17-spatial-canvas/wiki-link-edges.spec.ts`
- `frontend/static/js/canvas.js`
- `frontend/static/css/workspace.css`
- `backend/app/canvas/router.py`
- `backend/app/canvas/schemas.py`
- `frontend/static/js/canvas.js`
- `frontend/static/js/workspace.js`
- `backend/app/canvas/router.py`
- `backend/app/canvas/schemas.py`
- `backend/app/templates/browser/tree_children.html`
