# S04: UI Polish & Consistency — Research

**Date:** 2026-03-15
**Covers:** UIPOL-01

## Summary

Straightforward CSS/template work. All 6 items in UIPOL-01 are independent and touch known files with established patterns. No new technology, no risky integration. The right sidebar already implements the target chevron pattern (Lucide `chevron-right` SVG) — the left sidebar just needs to match it. Dashboard/workflow "New X" entries already exist as tree-leaves — they move to header plus-buttons following the OBJECTS section pattern. The inference button is an `<a>` tag among `<button>` siblings causing size mismatch. The relationships graph uses `fcose` layout with a fixed 500px height container.

## Recommendation

Six independent CSS/template changes, all safe to parallelize into a single task or two small tasks. No backend Python changes needed. Changes touch: `workspace.html`, `favorites_section.html`, `shared_nav_section.html`, `views_explorer.html`, `dashboard_explorer.html`, `workflow_explorer.html`, `model_ontology_diagram.html`, `models.html`, `workspace.css`, and `style.css`.

## Implementation Landscape

### Key Files

- `backend/app/templates/browser/workspace.html` — Left sidebar sections. Lines 32, 65, 76, 90 have `<span class="explorer-section-chevron">&#9656;</span>` that need to become `<i data-lucide="chevron-right" class="explorer-section-chevron"></i>`. Also: DASHBOARDS (line 77) and WORKFLOWS (line 91) headers need plus-button added to a new `explorer-header-actions` span.
- `backend/app/templates/browser/partials/favorites_section.html` — Line 9: same chevron replacement.
- `backend/app/templates/browser/partials/shared_nav_section.html` — Line 12: same chevron replacement.
- `frontend/static/css/workspace.css` — Lines 98-107: `.explorer-section-chevron` CSS currently styles a text character (font-size, width, text-align). Needs to change to SVG sizing (width/height 12px, flex-shrink:0, stroke:currentColor) matching `.right-section-chevron` at line 2032. Lines 119-131: `.explorer-header-actions` has `opacity: 0` — change to `opacity: 1` for always-visible OBJECTS buttons. Lines 4583-4600: responsive overrides for chevrons need updating.
- `backend/app/templates/browser/dashboard_explorer.html` — Remove the "New Dashboard" tree-leaf at bottom (lines 22-25). This action moves to the section header.
- `backend/app/templates/browser/workflow_explorer.html` — Remove the "New Workflow" tree-leaf at bottom (lines 22-25). This action moves to the section header.
- `backend/app/templates/browser/views_explorer.html` — Ontology Viewer entry (line 11-15): add a CSS class like `view-leaf--accent` for blue styling.
- `frontend/static/css/views.css` or `workspace.css` — Add `.view-leaf--accent` rule with `color: var(--color-accent)` or similar.
- `backend/app/templates/admin/models.html` — Line 89-93: Inference button is `<a class="btn btn-warning btn-sm">` while siblings are `<button class="btn btn-* btn-sm">`. Change to `<button>` for consistent sizing, or add explicit `line-height`/`box-sizing` to `.btn` for `<a>` tags.
- `backend/app/templates/admin/model_ontology_diagram.html` — Cytoscape layout config at line ~118: change from `fcose` to `dagre` with `rankDir: 'LR'` for horizontal layout. Container `.ontology-cy-container` in `style.css` line 2051: change `height: 500px` to `height: 600px` or use `min-height` + flex for full-width responsive behavior.
- `frontend/static/css/style.css` — Line 2051: `.ontology-cy-container` height/width adjustments for full-width horizontal graph.

### Build Order

1. **Chevron replacement (left sidebar)** — 3 template files + CSS update. Highest visual impact. Affects workspace.html, favorites_section.html, shared_nav_section.html, workspace.css.
2. **OBJECTS buttons always visible** — Single CSS change (opacity:0 → opacity:1 or remove the hover-reveal). Trivial.
3. **DASHBOARDS/WORKFLOWS header plus-buttons** — Template changes in workspace.html (add buttons to headers) + dashboard_explorer.html / workflow_explorer.html (remove "New X" tree-leaves). Needs JS function names: `openDashboardBuilderTab()` and `openWorkflowBuilderTab()` already exist in workspace.js.
4. **Inference button normalization** — Change `<a>` to `<button>` in models.html (line 89) or add `display: inline-flex; align-items: center;` to `.btn` for `<a>` tags.
5. **Ontology Viewer button blue** — Add accent class to views_explorer.html + CSS rule.
6. **Relationships graph full-width horizontal** — Change Cytoscape layout to `dagre` with `rankDir: 'LR'` in model_ontology_diagram.html. Update `.ontology-cy-container` height in style.css. Note: dagre layout extension must be available (check if it's loaded via CDN in base.html).

### Verification Approach

- **Docker hot-reload** — All changes are CSS/template, volume-mounted. No rebuild needed.
- **Visual verification** — Browser check each item:
  1. Left sidebar chevrons render as Lucide SVG icons matching right sidebar
  2. OBJECTS refresh/plus buttons visible without hover
  3. DASHBOARDS/WORKFLOWS sections have + button in header, no "New X" tree-leaf entries
  4. Inference button on admin models page aligns with Remove/Refresh buttons
  5. Ontology Viewer link in VIEWS section has blue/accent color
  6. Model detail → Relationships tab graph renders horizontally with full container width
- **Lucide re-render** — After chevron replacement, verify `lucide.createIcons()` runs on sidebar init (it does — already called in workspace.js init).

## Constraints

- **Lucide SVG flex-shrink** — Per CLAUDE.md rule: Lucide icons in flex containers must have `flex-shrink: 0` via CSS, not inline styles.
- **Dagre availability** — Confirmed: `dagre@0.8.5` and `cytoscape-dagre@2.5.0` are already loaded via CDN in `base.html` (lines 34-35). The workspace graph view already uses dagre as a layout option in `graph.js` line 14. Safe to use.
- **No full-page rebuild** — All files are volume-mounted. `docker compose restart frontend` only if nginx config changes (not needed here).

## Common Pitfalls

- **Chevron rotation direction** — Right sidebar uses `<details>` open/close state (`.right-section[open]`) for rotation. Left sidebar uses `.explorer-section.expanded` class toggled by JS click. The rotation CSS selector must match the left sidebar's class-based pattern, not the right sidebar's `[open]` attribute pattern.
- **Dashboard/Workflow plus-button event propagation** — The section header `onclick` toggles expand/collapse. Plus buttons need `event.stopPropagation()` like the OBJECTS buttons do.
