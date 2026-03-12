# T01: 12-sidebar-and-navigation 01

**Slice:** S12 — **Milestone:** M001

## Description

Restructure the sidebar from a flat nav list with Unicode emoji icons into a grouped, collapsible navigation system with Lucide SVG icons, section headers, and a collapse-to-icon-rail toggle (Ctrl+B).

Purpose: Replace the flat 8-item sidebar with organized grouped sections (Admin, Meta, Apps, Debug), add Lucide SVG icons via CDN, implement the 220px-to-48px collapse animation with localStorage persistence, and pass user data to the template context for the user menu (Plan 02).

Output: Restructured `_sidebar.html`, new `sidebar.js`, updated CSS with collapse transitions, Lucide CDN in `base.html`, all route handlers passing `user` in template context.

## Must-Haves

- [ ] "Pressing Ctrl+B collapses the sidebar to a 48px icon rail with smooth CSS transition; pressing again expands to 220px with labels"
- [ ] "Collapsed/expanded state persists across page reloads via localStorage"
- [ ] "Sidebar navigation is organized into grouped sections (Admin, Meta, Apps, Debug) with collapsible section headers"
- [ ] "Apps section contains Object Browser and SPARQL Console; Debug section contains Commands, API Docs, Health Check, and Event Log"
- [ ] "Meta section contains a Docs & Tutorials placeholder link"
- [ ] "Hovering over an icon in collapsed mode shows a tooltip with the item name"
- [ ] "Clicking the SemPKM brand logo navigates home (Home nav item removed)"
- [ ] "Lucide SVG icons replace all Unicode emoji icons"

## Files

- `backend/app/templates/components/_sidebar.html`
- `backend/app/templates/base.html`
- `frontend/static/css/style.css`
- `frontend/static/js/sidebar.js`
- `frontend/static/js/workspace.js`
- `backend/app/shell/router.py`
- `backend/app/browser/router.py`
- `backend/app/admin/router.py`
