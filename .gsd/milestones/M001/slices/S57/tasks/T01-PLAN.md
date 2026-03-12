# T01: 57-spatial-canvas 01

**Slice:** S57 — **Milestone:** M001

## Description

Snap-to-grid alignment, edge label polish, and keyboard navigation for the spatial canvas.

Purpose: Make the canvas feel precise and keyboard-accessible -- nodes align cleanly to the 24px grid, edge labels are readable, and users can navigate/manipulate nodes without a mouse.
Output: Modified canvas.js with snapToGrid function, keyboard handler, and selection state; updated workspace.css with focus ring and edge label background styling; Wave 0 E2E test stubs for all phase requirements.

## Must-Haves

- [ ] "Dragged nodes snap to 24px grid positions during drag"
- [ ] "Expanded neighbor nodes snap to 24px grid positions"
- [ ] "Arrow keys move the selected node by one grid step (24px)"
- [ ] "Shift+Arrow moves the selected node by 5 grid steps (120px)"
- [ ] "Tab/Shift+Tab cycles focus through nodes in spatial order (top-to-bottom, left-to-right)"
- [ ] "Escape deselects the current node (clears focus ring)"
- [ ] "Delete/Backspace removes the selected node immediately without confirmation"
- [ ] "Enter toggles neighbor expansion on the selected node"
- [ ] "Ctrl+S / Cmd+S saves the current canvas session"
- [ ] "Edge labels display between connected nodes with readable background"

## Files

- `frontend/static/js/canvas.js`
- `frontend/static/css/workspace.css`
- `e2e/tests/17-spatial-canvas/snap-to-grid.spec.ts`
- `e2e/tests/17-spatial-canvas/edge-labels.spec.ts`
- `e2e/tests/17-spatial-canvas/keyboard-nav.spec.ts`
- `e2e/tests/17-spatial-canvas/bulk-drop.spec.ts`
- `e2e/tests/17-spatial-canvas/wiki-link-edges.spec.ts`
