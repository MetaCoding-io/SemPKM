# S05: Favorites System

**Goal:** Users can star/unstar objects and access favorited objects from a dedicated FAVORITES section in the explorer pane.
**Demo:** Star button on object toolbar toggles favorite state; FAVORITES section in explorer shows all starred objects; clicking a favorite opens its object tab; unfavoriting removes it from the list; empty state shows hint text.

## Must-Haves

- `user_favorites` SQL table with `(user_id, object_iri, created_at)` and unique constraint on `(user_id, object_iri)`
- Alembic migration `009_user_favorites.py` creating the table
- `POST /browser/favorites/toggle` endpoint that adds or removes a favorite, returns updated star state
- `GET /browser/favorites/list` endpoint returning favorited objects as htmx tree HTML with labels and type icons
- Star button in object toolbar that toggles per-user favorite state
- FAVORITES collapsible section in explorer pane (above OBJECTS) that lazy-loads via htmx
- FAVORITES section refreshes when star is toggled (via HX-Trigger response header)
- Dangling favorites (deleted objects) handled gracefully — filtered out on list render
- Empty state message when user has no favorites
- E2E test coverage for star toggle and FAVORITES section

## Proof Level

- This slice proves: integration
- Real runtime required: yes (Docker Compose stack with triplestore for label/icon resolution)
- Human/UAT required: no

## Verification

- `docker compose exec backend .venv/bin/pytest backend/tests/test_favorites.py -v` — unit tests for UserFavorite model CRUD operations (toggle idempotency, list with dangling cleanup)
- `npx playwright test e2e/tests/20-favorites/` — E2E tests for star button toggle, FAVORITES section visibility, favorite navigation, unfavorite removal
- Manual check: `curl -s localhost:8001/browser/favorites/list -H 'Cookie: sempkm_session=...'` returns valid HTML partial

## Observability / Diagnostics

- Runtime signals: Python `logging.getLogger("app.browser.favorites")` logs toggle actions (user_id, object_iri, action=add/remove) at DEBUG level
- Inspection surfaces: `user_favorites` SQL table queryable directly; `/browser/favorites/list` endpoint returns current state as HTML
- Failure visibility: Toggle endpoint returns 401 for unauthenticated, 422 for missing IRI; list endpoint logs warning when dangling favorites are filtered out
- Redaction constraints: None — no secrets involved; object IRIs and user IDs are non-sensitive

## Integration Closure

- Upstream surfaces consumed: Explorer pane structure from S01 (`workspace.html` section pattern, `.explorer-section` CSS), `get_current_user` auth dependency, `LabelService.resolve_batch()` and `IconService.get_type_icon()` for label/icon resolution, `tree_children.html` rendering pattern for favorites list
- New wiring introduced in this slice: `favorites_router` included in `browser/router.py`; `UserFavorite` model imported in `migrations/env.py`; FAVORITES section partial included in `workspace.html`; star toggle JS function in `workspace.js`; `favoritesRefreshed` htmx trigger event
- What remains before the milestone is truly usable end-to-end: S06 (comments), S07 (ontology viewer + gist), S08 (class creation), S09 (admin stats), S10 (E2E gap coverage)

## Tasks

- [x] **T01: UserFavorite model, migration, and unit tests** `est:45m`
  - Why: The SQL storage layer is the foundation — toggle/list endpoints and all UI depend on it
  - Files: `backend/app/favorites/__init__.py`, `backend/app/favorites/models.py`, `backend/migrations/versions/009_user_favorites.py`, `backend/migrations/env.py`, `backend/tests/test_favorites.py`
  - Do: Create `UserFavorite` SQLAlchemy model with uuid PK, user_id FK to users.id, object_iri String(2048), created_at with server_default. Add UniqueConstraint on (user_id, object_iri). Write Alembic migration 009 with render_as_batch=True. Import model in migrations/env.py. Write unit tests covering: create favorite, duplicate insert ignored, delete favorite, list favorites by user, toggle idempotency.
  - Verify: `docker compose exec backend .venv/bin/pytest backend/tests/test_favorites.py -v` passes
  - Done when: Migration applies cleanly, model CRUD works in tests, unique constraint prevents duplicates

- [x] **T02: Favorites router with toggle and list endpoints** `est:1h`
  - Why: The API endpoints power both the star button (toggle) and the FAVORITES section (list) — needed before any UI work
  - Files: `backend/app/browser/favorites.py`, `backend/app/browser/router.py`, `backend/app/templates/browser/partials/favorites_list.html`
  - Do: Create `favorites_router` with two endpoints: (1) `POST /favorites/toggle` accepting `object_iri` form field, queries UserFavorite for current user — if exists DELETE else INSERT, returns HTML snippet with updated star button state plus `HX-Trigger: favoritesRefreshed` header; (2) `GET /favorites/list` queries UserFavorite for current user, batch-resolves labels via LabelService and types+icons via SPARQL, filters out dangling favorites (unresolved labels), renders `favorites_list.html` using tree-leaf pattern. Include `favorites_router` in `browser/router.py`. Create `favorites_list.html` template reusing tree-leaf structure with handleTreeLeafClick onclick, type icons, and empty state message.
  - Verify: `curl -X POST localhost:8001/browser/favorites/toggle -d 'object_iri=...'` returns star button HTML; `curl localhost:8001/browser/favorites/list` returns favorites HTML or empty state
  - Done when: Toggle endpoint adds/removes favorites idempotently, list endpoint returns labeled objects with icons, dangling IRIs are silently filtered, HX-Trigger header present on toggle response

- [x] **T03: Star button UI, FAVORITES explorer section, and E2E tests** `est:1h`
  - Why: Connects the backend to the user-facing UI — star button in object toolbar and FAVORITES section in explorer pane — and proves the whole flow works end-to-end
  - Files: `backend/app/templates/browser/object_tab.html`, `backend/app/templates/browser/workspace.html`, `backend/app/templates/browser/partials/favorites_section.html`, `frontend/static/css/workspace.css`, `frontend/static/js/workspace.js`, `e2e/tests/20-favorites/favorites.spec.ts`
  - Do: (1) Add star button to object_tab.html toolbar actions — two `<i data-lucide="star">` elements (outline and filled), toggle visibility based on `is_favorite` context var. Wire onclick to `toggleFavorite(iri)` JS function. (2) Pass `is_favorite` from object tab endpoint by querying UserFavorite. (3) Create `favorites_section.html` partial — collapsible `.explorer-section` with `hx-get="/browser/favorites/list"` `hx-trigger="load, favoritesRefreshed from:body"`. (4) Include partial in workspace.html before OBJECTS section. (5) Add `toggleFavorite(iri)` to workspace.js — fetch POST to toggle endpoint, swap star icon state, htmx triggers FAVORITES refresh via HX-Trigger. (6) Add CSS for star button (flex-shrink:0, stroke:currentColor, filled state uses fill). (7) Write Playwright E2E tests: star button visible on object tab, clicking star toggles state, FAVORITES section shows starred object, clicking favorite opens tab, unfavoriting removes from FAVORITES, empty state displays hint.
  - Verify: `npx playwright test e2e/tests/20-favorites/ --headed` passes all tests
  - Done when: Star toggle works visually and persists, FAVORITES section updates live, E2E tests pass covering FAV-01 and FAV-02

## Files Likely Touched

- `backend/app/favorites/__init__.py`
- `backend/app/favorites/models.py`
- `backend/migrations/versions/009_user_favorites.py`
- `backend/migrations/env.py`
- `backend/app/browser/favorites.py`
- `backend/app/browser/router.py`
- `backend/app/browser/objects.py` (pass `is_favorite` to object_tab template)
- `backend/app/templates/browser/object_tab.html`
- `backend/app/templates/browser/workspace.html`
- `backend/app/templates/browser/partials/favorites_section.html`
- `backend/app/templates/browser/partials/favorites_list.html`
- `frontend/static/css/workspace.css`
- `frontend/static/js/workspace.js`
- `backend/tests/test_favorites.py`
- `e2e/tests/20-favorites/favorites.spec.ts`
