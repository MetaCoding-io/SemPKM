# S03: Command Palette & Persona/Layout Dialog UX

**Goal:** Fix command palette scroll jump, replace persona-create and layout-save-as antipattern with proper input dialogs, and fix admin graph popover positioning.
**Demo:** After this: F1 → 'Persona: Create New' → input dialog → type name → Create → persona saved. F1 → 'Layout: Save As' → input dialog → type name → Save → layout saved. Command palette opens without scroll jump. Admin graph popover positions near the node.

## Tasks
- [x] **T01: Fixed command palette scroll jump by freezing body overflow on open, replaced shadow-DOM input hacks for persona-create and layout-save-as with proper showInputDialog() modal dialogs** — ## Description

Three related changes in workspace.js and workspace.css:

1. **Scroll jump fix (#24):** The ninja-keys component calls `scrollIntoView()` on highlighted actions, which propagates to `document.body` when the modal overlay has `overflow: auto`. Fix by toggling `document.body.style.overflow = 'hidden'` in the existing open/close patch.

2. **Input dialog function:** Create `showInputDialog(title, placeholder, onConfirm, confirmText)` modeled on the existing `showConfirmDialog()` at line 3385. Uses `<dialog>` element with `.confirm-dialog` base styling plus an `<input>` field.

3. **Persona create + Layout save rewiring (#33, #34, #35):** Replace the antipattern where users type a name in the ninja-keys search field and select a confirm child item. Instead, each command closes the palette and opens the new input dialog.

## Steps

1. Read `frontend/static/js/workspace.js` lines 1513-1520 (open/close patch). Add `_savedOverflow` variable. In `ninja.open`, save `document.body.style.overflow` and set to `'hidden'`. In `ninja.close`, restore the saved value.

2. Add `showInputDialog(title, placeholder, onConfirm, confirmText)` function near `showConfirmDialog()` (around line 3385). Implementation:
   - Create `<dialog>` with class `confirm-dialog`
   - Build HTML: title `<h3>`, `<input type="text">` with placeholder and autofocus, actions div with Cancel + confirm button
   - The confirm button uses class `btn-primary` (new CSS class, styled like `btn-danger` but with accent color)
   - Wire cancel → cleanup, confirm → call `onConfirm(input.value.trim())` if non-empty else show toast, Escape → cleanup
   - Also handle Enter key on the input to submit
   - Call `dialog.showModal()`
   - Export as `window.SemPKM.showInputDialog = showInputDialog`

3. Add CSS for `.confirm-dialog .btn-primary` in `workspace.css` near the existing `.confirm-dialog .btn-danger` rules (around line 3142). Style: `background: var(--color-accent)`, `color: var(--color-on-accent)`, same border-radius/padding/font as btn-danger. Add hover state.

4. Add CSS for `.confirm-dialog input[type="text"]` — full width, themed border/background/color, 13px font, 8px padding, border-radius 4px.

5. Rewire `persona-create` command entry (around line 1735): Remove `children: ['persona-create-confirm']`. Add `handler` that closes the palette (`ninja.close()`) and calls `showInputDialog('Create Persona', 'Persona name', function(name) { createNewPersona(name); }, 'Create')`.

6. Delete the entire `persona-create-confirm` entry object (the one with `parent: 'persona-create'` and the shadow DOM input extraction hack).

7. Rewire `layout-save-as` command entry (around line 1680): Remove `children: ['layout-save-confirm']`. Add `handler` that closes the palette and calls `showInputDialog('Save Layout', 'Layout name', function(name) { window.SemPKMLayouts.save(name); showToast('Layout "' + name + '" saved'); _refreshLayoutPaletteItems(document.querySelector('ninja-keys')); }, 'Save')`.

8. Delete the entire `layout-save-confirm` entry object (the one with `parent: 'layout-save-as'` and the shadow DOM input extraction hack).

9. Verify: `grep -c 'persona-create-confirm' frontend/static/js/workspace.js` returns 0. `grep -c 'layout-save-confirm' frontend/static/js/workspace.js` returns 0. `grep -c 'showInputDialog' frontend/static/js/workspace.js` returns at least 3 (definition + 2 calls + export). `grep -c '_savedOverflow' frontend/static/js/workspace.js` returns at least 2.
  - Estimate: 45m
  - Files: frontend/static/js/workspace.js, frontend/static/css/workspace.css
  - Verify: grep -c 'persona-create-confirm' frontend/static/js/workspace.js | grep -q '^0$' && grep -c 'layout-save-confirm' frontend/static/js/workspace.js | grep -q '^0$' && grep -q 'showInputDialog' frontend/static/js/workspace.js && grep -q '_savedOverflow' frontend/static/js/workspace.js && grep -q 'btn-primary' frontend/static/css/workspace.css && echo 'PASS'
- [x] **T02: Fixed admin ontology diagram popover positioning by removing panel-relative offset subtraction from both node and edge hover handlers, using viewport coordinates to match position:fixed CSS** — ## Description

The admin model ontology diagram popover (`.graph-popover`) has `position: fixed` in CSS but the positioning JS in `model_ontology_diagram.html` computes panel-relative coordinates by subtracting `panelRect`. This causes the popover to appear offset from the hovered node.

## Steps

1. Read `backend/app/templates/admin/model_ontology_diagram.html` lines 215-235 (the `showPopover` function's positioning block).

2. Fix the initial position calculation. Change:
   ```javascript
   var left = (containerRect.left - panelRect.left) + pos.x + 16;
   var top = (containerRect.top - panelRect.top) + pos.y - 12;
   ```
   To:
   ```javascript
   var left = containerRect.left + pos.x + 16;
   var top = containerRect.top + pos.y - 12;
   ```

3. Fix the right-edge overflow check. Change:
   ```javascript
   popover.style.left = ((containerRect.left - panelRect.left) + pos.x - pRect.width - 12) + 'px';
   ```
   To:
   ```javascript
   popover.style.left = (containerRect.left + pos.x - pRect.width - 12) + 'px';
   ```

4. Fix the bottom-edge overflow check. Change:
   ```javascript
   popover.style.top = ((containerRect.top - panelRect.top) + pos.y - pRect.height + 12) + 'px';
   ```
   To:
   ```javascript
   popover.style.top = (containerRect.top + pos.y - pRect.height + 12) + 'px';
   ```

5. Update the overflow boundary checks from panel bounds to viewport bounds. Change:
   ```javascript
   if (pRect.right > panelRect.right - 8) {
   ```
   To:
   ```javascript
   if (pRect.right > window.innerWidth - 8) {
   ```
   And change:
   ```javascript
   if (pRect.bottom > panelRect.bottom - 8) {
   ```
   To:
   ```javascript
   if (pRect.bottom > window.innerHeight - 8) {
   ```

6. The `panelRect` variable is no longer needed in the positioning block. It can be removed or left — the `panel` variable is still used for `panel.appendChild(popover)` earlier in the function.

7. Verify: `grep -c 'panelRect.left\|panelRect.right\|panelRect.top\|panelRect.bottom' backend/app/templates/admin/model_ontology_diagram.html` returns 0. `grep -c 'containerRect.left + pos' backend/app/templates/admin/model_ontology_diagram.html` returns at least 1.
  - Estimate: 15m
  - Files: backend/app/templates/admin/model_ontology_diagram.html
  - Verify: grep -c 'panelRect\.left\|panelRect\.right\|panelRect\.top\|panelRect\.bottom' backend/app/templates/admin/model_ontology_diagram.html | grep -q '^0$' && grep -q 'containerRect.left + pos' backend/app/templates/admin/model_ontology_diagram.html && grep -q 'window.innerWidth' backend/app/templates/admin/model_ontology_diagram.html && echo 'PASS'
