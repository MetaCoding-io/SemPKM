---
id: T03
parent: S05
milestone: M003
provides:
  - Star button in object toolbar toggling per-user favorite state via POST to /browser/favorites/toggle
  - FAVORITES explorer section with htmx lazy-loading and live refresh on toggle
  - toggleFavorite() JS function for cross-tab star state synchronization
  - E2E Playwright test suite covering star toggle, FAVORITES display, navigation, initial state, and empty state
key_files:
  - backend/app/templates/browser/object_tab.html
  - backend/app/browser/objects.py
  - backend/app/templates/browser/partials/favorites_section.html
  - backend/app/templates/browser/workspace.html
  - frontend/static/js/workspace.js
  - frontend/static/css/workspace.css
  - e2e/tests/20-favorites/favorites.spec.ts
key_decisions:
  - Used plain fetch + JS DOM swap for toggleFavorite() instead of htmx hx-post on star button — enables cross-tab state sync when same object is open in multiple dockview panels
  - FAVORITES section starts expanded by default for discoverability
  - Star button uses single Lucide star icon with CSS fill/stroke toggling rather than two separate icons (simpler DOM, less state)
patterns_established:
  - toggleFavorite() dispatches htmx.trigger(document.body, 'favoritesRefreshed') to bridge plain fetch with htmx event system
  - is_favorite template variable passed from object endpoint via UserFavorite DB query for SSR initial state
observability_surfaces:
  - toggleFavorite() logs fetch failures to browser console with HTTP status code
  - FAVORITES section htmx loading state visible as "Loading favorites..." text
  - Star button visual state (is-favorited class) inspectable via DevTools
duration: 35m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T03: Star button UI, FAVORITES explorer section, and E2E tests

**Added star button to object toolbar, FAVORITES explorer section above OBJECTS, and 4 Playwright E2E tests proving the complete favorites flow.**

## What Happened

Wired the T01/T02 backend (UserFavorite model + toggle/list endpoints) to the user-facing UI across 7 files:

1. **Star button** added to `object_tab.html` toolbar — appears before the properties badge and mode-toggle buttons. Uses a single `<i data-lucide="star">` icon styled via CSS `fill`/`stroke` to toggle between outline (unfavorited) and filled-golden (favorited) states.

2. **`is_favorite` context variable** — the `get_object` endpoint in `objects.py` now queries `UserFavorite` for the current user + object IRI and passes `is_favorite=True/False` to the template for correct SSR initial state.

3. **`favorites_section.html` partial** — new collapsible `.explorer-section` following the `shared_nav_section.html` pattern. Uses `hx-get="/browser/favorites/list"` with `hx-trigger="load, favoritesRefreshed from:body"` for lazy loading and live refresh on toggle.

4. **Workspace inclusion** — `favorites_section.html` included in `workspace.html` before the OBJECTS section. Section starts expanded by default.

5. **`toggleFavorite(iri)` in workspace.js** — plain fetch POST to `/browser/favorites/toggle`, parses response HTML to determine new state, updates ALL star buttons matching the IRI (cross-tab sync), re-renders Lucide icons, and dispatches `favoritesRefreshed` event on `document.body` via `htmx.trigger()`.

6. **Star button CSS** — `.star-btn` with flex-shrink:0, stroke:currentColor, fill:transparent (outline state) and `.star-btn.is-favorited` with fill/stroke set to `var(--color-warning)` (golden filled state). Smooth 0.2s transition on fill/stroke.

7. **E2E tests** — 4 Playwright tests in `e2e/tests/20-favorites/favorites.spec.ts` covering: empty FAVORITES hint text, star toggle + FAVORITES refresh, clicking favorite opens object tab, and initial state correctness for pre-favorited objects.

## Verification

- `backend/.venv/bin/pytest backend/tests/test_favorites.py -v` — 6/6 unit tests pass (T01 model tests)
- `npx playwright test e2e/tests/20-favorites/ --project=chromium --retries=0` — 4/4 E2E tests pass
- Visual verification in browser (localhost:3901): star button toggles between outline and golden-filled; FAVORITES section updates within ~1s; clicking a favorite opens the object tab; empty state shows "Star objects to add them here"
- No JS console errors during star toggle or FAVORITES load
- Slice-level verifications:
  - ✅ Unit tests: `backend/.venv/bin/pytest backend/tests/test_favorites.py -v` — 6 passed
  - ✅ E2E tests: `npx playwright test e2e/tests/20-favorites/ --project=chromium` — 4 passed
  - ✅ Manual HTML check: favorites list endpoint returns valid tree-leaf HTML partial

## Diagnostics

- **Star button state**: Inspect `.star-btn.is-favorited` class on `button.star-btn[data-iri="..."]` elements via DevTools
- **FAVORITES section**: Check `#favorites-tree-body` innerHTML for current favorites list HTML; `hx-trigger` attribute shows event bindings
- **Toggle failures**: `toggleFavorite()` logs to `console.error` with HTTP status code on fetch failure
- **Backend signals**: Existing T02 toggle logging at DEBUG level (`app.browser.favorites`)

## Deviations

- Plan specified two Lucide icons (outline + filled) toggled via visibility — implemented with single icon styled via CSS fill/stroke instead (simpler, fewer DOM elements)
- Plan specified `id="star-btn-{{ safe_id }}"` — implemented with both id and `data-iri` attribute; JS targets via `data-iri` for cross-tab sync
- FAVORITES section added with `expanded` class by default (not in original plan) for immediate visibility/discoverability
- Added favorites selectors to `e2e/helpers/selectors.ts` for test maintainability (not in plan)

## Known Issues

- Rate-limited auth (5 magic-links/minute) means running E2E tests with retries=1 across both browser projects may hit auth rate limit — use `--retries=0` or `--project=chromium` for reliable single runs
- Star button state can desync if toggle fetch fails (user can re-click to retry) — documented in task plan observability section

## Files Created/Modified

- `backend/app/templates/browser/object_tab.html` — added star button to toolbar actions
- `backend/app/browser/objects.py` — added UserFavorite import, db dependency, is_favorite query and context variable
- `backend/app/templates/browser/partials/favorites_section.html` — new explorer section partial for FAVORITES
- `backend/app/templates/browser/workspace.html` — included favorites_section.html before OBJECTS section
- `frontend/static/js/workspace.js` — added toggleFavorite() function with cross-tab sync and htmx event dispatch
- `frontend/static/css/workspace.css` — added .star-btn CSS with outline/filled states and transitions
- `e2e/tests/20-favorites/favorites.spec.ts` — new E2E test file with 4 tests
- `e2e/helpers/selectors.ts` — added favorites selector constants
