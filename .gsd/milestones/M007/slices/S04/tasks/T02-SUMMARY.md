---
id: T02
parent: S04
milestone: M007
provides:
  - Inference button normalized as <button> matching sibling size
  - Ontology Viewer accent-colored in VIEWS explorer
  - Horizontal dagre layout for relationships graph
  - 600px min-height graph container at full width
key_files:
  - backend/app/templates/admin/models.html
  - backend/app/templates/browser/views_explorer.html
  - frontend/static/css/workspace.css
  - backend/app/templates/admin/model_ontology_diagram.html
  - frontend/static/css/style.css
key_decisions:
  - Converted inference <a> to <button> preserving htmx navigation (hx-get already present, href was fallback only)
  - Targeted .tree-leaf-label inside .view-leaf--accent so icon color stays muted while label goes accent
  - Used min-height instead of fixed height on .ontology-cy-container for flexibility
patterns_established:
  - view-leaf--accent class pattern for highlighting specific view entries
observability_surfaces:
  - none
duration: ~25 min
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Inference button, Ontology Viewer accent, and horizontal graph

**Normalized inference button to `<button>`, added accent color to Ontology Viewer, and switched relationships graph to horizontal dagre layout.**

## What Happened

Five targeted edits across 5 files:

1. **models.html** — Changed inference `<a class="btn btn-warning btn-sm">` to `<button>` with same htmx attributes (`hx-get`, `hx-target`, `hx-swap`, `hx-push-url`). The `href` was redundant since htmx was handling navigation. All three action buttons (Inference, Refresh, Remove) now render at identical 32px height.

2. **views_explorer.html** — Added `view-leaf--accent` class to the Ontology Viewer `<a>` element.

3. **workspace.css** — Added `.view-leaf--accent .tree-leaf-label` rule with `color: var(--color-accent)` and hover state using `--color-accent-hover`. Scoped to `.tree-leaf-label` so the icon color stays `--color-text-muted`.

4. **model_ontology_diagram.html** — Replaced `fcose` layout with `dagre` layout using `rankDir: 'LR'`, `nodeSep: 50`, `rankSep: 80`. Preserved `animate: true` and `animationDuration: 600`.

5. **style.css** — Changed `.ontology-cy-container` from `height: 500px` to `min-height: 600px`. Width was already `100%`.

## Verification

- **Inference button:** Verified all three buttons are `<button>` tags at 32px height via `document.querySelectorAll('button')` — all matching `offsetHeight: 32`.
- **Ontology Viewer accent:** `document.querySelector('.view-leaf--accent .tree-leaf-label')` computed color is `rgb(13, 148, 136)` (teal accent). Visual screenshot confirms distinct color.
- **Dagre layout:** Relationships tab shows nodes flowing left-to-right (Note → Concept/Project → Person). Container dimensions: 860×600px.
- **No new JS errors** on admin/models, workspace/browser, or model detail pages. Pre-existing "Invalid or unexpected token" and "#nav-pane" errors are unrelated to this task.

### Slice Verification Status (T02 of 2)

- [x] Left sidebar: all 5 section chevrons render as Lucide SVG icons (T01)
- [x] OBJECTS section: refresh and plus buttons visible without hovering (T01)
- [x] DASHBOARDS section: + button in header; no "New Dashboard" tree-leaf (T01)
- [x] WORKFLOWS section: + button in header; no "New Workflow" tree-leaf (T01)
- [x] Admin → Mental Models: inference button same height/alignment as Remove and Refresh
- [x] VIEWS section: Ontology Viewer entry has blue/accent color
- [x] Admin → Model detail → Relationships tab: graph renders horizontally with dagre layout at full container width

## Diagnostics

- Inference button alignment: `[...document.querySelectorAll('td button.btn-sm')].map(b => ({text: b.textContent.trim(), tag: b.tagName, h: b.offsetHeight}))`
- Accent class: `document.querySelector('.view-leaf--accent .tree-leaf-label')?.textContent` + `getComputedStyle(...).color`
- Container size: `document.querySelector('.ontology-cy-container')?.offsetHeight` — should be ≥ 600

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/templates/admin/models.html` — Changed inference `<a>` to `<button>` with same htmx attributes
- `backend/app/templates/browser/views_explorer.html` — Added `view-leaf--accent` class to Ontology Viewer entry
- `frontend/static/css/workspace.css` — Added `.view-leaf--accent` CSS rule with accent color and hover state
- `backend/app/templates/admin/model_ontology_diagram.html` — Changed Cytoscape layout from fcose to dagre with LR direction
- `frontend/static/css/style.css` — Changed `.ontology-cy-container` from fixed 500px height to 600px min-height
