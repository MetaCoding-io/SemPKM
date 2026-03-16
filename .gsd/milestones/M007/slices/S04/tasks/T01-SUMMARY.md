---
id: T01
parent: S04
milestone: M007
provides:
  - Lucide SVG chevrons on all 6 left sidebar explorer sections
  - Always-visible OBJECTS header action buttons
  - Plus-buttons on DASHBOARDS and WORKFLOWS headers
  - Removed "New Dashboard" and "New Workflow" tree-leaf entries
key_files:
  - backend/app/templates/browser/workspace.html
  - backend/app/templates/browser/partials/favorites_section.html
  - backend/app/templates/browser/partials/shared_nav_section.html
  - backend/app/templates/browser/partials/shared_nav_content.html
  - backend/app/templates/browser/dashboard_explorer.html
  - backend/app/templates/browser/workflow_explorer.html
  - frontend/static/css/workspace.css
key_decisions:
  - Used same explorer-header-actions pattern from OBJECTS section for DASHBOARDS/WORKFLOWS plus-buttons
  - Changed opacity model from hover-reveal (opacity: 0 → 1 on hover) to always-visible (opacity: 1)
patterns_established:
  - All left sidebar section headers now use Lucide chevron-right SVG icons consistently with right sidebar
observability_surfaces:
  - none
duration: 30m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Sidebar chevrons, button visibility, and header plus-buttons

**Replaced text chevrons with Lucide SVGs in all 6 sidebar sections, made OBJECTS buttons always visible, added + buttons to DASHBOARDS/WORKFLOWS headers, removed "New X" tree-leaf entries.**

## What Happened

Replaced `<span class="explorer-section-chevron">&#9656;</span>` with `<i data-lucide="chevron-right" class="explorer-section-chevron"></i>` across 7 template files (workspace.html had 4 instances, favorites_section.html, shared_nav_section.html, and shared_nav_content.html had 1 each). The shared_nav_content.html file was discovered during verification — it's the server-rendered htmx response that replaces the initial shared_nav_section.html markup.

Added `explorer-header-actions` spans with plus-buttons to DASHBOARDS and WORKFLOWS section headers, following the existing OBJECTS section pattern. Both buttons use `event.stopPropagation()` to prevent header toggle.

Removed the "New Dashboard" and "New Workflow" `.tree-leaf.tree-action` entries from their respective explorer templates since this functionality now lives in the header buttons.

Restyled `.explorer-section-chevron` CSS from text character properties (font-size, text-align) to SVG-appropriate sizing (width/height: 12px, stroke: currentColor, flex-shrink: 0). Updated the rotation selector to use the more specific `> .explorer-section-header` descendant combinator. Changed `.explorer-header-actions` from opacity: 0 (hover-reveal) to opacity: 1 (always visible). Updated responsive overrides to add `stroke: currentColor` for the SVG chevrons.

## Verification

All checks passed via browser testing at http://localhost:3000/browser:

- **6/6 chevrons are SVGs:** Confirmed via `document.querySelectorAll('.explorer-section-chevron')` — all return `tagName: 'svg'` across section-favorites, section-objects, section-views, section-dashboards, section-workflows, section-shared
- **Chevron rotation:** Clicking VIEWS section header toggled `expanded` class; computed transform was `matrix(0, 1, -1, 0, 0, 0)` (= rotate(90deg)) when expanded, `none` when collapsed
- **OBJECTS buttons always visible:** `getComputedStyle(actionsEl).opacity` returned `'1'` at rest (no hover)
- **DASHBOARDS + button:** Click opened "New Dashboard" builder tab (heading appeared)
- **WORKFLOWS + button:** Click opened "New Workflow" builder tab (heading appeared)
- **No "New Dashboard" tree-leaf:** `dashboards-tree` innerHTML confirmed no "New Dashboard" text
- **No "New Workflow" tree-leaf:** `workflows-tree` innerHTML confirmed no "New Workflow" text
- **9/9 browser assertions PASS:** selector_visible checks for all 6 chevrons, both + buttons, and OBJECTS header-actions

### Slice-level verification (partial — T01 scope):

- ✅ Left sidebar: all 5+ section chevrons render as Lucide SVG icons, rotate on expand
- ✅ OBJECTS section: refresh and plus buttons visible without hovering the header
- ✅ DASHBOARDS section: + button in header opens builder; no "New Dashboard" tree-leaf entry
- ✅ WORKFLOWS section: + button in header opens builder; no "New Workflow" tree-leaf entry
- ⬜ Admin → Mental Models: inference button sizing (T02)
- ⬜ VIEWS section: Ontology Viewer accent color (T02)
- ⬜ Admin → Model detail → Relationships tab: graph layout (T02)

## Diagnostics

No new runtime signals. Inspect chevrons via browser console:
```js
document.querySelectorAll('.explorer-section-chevron').forEach(e => console.log(e.tagName, e.closest('.explorer-section')?.id))
```
All should log `svg` with their respective section IDs.

## Deviations

- **shared_nav_content.html** required an additional chevron replacement not listed in the task plan. The plan listed shared_nav_section.html (the initial template), but the htmx endpoint replaces it with shared_nav_content.html via `outerHTML` swap. Without fixing both, the SHARED section chevron reverted to `<span>` after the server response loaded. Fixed in-flight.
- **7 files modified instead of 6** due to the shared_nav_content.html discovery.

## Known Issues

- OBJECTS header action buttons (refresh, plus) are slightly clipped at the right edge when the sidebar is narrow — this is a pre-existing layout constraint, not introduced by this task.

## Files Created/Modified

- `backend/app/templates/browser/workspace.html` — 4 chevron replacements, 2 new header action spans (DASHBOARDS/WORKFLOWS)
- `backend/app/templates/browser/partials/favorites_section.html` — 1 chevron replacement
- `backend/app/templates/browser/partials/shared_nav_section.html` — 1 chevron replacement
- `backend/app/templates/browser/partials/shared_nav_content.html` — 1 chevron replacement (htmx response template)
- `backend/app/templates/browser/dashboard_explorer.html` — "New Dashboard" tree-leaf removed
- `backend/app/templates/browser/workflow_explorer.html` — "New Workflow" tree-leaf removed
- `frontend/static/css/workspace.css` — `.explorer-section-chevron` restyled for SVG, rotation selector updated, `.explorer-header-actions` opacity: 1, responsive overrides updated
