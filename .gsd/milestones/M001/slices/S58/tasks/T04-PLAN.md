# T04: 58-federation 04

**Slice:** S58 — **Milestone:** M001

## Description

Inbox notification UI, collaboration panel, and nav tree shared section.

Purpose: Give users a workspace interface for federation features -- viewing and acting on notifications, managing shared graphs and remote contacts, seeing shared data in the nav tree, and triggering manual sync. This completes the user-facing federation experience.

Output: Inbox sidebar panel (notification list with per-type actions), Collaboration sidebar panel (shared graphs, contacts, sync controls), SHARED nav tree section (shared graph objects by type), federation.js/css for interactions.

## Must-Haves

- [ ] "User can see inbox notifications in a sidebar panel with badge count for unread"
- [ ] "User can view notification details and take actions (accept invitation, import recommendation, dismiss)"
- [ ] "Collaboration panel shows registered remote contacts, shared graphs, and their sync status"
- [ ] "Shared graphs appear in a SHARED section of the nav tree with their objects grouped by type"
- [ ] "Sync Now button triggers sync and shows toast with pulled/pushed counts"
- [ ] "Sync status shows green (<24h), yellow (>24h), or gray (never) dot"

## Files

- `backend/app/templates/browser/workspace.html`
- `backend/app/templates/browser/partials/inbox_panel.html`
- `backend/app/templates/browser/partials/collaboration_panel.html`
- `backend/app/templates/browser/partials/shared_nav_section.html`
- `frontend/static/js/federation.js`
- `frontend/static/css/federation.css`
- `backend/app/federation/router.py`
- `backend/app/browser/router.py`
