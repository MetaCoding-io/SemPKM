# S33: Named Layouts And Vfs Settings Restore

**Goal:** Create the named layouts data layer and fix VFS Settings icon visibility.
**Demo:** Create the named layouts data layer and fix VFS Settings icon visibility.

## Must-Haves


## Tasks

- [x] **T01: 33-named-layouts-and-vfs-settings-restore 01** `est:2min`
  - Create the named layouts data layer and fix VFS Settings icon visibility.

Purpose: Establish the localStorage-based layout persistence module that Plan 02 will wire into the Command Palette and user menu. Also fix the VFS Settings Lucide icon bug (BUG-02) which is independent and small.

Output: `named-layouts.js` module with full save/restore/delete/list API on `window.SemPKMLayouts`; `workspace-layout.js` migrated from sessionStorage to localStorage for auto-save; VFS Settings icons visible.
- [x] **T02: 33-named-layouts-and-vfs-settings-restore 02** `est:2min`
  - Wire named layout save/restore/delete into the Command Palette and user menu.

Purpose: Complete the DOCK-02 user experience -- users can save, restore, and delete named layouts via the Ctrl+K Command Palette and the lower-left user menu. Toast notifications provide feedback. Naming is done entirely inline in the palette (no modal, no prompt()).

Output: Working layout management UX accessible from both Command Palette and user popover.

## Files Likely Touched

- `frontend/static/js/named-layouts.js`
- `frontend/static/js/workspace-layout.js`
- `backend/app/templates/browser/_vfs_settings.html`
- `frontend/static/css/settings.css`
- `frontend/static/js/workspace.js`
- `frontend/static/css/workspace.css`
- `backend/app/templates/components/_sidebar.html`
