# S03 Research: Window Namespace Consolidation

## Summary

Move all custom `window.*` globals to `window.SemPKM.*` namespace. Scope: ~144 distinct custom globals across 29 JS files, referenced from ~37 template files and 6 E2E test files. Three modules already use the `window.SemPKM*` prefix (SemPKMSettings, SemPKMLayouts, SemPKMCanvas). The work is mechanical but wide — every file that exports or consumes a cross-IIFE global needs updating. Backward-compatible shims eliminate rollout risk.

## Recommendation

**Approach: Namespace object + backward-compatible shims**

1. Create `window.SemPKM = window.SemPKM || {}` early in the script load order (api-fetch.js or a new tiny bootstrap file before all others)
2. Each IIFE exports to `window.SemPKM.X` instead of `window.X`
3. For the migration period, also set `window.X = window.SemPKM.X` as a deprecated alias (backward compat for any cached templates or third-party references)
4. Update all template `onclick` handlers and inline `<script>` blocks to use `SemPKM.X()`
5. Update all cross-IIFE `typeof window.X === 'function'` guards to `typeof SemPKM.X === 'function'`
6. Update E2E test `page.evaluate()` calls that reference `window.openTab`, `window._dockview`, etc.
7. Verification: `rg 'window\.\w+ =' frontend/static/js/` should return zero non-SemPKM, non-builtin, non-third-party results

**Don't touch:**
- Browser builtins: `window.location`, `window.open`, `window.confirm`, `window.localStorage`, etc.
- Third-party libs: `window.htmx`, `window.lucide`, `window.posthog`, `window.Yasgui`, `window.Chart`, `window.driver`, `window.DockviewCore`
- Already-namespaced: `window.SemPKMSettings`, `window.SemPKMLayouts`, `window.SemPKMCanvas` — these already follow the convention. They stay as-is under `window.SemPKM*` (they're effectively already namespaced, just using concatenated naming rather than dot notation). Moving them to `window.SemPKM.Settings` etc. is optional polish — not required for this slice.

## Implementation Landscape

### Files that EXPORT globals (source files that set `window.X =`)

| File | Export count | Key globals |
|------|-------------|-------------|
| workspace.js | ~90 | openTab, closeTab, switchTab, markDirty, markClean, showToast, showTypePicker, showCreateFormForType, toggleObjectMode, saveCurrentObject, showConfirmDialog, toggleBottomPanel, refreshNavTree, etc. |
| workspace-layout.js | ~11 | _dockview, initWorkspaceLayout, splitRight, getActiveEditorArea, switchTabInGroup, loadTabInGroup, closeTabInGroup, renderGroupTabBar, setActiveGroup, _tabMeta, _workspaceLayout |
| graph.js | ~12 | initGraph, filterGraph, _sempkmGraph, _sempkmTypeColors, switchGraphTheme, changeLayout, registerLayout, _setIconMode, _toggleGraphIcons |
| federation.js | ~13 | acceptInvitation, declineInvitation, syncSharedGraph, showFederationToast, showInviteForm, etc. |
| editor.js | ~8 | initEditor, getEditor, destroyEditor, editorAction, switchEditorThemes |
| tutorials.js | ~10 | startWelcomeTour, startCreateObjectTour, startDemoTour, openGenericViewTab, openDashboardTab, openCanvasTab, openTab (re-export) |
| canvas.js | ~3 | SemPKMCanvas, __canvasDragPayload |
| calendar.js | ~6 | initCalendar, _sempkmCalendar, __calendarDragPayload, _calendarSelectedDates |
| cleanup.js | ~3 | registerCleanup, runCleanup, _sempkmCleanup |
| sidebar.js | ~4 | toggleSidebar, toggleSidebarGroup, getAvatarColor, getInitials |
| theme.js | ~3 | setTheme |
| api-fetch.js | ~1 | apiFetch |
| settings.js | ~1 | SemPKMSettings (already namespaced) |
| named-layouts.js | ~1 | SemPKMLayouts (already namespaced) |
| markdown-render.js | ~2 | renderMarkdownBody, renderMarkdownFromUrl |
| column-prefs.js | ~1 | ColumnPrefs |
| bmc.js, okr.js, quadrant.js, decision-matrix.js, kanban.js | 1 each | initBMC, initOKR, initQuadrant, initDecisionMatrix, initKanban |
| recurrence-editor.js | ~2 | initRecurrenceEditor, initExdateEditor |
| vfs-browser.js | ~2 | openMountSettings |
| posthog.js | ~1 | posthog (third-party — leave as-is) |
| context-indicator.js | ~1 | switchPersona (re-export) |

### Templates that DEFINE globals (inline `<script>` blocks)

| Template | Globals defined | Notes |
|----------|----------------|-------|
| object_tab.html | 11 | getPropsPreference, setPropsPreference, toggleProperties, initPropertiesState + _tabMeta writes |
| event_log.html | 7 | sempkmRefreshEventLog, sempkmToggleAutoRefresh, _sempkmRefreshTimer, _sempkmCmdListener |
| workflow_builder.html | 7 | _wfBuilder* functions |
| dashboard_builder.html | 7 | _builder* functions, _deleteDashboard |
| settings_page.html | 5 | showSettingsCategory, filterSettings, settingChanged, resetSingleSetting, resetCategorySettings |
| lint_panel.html | 1 | _viewFilterRefocusBound |
| others (ontology, webid, notifications, etc.) | 1-4 each | Various small inline handlers |

### Templates that CONSUME globals (onclick handlers / inline calls)

- **30 `openTab()` calls** across ~15 templates (the single most-referenced global)
- **10 `editorAction()` calls** in object_tab.html toolbar
- **10 `renderMarkdownBody()` calls** in object_read.html and partials
- Templates use BOTH patterns: `onclick="openTab(...)"` (bare — resolves via global scope) and `onclick="window.openTab(...)"` (explicit). After migration, both must become `SemPKM.openTab(...)`.

### E2E tests that reference window globals

| File | Globals used |
|------|-------------|
| e2e/helpers/dockview.ts | `window._dockview`, `window.openGenericViewTab`, `window.openTab` |
| e2e/tests/02-views/graph-interaction.spec.ts | `window._sempkmGraph` (via `dispatchEvent`) |
| e2e/tests/03-navigation/split-panes.spec.ts | `window._dockview` |
| e2e/tests/03-navigation/named-layouts.spec.ts | `window.SemPKMLayouts` |
| e2e/tests/50-demo/demo-full-flow.spec.ts | `window.startDemoTour` |
| e2e/tests/screenshots/capture.spec.ts | `window.openDashboardTab` |

### Script load order (base.html)

```
vendor.js → posthog.js → api-fetch.js → auth.js → tutorials.js →
cleanup.js → markdown-render.js → editor.js (module) → sidebar.js →
theme.js → settings.js → workspace-layout.js → named-layouts.js →
workspace.js → graph.js → kanban.js → canvas.js → column-prefs.js
```

Plus from workspace.html: `workspace-vendor.js`, `dockview-core CDN`, `federation.js (defer)`, `context-indicator.js`.

**Key constraint:** `window.SemPKM = {}` must be initialized before `api-fetch.js` (the first custom script that exports). Best place: top of `api-fetch.js` itself, or a 1-line inline `<script>` in `base.html` before all custom JS.

## Seams & Task Decomposition

The work divides cleanly into 4-5 tasks:

### T01: Namespace bootstrap + JS file migration
- Add `window.SemPKM = window.SemPKM || {};` to the earliest-loading JS file (api-fetch.js, line 1 of the IIFE)
- For each of the ~29 JS files: change `window.X = ...` to `window.SemPKM.X = ...`
- At the end of each file's export block, add backward-compat shims: `window.X = window.SemPKM.X;`
- Update all `typeof window.X === 'function'` guards within JS files to `typeof SemPKM.X === 'function'`
- Update all `window.X(...)` calls within JS files to `SemPKM.X(...)`

This is the largest task (~29 files × ~5-20 edits each) but fully mechanical. The backward-compat shims mean nothing breaks during migration.

**Verification:** `node -c` on each modified JS file. `rg 'window\.\w+ =' frontend/static/js/` should only show `window.SemPKM` assignments plus backward-compat shim lines.

### T02: Template migration
- Update all 37 template files that reference custom globals
- `onclick="openTab(...)"` → `onclick="SemPKM.openTab(...)"`
- `window.openTab(...)` → `SemPKM.openTab(...)`
- `typeof window.X === 'function'` → `typeof SemPKM.X === 'function'`
- Inline `<script>` blocks that define globals: `window.X = ...` → `window.SemPKM.X = ...` (plus shim if referenced from other templates)

**Verification:** `rg 'window\.\w+' backend/app/templates/` should only show browser builtins (`window.location`, `window.confirm`, etc.) and third-party (`window.htmx`, `window.lucide`).

### T03: E2E test updates
- Update 6 E2E test files to use `window.SemPKM.X` in `page.evaluate()` calls
- Small scope: ~10 references total

**Verification:** `npx tsc --noEmit` in `e2e/` (type-check). Running actual E2E tests is deferred to S07.

### T04: Remove backward-compat shims
- Remove all `window.X = window.SemPKM.X;` lines from JS files
- This is the "cut over" — after templates and E2E tests are migrated, the shims are dead code
- Keep this as the last task so T01 provides safety during T02/T03

**Verification:** `rg 'window\.\w+ =' frontend/static/js/` should show ONLY `window.SemPKM` assignments. `rg 'window\.SemPKM\.\w+ =' frontend/static/js/ | wc -l` should match the expected count (~144). Zero non-SemPKM, non-builtin, non-third-party assignments.

## Risks & Constraints

### Risk 1: Template inline scripts that define globals consumed by JS files (medium)
Some templates (object_tab.html, event_log.html, settings_page.html) define `window.X` functions in inline `<script>` blocks that are consumed by other JS files or other templates. These must migrate to `window.SemPKM.X` in T02, and the consumers in JS files must already expect the new location (done in T01 via shims).

**Mitigation:** T01 shims ensure both `window.X` and `window.SemPKM.X` work simultaneously. T02 migrates templates. T04 removes shims only after everything is migrated.

### Risk 2: Lazy-loaded ES modules (copilot.js, sparql-console.js) (low)
These modules use `window.openTab` in string concatenation for onclick handlers in dynamically generated HTML. The strings must be updated to `SemPKM.openTab`. These files don't export to window themselves — they only consume.

### Risk 3: htmx-swapped content with stale references (low)
Template partials loaded via htmx might be cached in the browser. If a user has a stale cached partial that calls `openTab(...)` (bare), it would fail after shim removal. In practice, htmx requests include cache-busting headers and the partials are server-rendered on each request. The shim period (T01→T04) provides safety.

### Risk 4: Naming collision with SemPKM sub-objects (low)
Current globals like `_sempkmGraph`, `_sempkmCalendar`, `_sempkmIcons` would become `SemPKM._sempkmGraph` — the `_sempkm` prefix is now redundant under the namespace. Consider dropping the prefix: `SemPKM.graph`, `SemPKM.calendar`, `SemPKM.icons`. This is cleaner but means the shim can't be a simple `window.X = SemPKM.X` since the name changes. **Recommendation:** Keep original names for mechanical safety (`SemPKM._sempkmGraph`). A follow-up cosmetic rename can happen later.

## What NOT to Do

- **Don't convert IIFEs to ES modules.** That's a different (larger) refactoring. This slice is purely about namespacing the global exports.
- **Don't reorganize or restructure the module boundaries.** Each file keeps its current responsibilities. We're only changing where exports land.
- **Don't rename the existing `SemPKMSettings`/`SemPKMLayouts`/`SemPKMCanvas` to `SemPKM.Settings` etc.** They already avoid collision. Moving them creates unnecessary churn. Leave them as-is.
- **Don't break the backward-compat shims prematurely.** T04 removes them only after T02+T03 are complete.

## Counts for Verification

After completion:
- `rg 'window\.\w+ =' frontend/static/js/ | grep -v 'window\.SemPKM' | grep -v '//'` → zero lines (excluding browser builtins)
- `rg 'window\.SemPKM\.' frontend/static/js/ | wc -l` → ~300+ (exports + consumers)
- `rg 'onclick=.*window\.\w+' backend/app/templates/ | grep -v 'window\.(location|confirm|prompt|open|matchMedia|lucide|htmx)'` → zero lines
- E2E: `rg 'window\.\w+' e2e/ -g '*.ts' | grep -v 'window\.(SemPKM|location|dispatchEvent|document)'` → zero lines

## Sources

No external libraries or docs needed — this is a codebase-internal refactoring of established patterns.
