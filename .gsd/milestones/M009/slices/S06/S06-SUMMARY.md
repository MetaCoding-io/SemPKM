---
id: S06
parent: M009
milestone: M009
provides:
  - Dynamic right pane endpoint merging platform sections + app contributions filtered by object type
  - App view contributions in Views explorer with lazy-load htmx pattern
  - App command palette entries fetched as JSON and injected into ninja-keys
  - Object renderer override dispatch in get_object() with AppRendererPref conflict resolution
  - object_tab_app.html template for app-rendered objects with flip card and edit fallback
  - Admin renderer assignment section with set/clear controls and Active/Default/Overridden status
  - loadRightPane() JS function with AbortController request cancellation
  - openAppViewTab() JS function with dockview tab dedup
  - apps_api_router for JSON endpoints (commands)
requires:
  - slice: S04
    provides: app_shell.html, [Apps] sidebar, fragment loading via htmx, browser apps.py sub-router
  - slice: S05
    provides: AppRegistry with renderer/contribution metadata, AppRendererPref model, scheduler running, permissions enforced
affects:
  - S07
key_files:
  - backend/app/apps/registry.py
  - backend/app/browser/apps.py
  - backend/app/browser/objects.py
  - backend/app/apps/admin_router.py
  - backend/app/templates/browser/right_pane_sections.html
  - backend/app/templates/browser/object_tab_app.html
  - backend/app/templates/browser/app_view_tab.html
  - backend/app/templates/browser/app_views_explorer.html
  - backend/app/templates/browser/workspace.html
  - backend/app/templates/browser/views_explorer.html
  - backend/app/templates/admin/apps/detail.html
  - frontend/static/js/workspace.js
  - frontend/static/js/workspace-layout.js
  - frontend/static/css/workspace.css
  - backend/app/main.py
  - backend/tests/test_right_pane_sections.py
  - backend/tests/test_app_views_commands.py
  - backend/tests/test_renderer_overrides.py
  - backend/tests/test_admin_renderers.py
key_decisions:
  - D147: Dynamic right pane via single endpoint merging platform + app sections, replacing 3 hardcoded <details> blocks
  - D148: Renderer override dispatch pattern — registry → pref table → template swap, silent fallback on any error
  - Used hx-trigger="load" on dynamically-swapped sections (not "toggle once") since sections are already visible when injected
  - Created separate apps_api_router for JSON endpoints following dashboard/workflow pattern
  - appcmd: prefix for ninja-keys entry IDs to namespace and allow clean filtering on refresh
patterns_established:
  - Dynamic right pane pattern: endpoint returns full section HTML → JS swaps into #right-pane-dynamic → htmx.process() for nested attributes
  - AbortController cancellation for rapid tab switching — stored on window._rightPaneAbort
  - Views explorer lazy-load: htmx div with hx-trigger="load, appsRefreshed from:body" for app view contributions
  - Command palette injection: fetch JSON → filter existing appcmd: entries → concat new entries
  - Renderer override dispatch: registry lookup → pref table check → template swap with context augmentation
  - App renderer template: platform toolbar chrome preserved, content area replaced with htmx fragment div
  - Edit fallback: has_custom_edit=False → standard SHACL form + body editor on edit face
  - Admin renderer management: _build_renderer_assignments() queries pref table, builds status list with Active/Default/Overridden states
observability_surfaces:
  - Logger app.browser.apps at DEBUG — type count + app section count per right pane request
  - Logger app.browser.apps at WARNING — triplestore/registry failures with graceful degradation
  - Logger app.browser.objects at DEBUG — renderer override dispatch with app_id and fragment URLs
  - Logger app.browser.objects at WARNING — renderer lookup failures with traceback
  - Logger app.apps.admin_router at INFO — renderer pref set/clear operations
  - GET /browser/apps/right-pane-sections?iri=<IRI> — inspectable merged section HTML
  - GET /api/apps/commands — inspectable JSON array of registered commands
  - SELECT * FROM app_renderer_prefs — active renderer preferences
  - window._rightPaneAbort in browser devtools — cancellation state
  - HTML response with app-renderer-content class indicates renderer override active
drill_down_paths:
  - .gsd/milestones/M009/slices/S06/tasks/T01-SUMMARY.md
  - .gsd/milestones/M009/slices/S06/tasks/T02-SUMMARY.md
  - .gsd/milestones/M009/slices/S06/tasks/T03-SUMMARY.md
  - .gsd/milestones/M009/slices/S06/tasks/T04-SUMMARY.md
duration: ~2h
verification_result: passed
completed_at: 2026-03-17
---

# S06: Frontend Level 2+3 — Workspace Contributions & Renderer Overrides

**All 3 frontend integration levels complete — apps can inject right pane sections, view entries, command palette commands, and custom object renderers into the workspace, with admin-controlled renderer conflict resolution.**

## What Happened

This slice completed the frontend integration surface for the app platform across four tasks, each adding a distinct integration point.

**T01 — Dynamic right pane (biggest structural change):** Replaced the 3 hardcoded `<details>` blocks in workspace.html (Relations, Lint, Comments) with a single `<div id="right-pane-dynamic">` that loads from `GET /browser/apps/right-pane-sections?iri=`. The endpoint queries the object's rdf:type, collects matching app contributions from `AppRegistry.get_right_pane_contributions()`, merges with platform sections, and renders a unified template. Platform sections always appear first; app contributions follow sorted by priority. In workspace.js, the three separate `loadRightPaneSection()` calls were replaced by a single `loadRightPane(objectIri)` with AbortController cancellation for rapid tab switching. The graceful degradation path was verified: triplestore/registry failures return platform-only sections.

**T02 — Views explorer + command palette:** Added `GET /browser/apps/views/explorer` returning app view entries for the Views sidebar, lazy-loaded via htmx between Graph View and Saved Views. Created `openAppViewTab()` JS function following the existing `openAppPageTab()` pattern with tab dedup. Added `GET /api/apps/commands` returning JSON for the command palette, with a new `apps_api_router` mounted at `/api/apps`. In workspace.js, `_loadAppCommandEntries()` fetches commands on palette init and injects them into ninja-keys with `appcmd:` prefix, handling dialog/post/navigate action types.

**T03 — Renderer override dispatch (most surgical change):** Added `get_renderer(type_iri)` and `get_renderer_for_app(app_id, type_iri)` to AppRegistry. In `get_object()`, the new `_get_renderer_override()` async helper checks each of the object's type IRIs against the registry, then consults `AppRendererPref` for user preference overrides. When a match is found, the endpoint renders `object_tab_app.html` instead of `object_tab.html`. The app template preserves the platform toolbar (label, type badge, favorite, mode toggle) and loads the app's read fragment via htmx. Edit face falls back to standard SHACL form if the app doesn't declare an edit renderer. Embed mode is unaffected — always uses `object_embed.html`.

**T04 — Admin renderer management:** Replaced the renderer placeholder in the admin detail page with a real table showing declared object renderers with Type, Mode, Status (Active/Default/Overridden badges), and Action buttons. Added `POST /admin/apps/{app_id}/renderers/set` (upserts AppRendererPref) and `POST /admin/apps/{app_id}/renderers/clear` (deletes pref). Both endpoints require owner role and log operations at INFO level.

## Verification

- `test_right_pane_sections.py` — 16/16 passed (6 registry + 10 endpoint tests)
- `test_app_views_commands.py` — 13/13 passed (4 views explorer + 3 view tab + 6 commands API tests)
- `test_renderer_overrides.py` — 19/19 passed (7 registry + 5 helper + 7 dispatch tests)
- `test_admin_renderers.py` — 13/13 passed (5 display + 3 set + 2 clear + 2 role + 1 placeholder tests)
- Full test suite: **1194 passed, zero regressions** (excluding pre-existing test_sdk_integration.py module import issue)
- All modified `.py` files pass `ast.parse()` syntax check
- `from app.browser.apps import apps_router` — importable without errors
- Structural grep checks: `right-pane-dynamic` in workspace.html ✓, `loadRightPaneSection` removed from workspace.js ✓, `openAppViewTab` present ✓, `app-view` case in workspace-layout.js ✓

## Requirements Advanced

- **APP-08** (frontend L2 — workspace contributions) — Right pane sections, views explorer entries, and command palette injection all implemented with contract tests. Runtime proof deferred to S07.
- **APP-09** (frontend L3 — renderer overrides) — get_object() dispatch, AppRendererPref conflict resolution, object_tab_app.html template all implemented with contract tests. Runtime proof deferred to S07.
- **APP-10** (admin monitoring portal) — Admin detail page now shows renderer assignments with set/clear controls, completing the S06 supporting contribution.

## Requirements Validated

- None moved to validated — APP-08 and APP-09 need live runtime verification in S07 Docker stack to validate.

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- **hx-trigger="load" instead of "toggle once":** Plan didn't specify trigger behavior. Since dynamically-swapped sections are already visible, "toggle once" would require user click to load content. "load" triggers immediately on swap, matching the old hardcoded behavior.
- **Separate apps_api_router:** Plan didn't specify router structure for the commands JSON endpoint. Created a separate API router following the dashboard/workflow pattern of browser + api router split.
- **Used app name as renderer_label:** Plan referenced `renderer.label` from manifest, but `AppObjectRenderer` model has no `label` field. Used `manifest.name` instead.
- **Test counts exceed plan minimums:** 61 total tests vs. plan's implied ~20. Expanded coverage for edge cases and graceful degradation paths.

## Known Limitations

- **test_sdk_integration.py** excluded from regression runs due to pre-existing `sempkm_app_sdk` module import failure — not introduced by S06.
- **Renderer override only matches full type IRIs** — no prefix expansion or pattern matching (v1 constraint, documented in T03).
- **App command palette entries only loaded at workspace init** — new app installs require page reload to appear in palette. Could be enhanced with event-driven refresh.
- **Right pane app sections depend on app being in "running" state** — stopped apps' contributions are excluded even if content is cacheable.

## Follow-ups

- S07 must exercise all 4 integration points (right pane, views, commands, renderers) in the test app manifest to prove they work end-to-end in Docker.
- The DeprecationWarning on S04's `apps_explorer` and `app_page` endpoints (old TemplateResponse signature) should be cleaned up — not blocking but noisy.

## Files Created/Modified

- `backend/app/apps/registry.py` — added `get_right_pane_contributions()`, `get_renderer()`, `get_renderer_for_app()` methods
- `backend/app/browser/apps.py` — added 4 new endpoints (right-pane-sections, views explorer, view tab, commands JSON) + `apps_api_router`
- `backend/app/browser/objects.py` — added `_get_renderer_override()` helper and renderer dispatch in `get_object()`
- `backend/app/apps/admin_router.py` — added `_build_renderer_assignments()`, `renderer_set()`, `renderer_clear()` endpoints
- `backend/app/main.py` — imported and mounted `apps_api_router`
- `backend/app/templates/browser/right_pane_sections.html` — new: platform + app section loop with htmx lazy loading
- `backend/app/templates/browser/object_tab_app.html` — new: app fragment loading with platform toolbar and flip card
- `backend/app/templates/browser/app_view_tab.html` — new: app view tab with fragment loading
- `backend/app/templates/browser/app_views_explorer.html` — new: tree-leaf entries for app views
- `backend/app/templates/browser/workspace.html` — replaced 3 hardcoded `<details>` with `<div id="right-pane-dynamic">`
- `backend/app/templates/browser/views_explorer.html` — added htmx lazy-load for app views
- `backend/app/templates/admin/apps/detail.html` — replaced renderer placeholder with real table UI
- `frontend/static/js/workspace.js` — replaced `loadRightPaneSection()` with `loadRightPane()` + AbortController, added `openAppViewTab()`, `_loadAppCommandEntries()`
- `frontend/static/js/workspace-layout.js` — added `app-view` special-panel factory case
- `frontend/static/css/workspace.css` — added `.app-renderer-content`, `.app-renderer-loading`, `.object-toolbar-app-badge` styles
- `backend/tests/test_right_pane_sections.py` — 16 tests
- `backend/tests/test_app_views_commands.py` — 13 tests
- `backend/tests/test_renderer_overrides.py` — 19 tests
- `backend/tests/test_admin_renderers.py` — 13 tests
- `backend/tests/test_app_admin.py` — updated placeholder assertion for new renderer section

## Forward Intelligence

### What the next slice should know
- The test app manifest in S07 must declare `ui.contributions.rightPane`, `ui.contributions.views`, `ui.contributions.commandPalette`, and `ui.objectRenderers` to exercise all four integration points. Each has a specific JSON structure — see `AppManifestSchema` in `manifest.py` for the Pydantic models.
- All 4 S06 endpoints filter by running app status. The test app must be started (not just installed) for contributions to appear.
- The views explorer lazy-loads app views via htmx with `hx-trigger="load, appsRefreshed from:body"` — S07's install flow should trigger `appsRefreshed` to refresh the views list.
- Command palette app entries only load at workspace init — after installing an app via admin, the page must be reloaded for commands to appear.

### What's fragile
- **Right pane depends on triplestore type query** — if the object's rdf:type triples are missing or the triplestore is slow, app sections won't appear (graceful degradation to platform-only). The test app should create objects with explicit rdf:type assertions.
- **Renderer dispatch checks types in order** — `_get_renderer_override()` returns on first match. If an object has multiple types, the first matching type determines the renderer. Test app should use a single distinctive type for clarity.

### Authoritative diagnostics
- `GET /browser/apps/right-pane-sections?iri=<IRI>` — curl this directly to see what sections render for any object
- `GET /api/apps/commands` — JSON array, empty when no apps running
- Logger `app.browser.apps` at DEBUG level — shows type count and section count per right pane request
- Logger `app.browser.objects` at DEBUG — shows when renderer override dispatch occurs

### What assumptions changed
- **Plan assumed `AppObjectRenderer` has a `label` field** — it doesn't. Used app name instead. S07 test app should be aware there's no per-renderer labeling, just per-app.
- **Plan said "request cancellation for right pane loading"** — implemented as AbortController on the fetch, which works well. No htmx-level cancellation was needed since we control the fetch directly.
