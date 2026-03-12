# T01: 31-object-view-redesign 01

**Slice:** S31 — **Milestone:** M001

## Description

Redesign the object tab so the Markdown body is the primary content in both view and edit modes, with RDF properties hidden behind a collapsible toggle badge in the toolbar. Implement the properties toggle with CSS grid-template-rows animation, localStorage per-object IRI persistence, and shared collapse state between read and edit faces.

Purpose: Fulfill VIEW-01 — users see content first, not metadata. Properties are one click away via a badge that shows "N properties".
Output: Restructured object_read.html, object_tab.html, workspace.css additions, and workspace.js integration.

## Must-Haves

- [ ] "Opening any object tab shows the rendered Markdown body immediately without properties visible"
- [ ] "User clicks a 'N properties' toggle badge and the full property list expands inline without a page reload"
- [ ] "User collapses properties, reloads the page, and reopens the same object — properties remain collapsed"
- [ ] "When an object has no Markdown body, properties auto-expand by default"
- [ ] "The existing CSS 3D flip to edit mode is unaffected and still reachable from the view header"

## Files

- `backend/app/templates/browser/object_read.html`
- `backend/app/templates/browser/object_tab.html`
- `frontend/static/css/workspace.css`
- `frontend/static/js/workspace.js`
