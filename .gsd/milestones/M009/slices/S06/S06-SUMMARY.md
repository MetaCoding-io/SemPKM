---
id: S06
parent: M009
milestone: M009
provides:
  - Dynamic right pane sections endpoint merging platform + app contributions with type-based filtering
  - AppRegistry helpers: get_right_pane_contributions(), get_renderer(), get_renderer_for_app()
  - Views explorer app contributions (app views in VIEWS section)
  - Command palette API (GET /api/apps/commands) with ninja-keys injection
  - Object renderer override dispatch in get_object() with AppRendererPref conflict resolution
  - object_tab_app.html template for app-rendered object views
  - Admin renderer assignment management with set/clear controls
  - loadRightPane() JS with AbortController request cancellation
  - openAppViewTab() JS with app-view special panel factory
requires:
  - slice: S04
    provides: app_shell.html, [Apps] sidebar, fragment loading pattern, openAppPageTab()
  - slice: S05
    provides: AppRegistry renderer/contribution metadata, scheduler running, permissions enforced
affects:
  - S07
key_files:
  - backend/app/browser/apps.py
  - backend/app/browser/objects.py
  - backend/app/apps/registry.py
  - backend/app/apps/admin_router.py
  - backend/app/templates/browser/right_pane_sections.html
  - backend/app/templates/browser/object_tab_app.html
  - backend/app/templates/browser/app_view_tab.html
  - backend/app/templates/browser/workspace.html
  - backend/app/templates/admin/apps/detail.html
  - frontend/static/js/workspace.js
  - frontend/static/js/workspace-layout.js
  - frontend/static/css/workspace.css
  - backend/tests/test_right_pane_sections.py
  - backend/tests/test_app_views_commands.py
  - backend/tests/test_renderer_overrides.py
  - backend/tests/test_admin_renderers.py
key_decisions:
  - none (all implementation followed plan — full IRI matching v1, first-match-wins, AppRendererPref for conflicts)
patterns_established:
  - Dynamic right pane via fetch+innerHTML swap with AbortController cancellation for rapid tab switching
  - App contribution injection pattern: platform sections first, app sections appended after type-based filtering, priority-sorted
  - Renderer override dispatch: registry lookup → AppRendererPref table override → fallback to default SHACL form, wrapped in try/except for graceful degradation
  - App view tabs follow openAppPageTab() pattern with tab key dedup (app-view:{appId}:{viewId})
  - Command palette entries fetched from API and merged into ninja-keys data array with per-command action dispatch (dialog/post/navigate)
  - htmx.process() called after innerHTML swap to activate hx-get attributes in dynamically injected content
  - MockRendererPrefStore in-memory pattern for testing async session CRUD without real DB
observability_surfaces:
  - GET /browser/apps/right-pane-sections?iri=<IRI> returns inspectable merged HTML of platform + app sections
  - GET /api/apps/commands returns JSON array of registered app command palette entries
  - Logger app.browser.apps at DEBUG: type count + app section count per right pane request
  - Logger app.browser.objects at DEBUG: renderer override details (app_id, type, fragments) when active
  - Logger app.browser.objects at WARNING: stale AppRendererPref entries and override lookup failures
  - Logger app.apps.admin_router at INFO: renderer pref set/clear with type, mode, app_id
  - Admin detail page Renderer Overrides section with color-coded status badges (Active/Default/Overridden)
  - Database: SELECT * FROM app_renderer_prefs for active renderer assignments
  - Graceful degradation: right pane returns platform-only on any error; renderer override falls back to default SHACL form on any error
drill_down_paths:
  - .gsd/milestones/M009/slices/S06/tasks/T01-SUMMARY.md
  - .gsd/milestones/M009/slices/S06/tasks/T03-SUMMARY.md
  - .gsd/milestones/M009/slices/S06/tasks/T04-SUMMARY.md
duration: 35m
verification_result: passed
completed_at: 2026-03-17
---

# S06: Frontend Level 2+3 — Workspace Contributions & Renderer Overrides

**App contributions fully integrated into workspace at all 3 frontend levels — dynamic right pane sections, views explorer entries, command palette injection, and object renderer override dispatch with admin management**

## What Happened

This slice completed the final layer of frontend integration for the app platform, adding workspace contributions (Level 2) and renderer overrides (Level 3) on top of the standalone pages (Level 1) delivered in S04.

**T01 — Dynamic right pane sections.** The right pane was refactored from 3 hardcoded `<details>` blocks with 3 separate JS calls to a single dynamic endpoint (`GET /browser/apps/right-pane-sections?iri=`) that merges platform sections (relations, lint, comments) with app contributions. `AppRegistry.get_right_pane_contributions(type_iris)` iterates running app manifests, filters by `targetTypes` (wildcard `["*"]` matches all objects), and returns priority-sorted contributions. The JS side was simplified to a single `loadRightPane(objectIri)` function using `fetch` + `innerHTML` swap with `AbortController` to cancel superseded requests during rapid tab switching. `htmx.process()` is called post-swap to activate `hx-get` attributes in dynamically injected content.

**T02 — Views explorer + command palette.** Three new endpoints were added: `GET /browser/apps/views/explorer` returns HTML fragment of app view entries for inclusion in the views explorer section; `GET /browser/apps/views/{app_id}/{view_id}` renders `app_view_tab.html` loading app fragment via htmx; `GET /api/apps/commands` returns a JSON array of command palette entries from running apps. `openAppViewTab()` follows the established `openAppPageTab()` pattern with tab key dedup. The `app-view` case was added to workspace-layout.js's special-panel factory. In `workspace.js`, `initCommandPalette()` fetches `/api/apps/commands` and merges entries into `ninja.data` with per-command action dispatch (dialog opens htmx fragment in modal, post triggers htmx POST, navigate changes location).

**T03 — Renderer override dispatch.** `AppRegistry.get_renderer(type_iri)` iterates manifests checking `ui.objectRenderers` for type IRI matches, returning app_id plus read/edit fragment paths. `_get_renderer_override()` in objects.py queries the `AppRendererPref` table for conflict resolution when multiple apps claim the same type. In `get_object()`, after type resolution, the override helper is called inside try/except — on match, `object_tab_app.html` renders with the app's custom read face loaded via htmx; on no match or error, the standard `object_tab.html` renders unchanged. The app template mirrors all platform chrome (label, type badge, favorite toggle, mode toggle flip card) but replaces face content with app fragments.

**T04 — Admin renderer management.** The placeholder in the admin app detail page was replaced with a real Renderer Overrides section. `_build_renderer_assignments()` queries each app's manifest renderers against the `AppRendererPref` table and builds status dicts. Color-coded badges show Active (green), Default (yellow), or Overridden by {other_app} (red). `POST /renderers/set` and `POST /renderers/clear` endpoints manage `AppRendererPref` rows with htmx-driven UI updates.

## Verification

- `pytest backend/tests/test_right_pane_sections.py -v` → **16/16 passed** ✅
- `pytest backend/tests/test_app_views_commands.py -v` → **13/13 passed** ✅
- `pytest backend/tests/test_renderer_overrides.py -v` → **19/19 passed** ✅
- `pytest backend/tests/test_admin_renderers.py -v` → **13/13 passed** ✅
- `pytest backend/tests/ -x --ignore=test_sdk_integration.py` → **1201 passed** ✅ (zero regressions)
- All `.py` files pass `ast.parse()` ✅
- `from app.browser.apps import apps_router` → importable ✅
- `grep loadRightPaneSection workspace.js` → 0 occurrences (old function fully removed) ✅
- `grep right-pane-dynamic workspace.html` → present ✅

## Requirements Advanced

- **APP-08** — Right pane sections appear alongside Relations/Lint from app contributions. Views explorer shows app view entries. Command palette entries from apps injected into ninja-keys. All 3 Level 2 workspace contribution points implemented and tested.
- **APP-09** — Object renderer override dispatch checks AppRegistry before SHACL form. `object_tab_app.html` loads app fragments. AppRendererPref resolves conflicts. Edit face falls back to SHACL form when app has no edit renderer. All Level 3 renderer override mechanics implemented and tested.
- **APP-10** — Admin app detail page now shows renderer assignment section with status badges and set/clear controls (was placeholder). Supporting slice contribution complete.

## Requirements Validated

- **APP-08** — 29 unit tests prove: right pane merges platform + app sections with type filtering and priority ordering (16 tests); views explorer shows app entries and excludes stopped apps (4 tests); app view tab loads correct fragments (3 tests); command palette API returns correct JSON with action types and excludes stopped apps (6 tests).
- **APP-09** — 19 unit tests prove: registry returns correct renderer for matching type and None for non-matching (7 tests); override helper respects AppRendererPref and handles stale prefs (5 tests); get_object() dispatches to app template with toolbar preservation and falls back on error (7 tests).

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

T01 was fully implemented by T02's work (T02 was executed first and included T01's deliverables). T01 execution was verification-only. No plan changes were needed — all deliverables matched the plan.

## Known Limitations

- Renderer type matching is full IRI only (v1) — no prefix expansion or pattern matching
- `test_sdk_integration.py` has a pre-existing failure (missing `sempkm_app_sdk` module from S02) — unrelated to this slice
- Command palette app entries are fetched once at workspace init — not refreshed if apps start/stop during session (acceptable for v1, workspace reload picks up changes)
- Right pane app fragment errors are silently swallowed at the htmx level — the `<details>` block renders but content may show a load error. Graceful degradation is correct behavior.

## Follow-ups

- S07 will exercise all these integration points with a real test app and E2E tests
- S08 will document the 3 frontend integration levels for app developers

## Files Created/Modified

- `backend/app/browser/apps.py` — right-pane-sections endpoint, views explorer endpoint, app view tab endpoint, commands API endpoint
- `backend/app/browser/objects.py` — `_get_renderer_override()` helper, dispatch branch in `get_object()`
- `backend/app/apps/registry.py` — `get_right_pane_contributions()`, `get_renderer()`, `get_renderer_for_app()` methods
- `backend/app/apps/admin_router.py` — `_build_renderer_assignments()` helper, `renderer_set()` and `renderer_clear()` endpoints
- `backend/app/templates/browser/right_pane_sections.html` — new template with platform + app `<details>` blocks
- `backend/app/templates/browser/object_tab_app.html` — new template for app-rendered object views with flip card
- `backend/app/templates/browser/app_view_tab.html` — new template for app view tabs
- `backend/app/templates/browser/workspace.html` — right pane refactored to dynamic `#right-pane-dynamic` container
- `backend/app/templates/admin/apps/detail.html` — placeholder replaced with Renderer Overrides section
- `frontend/static/js/workspace.js` — `loadRightPane()` with AbortController, `openAppViewTab()`, command palette app entry injection
- `frontend/static/js/workspace-layout.js` — `app-view` special panel factory case
- `frontend/static/css/workspace.css` — `.app-renderer-content` and `.app-renderer-loading` styles
- `backend/tests/test_right_pane_sections.py` — 16 tests for registry helper + endpoint
- `backend/tests/test_app_views_commands.py` — 13 tests for views + commands
- `backend/tests/test_renderer_overrides.py` — 19 tests for registry + helper + dispatch
- `backend/tests/test_admin_renderers.py` — 13 tests for admin renderer management

## Forward Intelligence

### What the next slice should know
- All 3 frontend integration levels are now functional: standalone pages (S04), workspace contributions (S06), renderer overrides (S06). S07's test app should exercise all of them.
- The test app manifest needs `ui.rightPane`, `ui.views`, `ui.commands`, and `ui.objectRenderers` sections to trigger S06's code paths.
- App fragments for right pane, views, and renderers are loaded via `GET /app/{appId}/_fragments/{fragment}?iri={iri}` — the test app's SDK routes need to serve these.
- Command palette commands need `actionType` of `dialog`, `post`, or `navigate` — test app should include at least a `dialog` type.
- `openAppViewTab()` and `openAppPageTab()` both exist — test E2E should verify both open correctly.

### What's fragile
- Right pane `innerHTML` swap + `htmx.process()` pattern — if htmx changes how `process()` handles already-initialized elements, the lazy-load `hx-get` attributes on injected `<details>` blocks could break. The pattern works today but couples to htmx internals.
- Renderer override dispatch wraps everything in try/except for graceful degradation — this means silent failures. If a renderer lookup has a bug, it will silently fall back to the default SHACL form with only a WARNING log. E2E tests should explicitly verify the app template renders, not just that the page loads.

### Authoritative diagnostics
- `GET /browser/apps/right-pane-sections?iri=<any-iri>` — returns inspectable HTML; check for `<details>` blocks with `data-app-id` attributes for app contributions
- `GET /api/apps/commands` — returns JSON array; empty when no apps running, populated when apps with commands are active
- `SELECT * FROM app_renderer_prefs` — shows active renderer assignments
- Logger `app.browser.objects` at DEBUG — shows renderer override details when dispatching to app template

### What assumptions changed
- T02 was executed before T01 and included all T01 deliverables — the tasks weren't independent as planned. This had no negative impact but means T01's summary is verification-only.
