---
estimated_steps: 6
estimated_files: 6
---

# T01: Sidebar chevrons, button visibility, and header plus-buttons

**Slice:** S04 — UI Polish & Consistency
**Milestone:** M007

## Description

Replace text-character chevrons (`&#9656;`) with Lucide `chevron-right` SVG icons in all 5 left sidebar explorer sections. Make OBJECTS header action buttons always visible (remove hover-only opacity). Add plus-sign buttons to DASHBOARDS and WORKFLOWS section headers, remove the "New X" tree-leaf entries from their explorer templates.

## Steps

1. **Replace chevrons in `workspace.html`** — Find all instances of `<span class="explorer-section-chevron">&#9656;</span>` (lines ~32, 65, 76, 90 — FAVORITES, OBJECTS, DASHBOARDS, WORKFLOWS sections). Replace each with `<i data-lucide="chevron-right" class="explorer-section-chevron"></i>`. There should be 4 instances in this file.

2. **Replace chevron in `favorites_section.html`** — Line ~9: same replacement of `&#9656;` span → Lucide `<i>` tag.

3. **Replace chevron in `shared_nav_section.html`** — Line ~12: same replacement.

4. **Add plus-buttons to DASHBOARDS header** — In `workspace.html`, find the DASHBOARDS section header. Add an `explorer-header-actions` span (same pattern as OBJECTS section) containing a button with `onclick="event.stopPropagation(); openDashboardBuilderTab()"` and a `data-lucide="plus"` icon.

5. **Add plus-buttons to WORKFLOWS header** — Same pattern as step 4, with `onclick="event.stopPropagation(); openWorkflowBuilderTab()"`.

6. **Remove "New Dashboard" tree-leaf** — In `dashboard_explorer.html`, delete the tree-leaf entry for "New Dashboard" (lines ~22-25). This action now lives in the header button.

7. **Remove "New Workflow" tree-leaf** — In `workflow_explorer.html`, delete the tree-leaf entry for "New Workflow" (lines ~22-25).

8. **Restyle `.explorer-section-chevron` in `workspace.css`** — Current CSS (lines ~98-107) styles a text character with `font-size`, `width`, `text-align`. Replace with SVG-appropriate sizing:
   ```css
   .explorer-section-chevron {
       width: 12px;
       height: 12px;
       flex-shrink: 0;
       stroke: currentColor;
       transition: transform 0.2s ease;
   }
   ```
   Use `.right-section-chevron` at line ~2032 as the reference implementation.

9. **Fix rotation selector** — The left sidebar uses `.explorer-section.expanded` class (toggled by JS), NOT `<details>[open]` like the right sidebar. Ensure rotation CSS uses:
   ```css
   .explorer-section.expanded > .explorer-section-header .explorer-section-chevron {
       transform: rotate(90deg);
   }
   ```

10. **Make OBJECTS buttons always visible** — In `workspace.css` lines ~119-131, change `.explorer-header-actions` from `opacity: 0` to `opacity: 1` (or remove the hover-reveal entirely).

11. **Update responsive overrides** — Lines ~4583-4600 in `workspace.css` have responsive rules for chevrons. Update selectors/properties to match the new SVG-based chevron styling.

## Must-Haves

- [ ] All 5 sidebar sections use `<i data-lucide="chevron-right">` (not text `&#9656;`)
- [ ] `.explorer-section-chevron` has `flex-shrink: 0` (CLAUDE.md Lucide-in-flex rule)
- [ ] Chevron rotation uses `.explorer-section.expanded` selector (not `[open]`)
- [ ] `.explorer-header-actions` opacity is 1 (always visible)
- [ ] DASHBOARDS header has + button calling `openDashboardBuilderTab()`
- [ ] WORKFLOWS header has + button calling `openWorkflowBuilderTab()`
- [ ] Both + buttons use `event.stopPropagation()` to prevent header toggle
- [ ] "New Dashboard" and "New Workflow" tree-leaf entries removed
- [ ] `lucide.createIcons()` already runs on sidebar init (no extra call needed — verify, don't add)

## Verification

- Open workspace in browser at http://localhost:3000
- All 5 sidebar section headers show Lucide chevron-right SVG icons (not text triangles)
- Clicking a section header: chevron rotates 90° on expand, rotates back on collapse
- OBJECTS section: refresh (↻) and plus (+) buttons visible without hovering the header row
- DASHBOARDS section: + button visible in header row, clicking it opens the dashboard builder tab
- WORKFLOWS section: + button visible in header row, clicking it opens the workflow builder tab
- Neither DASHBOARDS nor WORKFLOWS sections have "New Dashboard" / "New Workflow" tree-leaf entries

## Inputs

- S04 Research doc: identified exact line numbers and patterns for all changes
- Reference implementation: `.right-section-chevron` CSS at workspace.css line ~2032
- Existing pattern: OBJECTS `explorer-header-actions` span in workspace.html

## Expected Output

- `backend/app/templates/browser/workspace.html` — 4 chevron replacements + 2 new header action spans
- `backend/app/templates/browser/partials/favorites_section.html` — 1 chevron replacement
- `backend/app/templates/browser/partials/shared_nav_section.html` — 1 chevron replacement
- `backend/app/templates/browser/dashboard_explorer.html` — "New Dashboard" tree-leaf removed
- `backend/app/templates/browser/workflow_explorer.html` — "New Workflow" tree-leaf removed
- `frontend/static/css/workspace.css` — `.explorer-section-chevron` restyled, rotation selector updated, `.explorer-header-actions` opacity fixed, responsive overrides updated

## Observability Impact

- **No new runtime signals.** All changes are static HTML templates and CSS — no server-side code, no JS logic changes, no new API endpoints.
- **Future inspection:** Run `document.querySelectorAll('.explorer-section-chevron').forEach(e => console.log(e.tagName, e.closest('.explorer-section')?.id))` in browser console to verify all chevrons are SVGs.
- **Failure visibility:** If Lucide JS fails to load or `createIcons()` doesn't run, the `<i data-lucide="chevron-right">` tags will render as empty/invisible elements — sections will appear to have no chevrons. Check browser console for Lucide errors.
