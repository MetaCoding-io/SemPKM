# S06: Frontend Level 2+3 — Workspace Contributions & Renderer Overrides

**Goal:** App contributions fully integrated into the workspace at all 3 frontend levels — right pane sections appear alongside Relations/Lint, app views appear in Views explorer, command palette entries registered with ninja-keys, and apps can override default SHACL form with custom read/edit renderers for specific types.
**Demo:** When viewing an object whose type matches an app's `rightPane` contributions, additional `<details>` sections appear in the right pane with app-served content. App views are clickable in the Views explorer. App commands are searchable in the command palette. Objects of types with renderer overrides show the app's custom read view instead of the default SHACL form. Admin shows renderer assignment status with override controls.

## Must-Haves

- Dynamic right pane endpoint merging platform sections (relations, lint, comments) + app contributions, loaded via htmx when object tab activates
- App view contributions appear in Views explorer as clickable entries that open in workspace tabs
- App command palette entries fetched from API and injected into ninja-keys data
- Object renderer override dispatch in `get_object()` — checks AppRegistry for type match before falling back to default SHACL form
- `object_tab_app.html` template loading app fragment for read face, with optional edit face fallback to SHACL form
- `AppRegistry` helper methods: `get_right_pane_contributions(type_iris)` and `get_renderer(type_iri)`
- Admin renderer assignment section replacing placeholder in detail.html with set/clear controls
- `AppRendererPref` table used for conflict resolution when multiple apps declare renderers for same type
- Request cancellation for right pane loading to prevent stale section display on rapid tab switching

## Proof Level

- This slice proves: integration
- Real runtime required: no (contract tests with mocked registry)
- Human/UAT required: no (deferred to S07 browser verification)

## Verification

- `cd /home/james/Code/SemPKM/.gsd/worktrees/M009 && python -m pytest backend/tests/test_right_pane_sections.py -v` — dynamic right pane endpoint returns merged platform + app sections, filters by targetTypes, respects priority ordering, handles no-app case identically to current behavior
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M009 && python -m pytest backend/tests/test_app_views_commands.py -v` — views explorer includes app view entries, command palette endpoint returns correct JSON, handles empty/stopped apps
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M009 && python -m pytest backend/tests/test_renderer_overrides.py -v` — get_object() dispatches to app renderer when type matches, falls back to default when no match, respects AppRendererPref for conflicts
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M009 && python -m pytest backend/tests/test_admin_renderers.py -v` — admin set/clear endpoints modify AppRendererPref correctly, detail page shows renderer info
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M009 && python -m pytest backend/tests/ -x --timeout=30` — zero regressions across full test suite
- All modified `.py` files pass `python3 -c "import ast; ast.parse(open(f).read())"`
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M009 && .venv/bin/python -c "from fastapi.testclient import TestClient; from app.browser.apps import apps_router; print('endpoint importable')"` — endpoint module loads without import errors
- Diagnostic: `GET /browser/apps/right-pane-sections?iri=http://nonexistent/iri` returns 200 with platform sections only (graceful degradation for unknown IRI)

## Observability / Diagnostics

- Runtime signals: Logger `app.browser.apps` logs WARNING when app contribution fragment fails to load; right pane endpoint logs app count + section count at DEBUG level
- Inspection surfaces: `GET /browser/right-pane-sections?iri=<IRI>` returns inspectable HTML of merged sections; `GET /api/apps/commands` returns JSON array of registered commands; `SELECT * FROM app_renderer_prefs` shows active renderer assignments
- Failure visibility: 404 with descriptive detail for unknown renderer app/fragment; right pane gracefully degrades to platform-only sections when app contributions fail; renderer override falls back to default SHACL form on any error
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `AppRegistry.list_apps()` / `get_manifest()` from S01, `AppManager.get_status()` from S01, `AppProxy.forward()` from S02, `apps_explorer.html` / `app_page.html` / `openAppPageTab()` from S04, `AppRendererPref` model from S01, `AppScheduler` running from S05
- New wiring introduced in this slice: 4 new endpoints in `apps.py` (right-pane-sections, app view tab, commands API), renderer dispatch branch in `objects.py`, ninja-keys injection in `workspace.js`, admin renderer endpoints in `admin_router.py`
- What remains before the milestone is truly usable end-to-end: S07 (test app exercising all features + E2E tests), S08 (documentation)

## Tasks

- [x] **T01: Dynamic right pane sections endpoint and JS refactor** `est:1h30m`
  - Why: The right pane currently has 3 hardcoded `<details>` blocks and 3 hardcoded JS calls. D153 directs making this dynamic via an htmx endpoint that merges platform sections + app contributions. This is the biggest structural change in the slice and establishes the dynamic pattern for app section injection.
  - Files: `backend/app/browser/apps.py`, `backend/app/templates/browser/right_pane_sections.html`, `backend/app/templates/browser/workspace.html`, `frontend/static/js/workspace.js`, `backend/app/apps/registry.py`, `backend/tests/test_right_pane_sections.py`
  - Do: (1) Add `get_right_pane_contributions(type_iris)` helper to `AppRegistry` — iterates running apps' manifests, collects rightPane contributions matching any of the given type IRIs (empty targetTypes = all objects), returns sorted by priority. (2) Create `GET /browser/apps/right-pane-sections?iri={iri}` endpoint in `apps.py` — queries object's rdf:type via SPARQL, calls registry helper, merges with platform sections (relations, lint, comments) into ordered list, renders `right_pane_sections.html`. (3) Create template with platform `<details>` blocks first (each with `hx-get` for lazy content load like current pattern), then app contribution `<details>` blocks (each with `hx-get` to `/app/{appId}/_fragments/{fragment}?iri={iri}`). (4) Replace the 3 hardcoded `<details>` blocks in `workspace.html` right pane with a single `<div id="right-pane-dynamic">` that loads via htmx. Keep inbox_panel and collaboration_panel as static `{% include %}` directives below the dynamic container. (5) Replace `loadRightPaneSection()` calls in `workspace.js` with a single `loadRightPane(objectIri)` that fetches the dynamic endpoint via htmx swap. Add AbortController to cancel superseded requests on rapid tab switching. (6) Write tests covering: platform-only sections (no apps), platform + app sections merged, targetTypes filtering, priority ordering, unknown object IRI returns platform sections only.
  - Verify: `python -m pytest backend/tests/test_right_pane_sections.py -v`
  - Done when: Right pane endpoint returns correct merged HTML for platform + app sections with type-based filtering, and JS uses single endpoint call with request cancellation.

- [ ] **T02: Views explorer app contributions and command palette API** `est:1h`
  - Why: APP-08 requires app views in the Views section and app commands in the command palette. The views explorer is currently a static template and ninja-keys has hardcoded entries — both need app contribution injection. These two integration points are independent of the right pane work but complete the Level 2 workspace contributions.
  - Files: `backend/app/browser/apps.py`, `backend/app/templates/browser/views_explorer.html`, `backend/app/templates/browser/app_view_tab.html`, `frontend/static/js/workspace.js`, `frontend/static/js/workspace-layout.js`, `backend/tests/test_app_views_commands.py`
  - Do: (1) Add `GET /browser/apps/views/explorer` endpoint in `apps.py` — queries AppRegistry for running apps with `ui.views` contributions, returns HTML fragment of app view entries grouped under an "App Views" heading. (2) Modify views explorer endpoint (or template) to include app view contributions after the generic views and before Saved Views folder. Use htmx `hx-get` include or template variable passing. (3) Create `app_view_tab.html` template — similar to `app_page.html` but for view contributions. The template loads the app's view fragment via htmx from `/app/{appId}/_fragments/{fragment}`. (4) Add `openAppViewTab(appId, viewId, label)` JS function following `openAppPageTab()` pattern with tab key `app-view:{appId}:{viewId}`. Add `app-view` case to `workspace-layout.js` special-panel factory. (5) Create `GET /api/apps/commands` endpoint returning JSON array of command palette entries from running apps — each entry has `id`, `title`, `icon`, `section` (app name), `actionType`, `actionUrl`. (6) In `workspace.js` `initCommandPalette()`, after setting up static entries, fetch `/api/apps/commands` and push entries into `ninja.data`. Each entry's handler dispatches: `dialog` → htmx GET fragment into modal, `post` → htmx POST, `navigate` → window location change. (7) Write tests: views explorer with app contributions, views explorer with no apps, command palette JSON format, command palette excludes stopped apps.
  - Verify: `python -m pytest backend/tests/test_app_views_commands.py -v`
  - Done when: Views explorer shows app view entries, command palette API returns correct JSON, and JS injects app commands into ninja-keys.

- [ ] **T03: Object renderer override dispatch and app renderer template** `est:1h30m`
  - Why: APP-09 requires apps to replace the default SHACL form for specific types with custom renderers. This is the most surgically precise change — modifying `get_object()` with a conditional branch that checks AppRegistry before rendering the default template. Renderer conflict resolution via AppRendererPref completes the dispatch logic.
  - Files: `backend/app/browser/objects.py`, `backend/app/apps/registry.py`, `backend/app/templates/browser/object_tab_app.html`, `backend/app/apps/models.py`, `backend/tests/test_renderer_overrides.py`
  - Do: (1) Add `get_renderer(type_iri)` method to `AppRegistry` — iterates running apps' manifests checking `ui.objectRenderers` for matching type. Returns `(app_id, read_fragment, edit_fragment_or_none)` or None. Type matching uses full IRIs (v1 — no prefix expansion). If multiple apps match, return the first found (preference resolution deferred to step 3). (2) In `get_object()` (objects.py), after resolving `type_iris` (~line 107), call `registry.get_renderer(type_iri)` for each type. If a renderer is found, check `AppRendererPref` table for user preference override. If `AppRendererPref` row exists for this (type_iri, mode='read'), use that app's renderer; otherwise use the registry result. (3) Create `object_tab_app.html` template. Structure: same toolbar as `object_tab.html` (label, type badge, favorite toggle, mode toggle). Read face loads app fragment via htmx `hx-get="/app/{appId}/_fragments/{read_fragment}?iri={object_iri}"`. Edit face: if app declares edit renderer, load from app fragment; otherwise fall back to standard SHACL form (include the existing form partial). The mode toggle (read/edit flip) works the same as the current flip card. (4) Pass `renderer_app_id`, `read_fragment`, `edit_fragment`, and `has_custom_edit` to the template context when an override is active. Pass `use_default_renderer=True` when no override — existing template renders as-is. (5) Write tests: get_renderer returns correct app for matching type, get_renderer returns None for non-matching type, get_object renders object_tab_app.html when override exists, get_object renders object_tab.html when no override, AppRendererPref preference wins over registry default, multiple renderer conflict uses preference, edit fallback to SHACL when app has no edit renderer.
  - Verify: `python -m pytest backend/tests/test_renderer_overrides.py -v`
  - Done when: `get_object()` dispatches to app renderer for overridden types, falls back to default for others, respects user preferences for conflicts, and app template loads correct fragments.

- [ ] **T04: Admin renderer assignment management** `est:45m`
  - Why: APP-10 requires the admin detail page to show renderer assignments with override controls. The current admin detail has a placeholder at line 273. This task replaces it with a real UI showing which types this app renders, current assignment status, and set/clear controls.
  - Files: `backend/app/apps/admin_router.py`, `backend/app/templates/admin/apps/detail.html`, `backend/tests/test_admin_renderers.py`
  - Do: (1) In `app_detail()` endpoint, query the app's manifest for declared `objectRenderers`. For each renderer type, query `AppRendererPref` table to check if this app is the active renderer or another app is. Build a list of `{type_iri, mode, is_active, active_app_id}` dicts and pass to template. (2) Add `POST /admin/apps/{app_id}/renderers/set` endpoint — accepts `type_iri` and `mode` form params, upserts `AppRendererPref` row with this app as the preferred renderer. Returns htmx fragment replacing the renderer section. (3) Add `POST /admin/apps/{app_id}/renderers/clear` endpoint — accepts `type_iri` and `mode` form params, deletes the `AppRendererPref` row. Returns htmx fragment. (4) Replace placeholder in `detail.html` with real renderer section: table of declared renderer types with columns (Type IRI, Mode, Status, Action). Status shows "Active" with green badge if this app is the preferred renderer, "Override by {other_app}" if another app is preferred, or "Default" if no preference set. Action buttons: "Set as default" (POST to set endpoint) / "Clear override" (POST to clear endpoint) with htmx. (5) Write tests: detail page shows renderer info, set endpoint creates AppRendererPref, clear endpoint removes AppRendererPref, detail shows correct status for active/overridden/default states.
  - Verify: `python -m pytest backend/tests/test_admin_renderers.py -v`
  - Done when: Admin detail page shows renderer assignments with accurate status and working set/clear controls.

## Files Likely Touched

- `backend/app/browser/apps.py`
- `backend/app/browser/objects.py`
- `backend/app/apps/registry.py`
- `backend/app/apps/admin_router.py`
- `backend/app/apps/models.py`
- `backend/app/templates/browser/workspace.html`
- `backend/app/templates/browser/right_pane_sections.html` (new)
- `backend/app/templates/browser/object_tab_app.html` (new)
- `backend/app/templates/browser/app_view_tab.html` (new)
- `backend/app/templates/browser/views_explorer.html`
- `backend/app/templates/admin/apps/detail.html`
- `frontend/static/js/workspace.js`
- `frontend/static/js/workspace-layout.js`
- `backend/tests/test_right_pane_sections.py` (new)
- `backend/tests/test_app_views_commands.py` (new)
- `backend/tests/test_renderer_overrides.py` (new)
- `backend/tests/test_admin_renderers.py` (new)
