# S05: Favorites System — Research

**Date:** 2026-03-12

## Summary

The favorites system is a straightforward per-user feature: a star button on object views toggles favorite state (SQL-backed), and a FAVORITES collapsible section in the explorer pane shows all starred objects with quick navigation. The risk is low — all needed patterns exist in the codebase. The main decisions are already locked (D021: SQL storage, not RDF) and the integration points are well-defined (explorer pane structure from S01, auth user model, existing tree leaf rendering).

The slice requires: (1) a new `user_favorites` SQLAlchemy model + Alembic migration, (2) a `POST /browser/favorites/toggle` endpoint, (3) a `GET /browser/favorites/list` endpoint returning htmx tree HTML, (4) a star button in the object toolbar, (5) a FAVORITES collapsible section in `workspace.html` that lazy-loads via htmx, and (6) E2E test coverage.

## Recommendation

Follow the existing patterns exactly:

- **Model**: New `UserFavorite` model in a new `backend/app/favorites/` module (or alongside auth models — but a dedicated module is cleaner since favorites has its own router). Follows the `sparql/models.py` pattern.
- **Migration**: `009_user_favorites.py` — simple table with `(user_id, object_iri, created_at)`, unique constraint on `(user_id, object_iri)`.
- **Router**: New `favorites_router` in `backend/app/browser/favorites.py`, included in `browser/router.py`. Two endpoints: toggle (POST) and list (GET).
- **Star button**: Add to `object_tab.html` toolbar (next to Edit/Save buttons). Uses `lucide:star` / `lucide:star` with fill for active state. Calls toggle endpoint via fetch, swaps icon state client-side.
- **Explorer section**: New FAVORITES section in `workspace.html` inserted before OBJECTS. Uses `hx-get="/browser/favorites/list"` with `hx-trigger="load"`. Same `explorer-section` pattern as SHARED section.
- **Favorites list**: Renders as tree-leaf nodes (reuse `tree_children.html` pattern) with type icons. Clicking opens the object tab via `handleTreeLeafClick`.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| SQL model + async sessions | SQLAlchemy 2.0 ORM + `get_db_session` dependency | Project standard; async, tested |
| DB migration | Alembic with `render_as_batch=True` | Already 8 migrations; chain continues |
| Auth context in endpoints | `get_current_user` FastAPI dependency | Provides `User` with `.id` for scoping |
| Explorer section UI | `.explorer-section` CSS + `shared_nav_section.html` pattern | Exact pattern for collapsible sections |
| Tree leaf rendering | `tree_children.html` pattern | Click-to-open, icons, drag support |
| Label resolution | `LabelService.resolve_batch()` | Already used by all explorer modes |
| Icon resolution | `IconService.get_type_icon()` | Already used by all tree renderers |

## Existing Code and Patterns

- `backend/app/auth/models.py` — ORM model pattern: `User`, `UserSetting`. The `UserFavorite` model follows this exact pattern (uuid PK, user_id FK, timestamps).
- `backend/app/sparql/models.py` — More recent ORM models. Good reference for `UniqueConstraint` usage.
- `backend/app/db/session.py` — `get_db_session()` dependency provides `AsyncSession`. Commit-on-success, rollback-on-error.
- `backend/app/browser/router.py` — Sub-router inclusion pattern. Add `favorites_router` in the include chain.
- `backend/app/browser/workspace.py` — Explorer mode handlers, `_execute_sparql_select`, `_bindings_to_objects`. The favorites list endpoint needs label + icon resolution for stored IRIs.
- `backend/app/templates/browser/workspace.html` — Explorer pane with OBJECTS, VIEWS, MY VIEWS, SHARED sections. FAVORITES section goes before OBJECTS.
- `backend/app/templates/browser/partials/shared_nav_section.html` — Reference pattern for a lazy-loaded collapsible explorer section. FAVORITES section follows this exactly.
- `backend/app/templates/browser/tree_children.html` — Tree leaf rendering with `handleTreeLeafClick`, `data-iri`, drag support, icons. Favorites list reuses this pattern.
- `backend/app/templates/browser/object_tab.html` — Object toolbar with mode toggle and save buttons. Star button goes in `.object-toolbar-actions`.
- `backend/migrations/versions/008_sharing_promotion.py` — Latest migration. Next is `009` with `down_revision = "008"`.
- `backend/migrations/env.py` — Must import new model here for Alembic autogenerate awareness.
- `frontend/static/js/workspace.js` — `handleTreeLeafClick()` (line ~992), `clearSelection()`, `initExplorerMode()`. Favorites click handler reuses `handleTreeLeafClick`. Star toggle needs a small JS function.
- `frontend/static/css/workspace.css` — `.explorer-section-*` CSS classes, `.tree-leaf` styling. Star button needs minimal CSS (lucide icon + fill toggle).

## Constraints

- **SQLite + PostgreSQL dual support**: Alembic migration uses `render_as_batch=True` for SQLite ALTER TABLE compatibility. Use `sa.String()` for IRI storage (not Text — IRIs are bounded length).
- **Favorites store object IRIs as strings**: IRIs from the triplestore are opaque strings to SQL. No FK to triplestore. If an object is deleted from RDF, the favorite becomes a dangling reference — handle gracefully in the list endpoint (skip objects whose labels can't be resolved, or show as "[deleted]").
- **User.id is uuid.UUID**: FK in `user_favorites` must match.
- **No RDF for favorites** (D021): This is a user-preference, not knowledge-graph data.
- **Explorer section ordering**: FAVORITES should appear before OBJECTS per boundary map ("adds new section below OBJECTS" — but typical UX puts favorites above the main list for quick access). Confirm during implementation — the roadmap says "separate from OBJECTS", not explicit position. Recommend: above OBJECTS.
- **htmx trigger on favorite toggle**: When a user stars/unstars, the FAVORITES section body should refresh. Use `HX-Trigger` response header to trigger re-fetch.
- **No build step for JS**: All JS is vanilla, loaded as static files. Any new JS for star toggle goes inline in the template or added to `workspace.js`.

## Common Pitfalls

- **Dangling favorites after object deletion** — The RDF object may be deleted but the SQL favorite row persists. The list endpoint must handle missing labels gracefully: either filter out dangling favorites or show them with a "[deleted]" label. Recommend: filter out + periodically clean (or clean on list load).
- **Race condition on rapid toggle** — User double-clicks star. Use `INSERT OR IGNORE` / `ON CONFLICT DO NOTHING` for add, and a simple `DELETE` for remove. The toggle endpoint should be idempotent: if already favorited, unfavorite; if not, favorite. Single SQL query per toggle.
- **IRI length in SQL column** — IRIs can be long (200+ chars). Use `String(2048)` to be safe, matching URL length conventions.
- **Lucide icon state** — Lucide replaces `<i>` with `<svg>`. To toggle between outline star and filled star, need to either: (a) swap the `data-lucide` attribute and re-call `lucide.createIcons()`, or (b) use two elements and toggle visibility. Option (b) is simpler and avoids Lucide re-render timing issues.
- **FAVORITES section empty state** — When user has no favorites, show "No favorites yet" with a hint ("Star objects to add them here"). Don't hide the section — users need to discover it.
- **Type resolution for favorites** — To show type icons in the favorites list, need to query `rdf:type` for each favorited IRI from the triplestore. Batch this in a single SPARQL query, not N+1.

## Open Risks

- **Object deletion doesn't clean up favorites** — Low risk (cosmetic), but needs graceful handling. Could add a post-delete hook to clean favorites, or handle lazily on list render. Recommend: lazy cleanup on list render (simpler, no coupling to delete path).
- **Performance with many favorites** — Unlikely bottleneck (users won't star thousands of objects), but the list endpoint does a SPARQL query for type resolution + label resolution. Both are already batched via `LabelService`. No concern at realistic scale.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| htmx | `mindrally/skills@htmx` (198 installs) | available — not needed, patterns well-established in codebase |
| FastAPI | `wshobson/agents@fastapi-templates` (6.2K installs) | available — not needed, patterns well-established in codebase |
| SQLAlchemy | (search timed out) | not needed — patterns well-established in codebase |

All technologies are well-covered by existing codebase patterns. No skill installation needed.

## Sources

- Codebase exploration of `backend/app/auth/models.py`, `backend/app/sparql/models.py`, `backend/app/browser/workspace.py`, `backend/app/browser/router.py`, `backend/app/templates/browser/workspace.html`, `backend/app/templates/browser/partials/shared_nav_section.html`, `backend/app/templates/browser/tree_children.html`, `backend/app/templates/browser/object_tab.html`
- Decision register entries D021 (SQL storage for favorites), D031 (explorer endpoint pattern), D034 (selection clearing on mode switch)
- Requirements FAV-01 (star/unstar objects), FAV-02 (FAVORITES explorer section)
- Boundary map: S05 produces `user_favorites` SQL table, toggle endpoint, star button component, FAVORITES section, favorites list endpoint. Consumes from S01: explorer pane structure.
