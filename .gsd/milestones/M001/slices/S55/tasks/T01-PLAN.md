# T01: 55-browser-ui-polish 01

**Slice:** S55 — **Milestone:** M001

## Description

Add hover-reveal action buttons (refresh, plus) to the OBJECTS section header in the nav tree, and extend the command palette with per-type "Create X" entries.

Purpose: Give users quick access to refresh the object list and create new objects without keyboard shortcuts, following the VS Code Explorer pattern.
Output: Modified workspace.html, workspace.js, workspace.css with header controls and command palette entries.

## Must-Haves

- [ ] "OBJECTS section header shows refresh and plus buttons on hover"
- [ ] "Clicking refresh reloads the nav tree and collapses all expanded type nodes"
- [ ] "Clicking plus opens the command palette"
- [ ] "Command palette has per-type Create entries (Create Note, Create Project, etc.)"
- [ ] "Typing 'create' in the command palette shows all per-type create entries"
- [ ] "Selecting a create entry opens a create form in a dockview tab"

## Files

- `backend/app/templates/browser/workspace.html`
- `backend/app/templates/browser/nav_tree.html`
- `frontend/static/js/workspace.js`
- `frontend/static/css/workspace.css`
