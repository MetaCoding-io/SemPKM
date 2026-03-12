# S12: Sidebar And Navigation

**Goal:** Restructure the sidebar from a flat nav list with Unicode emoji icons into a grouped, collapsible navigation system with Lucide SVG icons, section headers, and a collapse-to-icon-rail toggle (Ctrl+B).
**Demo:** Restructure the sidebar from a flat nav list with Unicode emoji icons into a grouped, collapsible navigation system with Lucide SVG icons, section headers, and a collapse-to-icon-rail toggle (Ctrl+B).

## Must-Haves


## Tasks

- [x] **T01: 12-sidebar-and-navigation 01** `est:4min`
  - Restructure the sidebar from a flat nav list with Unicode emoji icons into a grouped, collapsible navigation system with Lucide SVG icons, section headers, and a collapse-to-icon-rail toggle (Ctrl+B).

Purpose: Replace the flat 8-item sidebar with organized grouped sections (Admin, Meta, Apps, Debug), add Lucide SVG icons via CDN, implement the 220px-to-48px collapse animation with localStorage persistence, and pass user data to the template context for the user menu (Plan 02).

Output: Restructured `_sidebar.html`, new `sidebar.js`, updated CSS with collapse transitions, Lucide CDN in `base.html`, all route handlers passing `user` in template context.
- [x] **T02: 12-sidebar-and-navigation 02** `est:2min`
  - Add a VS Code-style user menu at the bottom of the sidebar with a colored initials avatar, display name, and a popover containing Settings, Theme toggle placeholder, and a working Logout action.

Purpose: Give users visible identity feedback and quick access to account actions without navigating away from their current work.

Output: User area in `_sidebar.html`, CSS for avatar and popover, JS helper for avatar colors/initials.

## Files Likely Touched

- `backend/app/templates/components/_sidebar.html`
- `backend/app/templates/base.html`
- `frontend/static/css/style.css`
- `frontend/static/js/sidebar.js`
- `frontend/static/js/workspace.js`
- `backend/app/shell/router.py`
- `backend/app/browser/router.py`
- `backend/app/admin/router.py`
- `backend/app/templates/components/_sidebar.html`
- `frontend/static/css/style.css`
- `frontend/static/js/sidebar.js`
