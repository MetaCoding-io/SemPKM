---
id: T02
parent: S05
milestone: M003
provides:
  - POST /browser/favorites/toggle endpoint for starring/unstarring objects
  - GET /browser/favorites/list endpoint returning tree-leaf HTML with resolved labels and type icons
  - favorites_list.html template with empty state
key_files:
  - backend/app/browser/favorites.py
  - backend/app/browser/router.py
  - backend/app/templates/browser/partials/favorites_list.html
key_decisions:
  - Toggle endpoint returns full star button HTML snippet for htmx outerHTML swap rather than JSON — keeps htmx-first pattern
  - Dangling favorite detection uses label==rawIRI AND no type in triplestore as heuristic — avoids false positives from objects with raw IRI labels
patterns_established:
  - favorites_router follows same sub-router pattern as workspace_router, search_router etc
  - HX-Trigger header "favoritesRefreshed" enables decoupled FAVORITES section refresh
observability_surfaces:
  - app.browser.favorites logger — DEBUG for toggle actions (user_id, object_iri, action), WARNING for dangling favorites count
  - GET /browser/favorites/list — returns current favorites as HTML (inspection endpoint)
  - 401 for unauthenticated, 422 for missing object_iri on toggle
duration: 20m
verification_result: passed
completed_at: 2026-03-13
blocker_discovered: false
---

# T02: Favorites router with toggle and list endpoints

**Created POST toggle and GET list API endpoints for the favorites feature with label/icon resolution and dangling-favorite filtering.**

## What Happened

Built `backend/app/browser/favorites.py` with two endpoints:

1. **POST /browser/favorites/toggle** — accepts `object_iri` form field, queries UserFavorite for the current user. If exists, deletes (unfavorite); if not, inserts (favorite). Returns an HTML snippet of the updated star button (filled/outline states with htmx `hx-post` wiring). Sets `HX-Trigger: favoritesRefreshed` response header.

2. **GET /browser/favorites/list** — queries all UserFavorite rows for the current user ordered by `created_at` desc. Batch-resolves labels via `LabelService.resolve_batch()`. Batch-resolves types via a single SPARQL query for `rdf:type` of all favorited IRIs, then `IconService.get_type_icon()` for each. Filters out dangling favorites (IRIs with no resolved label and no type). Renders `favorites_list.html` template.

Created `favorites_list.html` reusing the tree-leaf pattern from `tree_children.html` — each favorite as a `.tree-leaf` div with `data-iri`, `onclick="handleTreeLeafClick(...)"`, Lucide type icon, and label text. Empty state shows "Star objects to add them here".

Wired `favorites_router` into `browser/router.py` after the existing sub-routers.

## Verification

- `curl -X POST .../browser/favorites/toggle -d 'object_iri=urn:sempkm:model:basic-pkm:seed-person-carol'` → 200, returns star button HTML with `is-favorited` class
- Second toggle of same IRI → 200, returns star button HTML without `is-favorited` class (unfavorited)
- `curl .../browser/favorites/list` with favorited objects → 200, returns tree-leaf HTML with resolved labels ("Bobby Martinez", "Carol Singh") and Person type icons (user icon, #e11d48)
- `curl .../browser/favorites/list` with no favorites → 200, returns empty state div
- Response headers confirmed: `HX-Trigger: favoritesRefreshed` present on toggle responses
- Rapid 3x toggle calls → all 200, no 500 errors (idempotency confirmed)
- Unauthenticated GET /favorites/list → 302 redirect
- Missing object_iri on POST /favorites/toggle → 422 with validation error
- No errors in backend logs during all toggle/list operations
- `backend/.venv/bin/pytest backend/tests/test_favorites.py -v` → 6 passed (T01 model tests still green)

### Slice-level verification status

- ✅ `pytest backend/tests/test_favorites.py -v` — 6 passed
- ⏳ `npx playwright test e2e/tests/20-favorites/` — E2E tests are T03 scope
- ✅ Manual curl check — valid HTML partial returned

## Diagnostics

- Hit `GET /browser/favorites/list` to see current favorites as HTML
- Query `user_favorites` table directly for raw data
- Check backend logs for toggle activity (DEBUG level)
- Dangling favorites logged at WARNING level when filtered from list render
- Toggle returns 401 unauthenticated, 422 missing IRI

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/favorites.py` — new favorites router with toggle and list endpoints
- `backend/app/browser/router.py` — added favorites_router import and include
- `backend/app/templates/browser/partials/favorites_list.html` — tree-leaf HTML template for favorites list with empty state
