# T02: 12-sidebar-and-navigation 02

**Slice:** S12 — **Milestone:** M001

## Description

Add a VS Code-style user menu at the bottom of the sidebar with a colored initials avatar, display name, and a popover containing Settings, Theme toggle placeholder, and a working Logout action.

Purpose: Give users visible identity feedback and quick access to account actions without navigating away from their current work.

Output: User area in `_sidebar.html`, CSS for avatar and popover, JS helper for avatar colors/initials.

## Must-Haves

- [ ] "A user area pinned to the bottom of the sidebar shows the user's colored initials avatar and display name"
- [ ] "Clicking the user area opens a popover with Settings link, Theme toggle placeholder, and Logout button"
- [ ] "When sidebar is collapsed to icon rail, user area shows just the small avatar circle and clicking opens the same popover"
- [ ] "Clicking Logout ends the session and redirects to the login page"

## Files

- `backend/app/templates/components/_sidebar.html`
- `frontend/static/css/style.css`
- `frontend/static/js/sidebar.js`
