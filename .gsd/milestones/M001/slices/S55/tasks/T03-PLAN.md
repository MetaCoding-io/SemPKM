# T03: 55-browser-ui-polish 03

**Slice:** S55 — **Milestone:** M001

## Description

Add an expandable edge inspector to the Relations panel. Clicking a relation item expands it inline to show edge provenance (predicate QName, timestamp, author, source, event link). Add a backend endpoint for edge provenance queries. Add edge delete capability for user-asserted edges. Also define a reusable `showConfirmDialog` function (used here for edge delete, and later by Plan 55-02 for bulk delete).

Purpose: Give users visibility into edge metadata and provenance without leaving the current context, and enable precise edge management.
Output: Modified properties.html, workspace.js, workspace.css, browser/router.py with edge inspector and provenance API.

## Must-Haves

- [ ] "Clicking a relation item expands it inline to show edge provenance detail"
- [ ] "Expanded detail shows predicate IRI as QName"
- [ ] "Expanded detail shows creation timestamp and author"
- [ ] "Expanded detail shows source (user-asserted vs OWL-inferred)"
- [ ] "Expanded detail shows clickable event link that opens Event Log in the bottom panel"
- [ ] "A separate open icon on each relation navigates to the target object tab"
- [ ] "User-asserted edges show a delete button; inferred edges do not"
- [ ] "Clicking delete on an edge shows confirmation before removing it"

## Files

- `backend/app/browser/router.py`
- `backend/app/templates/browser/properties.html`
- `frontend/static/js/workspace.js`
- `frontend/static/css/workspace.css`
