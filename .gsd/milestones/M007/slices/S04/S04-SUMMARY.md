---
id: S04
parent: M007
milestone: M007
provides:
  - Lucide SVG chevrons on all 6 left sidebar explorer sections (matching right sidebar)
  - Always-visible OBJECTS header action buttons (refresh, plus)
  - Plus-buttons on DASHBOARDS and WORKFLOWS section headers
  - Removed "New Dashboard" and "New Workflow" tree-leaf entries
  - Inference button normalized as <button> matching sibling sizing
  - Ontology Viewer accent-colored in VIEWS explorer
  - Horizontal dagre layout for relationships graph at 600px min-height
requires: []
affects: []
key_files:
  - backend/app/templates/browser/workspace.html
  - backend/app/templates/browser/partials/favorites_section.html
  - backend/app/templates/browser/partials/shared_nav_section.html
  - backend/app/templates/browser/partials/shared_nav_content.html
  - backend/app/templates/browser/dashboard_explorer.html
  - backend/app/templates/browser/workflow_explorer.html
  - backend/app/templates/admin/models.html
  - backend/app/templates/browser/views_explorer.html
  - backend/app/templates/admin/model_ontology_diagram.html
  - frontend/static/css/workspace.css
  - frontend/static/css/style.css
key_decisions:
  - Converted inference <a> to <button> preserving htmx navigation (hx-get already handled routing, href was redundant)
  - Scoped .view-leaf--accent to .tree-leaf-label so icon color stays muted while label goes accent
  - Used min-height instead of fixed height on .ontology-cy-container for flexibility
  - Changed opacity model from hover-reveal (0 → 1) to always-visible (1) for header actions
patterns_established:
  - All left sidebar section headers now use Lucide chevron-right SVG icons consistently with right sidebar
  - view-leaf--accent CSS class pattern for highlighting specific view entries in explorer
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M007/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M007/slices/S04/tasks/T02-SUMMARY.md
duration: ~55 min
verification_result: passed
completed_at: 2026-03-15
---

# S04: UI Polish & Consistency

**Fixed 6 UI inconsistencies: Lucide sidebar chevrons, always-visible OBJECTS buttons, DASHBOARDS/WORKFLOWS header plus-buttons, normalized inference button, accent Ontology Viewer, horizontal relationships graph.**

## What Happened

Two tasks, pure CSS/HTML template work with no backend logic changes.

**T01 (sidebar):** Replaced text chevrons (`&#9656;`) with `<i data-lucide="chevron-right">` across 7 templates — workspace.html (4 instances), favorites_section.html, shared_nav_section.html, and shared_nav_content.html (discovered during verification as the htmx replacement template). Restyled `.explorer-section-chevron` CSS from text sizing to SVG sizing (12px, stroke: currentColor, flex-shrink: 0). Updated rotation selector for `.explorer-section.expanded` class. Changed `.explorer-header-actions` from opacity: 0 to opacity: 1 for always-visible buttons. Added plus-button spans to DASHBOARDS and WORKFLOWS headers following the OBJECTS pattern. Removed "New Dashboard" and "New Workflow" tree-leaf entries since that functionality moved to header buttons.

**T02 (admin/views):** Changed inference `<a>` to `<button>` on admin models page — htmx attributes preserved, `href` was redundant. Added `view-leaf--accent` class to Ontology Viewer entry with CSS rule targeting `.tree-leaf-label` for accent color. Switched relationships graph from `fcose` to `dagre` layout with `rankDir: 'LR'` for horizontal rendering. Changed `.ontology-cy-container` from fixed 500px height to 600px min-height.

## Verification

All 6 UIPOL-01 items verified via browser testing:

1. **Chevrons:** 6/6 sidebar sections render SVG chevrons (confirmed tagName === 'svg'). Rotation works on expand/collapse via `.expanded` class.
2. **OBJECTS buttons:** Header actions opacity is 1 at rest — visible without hover.
3. **DASHBOARDS + button:** Opens builder tab. No "New Dashboard" tree-leaf in expanded content.
4. **WORKFLOWS + button:** Opens builder tab. No "New Workflow" tree-leaf in expanded content.
5. **Inference button:** All three admin buttons (Inference, Refresh, Remove) are `<button>` elements at identical 32px height.
6. **Ontology Viewer accent:** `.view-leaf--accent .tree-leaf-label` computed color is teal accent.
7. **Relationships graph:** Dagre layout renders left-to-right at 860×600px container.

9/9 browser assertions passed across both tasks.

## Requirements Validated

- UIPOL-01 — All 6 items from user review feedback verified: sidebar chevrons match right sidebar, OBJECTS buttons always visible, DASHBOARDS/WORKFLOWS use header plus-signs (no tree-leaf entries), inference button normalized, Ontology Viewer blue, relationships graph horizontal full-width.

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- **shared_nav_content.html** required an additional chevron replacement not in the plan. This template is the htmx response that replaces shared_nav_section.html — without fixing both, the SHARED section chevron reverted to `<span>` after server response loaded. 7 files modified instead of the planned 6.

## Known Limitations

- OBJECTS header action buttons (refresh, plus) are slightly clipped at the right edge when the sidebar is narrow — pre-existing layout constraint, not introduced by this slice.

## Follow-ups

- none

## Files Created/Modified

- `backend/app/templates/browser/workspace.html` — 4 chevron replacements, 2 new header action spans (DASHBOARDS/WORKFLOWS)
- `backend/app/templates/browser/partials/favorites_section.html` — 1 chevron replacement
- `backend/app/templates/browser/partials/shared_nav_section.html` — 1 chevron replacement
- `backend/app/templates/browser/partials/shared_nav_content.html` — 1 chevron replacement (htmx response template)
- `backend/app/templates/browser/dashboard_explorer.html` — "New Dashboard" tree-leaf removed
- `backend/app/templates/browser/workflow_explorer.html` — "New Workflow" tree-leaf removed
- `backend/app/templates/admin/models.html` — inference `<a>` → `<button>` with same htmx attrs
- `backend/app/templates/browser/views_explorer.html` — `view-leaf--accent` class on Ontology Viewer
- `frontend/static/css/workspace.css` — chevron SVG styling, rotation selector, opacity: 1, accent class
- `backend/app/templates/admin/model_ontology_diagram.html` — fcose → dagre layout with LR direction
- `frontend/static/css/style.css` — `.ontology-cy-container` height: 500px → min-height: 600px

## Forward Intelligence

### What the next slice should know
- All left sidebar explorer sections now follow a consistent pattern: Lucide chevron-right SVG + JS `.expanded` class toggle + optional `explorer-header-actions` span in the header. New sections should follow this pattern.

### What's fragile
- shared_nav_content.html is easy to miss — it's the htmx response template that replaces shared_nav_section.html. Any future changes to the SHARED section header need to update both files.

### Authoritative diagnostics
- `document.querySelectorAll('.explorer-section-chevron').forEach(e => console.log(e.tagName, e.closest('.explorer-section')?.id))` — all should log `svg` with section IDs.
- `getComputedStyle(document.querySelector('#section-objects .explorer-header-actions')).opacity` — should be `'1'`.

### What assumptions changed
- Plan assumed 6 files needed chevron changes — actually 7 due to shared_nav_content.html htmx template.
