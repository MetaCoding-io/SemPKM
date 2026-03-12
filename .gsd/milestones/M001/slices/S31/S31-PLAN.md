# S31: Object View Redesign

**Goal:** Redesign the object tab so the Markdown body is the primary content in both view and edit modes, with RDF properties hidden behind a collapsible toggle badge in the toolbar.
**Demo:** Redesign the object tab so the Markdown body is the primary content in both view and edit modes, with RDF properties hidden behind a collapsible toggle badge in the toolbar.

## Must-Haves


## Tasks

- [x] **T01: 31-object-view-redesign 01** `est:3min`
  - Redesign the object tab so the Markdown body is the primary content in both view and edit modes, with RDF properties hidden behind a collapsible toggle badge in the toolbar. Implement the properties toggle with CSS grid-template-rows animation, localStorage per-object IRI persistence, and shared collapse state between read and edit faces.

Purpose: Fulfill VIEW-01 — users see content first, not metadata. Properties are one click away via a badge that shows "N properties".
Output: Restructured object_read.html, object_tab.html, workspace.css additions, and workspace.js integration.
- [x] **T02: 31-object-view-redesign 02** `est:8min`
  - Human verification of the object view redesign. Confirm body-first layout, properties toggle, localStorage persistence, empty-body behavior, edit mode layout, and 3D flip animation all work correctly in the browser.

Purpose: Visual and functional verification that cannot be done through automated testing alone — CSS transitions, layout correctness, animation integrity.
Output: Verified phase completion or bug list for gap closure.

## Files Likely Touched

- `backend/app/templates/browser/object_read.html`
- `backend/app/templates/browser/object_tab.html`
- `frontend/static/css/workspace.css`
- `frontend/static/js/workspace.js`
