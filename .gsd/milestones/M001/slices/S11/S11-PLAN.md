# S11: Read Only Object View

**Goal:** Build the read-only object view backend, template, and styling so that objects display a polished property table and rendered Markdown body by default.
**Demo:** Build the read-only object view backend, template, and styling so that objects display a polished property table and rendered Markdown body by default.

## Must-Haves


## Tasks

- [x] **T01: 11-read-only-object-view 01** `est:4min`
  - Build the read-only object view backend, template, and styling so that objects display a polished property table and rendered Markdown body by default.

Purpose: Transform the object viewing experience from edit-by-default to read-by-default, giving users a clean, document-like presentation of their data.
Output: Enhanced backend endpoint, new read-only template, flip container structure, Markdown rendering JS, and all CSS for the read-only presentation.
- [x] **T02: 11-read-only-object-view 02** `est:interactive-session`
  - Implement the interactive mode toggle (Edit/Done button, Ctrl+E shortcut, unsaved changes confirmation, deferred editor initialization) and the body editor maximize/restore toggle.

Purpose: Complete the read/edit mode switching UX with smooth flip animation and give users a way to maximize the body editor for focused writing.
Output: Working mode toggle with keyboard shortcut, flip animation, unsaved changes protection, and body editor maximize/restore.

## Files Likely Touched

- `backend/app/browser/router.py`
- `backend/app/templates/base.html`
- `backend/app/templates/browser/object_tab.html`
- `backend/app/templates/browser/object_read.html`
- `frontend/static/js/markdown-render.js`
- `frontend/static/css/workspace.css`
- `frontend/static/js/workspace.js`
- `backend/app/templates/browser/object_tab.html`
- `frontend/static/css/workspace.css`
