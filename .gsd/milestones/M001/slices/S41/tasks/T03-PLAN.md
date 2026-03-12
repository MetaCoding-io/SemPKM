# T03: 41-gap-closure-rules-flip-vfs 03

**Slice:** S41 — **Milestone:** M001

## Description

Add an in-app VFS browser view as a dockview tab accessible from the sidebar.

Purpose: Users currently need an external WebDAV client to browse the virtual filesystem. This plan adds a tree-view browser inside the workspace, following the established special-panel pattern (settings, docs, canvas). The tree shows installed models -> types -> objects, with click-to-open for objects.
Output: Backend route, template, sidebar entry, and JS tab function.

## Must-Haves

- [ ] "Users can open an in-app VFS browser view as a dockview tab"
- [ ] "VFS browser shows the virtual filesystem tree (model -> type -> objects)"
- [ ] "VFS browser is accessible from sidebar navigation"
- [ ] "Clicking an object in the VFS tree opens it in a workspace tab"

## Files

- `backend/app/browser/router.py`
- `backend/app/templates/browser/vfs_browser.html`
- `backend/app/templates/components/_sidebar.html`
- `frontend/static/js/workspace.js`
- `frontend/static/css/workspace.css`
