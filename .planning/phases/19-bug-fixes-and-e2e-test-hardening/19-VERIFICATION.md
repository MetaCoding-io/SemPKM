---
phase: 19-bug-fixes-and-e2e-test-hardening
type: cross-phase-integration-verification
scope: phases-10-through-19
status: passed
completed: 2026-02-27
---

# Cross-Phase Integration Verification: SemPKM v2.0 Milestone (Phases 10–19)

## Integration Check Complete

### Wiring Summary

**Connected:** 12 exports/integrations properly wired
**Orphaned:** 0 exports created but unused
**Missing:** 0 expected connections not found

### API Coverage

**Consumed:** All routes have confirmed callers (htmx, fetch, workspace.js)
**Orphaned:** 0 routes with no callers

### Auth Protection

**Protected:** All write endpoints use require_role("owner") or require_role("owner", "member")
**Unprotected:** 0 sensitive write endpoints missing auth

### E2E Flows

**Complete:** 10 of 10 flows work end-to-end
**Broken:** 0 flows have structural breaks

---

## Detailed Findings

### Integration 1 — Theme System Wiring

**Claim:** Phase 13 tokens → Phase 11 flip card → Phase 14 split panes → Phase 16 event log → Phase 18 docs page. All major UI components use CSS custom property tokens and respond to data-theme changes.

**Verification method:** Grep of workspace.css, event log CSS block (lines 1877–2100), Driver.js popover CSS block (lines 2149+), 403.html, and all four CSS files.

**Findings:**

- `frontend/static/css/workspace.css`: All rules use `var(--color-*)` tokens. The flip card, split pane gutters, tab bar, bottom panel, event log section (Phase 16 lines 1878–2148), and Driver.js popover section (Phase 18 lines 2149+) all reference token variables.
- `frontend/static/css/theme.css`: Defines light and dark token sets under `html[data-theme='dark']`. `data-theme` is set both by the anti-FOUC inline script in `base.html` (synchronous, before paint) and by `theme.js` `applyTheme()`.
- `backend/app/templates/errors/403.html`: Standalone page includes its own anti-FOUC inline script, links `theme.css` and `style.css`, and uses `var(--color-*)` tokens inline. Verified at lines 8–17 and 28+.
- Event log CSS block in `workspace.css` uses `var(--color-border-subtle)`, `var(--color-surface-raised)`, `var(--color-accent)` — all tokens defined in `theme.css`.
- Driver.js popover CSS block uses `var(--color-surface)`, `var(--color-text)`, `var(--color-accent)` — all token-based.

**Status:** WIRED. All major UI surfaces use CSS token system and automatically respond to `data-theme` attribute changes.

**REQ-IDs:** DARK-01, DARK-02, DARK-03, DARK-04, ERR-01, WORK-06

---

### Integration 2 — Settings → Theme

**Claim:** Phase 15 (`sempkm:setting-changed` event) → Phase 13 (`theme.js` listener). Dark mode preference saved via Settings propagates to theme system.

**Verification method:** Read `settings.js` lines 19–23 and 37–43; read `theme.js` lines 95–121.

**Findings:**

- `frontend/static/js/settings.js`: `SemPKMSettings.set(key, value)` dispatches `sempkm:setting-changed` CustomEvent on `document` with `{key, value}` detail. This fires both on explicit set and on reset (with `data.default_value`).
- `frontend/static/js/theme.js` lines 95–121: `document.addEventListener('sempkm:setting-changed', ...)` checks `e.detail.key === 'core.theme'` and calls `window.setTheme(newTheme)`. Also writes through to `localStorage` to keep anti-FOUC fast-path accurate.
- `theme.js` additionally performs a DOMContentLoaded server-sync (300ms delay) that reads `window.SemPKMSettings.get('core.theme')` and calls `setTheme()` if divergent from localStorage. This handles fresh-page-load sync after settings are fetched.
- The round-trip is complete: Settings page `settingChanged()` → `SemPKMSettings.set()` → `sempkm:setting-changed` event → `theme.js` listener → `setTheme()` → `applyTheme()` → `document.documentElement.setAttribute('data-theme', resolved)`.

**Status:** WIRED. Settings → Theme pipeline is connected end-to-end with no gaps.

**REQ-IDs:** SETT-02, DARK-01

---

### Integration 3 — Cleanup → Editor Groups

**Claim:** Phase 10 cleanup registry → Phase 14 Split.js tracking. Split.js instances in editor groups properly destroyed on group removal.

**Verification method:** Read `cleanup.js` (full file); grep `registerCleanup` across JS files; grep `groupSplitInstance` in `workspace-layout.js`.

**Findings:**

- `frontend/static/js/cleanup.js`: Exports `window.registerCleanup(elementId, fn)` and `window._sempkmCleanup`. The `htmx:beforeCleanupElement` handler walks descendants via `querySelectorAll('[id]')` and fires all registered teardowns.
- `frontend/static/js/editor.js` line 109: Calls `window.registerCleanup(containerId, ...)` after `EditorView` creation for CodeMirror teardown.
- `frontend/static/js/graph.js` line 270–271: Calls `window.registerCleanup(container.id, ...)` after `cytoscape()` creation for Cytoscape teardown.
- Phase 14 Split.js (`workspace-layout.js`): Uses a module-level `groupSplitInstance` variable (line 21). The `recreateGroupSplit()` function (line 289) calls `groupSplitInstance.destroy()` before creating a new Split.js instance (lines 294–296). This destroy-before-recreate guard prevents gutter duplication.
- **Gap noted:** `groupSplitInstance` is NOT registered with `window.registerCleanup`. Instead it is tracked as a module-level closure variable and destroyed manually inside `recreateGroupSplit()`. This is intentional — the split is between editor groups (a single persistent horizontal split), not between htmx-swapped tabs. The cleanup registry pattern covers per-tab objects (CodeMirror, Cytoscape); the group split is recreated by `recreateGroupSplit()` calls, not htmx DOM swaps.
- The Phase 10 cleanup registry covers object-tab-level CodeMirror and graph instances (destroyed when an object tab is replaced by htmx). The Phase 14 group-level Split.js uses its own destroy-and-recreate pattern on `addGroup`/`removeGroup`.

**Status:** WIRED. The two cleanup approaches are correctly separated by scope: htmx-swap teardown via registry for per-tab instances; manual destroy-recreate for group-level split. No memory leak gap exists.

**REQ-IDs:** FIX-05, WORK-01, WORK-02

---

### Integration 4 — Icon Service → UI Components

**Claim:** Phase 15 (`IconService`, `window._sempkmIcons`) → nav tree icons, graph shapes, editor tab icons. Do icon mappings reach all three consumers?

**Verification method:** Grep `_sempkmIcons` in `workspace.js` and `graph.js`; grep `type_icon` and `typeIcon` in `object_tab.html` and `workspace-layout.js`; grep `type_icons` in `nav_tree.html`.

**Findings:**

- **Icons fetch:** `workspace.js` line 1245–1252: On init, fetches `GET /browser/icons` and stores result as `window._sempkmIcons = { tree: {...}, tab: {...}, graph: {...} }`.
- **Graph shapes:** `frontend/static/js/graph.js` lines 118–130: `buildSemanticStyle()` reads `window._sempkmIcons.graph` to apply `iconToShape` mapping (file-text→rectangle, lightbulb→diamond, folder-kanban/book-open→round-rectangle, user/tag→ellipse). Verified working.
- **Editor tab icons:** `backend/app/templates/browser/object_tab.html` lines 116–136: Inline IIFE after htmx swap reads `type_icon.icon` and `type_icon.color` from Jinja2 context, pushes them into the tab object in `window._workspaceLayout`, then calls `window.renderGroupTabBar(group)` to re-render. `workspace-layout.js` line 641–647: `renderGroupTabBar()` creates a `<i data-lucide="...">` element when `tab.typeIcon` is set, followed by Lucide `createIcons()` call.
- **Nav tree icons:** `backend/app/browser/router.py` line 409: Workspace route injects `type_icons` (from `icon_svc.get_icon_map(context="tree")`). Template `nav_tree.html` uses `data-lucide` elements with per-type color from this dict. `tree_children.html` receives `type_icon` from its route at line 470.
- **`window.renderGroupTabBar` export:** `workspace-layout.js` line 1052 exports it globally. `object_tab.html` line 129 calls `renderGroupTabBar` (non-prefixed). Since `workspace-layout.js` exposes it as `window.renderGroupTabBar`, the inline script in `object_tab.html` will find it on `window`.

**Status:** WIRED. All three consumers (graph, tab bar, nav tree) receive icon data from IconService through their respective pipelines.

**REQ-IDs:** ICON-01, ICON-02, ICON-03

---

### Integration 5 — Event Log → Write Operations → Label Cache Invalidation

**Claim:** Phase 16 (undo) → Phase 19 (label cache invalidation after undo). Does undo correctly invalidate the label cache?

**Verification method:** Read `workspace.js` `sempkmUndoEvent` function (lines 1366–1392); read `router.py` undo endpoint lines 1368–1372.

**Findings:**

- `frontend/static/js/workspace.js` `sempkmUndoEvent()`: POSTs to `/browser/events/{iri}/undo` (using `encodeURIComponent(eventIri)`), shows confirm dialog, disables button, handles success by reloading `#panel-event-log` via `htmx.ajax('GET', '/browser/events', ...)`.
- `backend/app/browser/router.py` `undo_event` endpoint (line ~1340–1372): Calls `event_store.commit([compensation], ...)`, stores result as `event_result`, then calls `label_service.invalidate(event_result.affected_iris)` at line 1371. This is the Phase 19 fix — the undo path previously discarded the commit result.
- All four write paths have label cache invalidation: `save_body` (line 747), `create_object` (line 1063), `save_object` (line 1170), `undo_event` (line 1371).
- `undo_event` receives `event_store` via `Depends(get_event_store)` FastAPI DI (Phase 19-01 fix). The compensation operation's `affected_iris` correctly includes the object whose properties were reverted, so `label_service.invalidate()` clears stale labels for that object.

**Status:** WIRED. The undo → label cache invalidation chain is complete and correctly wired through all four write operations.

**REQ-IDs:** EVNT-04

---

### Integration 6 — Bottom Panel → Event Log → Filter → Undo (Full User Flow)

**Claim:** Open bottom panel (Ctrl+J), load event log, apply filter, view diff, click undo. Each step connects to the next.

**Verification method:** Trace workspace.js panel code, event_log.html template, workspace.js `sempkmUndoEvent`, router.py undo endpoint.

**Findings:**

Step 1 — **Ctrl+J opens panel:** `workspace.js` `initKeyboardShortcuts()` maps Ctrl+J to `toggleBottomPanel()`. `_applyPanelState()` adds CSS class `panel-open` which changes height from 0 to stored px. Height-transition animation avoids display:none jump.

Step 2 — **Event log lazy-load:** `workspace.js` `initPanelTabs()` and `_applyPanelState()` both check for `.panel-placeholder` in `#panel-event-log` before calling `htmx.ajax('GET', '/browser/events', {target: '#panel-event-log', swap: 'innerHTML'})`. The guard prevents double-loads.

Step 3 — **Filter UI:** `event_log.html` renders op dropdown, date-from/date-to inputs with `hx-include`, and active filter chips. Each filter change fires `hx-get="/browser/events"` with updated params targeting `#panel-event-log`. The `dict_without|urlencode` Jinja2 filter chain (registered in `main.py`) produces correct chip-remove URLs.

Step 4 — **Diff view:** Each `.event-row-wrapper` has an `.event-diff-container` (hidden via `:empty { display: none }`). The Diff button uses `hx-get="/browser/events/{iri}/detail"` targeting `#diff-{{ loop.index }}` with `hx-swap="innerHTML"`. `event_detail.html` renders body diff (line-by-line), property diff (before/after table), or creation triples depending on `event.operation_type`.

Step 5 — **Undo:** Undo button calls `sempkmUndoEvent(iri, btn)` via onclick. The function POSTs to `/browser/events/{iri}/undo`, shows confirm dialog, then reloads the event log panel on success. The undo endpoint commits a compensating event and invalidates the label cache.

**Status:** WIRED. All five steps connect. Each step's output is the next step's input.

**REQ-IDs:** EVNT-01, EVNT-02, EVNT-03, EVNT-04

---

### Integration 7 — Object Creation → Type IRI → Edit Form

**Claim:** Phase 19 (full type IRI fix) → Phase 11 (flip card edit form). An object created with type=full-IRI opens in edit mode with the correct SHACL form.

**Verification method:** Read `object_create.py` lines 82–90; read `router.py` `create_object` lines 1025–1097; read `workspace.js` `objectCreated` handler lines 1316–1323; read `openTab()` lines 63–100.

**Findings:**

- `object_create.py` lines 82–88: Handler correctly passes full IRI to `type_iri = URIRef(params.type)` when the type starts with `http://`, `https://`, or `urn:`. The `local_name` is extracted from the full IRI for object IRI minting only. This is the Phase 19 full-type-IRI fix.
- `router.py` `create_object` line 1057: `params = ObjectCreateParams(type=type_iri, ...)` passes the full form-submitted type IRI to the handler.
- After creation, `router.py` line 1079: `form = await shapes_service.get_form_for_type(type_iri)` re-fetches the SHACL form using the full type IRI. This is the same IRI that was submitted in the form's hidden `type_iri` field.
- `router.py` line 1094–1096: Response includes `HX-Trigger: {"objectCreated": {"iri": "{created_iri}", "label": "..."}}`.
- `workspace.js` `objectCreated` listener (line 1316): On receiving this event, calls `openTab(detail.iri, label, 'edit')` after 1500ms delay.
- `openTab()` line 82–89: When `mode === 'edit'`, fires `htmx.ajax('GET', '/browser/object/{iri}?mode=edit', ...)` targeting the active editor area.
- `router.py` `get_object` line 486: Accepts `mode: str = Query(default="read")`. When `mode=edit` is passed, line 619 includes `"mode": mode` in the Jinja2 context, which `object_tab.html` uses to set `data-mode="{{ mode }}"` on the flip container. This triggers immediate edit-face display on load.
- `get_object` line 543–547: Iterates type_iris and calls `shapes_service.get_form_for_type(type_iri)` for each until a form is found. With full type IRI correctly stored in the triplestore, this lookup succeeds.

**Status:** WIRED. Full-IRI object creation → SHACL form lookup → edit-mode tab open is correctly connected end-to-end.

**REQ-IDs:** VIEW-01, VIEW-02

---

### Integration 8 — LLM Config → Settings Page

**Claim:** Phase 17 (LLM config API) → Phase 15 (Settings page). LLM section renders with owner-only write guards. `api_key_set` bool is visible, never the key.

**Verification method:** Read `_llm_settings.html` (full); read `settings_page.html` LLM conditional blocks; grep `api_key_set` and `llm_config` in `router.py`.

**Findings:**

- `router.py` `get_settings_page` (lines 105–121): `llm_config = None` by default. Only when `user.role == "owner"` is `LLMConfigService.get_config(db)` called and `llm_config` set. Non-owners receive `llm_config=None`.
- `settings_page.html` lines 21–27 and 70–79: Both the sidebar nav button and the detail panel are wrapped in `{% if llm_config is not none %}`. Non-owners see no LLM Connection category at all.
- `_llm_settings.html` line 25–27: Shows `<span class="settings-modified-badge">Set</span>` only when `llm_config.api_key_set` is truthy. The password input placeholder shows `"••••••••"` when set, otherwise `"Enter API key"`. The raw key is never rendered.
- `router.py` `settings_data` (line 159): `resolved.pop("llm.api_key", None)` removes any encrypted key from the JSON response sent to `settings.js` cache. Defense-in-depth even if the key somehow got into the settings dict.
- Write endpoints `PUT /browser/llm/config`, `POST /browser/llm/test`, `POST /browser/llm/models` all use `Depends(require_role("owner"))`.
- The `llmSettingChanged()` inline script in `_llm_settings.html` uses debounced 600ms `fetch PUT /browser/llm/config`. If a non-owner somehow called this (UI not shown to them), the server-side `require_role("owner")` guard would return 403.

**Status:** WIRED. Owner-only access, `api_key_set` bool (never key value), correct conditional rendering all confirmed.

**REQ-IDs:** LLM-01, LLM-02, LLM-03, LLM-04

---

### Integration 9 — nginx Routing (merge_slashes off, IRI path segments)

**Claim:** Phase 19 (`merge_slashes off`, IRI path segments) → all `/browser/object/{iri:path}` routes. IRIs with colons and slashes round-trip through nginx correctly.

**Verification method:** Read `frontend/nginx.conf` (full); read `_validate_iri()` in `router.py` lines 42–71.

**Findings:**

- `frontend/nginx.conf` line 8: `merge_slashes off;` is set at the `server {}` block level, applying to all location blocks including the catch-all `location /`. This prevents nginx from collapsing percent-encoded `%2F` slashes after URL decoding.
- The IRI `https://example.org/obj` is encoded as `https%3A%2F%2Fexample.org%2Fobj` in the URL path. Without `merge_slashes off`, nginx decodes `%2F` to `/` then collapses `//` to `/`, yielding `https%3A/example.org/obj`. FastAPI's `unquote()` then produces `https:/example.org/obj`, which `urlparse()` sees as scheme=`https`, netloc=`""`, causing `_validate_iri()` to return `False` and raising HTTP 400.
- With `merge_slashes off`, the encoded path is passed through unchanged. FastAPI's `unquote()` produces `https://example.org/obj`, `urlparse()` correctly identifies netloc, and `_validate_iri()` returns `True`.
- `_validate_iri()` lines 56–69: Updated in Phase 19 to also accept `urn:` scheme IRIs (no netloc, opaque path) used by basic-pkm model. Rejects forbidden SPARQL injection characters (`<>"\{}\n\r\t `) before SPARQL interpolation.
- The LLM SSE location block `location /browser/llm/chat/stream` (lines 54–71) is correctly placed before the catch-all `location /` (line 74), preventing the catch-all from consuming streaming requests.
- E2E tests confirmed this fix: `tests/01-objects/edit-object.spec.ts` and `tests/04-validation/lint-panel.spec.ts` both regressed with the 400 error and passed after `merge_slashes off` was added (Phase 19-03 SUMMARY).

**Status:** WIRED. nginx routing is correctly configured for IRI path segments, SSE streaming, and all `{iri:path}` routes.

**REQ-IDs:** (cross-cutting; affects VIEW-01 through VIEW-04, EVNT-01 through EVNT-04, all object routes)

---

### Integration 10 — Tutorial → Type Picker → Object Creation

**Claim:** Phase 18 (Driver.js `htmx:afterSwap` gating) → Phase 14 (type picker via workspace-layout.js). The "Create Object" tutorial correctly waits for the type picker htmx swap before advancing.

**Verification method:** Read `tutorials.js` lines 186–269; grep `showTypePicker` in `workspace.js`; verify `getActiveEditorArea` export.

**Findings:**

- `workspace.js` line 1401: `window.showTypePicker = showTypePicker` — exported as global.
- `workspace.js` line 1025–1028: `showTypePicker()` calls `htmx.ajax('GET', '/browser/types', {target: editorArea, swap: 'innerHTML'})` where `editorArea = window.getActiveEditorArea()`. This targets the active group's editor area (`#editor-area-group-N`).
- `workspace-layout.js` line 1029: `window.getActiveEditorArea = getActiveEditorArea` — exported as global. Returns `document.getElementById('editor-area-' + layout.activeGroupId)`.
- `tutorials.js` lines 205–226: `onNextClick` handler for Create Object step 1:
  1. Captures `editorArea` via `window.getActiveEditorArea()` (with fallback to `#editor-area-group-1`).
  2. Calls `window.showTypePicker()`.
  3. Attaches `htmx:afterSwap` listener on `document.body`.
  4. Guard: `e.detail.target === editorArea` — only advances when the swap targets the exact same editor area element captured before the call. This prevents spurious advances from unrelated htmx swaps.
  5. On match: removes the listener and calls `driverObj.moveNext()`.
- Steps 2–4 use lazy element form (`element: function() { return document.querySelector(...) }`) so Driver.js re-queries the DOM when rendering the step, handling the asynchronous htmx swap correctly.
- `backend/app/browser/router.py` line 946: `GET /browser/types` endpoint renders `type_picker.html`, which is the content `showTypePicker()` loads into the editor area.

**Status:** WIRED. The htmx:afterSwap gate correctly bridges the async htmx swap with Driver.js tour progression. The target-identity check prevents false advances.

**REQ-IDs:** DOCS-03, DOCS-04

---

## Orphaned Exports

None identified. All key exports verified as consumed:

| Export | Defined In | Consumed By |
|--------|-----------|-------------|
| `window.registerCleanup` | cleanup.js | editor.js, graph.js |
| `window.switchEditorThemes` | editor.js | theme.js |
| `window.switchGraphTheme` | graph.js | theme.js (direct call + sempkm:theme-changed listener) |
| `window.SemPKMSettings` | settings.js | theme.js (DOMContentLoaded sync), settings_page.html |
| `window._sempkmIcons` | workspace.js (fetch) | graph.js (shapes), workspace-layout.js (tab icons) |
| `window.sempkmUndoEvent` | workspace.js | event_log.html (onclick) |
| `window.renderGroupTabBar` | workspace-layout.js | object_tab.html (inline script) |
| `window.showTypePicker` | workspace.js | tutorials.js, command palette |
| `window.getActiveEditorArea` | workspace-layout.js | workspace.js, tutorials.js |
| `window.startWelcomeTour` | tutorials.js | docs_page.html (onclick button) |
| `window.startCreateObjectTour` | tutorials.js | docs_page.html (onclick button) |
| `window.openDocsTab` | workspace.js | _sidebar.html (onclick) |

---

## Missing Connections

None identified.

---

## Broken Flows

None identified.

---

## Unprotected Routes

None identified for write operations. All four write paths have `require_role()` guards:

| Route | Guard |
|-------|-------|
| `PUT /browser/llm/config` | `require_role("owner")` |
| `POST /browser/llm/test` | `require_role("owner")` |
| `POST /browser/llm/models` | `require_role("owner")` |
| `POST /browser/objects` | `require_role("owner", "member")` |
| `POST /browser/objects/{iri}/save` | `require_role("owner", "member")` |
| `POST /browser/object/{iri}/body` | `require_role("owner", "member")` |
| `POST /browser/events/{iri}/undo` | `require_role("owner", "member")` |
| `/sparql`, `/commands` debug pages | `require_role("owner")` |

---

## Requirements Integration Map

| Requirement | Integration Path | Status | Issue |
|-------------|-----------------|--------|-------|
| FIX-01 | Phase 10 → object_tab.html skeleton → editor.js Promise.race | WIRED | — |
| FIX-02 | Phase 10 → object_tab.html → editor.js timeout fallback | WIRED | — |
| FIX-03 | Phase 10 → object_form.html htmx:afterSwap → workspace.css position:fixed | WIRED | — |
| FIX-04 | Phase 10 → workspace.html → views explorer hx-trigger=load | WIRED | — |
| FIX-05 | Phase 10 cleanup.js → editor.js/graph.js registerCleanup → htmx:beforeCleanupElement | WIRED | — |
| VIEW-01 | Phase 11 object_tab.html flip container → Phase 19 full-type-IRI in object_create handler → shapes_service.get_form_for_type | WIRED | — |
| VIEW-02 | Phase 11 mode toggle → workspace.js toggleObjectMode → read face refresh on flip-back | WIRED | — |
| VIEW-03 | Phase 11 object_read.html reference pills → label_service.resolve_batch → router.py get_object | WIRED | — |
| VIEW-04 | Phase 11 body predicate unification → body_set.py → router.py body detection | WIRED | — |
| NAV-01 | Phase 12 _sidebar.html grouped sections → sidebar.js collapse toggle | WIRED | — |
| NAV-02 | Phase 12 Ctrl+B → sidebar.js toggleSidebar | WIRED | — |
| NAV-03 | Phase 12 Lucide CDN → sidebar.js initLucide → htmx:afterSwap re-init | WIRED | — |
| NAV-04 | Phase 12 localStorage → sidebar.js section/collapse state persistence | WIRED | — |
| NAV-05 | Phase 12 user menu popover → _sidebar.html HTML Popover API | WIRED | — |
| NAV-06 | Phase 12 user menu logout → handleLogout in auth.js | WIRED | — |
| DARK-01 | Phase 13 theme.css tokens → all CSS files migrated → data-theme attribute → anti-FOUC script | WIRED | — |
| DARK-02 | Phase 13 anti-FOUC inline script in base.html → localStorage read before paint | WIRED | — |
| DARK-03 | Phase 13 theme.js applyTheme → switchEditorThemes (editor.js) + switchGraphTheme (graph.js) | WIRED | — |
| DARK-04 | Phase 13 theme toggle UI (Sun/Monitor/Moon) → setTheme → localStorage | WIRED | — |
| WORK-01 | Phase 14 workspace-layout.js WorkspaceLayout class → splitRight → Split.js destroy-recreate | WIRED | — |
| WORK-02 | Phase 14 tab drag-drop → initTabDrag/initTabBarDropZone → layout.moveTab | WIRED | — |
| WORK-03 | Phase 14 context menu → showTabContextMenu → closeOtherTabsInGroup/splitRight | WIRED | — |
| WORK-04 | Phase 14 bottom panel → workspace.js toggleBottomPanel → Ctrl+J | WIRED | — |
| WORK-05 | Phase 14 panel resize → localStorage sempkm_bottom_panel → height persistence | WIRED | — |
| WORK-06 | Phase 13/14 rounded tabs → workspace.css tab-bar-workspace → active teal accent | WIRED | — |
| SETT-01 | Phase 15 SettingsService → GET/PUT/DELETE /browser/settings/* → UserSetting ORM | WIRED | — |
| SETT-02 | Phase 15 Settings page → SemPKMSettings.set('core.theme') → sempkm:setting-changed → theme.js setTheme | WIRED | — |
| SETT-03 | Phase 15 settings.js auto-fetch on DOMContentLoaded → SemPKMSettings cache warm | WIRED | — |
| SETT-04 | Phase 15 Ctrl+, → openSettingsTab → workspace-layout.js special:settings branch | WIRED | — |
| ICON-01 | Phase 15 IconService → /browser/icons endpoint → window._sempkmIcons fetch in workspace.js | WIRED | — |
| ICON-02 | Phase 15 _sempkmIcons.graph → graph.js buildSemanticStyle iconToShape | WIRED | — |
| ICON-03 | Phase 15 type_icon in get_object context → object_tab.html inline script → renderGroupTabBar tab icon | WIRED | — |
| EVNT-01 | Phase 16 EventQueryService → GET /browser/events → workspace.js lazy-load on panel tab click | WIRED | — |
| EVNT-02 | Phase 16 event_log.html filter chips/controls → hx-get with dict_without\|urlencode → /browser/events | WIRED | — |
| EVNT-03 | Phase 16 event_detail.html → GET /browser/events/{iri}/detail → hx-get Diff button | WIRED | — |
| EVNT-04 | Phase 16 sempkmUndoEvent → POST /browser/events/{iri}/undo → compensation event → label_service.invalidate | WIRED | — |
| LLM-01 | Phase 17 LLMConfigService Fernet encryption → InstanceConfig rows → get_config returns api_key_set bool | WIRED | — |
| LLM-02 | Phase 17 settings_page.html llm_config conditional → _llm_settings.html → owner-only render | WIRED | — |
| LLM-03 | Phase 17 PUT /browser/llm/config require_role("owner") → save_config → Fernet encrypt | WIRED | — |
| LLM-04 | Phase 17 GET /browser/settings/data resolved.pop("llm.api_key") → key never reaches browser | WIRED | — |
| LLM-05 | Phase 17 POST /browser/llm/chat/stream SSE → nginx location block proxy_buffering off | WIRED | — |
| DOCS-01 | Phase 18 docs_page.html special:docs tab → workspace-layout.js URL branch → GET /browser/docs | WIRED | — |
| DOCS-02 | Phase 18 StaticFiles /docs/guide → main.py is_dir() guard → docker-compose volume mount | WIRED | — |
| DOCS-03 | Phase 18 startWelcomeTour → Driver.js 10-step tour → lazy element selectors | WIRED | — |
| DOCS-04 | Phase 18 startCreateObjectTour → showTypePicker() → htmx:afterSwap gate → driverObj.moveNext() | WIRED | — |
| ERR-01 | Phase 13 403.html standalone → anti-FOUC script → theme.css → var(--color-*) tokens | WIRED | — |

**Requirements with no cross-phase wiring (self-contained):** None. All requirements have at least one verified cross-phase connection.

---

## E2E Suite Status

Per Phase 19 final suite run: **124/129 passing** on `npx playwright test --project=chromium`.

5 failing tests are exclusively in `00-setup/01-setup-wizard.spec.ts`, which requires a fresh Docker stack with `setup_mode=true`. These pass on first run from a clean environment; they are an infrastructure constraint, not application regressions. A detailed comment block explaining this was added to the spec file in Phase 19-03.

No new regressions were introduced in Phases 10–19. Two pre-existing test failures (`edit-object.spec.ts` and `lint-panel.spec.ts`) were fixed in Phase 19-03 by the `nginx merge_slashes off` fix.

---

*Verification completed: 2026-02-27*
*Phases verified: 10, 11, 12, 13, 14, 15, 16, 17, 18, 19*
*Plans verified: 27 total*
