# S55: Browser Ui Polish

**Goal:** Add hover-reveal action buttons (refresh, plus) to the OBJECTS section header in the nav tree, and extend the command palette with per-type "Create X" entries.
**Demo:** Add hover-reveal action buttons (refresh, plus) to the OBJECTS section header in the nav tree, and extend the command palette with per-type "Create X" entries.

## Must-Haves


## Tasks

- [x] **T01: 55-browser-ui-polish 01** `est:4min`
  - Add hover-reveal action buttons (refresh, plus) to the OBJECTS section header in the nav tree, and extend the command palette with per-type "Create X" entries.

Purpose: Give users quick access to refresh the object list and create new objects without keyboard shortcuts, following the VS Code Explorer pattern.
Output: Modified workspace.html, workspace.js, workspace.css with header controls and command palette entries.
- [x] **T02: 55-browser-ui-polish 02** `est:3min`
  - Add multi-select (shift-click range, ctrl-click toggle) to the nav tree and bulk delete with a styled confirmation dialog. Create a backend endpoint for object deletion via the event store.

Purpose: Enable users to manage multiple objects efficiently -- select a batch and delete them in one action, with proper event-sourced audit trail.
Output: Modified tree_children.html, workspace.js, workspace.css, browser/router.py with multi-select + bulk delete.
- [x] **T03: 55-browser-ui-polish 03** `est:7min`
  - Add an expandable edge inspector to the Relations panel. Clicking a relation item expands it inline to show edge provenance (predicate QName, timestamp, author, source, event link). Add a backend endpoint for edge provenance queries. Add edge delete capability for user-asserted edges. Also define a reusable `showConfirmDialog` function (used here for edge delete, and later by Plan 55-02 for bulk delete).

Purpose: Give users visibility into edge metadata and provenance without leaving the current context, and enable precise edge management.
Output: Modified properties.html, workspace.js, workspace.css, browser/router.py with edge inspector and provenance API.
- [x] **T04: 55-browser-ui-polish 04** `est:11min`
  - Add side-by-side raw/rendered preview to the VFS browser, polish file operations with dirty indicators, loading states, consistent Lucide icons, and add inline WebDAV help.

Purpose: Make the VFS file browser a productive editing environment with live preview and professional UX polish.
Output: Modified vfs-browser.js, vfs-browser.css, vfs_browser.html with preview, polish, and help.

## Files Likely Touched

- `backend/app/templates/browser/workspace.html`
- `backend/app/templates/browser/nav_tree.html`
- `frontend/static/js/workspace.js`
- `frontend/static/css/workspace.css`
- `backend/app/templates/browser/tree_children.html`
- `backend/app/browser/router.py`
- `frontend/static/js/workspace.js`
- `frontend/static/css/workspace.css`
- `backend/app/browser/router.py`
- `backend/app/templates/browser/properties.html`
- `frontend/static/js/workspace.js`
- `frontend/static/css/workspace.css`
- `frontend/static/js/vfs-browser.js`
- `frontend/static/css/vfs-browser.css`
- `backend/app/templates/browser/vfs_browser.html`
