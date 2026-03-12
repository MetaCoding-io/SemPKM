# T02: 55-browser-ui-polish 02

**Slice:** S55 — **Milestone:** M001

## Description

Add multi-select (shift-click range, ctrl-click toggle) to the nav tree and bulk delete with a styled confirmation dialog. Create a backend endpoint for object deletion via the event store.

Purpose: Enable users to manage multiple objects efficiently -- select a batch and delete them in one action, with proper event-sourced audit trail.
Output: Modified tree_children.html, workspace.js, workspace.css, browser/router.py with multi-select + bulk delete.

## Must-Haves

- [ ] "User can shift-click to select a range of objects in the nav tree"
- [ ] "User can ctrl-click to toggle individual object selection"
- [ ] "Selected objects are highlighted with a distinct background color"
- [ ] "OBJECTS header shows selection count badge and trash icon when items are selected"
- [ ] "Regular click still opens tab as before and clears selection"
- [ ] "Clicking trash icon shows a confirmation modal listing selected objects"
- [ ] "Confirming delete removes all selected objects and clears selection"
- [ ] "Delete confirmation is a styled HTML modal (not browser confirm())"

## Files

- `backend/app/templates/browser/tree_children.html`
- `backend/app/browser/router.py`
- `frontend/static/js/workspace.js`
- `frontend/static/css/workspace.css`
