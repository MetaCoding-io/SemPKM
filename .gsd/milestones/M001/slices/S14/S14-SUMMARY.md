---
id: S14
parent: M001
milestone: M001
provides:
  - Collapsible bottom panel with SPARQL, Event Log, AI Copilot placeholder panes
  - Ctrl+J keyboard shortcut toggles panel open/closed
  - Drag resize handle adjusts panel height (80px–80% of workspace), stored in localStorage
  - Maximize toggle hides editor groups and expands panel to full editor-column height
  - Panel open/closed state, height percentage, and active tab persist across page reloads
  - Command palette entries: Toggle Panel (ctrl+j), Maximize Panel, Split Right (ctrl+\\), Close Group
  - CSS height-transition-based open/close animation (replaces display toggle)
  - Bottom panel DOM preserved across recreateGroupSplit calls
requires: []
affects: []
key_files: []
key_decisions:
  - "CSS height transition (height: 0 -> Npx with overflow:hidden) for smooth panel open/close instead of display:none toggle -- avoids layout jump"
  - "Bottom panel DOM detached and re-inserted around recreateGroupSplit to survive Split.js reinitialization"
  - "panel-resize-handle visibility controlled by panel-open CSS class (not JS display) so transition applies"
  - "panelState.height stored as percentage (0-100) not pixels -- scales correctly on window resize"
patterns_established:
  - "Panel infrastructure pattern: placeholder tabs with Lucide icons ready for Phase 16/17 population"
  - "CSS height animation pattern for collapsible regions: height:0 + overflow:hidden + transition:height"
  - "DOM preservation pattern for Split.js recreation: save real DOM nodes, wipe container, re-insert before recreate"
observability_surfaces: []
drill_down_paths: []
duration: ~60min (including UAT bug fixes)
verification_result: passed
completed_at: 2026-02-24
blocker_discovered: false
---
# S14: Split Panes And Bottom Panel

**# Phase 14 Plan 01: WorkspaceLayout Foundation Summary**

## What Happened

# Phase 14 Plan 01: WorkspaceLayout Foundation Summary

WorkspaceLayout class with EditorGroup data model, Split.js destroy-and-recreate strategy, sessionStorage migration from sempkm_open_tabs to sempkm_workspace_layout, multi-group DOM structure, and full workspace.js delegation wiring.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create workspace-layout.js | a9c26b9 | frontend/static/js/workspace-layout.js (new, 637 lines) |
| 2 | Wire workspace.js, restructure HTML/CSS | 9ae2a9c | workspace.js, workspace.css, workspace.html, base.html |

## What Was Built

**workspace-layout.js (637 lines):**
- `WorkspaceLayout` class: addGroup (max 4), removeGroup (redistributes tabs to left neighbor), moveTab (cross-group), addTabToGroup, removeTabFromGroup, setActiveGroup, save, static restore
- `migrateTabState()`: converts sempkm_open_tabs + sempkm_active_tab to sempkm_workspace_layout on first load
- `recreateGroupSplit()`: destroys Split.js, clears editorPane.innerHTML, creates group DOM (editor-group > group-tab-bar + group-editor-area), creates new Split.js with gutterClass:'gutter-editor-groups' when groups.length > 1, restores content
- `renderGroupTabBar()`: builds tab HTML with draggable="true" and data-tab-id/data-group-id attributes (stub for Plan 02 DnD)
- `loadTabInGroup()`: htmx.ajax to #editor-area-{groupId}; detects view: prefix for view tabs
- `splitRight()`: addGroup() + duplicates active tab into new group
- `getActiveEditorArea()`: returns #editor-area-{activeGroupId}
- Window exports: _workspaceLayout, getActiveEditorArea, splitRight, setActiveGroup, initWorkspaceLayout, switchTabInGroup, closeTabInGroup, renderGroupTabBar, loadTabInGroup

**workspace.html restructure:**
- editor-pane now has classes `workspace-pane editor-column`
- Contains `editor-groups-container` div wrapping initial `group-1` DOM
- Old `#tab-bar` / `#editor-area` removed; replaced by `#tab-bar-group-1` / `#editor-area-group-1`
- `#bottom-panel-slot` placeholder added (Plan 03 implementation)

**workspace.js delegation:**
- openTab/closeTab/switchTab delegate to window._workspaceLayout
- All htmx targets use window.getActiveEditorArea() (no #editor-area references)
- Ctrl+\\ reassigned to splitRight; Ctrl+J stub; Ctrl+1-4 group focus
- Command palette: 'toggle-sidebar' entry replaced by 'split-right' entry
- init() calls window.initWorkspaceLayout() instead of old restoreTabState()

**workspace.css additions:**
- .editor-column (flex-direction: column)
- .editor-groups-container (display: flex, flex: 1)
- .editor-group (flex-direction: column, transition: flex 150ms ease-out)
- .group-tab-bar (mirrors .tab-bar-workspace; position: relative for Plan 02 drop indicators)
- .group-editor-area (flex: 1, overflow: auto, padding: 16px)
- .editor-group-active > .group-tab-bar (border-top: 2px solid var(--color-accent))
- .gutter.gutter-horizontal.gutter-editor-groups (1px VS Code style with ::after hit-target expansion)

## Decisions Made

1. **Ctrl+\\ = Split Right** (not sidebar toggle): CONTEXT.md and research both specify this reassignment; sidebar remains on Ctrl+B (Phase 12 decision).
2. **workspace-layout.js as separate module**: workspace.js was already 1024 lines; new module is cleaner per RESEARCH.md recommendation.
3. **gutterSize: 1 with CSS ::after**: Fixes Pitfall 2 — 1px visible gutter but 9px pointer target (4px each side).
4. **Tab normalization (both .id and .iri)**: Old tabs from migration only have .iri; new code uses .id as primary key; both set on addTabToGroup.
5. **Duplicate tabs in splitRight**: Per CONTEXT.md: "Duplicate objects are allowed — the same object can be open in multiple groups independently."

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] Added tab normalization for .id/.iri compatibility**
- **Found during:** Task 1 (addTabToGroup implementation)
- **Issue:** Old sessionStorage tabs have only `.iri` field; new code uses `.id` as primary key; mixing old and new tab objects would break tab lookups
- **Fix:** In addTabToGroup, always set both `.id = tab.iri` and `.iri = tab.id` if either is missing; all internal lookups use `(t.id || t.iri)`
- **Files modified:** frontend/static/js/workspace-layout.js
- **Commit:** a9c26b9

**2. [Rule 1 - Bug] Removed `renderTabs()` delegation stub**
- **Found during:** Task 2 analysis
- **Issue:** The plan called for `renderTabs()` to delegate to `renderGroupTabBar` for active group; but the old `renderTabs()` references `#tab-bar` which no longer exists. Instead of adding a stub that would reference a non-existent element, the function was not included in the new workspace.js (it was only called from internal tab management functions which now all use renderGroupTabBar directly)
- **Fix:** Removed renderTabs() entirely; all tab rendering now goes through window.renderGroupTabBar(group) in workspace-layout.js
- **Files modified:** frontend/static/js/workspace.js
- **Commit:** 9ae2a9c

## Self-Check

Files exist check:
- frontend/static/js/workspace-layout.js: FOUND
- frontend/static/css/workspace.css (contains .editor-groups-container): FOUND
- backend/app/templates/browser/workspace.html (contains editor-column): FOUND

Commits exist check:
- a9c26b9: FOUND
- 9ae2a9c: FOUND

## Self-Check: PASSED

# Phase 14 Plan 02: Tab Drag-and-Drop and Context Menu Summary

HTML5 Drag-and-Drop API for tab reordering within groups and cross-group moves, right-edge drop zone for creating new groups, and a right-click context menu with Close/Close Others/Split Right/Move to Group actions.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | HTML5 tab drag-and-drop (within group and between groups) | ed392a8 | frontend/static/js/workspace-layout.js |
| 2 | Right-click context menu on tabs and drag/drop CSS | 1262129 | workspace-layout.js, workspace.css |

## What Was Built

**workspace-layout.js additions (303 net insertions):**

- `isDragging` module-level flag: set `true` on dragstart, reset via `setTimeout(0)` on dragend (Pitfall 3 solution — prevents accidental tab switch after short drag that doesn't trigger dragstart fully)
- `initTabDrag(tabEl, tabId, groupId)`: sets `draggable="true"`, encodes `{tabId, sourceGroupId}` to dataTransfer, creates off-screen ghost clone with `setDragImage()`, applies/removes `.dragging` class, clears all `.drop-indicator` and `.tab-bar-drag-over` states on dragend
- `initTabBarDropZone(tabBarEl, targetGroupId)`: `dragover` → preventDefault + `_updateInsertionIndicator()`; `dragleave` → only removes state if `!tabBarEl.contains(e.relatedTarget)`; `drop` → parses data, calls `_getInsertBeforeTabId()`, calls `layout.moveTab()` + `loadTabInGroup()`
- `_updateInsertionIndicator(tabBarEl, clientX)`: finds/creates `.drop-indicator` element; iterates `.workspace-tab` elements finding first with midX > clientX; places indicator at correct left offset accounting for scrollLeft; adds `.drop-indicator-active`
- `initRightEdgeDropZone()`: attaches to `#editor-groups-container`; `dragover` checks `clientX > containerRect.right - 80` and `layout.groups.length < 4`; shows `#right-edge-drop-zone` overlay; `drop` calls `layout.addGroup()` then `layout.moveTab()` then `loadTabInGroup()`
- `renderGroupTabBar()`: **refactored** from innerHTML string-building to DOM element construction using `createElement/appendChild/addEventListener` — required for attaching `initTabDrag` and contextmenu event listeners per tab
- `recreateGroupSplit()`: **updated** to explicitly create `#editor-groups-container` div, append groups inside it, preserve/restore `#bottom-panel-slot`, then call `initRightEdgeDropZone()` after Split.js setup
- `showTabContextMenu(e, tabId, groupId)`: Pattern 6 from RESEARCH.md — removes existing `#tab-context-menu`, builds menu div with `.context-menu` class, items: Close, Close Others, separator, Split Right, and "Move to Group N" for each other group; viewport-clamped positioning; dismiss on outside click (setTimeout guard) and Escape keydown
- `closeOtherTabsInGroup(keepTabId, groupId)`: filters group.tabs to all except keepTabId, calls `layout.removeTabFromGroup()` for each

**workspace.css additions (95 lines):**

Phase 14 Tab Drag-and-Drop section:
- `.workspace-tab.dragging`: opacity 0.4, cursor grabbing
- `.group-tab-bar.tab-bar-drag-over`: `color-mix()` accent tint + dashed outline
- `.drop-indicator` / `.drop-indicator-active`: 2px vertical line, accent color, absolute positioned, transition on left
- `#right-edge-drop-zone` / `#right-edge-drop-zone.active`: 80px absolute overlay at right edge, accent fill with dashed left border

Phase 14 Tab Context Menu section:
- `.context-menu`: fixed, surface bg, border, border-radius 4px, box-shadow with fallback, z-index 10000
- `.context-menu-item`, `.context-menu-item:hover`, `.context-menu-separator`

## Decisions Made

1. **renderGroupTabBar DOM refactor**: Required for attaching event listeners per-tab element. The old innerHTML string approach cannot attach `initTabDrag` or `contextmenu` listeners without re-querying the DOM after setting innerHTML — DOM construction is cleaner and consistent with the DnD pattern.
2. **isDragging timeout reset (Pitfall 3)**: `setTimeout(0)` on dragend ensures the `click` event (which fires synchronously after a short drag) sees `isDragging = true` and bails, then it resets to false for normal subsequent clicks.
3. **initTabBarDropZone on empty tab bars**: Drop zones are registered even when tabs.length === 0, so you can drop onto a group that had all its tabs moved away (group wasn't removed yet because that only happens when source group empties).
4. **color-mix() usage**: The project already uses `color-mix()` in theme.css and workspace.css (per 14-01 SUMMARY noting color-mix is an existing pattern). The drag-over highlight uses it for consistency; a `var(--color-surface-hover)` fallback is available in the existing CSS if browser compat becomes an issue.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed recreateGroupSplit to explicitly create editor-groups-container**
- **Found during:** Task 1 analysis
- **Issue:** Original `recreateGroupSplit` in Plan 01 did `editorPane.innerHTML = ''` then appended groups directly to `editorPane`, bypassing the `#editor-groups-container` div needed for the right-edge drop zone. After Plan 01, the static HTML had `editor-groups-container` but first call to `recreateGroupSplit` would wipe it and not recreate it, meaning `initRightEdgeDropZone()` targeting `#editor-groups-container` would find nothing.
- **Fix:** Updated `recreateGroupSplit` to explicitly create `div#editor-groups-container` and append groups inside it; also preserve `#bottom-panel-slot` across rebuilds
- **Files modified:** frontend/static/js/workspace-layout.js
- **Commit:** ed392a8

**2. [Rule 2 - Missing functionality] Added Escape key dismissal for context menu**
- **Found during:** Task 2 implementation
- **Issue:** Plan spec mentioned "dismiss on outside click and on Escape" but the research Pattern 6 code only showed click-outside dismissal. Added keydown listener for Escape with proper cleanup to remove both click and keydown listeners on dismiss.
- **Fix:** Added `document.addEventListener('keydown', dismissKey)` alongside click-outside listener; both cleaned up on either trigger
- **Files modified:** frontend/static/js/workspace-layout.js
- **Commit:** 1262129

## Self-Check

Files exist check:
- frontend/static/js/workspace-layout.js (contains dragstart): FOUND
- frontend/static/css/workspace.css (contains .drop-indicator): FOUND

Commits exist check:
- ed392a8: FOUND
- 1262129: FOUND

## Self-Check: PASSED

# Phase 14 Plan 03: Bottom Panel Summary

**Collapsible bottom panel with SPARQL/Event Log/AI Copilot placeholder tabs, Ctrl+J toggle, drag resize, maximize toggle, and localStorage persistence -- plus four UAT bug fixes for smooth animation, DOM preservation, keydown dedup, and relations pane restoration.**

## Performance

- **Duration:** ~60 min (including UAT verification and bug fixes)
- **Started:** 2026-02-24T05:16Z
- **Completed:** 2026-02-24T06:03Z
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint, approved)
- **Files modified:** 4

## Accomplishments

- Complete bottom panel DOM in workspace.html: resize handle, tab bar (SPARQL, Event Log, AI Copilot), maximize/close controls, three placeholder panes with Lucide icons
- Full panel JavaScript: toggle, resize (clamped 80px–80%), maximize, tab switching, Ctrl+J shortcut, localStorage persistence across reloads
- Command palette now has all four locked entries: Toggle Panel (ctrl+j), Maximize Panel, Split Right (ctrl+\\), Close Group (guarded against single-group state)
- Four UAT-discovered bugs auto-fixed: smooth CSS height transition, DOM preservation across split recreation, keydown listener deduplication, relations/lint pane restoration

## Task Commits

Each task was committed atomically:

1. **Task 1: Add bottom panel DOM and CSS** - `c8184c0` (feat)
2. **Task 2: Panel JavaScript (toggle, resize, persistence, keyboard, command palette)** - `f752977` (feat)
3. **Task 3: Human verification of complete Phase 14 implementation** - checkpoint approved

**UAT bug fix commits:**
- `04840f2` fix(14-03): preserve real bottom panel DOM across recreateGroupSplit calls
- `93997cd` fix(14-03): smooth panel open/close with CSS height transition instead of display toggle
- `491da3d` fix(14-01): prevent keydown listener accumulation on htmx re-init
- `70eb14a` fix(14-02): update relations/lint panel when switching active editor group

## Files Created/Modified

- `backend/app/templates/browser/workspace.html` - Added panel resize handle div, full bottom panel DOM with three panes and Lucide icon placeholders; updated for CSS height transition (removed display:none, added panel-open class)
- `frontend/static/css/workspace.css` - Appended all bottom panel styles: resize handle, panel container, header, tab bar, tabs, controls, content area, panes, placeholder, maximized state; added height transition rule
- `frontend/static/js/workspace.js` - Added PANEL_KEY, panelState, restorePanelState, savePanelState, _applyPanelState, toggleBottomPanel, maximizeBottomPanel, initBottomPanelResize, initPanelTabs, initBottomPanel; Ctrl+J shortcut; four command palette entries; window exports
- `frontend/static/js/workspace-layout.js` - Added bottom panel DOM preservation logic in recreateGroupSplit: save panel node before innerHTML wipe, re-insert after editor groups container creation

## Decisions Made

- CSS height transition (height: 0 → explicit px with overflow:hidden) for smooth panel animation -- avoids the layout jump caused by display:none toggling
- Bottom panel DOM detached from DOM and re-inserted before Split.js reinitializes the editor-column, preserving its event listeners and state
- Panel height stored as percentage in localStorage, converted to pixels on apply using parentElement.getBoundingClientRect().height -- scales correctly on window resize
- panel-open CSS class controls resize handle visibility rather than JS inline style -- ensures the transition applies correctly

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Smooth panel animation via CSS height transition**
- **Found during:** UAT verification (Task 3)
- **Issue:** Panel used display:none / display:flex toggle which caused abrupt appearance with no animation
- **Fix:** Replaced display toggle with height:0 / height:Npx transition using overflow:hidden; removed display:none from initial HTML; added panel-open class to control resize handle visibility
- **Files modified:** workspace.html, workspace.css, workspace.js
- **Verification:** Panel opens and closes with smooth 200ms height transition; resize handle appears/disappears in sync
- **Committed in:** 93997cd

**2. [Rule 1 - Bug] Bottom panel DOM preservation across recreateGroupSplit**
- **Found during:** UAT verification (Task 3) -- panel disappeared after creating second editor group
- **Issue:** recreateGroupSplit in workspace-layout.js used innerHTML = '' to clear #editor-column, destroying the bottom panel DOM node and its attached event listeners
- **Fix:** Saved reference to #bottom-panel and #panel-resize-handle before innerHTML wipe; re-inserted them after the editor-groups-container was created
- **Files modified:** workspace-layout.js
- **Verification:** Splitting editor groups no longer destroys the bottom panel; panel state and event listeners persist
- **Committed in:** 04840f2

**3. [Rule 1 - Bug] Keydown listener accumulation on htmx re-init**
- **Found during:** UAT regression check (Task 3)
- **Issue:** initKeyboardShortcuts() was called on every htmx:afterSettle event without removing the previous listener, causing Ctrl+J (and other shortcuts) to fire multiple times
- **Fix:** Added document.removeEventListener before re-attaching the named keydown handler function
- **Files modified:** workspace.js
- **Verification:** Pressing Ctrl+J once toggles panel exactly once regardless of htmx navigations
- **Committed in:** 491da3d

**4. [Rule 1 - Bug] Relations and lint pane not loading when switching active editor group**
- **Found during:** UAT regression check (Task 3) -- relations panel stayed empty when clicking group-2
- **Issue:** setActiveGroup() updated the active group ID and re-rendered the tab bar but did not trigger the relations/lint panel reload for the newly focused tab
- **Fix:** Added a call to reload relations and lint panes for the active tab in the newly focused group inside setActiveGroup()
- **Files modified:** workspace-layout.js (fix applied to 14-02 scope)
- **Verification:** Clicking into a different editor group immediately loads relations and lint for that group's active tab
- **Committed in:** 70eb14a

---

**Total deviations:** 4 auto-fixed (all Rule 1 - Bug)
**Impact on plan:** All four fixes required for correct UAT behavior. No scope creep -- all bugs directly caused by or exposed by Plan 03's implementation.

## Issues Encountered

- Split.js recreation pattern (established in Plan 01/02) destroyed the bottom panel DOM every time a new editor group was created. Required saving and re-inserting the panel node around the recreateGroupSplit call. This is now a documented pattern for future phases that add persistent DOM siblings inside #editor-column.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 16 (Event Log): #panel-event-log pane is available at `document.querySelector('#panel-event-log')`, CSS styles are in place
- Phase 17 (LLM Copilot): #panel-ai-copilot pane is available at `document.querySelector('#panel-ai-copilot')`, CSS styles are in place
- SPARQL console: #panel-sparql pane ready, currently shows placeholder text
- Bottom panel infrastructure is complete and stable -- no regressions in Phase 12/13 features verified during UAT

---
*Phase: 14-split-panes-and-bottom-panel*
*Completed: 2026-02-24*

## Self-Check: PASSED

All files verified present:
- FOUND: workspace.html
- FOUND: workspace.css
- FOUND: workspace.js
- FOUND: workspace-layout.js
- FOUND: 14-03-SUMMARY.md

All commits verified:
- FOUND: c8184c0 (feat: bottom panel DOM and CSS)
- FOUND: f752977 (feat: bottom panel JS)
- FOUND: 04840f2 (fix: preserve bottom panel DOM)
- FOUND: 93997cd (fix: smooth panel animation)
- FOUND: 491da3d (fix: keydown listener dedup)
- FOUND: 70eb14a (fix: relations panel on group switch)
