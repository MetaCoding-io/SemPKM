# T02: 33-named-layouts-and-vfs-settings-restore 02

**Slice:** S33 — **Milestone:** M001

## Description

Wire named layout save/restore/delete into the Command Palette and user menu.

Purpose: Complete the DOCK-02 user experience -- users can save, restore, and delete named layouts via the Ctrl+K Command Palette and the lower-left user menu. Toast notifications provide feedback. Naming is done entirely inline in the palette (no modal, no prompt()).

Output: Working layout management UX accessible from both Command Palette and user popover.

## Must-Haves

- [ ] "User invokes 'Layout: Save As...' from Command Palette, types a name inline in the palette search field, and it persists"
- [ ] "User invokes 'Layout: Restore...' and sees a list of saved layout names; selecting one restores it"
- [ ] "User invokes 'Layout: Delete...' and sees saved layout names; selecting one removes it"
- [ ] "Toast notification appears after save, restore, and delete operations"
- [ ] "User can access layouts from the lower-left user menu"

## Files

- `frontend/static/js/workspace.js`
- `frontend/static/css/workspace.css`
- `backend/app/templates/components/_sidebar.html`
