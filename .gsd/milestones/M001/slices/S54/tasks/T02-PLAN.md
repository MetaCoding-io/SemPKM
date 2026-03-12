# T02: 54-sparql-advanced 02

**Slice:** S54 — **Milestone:** M001

## Description

Implement SPARQL query view promotion: promote saved queries into named views that appear in the nav tree, rendering results through the existing ViewSpec infrastructure.

Purpose: Allows users to "pin" frequently-used SPARQL queries as browsable views in the sidebar, turning ad-hoc queries into persistent data views without any model configuration.

Output: Promote/demote API endpoints, ViewSpecService integration, "My Views" nav tree section, promotion dialog, promote/demote UI in dropdown and results area.

## Must-Haves

- [ ] "User can promote a saved query to a named view via the Saved dropdown or results area"
- [ ] "Promoted views appear in a 'My Views' section in the nav tree below VIEWS"
- [ ] "Clicking a promoted view in the nav tree renders results using existing table/cards/graph infrastructure"
- [ ] "User can demote a promoted view back to just a saved query"
- [ ] "Promoted views are private to the creator (other users do not see them)"
- [ ] "Auto-detected columns from SELECT variables appear as table headers"

## Files

- `backend/app/sparql/router.py`
- `backend/app/views/service.py`
- `backend/app/views/router.py`
- `backend/app/browser/router.py`
- `backend/app/templates/browser/workspace.html`
- `backend/app/templates/browser/my_views.html`
- `backend/app/templates/browser/promote_dialog.html`
- `frontend/static/js/sparql-console.js`
- `frontend/static/css/workspace.css`
