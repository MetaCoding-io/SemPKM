# T01: 33-named-layouts-and-vfs-settings-restore 01

**Slice:** S33 — **Milestone:** M001

## Description

Create the named layouts data layer and fix VFS Settings icon visibility.

Purpose: Establish the localStorage-based layout persistence module that Plan 02 will wire into the Command Palette and user menu. Also fix the VFS Settings Lucide icon bug (BUG-02) which is independent and small.

Output: `named-layouts.js` module with full save/restore/delete/list API on `window.SemPKMLayouts`; `workspace-layout.js` migrated from sessionStorage to localStorage for auto-save; VFS Settings icons visible.

## Must-Haves

- [ ] "Named layouts can be saved, listed, and deleted via the SemPKMLayouts API"
- [ ] "Auto-save persists the current dockview layout to localStorage (survives browser close)"
- [ ] "SessionStorage layout is migrated to localStorage on first load (no data loss)"
- [ ] "VFS Settings copy-button icons are visible in flex containers"

## Files

- `frontend/static/js/named-layouts.js`
- `frontend/static/js/workspace-layout.js`
- `backend/app/templates/browser/_vfs_settings.html`
- `frontend/static/css/settings.css`
