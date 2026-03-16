# S04: UI Polish & Consistency

**Goal:** Fix 6 UI inconsistencies identified in user review: sidebar chevrons, button visibility, header actions, inference button sizing, accent colors, and graph layout.
**Demo:** Left sidebar chevrons match right sidebar Lucide icons. OBJECTS refresh/plus always visible. DASHBOARDS/WORKFLOWS headers have + buttons (no "New X" tree-leaves). Inference button same size as siblings. Ontology Viewer link is blue. Relationships graph renders horizontally at full width.

## Must-Haves

- Left sidebar `&#9656;` text chevrons replaced with `<i data-lucide="chevron-right">` in all 5 explorer sections
- `.explorer-section-chevron` CSS restyled for SVG sizing with `flex-shrink: 0` (per CLAUDE.md rule)
- Chevron rotation CSS uses `.explorer-section.expanded` class selector (not `[open]` attribute — left sidebar is JS-toggled, not `<details>`)
- `.explorer-header-actions` opacity changed from 0 to 1 (always visible)
- DASHBOARDS header gets plus-button calling `openDashboardBuilderTab()` with `event.stopPropagation()`
- WORKFLOWS header gets plus-button calling `openWorkflowBuilderTab()` with `event.stopPropagation()`
- "New Dashboard" and "New Workflow" tree-leaf entries removed from their respective explorer templates
- Inference button on admin models page normalized to `<button>` (from `<a>`) or given explicit sizing
- Ontology Viewer entry in VIEWS explorer gets blue/accent styling
- Relationships graph container full-width, layout changed to `dagre` with `rankDir: 'LR'` for horizontal rendering

## Verification

- Start Docker stack, open workspace in browser
- Left sidebar: all 5 section chevrons render as Lucide SVG icons (not text triangles), rotate on expand
- OBJECTS section: refresh and plus buttons visible without hovering the header
- DASHBOARDS section: + button in header opens builder; no "New Dashboard" tree-leaf entry
- WORKFLOWS section: + button in header opens builder; no "New Workflow" tree-leaf entry
- Admin → Mental Models: inference button same height/alignment as Remove and Refresh buttons
- VIEWS section: Ontology Viewer entry has blue/accent color
- Admin → Model detail → Relationships tab: graph renders horizontally with dagre layout at full container width

## Tasks

- [x] **T01: Sidebar chevrons, button visibility, and header plus-buttons** `est:45m`
  - Why: Fixes 3 of 6 UIPOL-01 items — the explorer left sidebar inconsistencies (chevrons, always-visible buttons, dashboard/workflow header actions)
  - Files: `backend/app/templates/browser/workspace.html`, `backend/app/templates/browser/partials/favorites_section.html`, `backend/app/templates/browser/partials/shared_nav_section.html`, `backend/app/templates/browser/dashboard_explorer.html`, `backend/app/templates/browser/workflow_explorer.html`, `frontend/static/css/workspace.css`
  - Do:
    1. In `workspace.html`: replace `<span class="explorer-section-chevron">&#9656;</span>` with `<i data-lucide="chevron-right" class="explorer-section-chevron"></i>` at lines ~32, 65, 76, 90. Add `explorer-header-actions` span with plus-button to DASHBOARDS header (onclick `openDashboardBuilderTab()` with `event.stopPropagation()`) and WORKFLOWS header (onclick `openWorkflowBuilderTab()` with `event.stopPropagation()`). Follow the existing OBJECTS header actions pattern.
    2. In `favorites_section.html` line ~9: same chevron replacement.
    3. In `shared_nav_section.html` line ~12: same chevron replacement.
    4. In `dashboard_explorer.html`: remove the "New Dashboard" tree-leaf entry (lines ~22-25).
    5. In `workflow_explorer.html`: remove the "New Workflow" tree-leaf entry (lines ~22-25).
    6. In `workspace.css`: restyle `.explorer-section-chevron` from text character sizing (font-size, width, text-align) to SVG sizing (width: 12px, height: 12px, flex-shrink: 0, stroke: currentColor). Match `.right-section-chevron` at line ~2032 as reference. Change `.explorer-header-actions` opacity from 0 to 1. Update rotation CSS to work with `.explorer-section.expanded .explorer-section-chevron` selector. Update responsive overrides at lines ~4583-4600.
    - **Pitfall:** Left sidebar uses `.explorer-section.expanded` class (JS-toggled), NOT `<details>[open]` like right sidebar. Rotation selector must match. Plus-buttons need `event.stopPropagation()` to prevent header click from toggling expand/collapse.
  - Verify: Open workspace in browser. All 5 sidebar section chevrons render as Lucide SVGs. Chevrons rotate on expand/collapse. OBJECTS buttons visible without hover. DASHBOARDS/WORKFLOWS headers have + buttons that open builders. No "New Dashboard" / "New Workflow" tree-leaf entries.
  - Done when: All 3 sidebar items from UIPOL-01 pass visual verification in browser.

- [x] **T02: Inference button, Ontology Viewer accent, and horizontal graph** `est:30m`
  - Why: Fixes remaining 3 UIPOL-01 items — admin page button sizing, accent color, and graph layout
  - Files: `backend/app/templates/admin/models.html`, `backend/app/templates/browser/views_explorer.html`, `backend/app/templates/admin/model_ontology_diagram.html`, `frontend/static/css/style.css`, `frontend/static/css/workspace.css`
  - Do:
    1. In `models.html` line ~89: change inference `<a class="btn btn-warning btn-sm">` to `<button class="btn btn-warning btn-sm">` (or add explicit `display: inline-flex; align-items: center; line-height` to normalize sizing with sibling `<button>` elements). Preserve the onclick/href behavior.
    2. In `views_explorer.html`: add a CSS class like `view-leaf--accent` to the Ontology Viewer entry (lines ~11-15).
    3. In `workspace.css` (or `views.css`): add `.view-leaf--accent` rule with `color: var(--color-accent)` or the project's blue accent variable.
    4. In `model_ontology_diagram.html` line ~118: change Cytoscape layout from `fcose` to `dagre` with `rankDir: 'LR'` for horizontal rendering. Dagre is already loaded via CDN (`dagre@0.8.5` + `cytoscape-dagre@2.5.0` in `base.html`).
    5. In `style.css` line ~2051: update `.ontology-cy-container` from `height: 500px` to larger height (e.g. 600px) and ensure `width: 100%` for full-width. Consider `min-height` + responsive flex.
  - Verify: Admin → Mental Models page: inference button aligns with Remove/Refresh siblings. VIEWS explorer: Ontology Viewer link is blue. Admin → Model detail → Relationships tab: graph renders horizontally with full container width.
  - Done when: All 3 remaining UIPOL-01 items pass visual verification in browser.

## Files Likely Touched

## Observability / Diagnostics

- **Chevron rendering:** Browser DevTools → inspect any `.explorer-section-chevron` element in the left sidebar; should be an `<svg>` tag (Lucide-rendered), not a `<span>` with text content. Check `document.querySelectorAll('.explorer-section-chevron').forEach(e => console.log(e.tagName))` — all should log `svg`.
- **Button visibility:** Inspect `#section-objects .explorer-header-actions` computed style — `opacity` should be `1` at rest (no hover needed).
- **Plus-button wiring:** Click DASHBOARDS/WORKFLOWS `+` buttons — should open builder tabs without toggling the section expand/collapse (stopPropagation working).
- **Tree-leaf removal:** Expand DASHBOARDS/WORKFLOWS sections — should not contain any `.tree-action` entries with "New Dashboard"/"New Workflow" text.
- **No new runtime signals** — all changes are static HTML/CSS template modifications with no server-side logic impact.

- `backend/app/templates/browser/workspace.html`
- `backend/app/templates/browser/partials/favorites_section.html`
- `backend/app/templates/browser/partials/shared_nav_section.html`
- `backend/app/templates/browser/dashboard_explorer.html`
- `backend/app/templates/browser/workflow_explorer.html`
- `backend/app/templates/admin/models.html`
- `backend/app/templates/browser/views_explorer.html`
- `backend/app/templates/admin/model_ontology_diagram.html`
- `frontend/static/css/workspace.css`
- `frontend/static/css/style.css`
