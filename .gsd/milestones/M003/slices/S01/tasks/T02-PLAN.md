---
estimated_steps: 4
estimated_files: 4
---

# T02: Add mode dropdown to workspace UI and wire htmx swap

**Slice:** S01 — Explorer Mode Infrastructure
**Milestone:** M003

## Description

Add a `<select>` dropdown to the OBJECTS section header in the workspace template, wire it to the `/browser/explorer/tree` endpoint via htmx attributes, add an `id="explorer-tree-body"` to the swap target div, create the placeholder template, and style the dropdown to fit the explorer header. This task makes the mode switching visible and functional in the UI.

## Steps

1. **Modify `workspace.html` OBJECTS section:**
   - Add `<select id="explorer-mode-select" name="mode" class="explorer-mode-select">` inside the `.explorer-header-actions` span, before the action buttons
   - Options: `<option value="by-type" selected>By Type</option>`, `<option value="hierarchy">By Hierarchy</option>`, `<option value="by-tag">By Tag</option>`
   - Add htmx attributes on the `<select>`: `hx-get="/browser/explorer/tree"`, `hx-include="this"`, `hx-target="#explorer-tree-body"`, `hx-trigger="change"`, `hx-swap="innerHTML"`
   - Add Lucide re-init after swap: `hx-on::after-swap="if(typeof lucide!=='undefined')lucide.createIcons()"`
   - Add `id="explorer-tree-body"` to the existing `.explorer-section-body` div that contains `{% include "browser/nav_tree.html" %}`
   - Ensure `onclick="event.stopPropagation()"` on the `<select>` to prevent the section expand/collapse toggle from firing when clicking the dropdown

2. **Update placeholder handlers in `workspace.py` to use template:**
   - Update `_handle_hierarchy` and `_handle_by_tag` to render `explorer_placeholder.html` with appropriate `mode_label` and `icon_name` context
   - Ensure placeholder HTML uses `data-testid="explorer-placeholder"` for E2E targeting

3. **Add CSS for the mode dropdown in `workspace.css`:**
   - `.explorer-mode-select` — compact select styling: small font, no border (matches header aesthetic), dark background matching explorer theme, text-muted color, cursor pointer
   - Ensure the dropdown doesn't push action buttons off the header (use appropriate flex ordering or sizing)
   - Keep dropdown width reasonable (auto or max-width) — it shares the header with selection badge, delete btn, refresh btn, plus btn

4. **Verify the htmx swap path works end-to-end:**
   - Start Docker stack
   - Confirm dropdown appears in OBJECTS header
   - Confirm selecting "By Hierarchy" swaps tree content to placeholder
   - Confirm selecting "By Type" swaps back to real type tree with working lazy expansion
   - Confirm clicking the dropdown does NOT expand/collapse the OBJECTS section

## Must-Haves

- [ ] Mode dropdown visible in OBJECTS section header
- [ ] Switching mode triggers htmx GET to `/browser/explorer/tree?mode={value}` and swaps `#explorer-tree-body`
- [ ] By-type mode renders the same tree as before (types with lazy children)
- [ ] Placeholder modes render styled empty-state with icon and message
- [ ] Clicking dropdown does not toggle section expand/collapse
- [ ] Lucide icons re-initialize after swap
- [ ] `#section-objects` DOM ID unchanged
- [ ] `data-testid="nav-section"` and `data-testid="nav-item"` preserved in by-type tree

## Verification

- Visual: dropdown in OBJECTS header, mode switch swaps tree content
- `data-testid="nav-section"` elements present after switching to by-type
- Placeholder modes show icon + message text
- Lazy expansion (click type node) still works after switching back to by-type
- OBJECTS section still expands/collapses when clicking the header text (not dropdown)

## Observability Impact

- Signals added/changed: None — UI only, backend logging from T01 covers server-side
- How a future agent inspects this: `document.getElementById('explorer-mode-select').value` shows current mode; `#explorer-tree-body` innerHTML shows rendered content
- Failure state exposed: If htmx swap fails, browser console shows htmx error; tree body remains with prior content

## Inputs

- `backend/app/browser/workspace.py` — T01 added the endpoint and handlers
- `backend/app/templates/browser/explorer_placeholder.html` — T01 created the template
- `backend/app/templates/browser/workspace.html` — current OBJECTS section structure
- `frontend/static/css/workspace.css` — existing explorer styles

## Expected Output

- `backend/app/templates/browser/workspace.html` — dropdown added, explorer-tree-body ID added
- `frontend/static/css/workspace.css` — `.explorer-mode-select` styles added
- `backend/app/templates/browser/explorer_placeholder.html` — may be updated with data-testid
- `backend/app/browser/workspace.py` — placeholder handlers may be updated to use template rendering
