# S06: Frontend Level 2+3 — Workspace Contributions & Renderer Overrides — Research

**Date:** 2026-03-16
**Milestone:** M009 — App Platform

## Summary

S06 integrates app contributions into the workspace at two levels: Level 2 (right pane sections, view contributions, command palette entries) and Level 3 (object renderer overrides). The manifest schema already defines all necessary models (`AppRightPaneContribution`, `AppViewContribution`, `AppCommandPaletteEntry`, `AppObjectRenderer`), `AppRegistry` provides manifest access, and the `AppRendererPref` SQLAlchemy model exists for conflict resolution. The work is wiring these existing structures into four frontend integration points plus adding renderer assignment management to admin.

All integration points follow established codebase patterns. The right pane is currently 3 hard-coded `<details>` blocks in `workspace.html` with 3 hardcoded `loadRightPaneSection()` JS calls — D153 directs making this dynamic via an htmx endpoint. The views explorer is a static template. The command palette uses `ninja-keys` with hardcoded entries plus a dynamic `_addTypeCreateEntries()` pattern that shows how to inject entries at runtime. The object tab always renders `object_tab.html` — renderer overrides intercept `get_object()` to check `AppRegistry` before falling back to the default SHACL form.

No new libraries or unfamiliar technology. This is integration work connecting existing backend structures to existing frontend patterns.

## Recommendation

Build in 4 tasks ordered by dependency and complexity:

1. **Right pane sections (dynamic endpoint + template)** — the biggest structural change. Replace hardcoded right pane with a dynamic endpoint that merges platform sections + app contributions. Create a new template. Update JS to call the endpoint. This is the riskiest piece because it touches `workspace.html` structure and `workspace.js` right-pane loading logic in multiple places.

2. **Views explorer + command palette** — extend the views explorer to include app view contributions and add a `/api/apps/commands` endpoint for command palette injection. Relatively independent from task 1.

3. **Object renderer overrides** — modify `get_object()` to check `AppRegistry` for renderer matching the object's type. Create `object_tab_app.html` template. Add renderer preference lookup from `AppRendererPref` table. This is the most surgically precise change.

4. **Admin renderer assignments** — replace the placeholder in admin detail with a real renderer assignment section. Add endpoints for setting/clearing renderer preferences.

## Implementation Landscape

### Key Files

- `backend/app/templates/browser/workspace.html` — right pane section at lines 175-215 has 3 hard-coded `<details>` blocks (relations, lint, comments) + inbox_panel + collaboration_panel includes. Must be replaced with a dynamic htmx-loaded container.
- `frontend/static/js/workspace.js` — `loadRightPaneSection()` at line 262 handles section loading. Hardcoded calls at lines 254-256 and 2446-2448 load relations/lint/comments. Must be replaced with a single dynamic fetch. Also: `initCommandPalette()` at line 1307 initializes ninja-keys data — app commands inject here.
- `backend/app/browser/objects.py` — `get_object()` at line 54 always returns `object_tab.html`. The renderer override intercept goes here: after resolving `type_iris`, check `AppRegistry.get_renderer(type_iri)` and `AppRendererPref` table, then conditionally render `object_tab_app.html`.
- `backend/app/browser/apps.py` — currently has explorer + page endpoints. Needs: right-pane sections endpoint, view contributions in explorer, command palette API, app view tab endpoint, renderer fragment endpoints.
- `backend/app/apps/registry.py` — `AppRegistry` with `get_manifest()`. Needs helper methods: `get_renderer(type_iri, mode)` to search all manifests for renderer overrides, `get_right_pane_contributions(type_iris)` to collect matching right pane sections.
- `backend/app/apps/admin_router.py` — `app_detail()` at line 120 builds context for detail page. Needs renderer assignment data. New endpoints for setting/clearing renderer prefs.
- `backend/app/templates/admin/apps/detail.html` — placeholder at line 273 for renderer assignments. Replace with actual UI showing type → mode → app mappings with override controls.
- `backend/app/templates/browser/views_explorer.html` — static template. App view contributions insert as additional `tree-leaf` entries (between generic views and Saved Views folder, or in a separate "App Views" group).
- `backend/app/apps/models.py` — `AppRendererPref` model already exists with (type_iri, mode) composite PK.

### New Files to Create

- `backend/app/templates/browser/right_pane_sections.html` — dynamic right pane template merging platform + app sections
- `backend/app/templates/browser/object_tab_app.html` — app renderer override tab (htmx loads fragment from app)
- `backend/app/templates/browser/app_view_tab.html` — app view contribution tab (already in roadmap)

### Integration Point Details

#### 1. Right Pane Sections (D153)

**Current state:** 3 `<details>` blocks hardcoded in `workspace.html`. JS calls `loadRightPaneSection(iri, 'relations')`, `loadRightPaneSection(iri, 'lint')`, `loadRightPaneSection(iri, 'comments')` when a tab activates.

**Target state:** A single `<div>` in `workspace.html` that htmx-loads `/browser/right-pane-sections?iri={iri}` when an object tab activates. The endpoint returns the full set of `<details>` blocks — platform sections first (relations, lint, comments, inbox, collaboration) plus app-contributed sections sorted by priority.

**Implementation:**
- New endpoint `GET /browser/right-pane-sections` in `apps.py` (or a new dedicated file). Accepts `?iri=` parameter. Queries `AppRegistry` for running apps with `rightPane` contributions matching the object's type(s). Merges with platform sections. Returns rendered `right_pane_sections.html`.
- Object type resolution: endpoint needs to query the object's `rdf:type` to match against `targetTypes` in app contributions. Can use a lightweight SPARQL query or accept type as a query parameter from the JS.
- The `workspace.html` right pane `<div id="right-content">` replaces its children via htmx swap.
- JS `loadRightPaneSection()` function replaced with a single `loadRightPane(objectIri)` that fetches the dynamic endpoint and swaps the content. The individual section content still loads lazily via htmx triggers on each `<details>` open.
- Critical: inbox_panel and collaboration_panel includes currently live inside the right pane statically. They must be included in the dynamic endpoint response or kept as static always-present sections.

**Key concern:** The inbox and collaboration panels are `{% include %}` directives that may depend on workspace-level context (user, etc.). The dynamic endpoint must pass appropriate context. Check what context these partials need.

#### 2. Views Explorer + Command Palette

**Views explorer:**
- Endpoint `GET /browser/views/explorer` currently returns static `views_explorer.html`.
- Change: query `AppRegistry` for running apps with `views` contributions. Pass app view entries to template. Template renders them as `tree-leaf` entries in an "App Views" group (or interleaved after generic views).
- Each app view entry calls `openAppViewTab(appId, viewId, label)` — a new JS function following the `openAppPageTab()` pattern.

**Command palette:**
- New API endpoint `GET /api/apps/commands` returns JSON array of registered command palette entries from running apps.
- JS: after `initCommandPalette()` sets up static entries, fetch `/api/apps/commands` and push entries into `ninja.data`.
- Each entry's handler dispatches based on `actionType`: dialog → htmx GET fragment into modal, post → htmx POST, navigate → location change.
- The design doc (§7 Level 2) shows this exact pattern.

#### 3. Object Renderer Overrides

**Dispatch flow in `get_object()`:**
1. After resolving `type_iris` (line ~107 in objects.py), check for renderer override.
2. Query `AppRegistry` helper: for each type_iri, check all running apps' `ui.objectRenderers` for a matching type. Prefix expansion needed (e.g., `rss:Article` → full IRI).
3. If multiple apps match, consult `AppRendererPref` table for user preference. Fallback: most recently installed app wins (`AppInstance.installed_at`).
4. If override found, render `object_tab_app.html` instead of `object_tab.html`. The app template loads read/edit fragments via htmx from `/app/{appId}/_fragments/{renderer_path}?iri={object_iri}`.
5. If no custom edit renderer, the edit face falls back to the default SHACL form (pass `has_custom_edit` flag to template).

**Template `object_tab_app.html`:**
- Similar structure to `object_tab.html` but read face is htmx-loaded from app fragment URL.
- Edit face: either htmx-loaded from app's edit fragment URL (if `modes.edit` is set) or falls back to standard SHACL form.
- Keep the toolbar (label, type badge, favorite, mode toggle) — it's platform chrome.

**Registry helper:**
- `AppRegistry.get_renderer(type_iri: str, mode: str) -> tuple[str, str] | None` — returns `(app_id, fragment_path)` or None. Iterates running apps, checks `ui.objectRenderers` for matching type. Handles prefix expansion by checking if the manifest type field is a prefixed name vs full IRI.
- Need to handle the type prefix expansion: manifest declares `rss:Article`, registry needs to match against full IRI `urn:sempkm:model:rss-feeds:Article`. The app's model dependencies declare which model provides the prefix. This may require checking the manifest's `dependencies.models` to resolve prefixes. **Simpler approach:** require `objectRenderers[].type` to be full IRIs in the manifest, not prefixed names. The manifest validation doesn't currently enforce this — check the design doc.

**Prefix resolution concern:** The design doc §7 Level 3 shows `rss:Article` as the type, but the actual RDF type in the triplestore is a full IRI. The manifest `AppObjectRenderer.type` field has no prefix expansion logic. Two options:
- (a) Require full IRIs in manifest — simple, unambiguous, but verbose.
- (b) Add prefix expansion using the app's model dependency chain — complex, fragile.

**Recommendation:** Accept both. If the type contains `:` but doesn't start with `http`/`urn`, treat it as a prefixed name and attempt expansion via installed model manifests. Otherwise use as-is. But for v1, start with full IRIs only and document the convention. Prefix expansion can be added in a follow-up.

#### 4. Admin Renderer Assignments

**Current state:** Placeholder text at line 273 of `detail.html`.

**Target state:** Section showing which types this app renders, with current assignment status (active/overridden by another app). Controls to set/clear this app as the preferred renderer.

**Endpoints:**
- `POST /admin/apps/{app_id}/renderers/{type_iri}/set` — sets `AppRendererPref` row for this (type_iri, mode, app_id)
- `DELETE /admin/apps/{app_id}/renderers/{type_iri}/clear` — removes `AppRendererPref` row

**Detail endpoint change:** `app_detail()` queries `AppRendererPref` for all rows matching the app's declared renderer types. Passes to template alongside the manifest's declared renderers.

### Build Order

1. **Right pane dynamic endpoint** — biggest structural change, touches workspace.html and workspace.js in multiple places. Build this first because it establishes the dynamic section pattern that app contributions plug into.
2. **Views explorer + command palette** — independent from right pane. Can be built in parallel conceptually but sequence after because it's simpler and less risky.
3. **Object renderer overrides** — the most surgically precise change. Modifies `get_object()` with a conditional branch. Needs the registry helper method.
4. **Admin renderer assignments** — extends existing admin detail page. Lowest risk, last in sequence.

### Verification Approach

**Unit tests (no Docker):**
- Right pane endpoint: test with mock registry containing apps with rightPane contributions, verify merged section HTML contains both platform and app sections, verify priority ordering, verify targetTypes filtering
- Views explorer: test with mock registry containing apps with view contributions, verify view entries appear in template
- Command palette endpoint: test JSON response contains entries from running apps
- Renderer override dispatch: test `get_object()` with mock registry declaring a renderer for the object's type, verify `object_tab_app.html` is rendered. Test fallback to `object_tab.html` when no override. Test user preference wins over default.
- Admin renderer: test set/clear endpoints modify `AppRendererPref` table correctly, test detail page shows renderer info

**Contract tests:**
- `AppRegistry.get_renderer()` helper returns correct (app_id, fragment_path) for matching type
- `AppRegistry.get_right_pane_contributions()` filters by targetTypes correctly
- Renderer preference resolution: user pref > most recent install > None

**Browser verification (deferred to S07):**
- Right pane shows app sections when viewing an object
- App view appears in Views explorer sidebar
- Command palette shows app commands
- Object tab renders app fragment for overridden type

## Constraints

- **Router registration order matters** — `apps_router` must stay before `objects_router` in `browser/router.py` (D052/D058/D136). Any new routes in `apps.py` inherit this priority.
- **workspace.html right pane structure is shared** — inbox_panel and collaboration_panel are `{% include %}` directives. The dynamic right pane endpoint must either include them or leave them as static elements outside the dynamic container.
- **Renderer type matching requires full IRIs** — the triplestore stores full IRIs (e.g., `urn:sempkm:model:rss-feeds:Article`), but manifests might use prefixed names (e.g., `rss:Article`). For v1, require full IRIs in manifest `objectRenderers[].type` field.
- **ninja-keys is a web component with shadow DOM** — app command injection must use the `ninja.data` array push pattern (already established). Cannot use CSS selectors to find elements inside its shadow root for interaction (only for the search input).

## Common Pitfalls

- **Right pane section loading race** — when switching tabs rapidly, multiple `loadRightPane()` calls may fire. The response for the first object could arrive after the second, showing stale sections. Use a request ID or abort controller to cancel superseded requests.
- **App contribution caching** — `AppRegistry` manifest data is in-memory and changes when apps start/stop. The right pane endpoint must query live registry state, not cache contributions. Views explorer and command palette should also query live state.
- **Object type resolution for right pane** — the right pane endpoint needs the object's type(s) to match `targetTypes`. Two approaches: (a) JS passes type as query param (requires JS to know the type), or (b) endpoint queries triplestore for type. Option (b) is cleaner — the endpoint does its own SPARQL query for `?type WHERE { <iri> a ?type }`. This adds a triplestore query but keeps the JS simple.
- **Renderer override breaks existing object tab features** — the app renderer template must preserve toolbar features: favorite toggle, type badge, mode toggle. Don't strip the platform chrome when rendering app fragments.

## Open Risks

- **Inbox and collaboration panels** — RESOLVED: both are self-contained `<details>` blocks with `hx-trigger="load"` that self-load via htmx. They don't depend on the current object context. They should remain as static always-present sections in the right pane. The dynamic right pane approach should only replace the object-context-dependent sections (relations, lint, comments + app contributions). The static panels (inbox, collaboration) stay as `{% include %}` directives below the dynamic container.
- **Command palette timing** — the `/api/apps/commands` fetch happens after `initCommandPalette()`. If the fetch is slow, commands won't be available for several seconds after workspace load. The design doc doesn't address this, but it's a minor UX concern — the fetch should complete well within 1 second for a local platform.
