---
estimated_steps: 22
estimated_files: 2
skills_used: []
---

# T01: Fix command palette scroll jump and replace persona/layout dialog UX

## Description

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

## Inputs

- ``frontend/static/js/workspace.js` — existing command palette init, showConfirmDialog reference`
- ``frontend/static/css/workspace.css` — existing .confirm-dialog CSS rules`

## Expected Output

- ``frontend/static/js/workspace.js` — scroll jump fix, showInputDialog function, rewired persona/layout commands, removed confirm child entries`
- ``frontend/static/css/workspace.css` — .btn-primary and input styling for confirm-dialog`

## Verification

grep -c 'persona-create-confirm' frontend/static/js/workspace.js | grep -q '^0$' && grep -c 'layout-save-confirm' frontend/static/js/workspace.js | grep -q '^0$' && grep -q 'showInputDialog' frontend/static/js/workspace.js && grep -q '_savedOverflow' frontend/static/js/workspace.js && grep -q 'btn-primary' frontend/static/css/workspace.css && echo 'PASS'
