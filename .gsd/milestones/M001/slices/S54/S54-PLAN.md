# S54: Sparql Advanced

**Goal:** Implement SPARQL query sharing: data models, migration, API endpoints, and full frontend UI for sharing saved queries between users.
**Demo:** Implement SPARQL query sharing: data models, migration, API endpoints, and full frontend UI for sharing saved queries between users.

## Must-Haves


## Tasks

- [x] **T01: 54-sparql-advanced 01** `est:4min`
  - Implement SPARQL query sharing: data models, migration, API endpoints, and full frontend UI for sharing saved queries between users.

Purpose: Enables collaboration by letting query owners share saved SPARQL queries with specific users on the instance. Recipients see shared queries in a dedicated "Shared with Me" section of their Saved dropdown, can run them, and fork them as their own.

Output: SharedQueryAccess + PromotedQueryView models, migration 008, share CRUD endpoints, extended Saved dropdown with share/shared-with-me/fork UI.
- [x] **T02: 54-sparql-advanced 02** `est:7min`
  - Implement SPARQL query view promotion: promote saved queries into named views that appear in the nav tree, rendering results through the existing ViewSpec infrastructure.

Purpose: Allows users to "pin" frequently-used SPARQL queries as browsable views in the sidebar, turning ad-hoc queries into persistent data views without any model configuration.

Output: Promote/demote API endpoints, ViewSpecService integration, "My Views" nav tree section, promotion dialog, promote/demote UI in dropdown and results area.

## Files Likely Touched

- `backend/app/sparql/models.py`
- `backend/app/sparql/schemas.py`
- `backend/app/sparql/router.py`
- `backend/migrations/versions/008_sharing_promotion.py`
- `frontend/static/js/sparql-console.js`
- `frontend/static/css/workspace.css`
- `backend/app/sparql/router.py`
- `backend/app/views/service.py`
- `backend/app/views/router.py`
- `backend/app/browser/router.py`
- `backend/app/templates/browser/workspace.html`
- `backend/app/templates/browser/my_views.html`
- `backend/app/templates/browser/promote_dialog.html`
- `frontend/static/js/sparql-console.js`
- `frontend/static/css/workspace.css`
