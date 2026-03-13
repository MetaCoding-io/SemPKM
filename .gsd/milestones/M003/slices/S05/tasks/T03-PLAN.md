---
estimated_steps: 7
estimated_files: 7
---

# T03: Star button UI, FAVORITES explorer section, and E2E tests

**Slice:** S05 — Favorites System
**Milestone:** M003

## Description

Wire the backend endpoints to the user-facing UI: add a star button to the object toolbar, add a FAVORITES collapsible section to the explorer pane, and write Playwright E2E tests proving the complete flow works. This task delivers the user-visible feature and closes FAV-01 and FAV-02.

## Steps

1. Add star button to `object_tab.html` toolbar: In `.object-toolbar-actions`, before the mode-toggle button, add a star button with two Lucide icons (outline `star` and filled `star` with a `.star-filled` class). Use `is_favorite` template variable to set initial state. Wire `onclick="toggleFavorite('{{ object_iri }}')"`. The button gets `id="star-btn-{{ safe_id }}"` and `data-iri="{{ object_iri }}"` for JS targeting.
2. Pass `is_favorite` from the object tab rendering endpoint: In `backend/app/browser/objects.py` (the endpoint that renders `object_tab.html`), query `UserFavorite` for the current user + object IRI. Pass `is_favorite=True/False` to the template context. Add `get_db_session` dependency to the endpoint.
3. Create `backend/app/templates/browser/partials/favorites_section.html` — a collapsible `.explorer-section` following the exact pattern of `shared_nav_section.html`. Uses `hx-get="/browser/favorites/list"` with `hx-trigger="load, favoritesRefreshed from:body"` on the section body div so it loads on page init and refreshes when a star is toggled. Section title: "FAVORITES".
4. Include the favorites section partial in `workspace.html` — insert `{% include "browser/partials/favorites_section.html" %}` before the OBJECTS section (`section-objects` div).
5. Add `toggleFavorite(iri)` function to `workspace.js`: POST to `/browser/favorites/toggle` with `object_iri` form data. On success response, find all star buttons for this IRI (could be in multiple tabs) and swap their filled/outline state. The `HX-Trigger: favoritesRefreshed` header from the server response will be picked up by htmx to refresh the FAVORITES section body automatically (htmx processes trigger headers from fetch responses when using `htmx.ajax()` — but since we use plain fetch, dispatch a custom `favoritesRefreshed` event on document.body via `htmx.trigger(document.body, 'favoritesRefreshed')`).
6. Add CSS for star button in `workspace.css`: `.star-btn svg` with flex-shrink:0, stroke:currentColor, width/height:16px. `.star-btn.is-favorited svg` with fill:var(--color-warning) and stroke:var(--color-warning) for the filled state. Transition on fill for smooth toggle animation.
7. Write `e2e/tests/20-favorites/favorites.spec.ts` with Playwright tests: (a) star button visible on object tab, (b) clicking star adds to FAVORITES section, (c) FAVORITES section shows starred object with correct label, (d) clicking a favorite in FAVORITES opens the object tab, (e) clicking star again (unfavorite) removes from FAVORITES section, (f) empty FAVORITES shows hint text.

## Must-Haves

- [ ] Star button visible in object toolbar with correct initial state (filled if already favorited)
- [ ] Clicking star toggles visual state and persists via POST to toggle endpoint
- [ ] FAVORITES section appears in explorer pane above OBJECTS
- [ ] FAVORITES section lazy-loads on workspace init and refreshes on star toggle
- [ ] Clicking a favorite in FAVORITES list opens object tab via handleTreeLeafClick
- [ ] Unfavoriting removes object from FAVORITES list on next refresh
- [ ] Empty favorites shows "Star objects to add them here" hint
- [ ] E2E tests pass covering star toggle, FAVORITES display, navigation, and empty state
- [ ] Star button CSS follows Lucide icon rules (flex-shrink:0, stroke:currentColor)

## Verification

- `npx playwright test e2e/tests/20-favorites/ -v` — all E2E tests pass
- Visual check: star button toggles between outline and filled on click
- Visual check: FAVORITES section updates within ~1s of toggling star
- No JS console errors during star toggle or FAVORITES load

## Observability Impact

- Signals added/changed: Client-side — `toggleFavorite()` logs errors to console on fetch failure; server-side toggle logs remain from T02
- How a future agent inspects this: E2E test output shows pass/fail per scenario; browser console shows any JS errors; FAVORITES section HTML is inspectable via DevTools
- Failure state exposed: Fetch failure in `toggleFavorite()` logged to console with status code; FAVORITES section shows loading text if endpoint unreachable; star button state may desync if toggle fetch fails (user can re-click)

## Inputs

- `backend/app/browser/favorites.py` — toggle and list endpoints (from T02)
- `backend/app/favorites/models.py` — `UserFavorite` model (from T01)
- `backend/app/templates/browser/partials/favorites_list.html` — list template (from T02)
- `backend/app/templates/browser/object_tab.html` — current toolbar structure
- `backend/app/templates/browser/workspace.html` — explorer pane with section pattern
- `backend/app/templates/browser/partials/shared_nav_section.html` — reference for section pattern
- `frontend/static/css/workspace.css` — existing `.panel-btn svg`, `.explorer-section` CSS
- `frontend/static/js/workspace.js` — `handleTreeLeafClick()`, `refreshNavTree()`, Lucide patterns
- `e2e/tests/19-explorer-modes/explorer-mode-switching.spec.ts` — reference E2E pattern

## Expected Output

- `backend/app/templates/browser/object_tab.html` — updated with star button
- `backend/app/browser/objects.py` — updated to pass `is_favorite` to template
- `backend/app/templates/browser/partials/favorites_section.html` — new explorer section partial
- `backend/app/templates/browser/workspace.html` — updated to include favorites section
- `frontend/static/js/workspace.js` — updated with `toggleFavorite()` function
- `frontend/static/css/workspace.css` — updated with star button CSS
- `e2e/tests/20-favorites/favorites.spec.ts` — new E2E test file
