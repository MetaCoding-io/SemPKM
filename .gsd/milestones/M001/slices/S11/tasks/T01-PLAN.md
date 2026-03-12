# T01: 11-read-only-object-view 01

**Slice:** S11 — **Milestone:** M001

## Description

Build the read-only object view backend, template, and styling so that objects display a polished property table and rendered Markdown body by default.

Purpose: Transform the object viewing experience from edit-by-default to read-by-default, giving users a clean, document-like presentation of their data.
Output: Enhanced backend endpoint, new read-only template, flip container structure, Markdown rendering JS, and all CSS for the read-only presentation.

## Must-Haves

- [ ] "Opening an existing object via the explorer shows a read-only property table with bold labels and formatted values, not the edit form"
- [ ] "Empty optional properties are hidden in read-only mode"
- [ ] "The Markdown body renders as styled HTML with syntax-highlighted code blocks below a horizontal rule separator"
- [ ] "Reference property values display as clickable pill/badges with a colored dot and the resolved object name"
- [ ] "Hovering a reference pill shows a tooltip with the linked object's type and name (e.g., 'Project: My Project')"
- [ ] "Clicking a reference pill opens the target object in a new tab"
- [ ] "Dates display as human-readable format (e.g., Feb 23, 2026), booleans as check/x icons, URIs as clickable links"

## Files

- `backend/app/browser/router.py`
- `backend/app/templates/base.html`
- `backend/app/templates/browser/object_tab.html`
- `backend/app/templates/browser/object_read.html`
- `frontend/static/js/markdown-render.js`
- `frontend/static/css/workspace.css`
