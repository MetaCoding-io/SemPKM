---
estimated_steps: 5
estimated_files: 4
---

# T02: Favorites router with toggle and list endpoints

**Slice:** S05 — Favorites System
**Milestone:** M003

## Description

Create the two API endpoints that power the favorites feature: a POST toggle endpoint for starring/unstarring objects, and a GET list endpoint that returns favorited objects as htmx-ready tree HTML with resolved labels and type icons. Wire the new router into the browser router coordinator.

## Steps

1. Create `backend/app/browser/favorites.py` with `favorites_router = APIRouter()`. Implement `POST /favorites/toggle`: accept `object_iri` as form field, get current user via `get_current_user` dependency, get db session via `get_db_session`. Query `UserFavorite` for (user.id, object_iri) — if exists, delete it (action="removed"); if not, insert new row (action="added"). Return an HTMLResponse with the updated star button HTML snippet (filled star if added, outline if removed). Set `HX-Trigger: favoritesRefreshed` response header so the FAVORITES section auto-refreshes.
2. Implement `GET /favorites/list`: query all `UserFavorite` rows for current user ordered by `created_at` desc. Extract object IRIs. Batch-resolve labels via `LabelService.resolve_batch()`. Batch-resolve types and icons via a single SPARQL query for `rdf:type` of all favorited IRIs, then `IconService.get_type_icon()` for each type. Filter out dangling favorites (IRIs where label resolution returned None/empty — log a warning with the count of dangling entries). Render `favorites_list.html` template with the resolved objects list. Handle empty favorites gracefully (template shows hint text).
3. Create `backend/app/templates/browser/partials/favorites_list.html` — reuse tree-leaf rendering pattern from `tree_children.html`: each favorite as a `.tree-leaf` div with `data-iri`, `onclick="handleTreeLeafClick(...)"`, type icon via Lucide, and label text. Include empty state: `<div class="tree-empty">Star objects to add them here</div>` when list is empty.
4. Include `favorites_router` in `backend/app/browser/router.py` — add import and `router.include_router(favorites_router)` after the existing includes.
5. Test endpoints manually against running Docker stack: POST toggle creates/removes favorites, GET list returns labeled objects or empty state, HX-Trigger header present.

## Must-Haves

- [ ] `POST /browser/favorites/toggle` accepts `object_iri`, adds or removes favorite, returns updated star HTML
- [ ] `GET /browser/favorites/list` returns tree-leaf HTML with resolved labels and type icons
- [ ] Toggle endpoint is idempotent — rapid double-clicks don't produce errors
- [ ] HX-Trigger response header set on toggle to refresh FAVORITES section
- [ ] Dangling favorites (deleted objects) filtered out of list silently with logged warning
- [ ] Empty state message rendered when user has no favorites
- [ ] Router wired into browser coordinator

## Verification

- `curl -X POST localhost:8001/browser/favorites/toggle -d 'object_iri=urn:test:obj1' -H 'Cookie: sempkm_session=...'` — returns star button HTML, repeated call toggles state
- `curl localhost:8001/browser/favorites/list -H 'Cookie: sempkm_session=...'` — returns HTML with favorited objects or empty state
- Response headers include `HX-Trigger: favoritesRefreshed` on toggle response
- No 500 errors in backend logs during toggle/list operations

## Observability Impact

- Signals added/changed: `app.browser.favorites` logger — DEBUG logs for toggle actions (user_id, object_iri, action=add/remove), WARNING for dangling favorites count on list render
- How a future agent inspects this: Hit `/browser/favorites/list` to see current favorites as HTML; query `user_favorites` table for raw data; check backend logs for toggle activity
- Failure state exposed: 401 if unauthenticated, 422 if object_iri missing from toggle request, WARNING log when dangling favorites exist

## Inputs

- `backend/app/favorites/models.py` — `UserFavorite` model (from T01)
- `backend/app/db/session.py` — `get_db_session` dependency
- `backend/app/auth/dependencies.py` — `get_current_user` dependency
- `backend/app/browser/workspace.py` — reference for `LabelService`, `IconService`, SPARQL query patterns, `_execute_sparql_select`, `_bindings_to_objects`
- `backend/app/templates/browser/tree_children.html` — tree-leaf rendering pattern to reuse

## Expected Output

- `backend/app/browser/favorites.py` — favorites router with toggle and list endpoints
- `backend/app/browser/router.py` — updated to include favorites_router
- `backend/app/templates/browser/partials/favorites_list.html` — tree-leaf HTML template for favorites
