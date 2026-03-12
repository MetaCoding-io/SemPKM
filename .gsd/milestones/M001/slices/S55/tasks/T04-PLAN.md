# T04: 55-browser-ui-polish 04

**Slice:** S55 — **Milestone:** M001

## Description

Add side-by-side raw/rendered preview to the VFS browser, polish file operations with dirty indicators, loading states, consistent Lucide icons, and add inline WebDAV help.

Purpose: Make the VFS file browser a productive editing environment with live preview and professional UX polish.
Output: Modified vfs-browser.js, vfs-browser.css, vfs_browser.html with preview, polish, and help.

## Must-Haves

- [ ] "VFS browser shows side-by-side raw editor and rendered markdown preview"
- [ ] "Preview pane is toggled via a button in the file tab bar (default off)"
- [ ] "Preview updates live as user types in the editor (debounced)"
- [ ] "VFS file tabs show a dirty indicator dot when unsaved"
- [ ] "Saving shows a brief 'Saved' flash indicator"
- [ ] "Edit/read toggle uses Lucide lock/unlock icons instead of text"
- [ ] "Loading states show spinner for tree, file content, and save operations"
- [ ] "Error feedback shown as toast or inline for save failures"
- [ ] "VFS browser has inline help about connecting OS to WebDAV endpoint"

## Files

- `frontend/static/js/vfs-browser.js`
- `frontend/static/css/vfs-browser.css`
- `backend/app/templates/browser/vfs_browser.html`
