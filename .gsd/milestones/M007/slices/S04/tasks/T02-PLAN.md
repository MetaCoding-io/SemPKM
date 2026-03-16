---
estimated_steps: 5
estimated_files: 5
---

# T02: Inference button, Ontology Viewer accent, and horizontal graph

**Slice:** S04 — UI Polish & Consistency
**Milestone:** M007

## Description

Normalize the inference button on the admin Mental Models page to match sibling button sizing. Add blue/accent styling to the Ontology Viewer entry in the VIEWS explorer. Change the relationships graph from vertical `fcose` layout to horizontal `dagre` layout at full container width.

## Steps

1. **Normalize inference button in `models.html`** — Line ~89: the inference button is an `<a class="btn btn-warning btn-sm">` while siblings are `<button class="btn btn-* btn-sm">`. Change the `<a>` to a `<button>` element. The current `<a>` likely has an `href` or `onclick` — preserve the action behavior. If it navigates via `href`, convert to `onclick="window.location.href='...'"` on the `<button>`, or use a form submission pattern. Check what the `<a>` actually does before converting.

2. **Add accent class to Ontology Viewer in `views_explorer.html`** — Lines ~11-15: add a CSS class `view-leaf--accent` to the Ontology Viewer tree-leaf entry's clickable element (likely the `<span>` or `<div>` with the label text).

3. **Add `.view-leaf--accent` CSS rule** — In `workspace.css` (near the views explorer styles), add:
   ```css
   .view-leaf--accent {
       color: var(--color-accent);
   }
   .view-leaf--accent:hover {
       color: var(--color-accent-hover, var(--color-accent));
   }
   ```
   Check which CSS variable the project uses for its blue accent color — look for existing `--color-accent` usage, or find the actual variable name by searching `workspace.css` and `style.css` for accent/blue color definitions.

4. **Change Cytoscape layout to horizontal dagre in `model_ontology_diagram.html`** — Line ~118: find the Cytoscape layout configuration (currently `name: 'fcose'` or similar). Replace with:
   ```javascript
   layout: {
       name: 'dagre',
       rankDir: 'LR',
       nodeSep: 50,
       rankSep: 80
   }
   ```
   Dagre is already loaded via CDN in `base.html` (`dagre@0.8.5` + `cytoscape-dagre@2.5.0`). The workspace graph view already uses dagre in `graph.js` — use that as reference for options.

5. **Update `.ontology-cy-container` dimensions in `style.css`** — Line ~2051: change `height: 500px` to `height: 600px` (or use `min-height: 600px` for flexibility). Ensure `width: 100%` is set (or remove any max-width constraint). The container should fill the available width of the tab content area.

## Must-Haves

- [ ] Inference button renders at same height/alignment as Remove and Refresh buttons
- [ ] Ontology Viewer entry in VIEWS explorer displays in blue/accent color
- [ ] Relationships graph renders with horizontal left-to-right dagre layout
- [ ] Graph container fills full available width

## Verification

- Open http://localhost:3000/admin/mental-models — inference button (if visible) aligns with Remove/Refresh button siblings in height and vertical alignment
- Open workspace → VIEWS section in left sidebar — Ontology Viewer entry text is blue/accent colored
- Open admin → any model detail page → Relationships tab — graph renders horizontally (nodes flow left to right) and fills the container width
- No JS console errors on any of the above pages

## Inputs

- T01 completed (sidebar changes don't conflict, but same Docker stack is running)
- Research: dagre already available via CDN, `graph.js` uses dagre as reference
- Research: inference button is `<a>` among `<button>` siblings causing size mismatch

## Expected Output

- `backend/app/templates/admin/models.html` — inference button changed from `<a>` to `<button>` (or given explicit sizing)
- `backend/app/templates/browser/views_explorer.html` — Ontology Viewer entry has `view-leaf--accent` class
- `frontend/static/css/workspace.css` — `.view-leaf--accent` rule added
- `backend/app/templates/admin/model_ontology_diagram.html` — Cytoscape layout changed to dagre with `rankDir: 'LR'`
- `frontend/static/css/style.css` — `.ontology-cy-container` height/width updated for full-width horizontal graph

## Observability Impact

All changes are static HTML/CSS/template modifications with no server-side logic:
- **Inference button:** Inspect with DevTools — all three action buttons should be `<button>` elements with identical `offsetHeight` values.
- **Ontology Viewer accent:** Check `document.querySelector('.view-leaf--accent .tree-leaf-label')` — `getComputedStyle().color` should return the `--color-accent` value.
- **Dagre layout:** Visual inspection of the Relationships tab graph — nodes should flow left-to-right. Container dimensions: `document.querySelector('.ontology-cy-container').offsetHeight` should be ≥ 600px.
- No new runtime signals, logs, or persisted state. No failure modes introduced.
