# T01: 54-sparql-advanced 01

**Slice:** S54 — **Milestone:** M001

## Description

Implement SPARQL query sharing: data models, migration, API endpoints, and full frontend UI for sharing saved queries between users.

Purpose: Enables collaboration by letting query owners share saved SPARQL queries with specific users on the instance. Recipients see shared queries in a dedicated "Shared with Me" section of their Saved dropdown, can run them, and fork them as their own.

Output: SharedQueryAccess + PromotedQueryView models, migration 008, share CRUD endpoints, extended Saved dropdown with share/shared-with-me/fork UI.

## Must-Haves

- [ ] "Owner can share a saved query with another non-guest user"
- [ ] "Shared queries appear in recipient's Saved dropdown under 'Shared with Me' section"
- [ ] "Recipient can load a shared query into the editor and run it"
- [ ] "Recipient can fork a shared query as their own via 'Save as my own'"
- [ ] "Owner can unshare a query by unchecking a user in the share picker"
- [ ] "Shared query shows 'Updated' badge when query changed since recipient last viewed it"

## Files

- `backend/app/sparql/models.py`
- `backend/app/sparql/schemas.py`
- `backend/app/sparql/router.py`
- `backend/migrations/versions/008_sharing_promotion.py`
- `frontend/static/js/sparql-console.js`
- `frontend/static/css/workspace.css`
