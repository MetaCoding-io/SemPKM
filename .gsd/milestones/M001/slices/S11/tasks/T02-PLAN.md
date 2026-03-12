# T02: 11-read-only-object-view 02

**Slice:** S11 — **Milestone:** M001

## Description

Implement the interactive mode toggle (Edit/Done button, Ctrl+E shortcut, unsaved changes confirmation, deferred editor initialization) and the body editor maximize/restore toggle.

Purpose: Complete the read/edit mode switching UX with smooth flip animation and give users a way to maximize the body editor for focused writing.
Output: Working mode toggle with keyboard shortcut, flip animation, unsaved changes protection, and body editor maximize/restore.

## Must-Haves

- [ ] "Clicking the Edit button flips the card with a horizontal 3D animation to reveal the edit form and CodeMirror editor"
- [ ] "Clicking the Done button flips back to read-only mode; if there are unsaved changes, a confirmation dialog asks before discarding"
- [ ] "Pressing Ctrl+E toggles between read-only and edit mode"
- [ ] "Newly created objects open directly in edit mode (no flip needed)"
- [ ] "In edit mode, a maximize/restore toggle button gives the CodeMirror editor 100% of the object tab area or restores the previous form/editor split ratio"

## Files

- `frontend/static/js/workspace.js`
- `backend/app/templates/browser/object_tab.html`
- `frontend/static/css/workspace.css`
