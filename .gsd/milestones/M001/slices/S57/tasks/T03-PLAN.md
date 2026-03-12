# T03: 57-spatial-canvas 03

**Slice:** S57 — **Milestone:** M001

## Description

Bulk drag-drop from nav tree to spatial canvas with auto-edge discovery.

Purpose: Enable users to select multiple objects in the nav tree and drop them onto the canvas as a group, automatically discovering and rendering the relationships between them. This is the key "drop a bunch of notes and instantly see how they connect" workflow.
Output: Modified workspace.js with getSelectedIris export, modified tree_children.html for multi-item drag payloads, new backend batch-edges endpoint, modified canvas.js with bulk drop handler and grid placement.

## Must-Haves

- [ ] "User can multi-select objects in the nav tree (shift/ctrl-click) and drag them to the canvas"
- [ ] "Dropped nodes appear in a 3-column grid layout at the drop point, snapped to 24px grid"
- [ ] "After dropping, edges between the dropped group are auto-discovered and rendered"
- [ ] "Duplicate nodes are silently skipped (no toast, no error)"
- [ ] "Dropping more than 20 nodes shows a confirmation dialog"

## Files

- `frontend/static/js/canvas.js`
- `frontend/static/js/workspace.js`
- `backend/app/canvas/router.py`
- `backend/app/canvas/schemas.py`
- `backend/app/templates/browser/tree_children.html`
