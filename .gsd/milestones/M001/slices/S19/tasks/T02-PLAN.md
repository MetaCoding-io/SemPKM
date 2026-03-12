# T02: 19-bug-fixes-and-e2e-test-hardening 02

**Slice:** S19 — **Milestone:** M001

## Description

Fix all 6 user-discovered UI bugs and add tag pill display and nav tree + graph node tooltip improvements.

Purpose: These are visible, user-facing regressions and missing polish items that affect daily use. Each fix is surgical — targeted to the exact function, template section, or CSS rule causing the issue.
Output: workspace-layout.js with tab active guard and split fix; workspace.js with docs/tutorial/autocomplete/edit-button/tooltip fixes; graph.js with confirmed graph-style node hover tooltip; object_read.html with tag pill rendering in read view; forms/_field.html with tag pill styling in edit view; tree_children.html with hover tooltip; workspace.css with .tag-pill styles and tooltip CSS.

## Must-Haves

- [ ] "Clicking the Docs & Tutorials nav link opens the docs tab correctly"
- [ ] "Tutorial buttons in the docs tab launch the Driver.js tours"
- [ ] "Clicking an already-active tab is a no-op — tab content does not reload"
- [ ] "Splitting a tab (Ctrl+\\) keeps original tab content in original group and loads new content in new group"
- [ ] "Edit/Done toggle works on the first click — no second-click required"
- [ ] "Autocomplete dropdown for reference properties appears and is selectable"
- [ ] "model:basic-pkm:tags values render as #Label pill elements in both read-only and edit form views"
- [ ] "Nav tree item hover shows a tooltip with type label and object label in graph-style format"
- [ ] "Graph node hover shows a tooltip with type label and object label in graph-style format"

## Files

- `frontend/static/js/workspace-layout.js`
- `frontend/static/js/workspace.js`
- `frontend/static/js/graph.js`
- `frontend/static/css/workspace.css`
- `backend/app/templates/browser/object_read.html`
- `backend/app/templates/forms/_field.html`
- `backend/app/templates/browser/tree_children.html`
- `backend/app/templates/browser/docs_page.html`
