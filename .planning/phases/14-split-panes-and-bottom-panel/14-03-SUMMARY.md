---
phase: 14-split-panes-and-bottom-panel
plan: 03
subsystem: ui
tags: [bottom-panel, localStorage, split-panes, keyboard-shortcuts, command-palette, css-transitions, lucide-icons]

# Dependency graph
requires:
  - phase: 14-01
    provides: WorkspaceLayout foundation, #editor-column DOM, #bottom-panel-slot placeholder
  - phase: 14-02
    provides: recreateGroupSplit pattern, tab rendering refactor
  - phase: 13-04
    provides: command palette (ninja-keys), Ctrl+K handler, initKeyboardShortcuts()
provides:
  - Collapsible bottom panel with SPARQL, Event Log, AI Copilot placeholder panes
  - Ctrl+J keyboard shortcut toggles panel open/closed
  - Drag resize handle adjusts panel height (80px–80% of workspace), stored in localStorage
  - Maximize toggle hides editor groups and expands panel to full editor-column height
  - Panel open/closed state, height percentage, and active tab persist across page reloads
  - Command palette entries: Toggle Panel (ctrl+j), Maximize Panel, Split Right (ctrl+\\), Close Group
  - CSS height-transition-based open/close animation (replaces display toggle)
  - Bottom panel DOM preserved across recreateGroupSplit calls
affects:
  - Phase 16 (Event Log): will populate #panel-event-log pane
  - Phase 17 (LLM Copilot): will populate #panel-ai-copilot pane
  - Any future SPARQL console work: #panel-sparql pane is ready

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CSS height transition for panel open/close (height:0 -> explicit px) instead of display:none toggle"
    - "localStorage keyed object (sempkm_bottom_panel) stores {open, height, maximized, activeTab}"
    - "panel DOM saved and re-inserted before Split.js recreateGroupSplit wipes #editor-column children"
    - "Lucide icon re-init after panel opens (lucide.createIcons called in _applyPanelState)"
    - "Resize: mousedown on handle records startY/startHeight, document-level mousemove/mouseup, clamp(80px, 80%)"

key-files:
  created: []
  modified:
    - backend/app/templates/browser/workspace.html
    - frontend/static/css/workspace.css
    - frontend/static/js/workspace.js
    - frontend/static/js/workspace-layout.js

key-decisions:
  - "CSS height transition (height: 0 -> Npx with overflow:hidden) for smooth panel open/close instead of display:none toggle -- avoids layout jump"
  - "Bottom panel DOM detached and re-inserted around recreateGroupSplit to survive Split.js reinitialization"
  - "panel-resize-handle visibility controlled by panel-open CSS class (not JS display) so transition applies"
  - "panelState.height stored as percentage (0-100) not pixels -- scales correctly on window resize"

patterns-established:
  - "Panel infrastructure pattern: placeholder tabs with Lucide icons ready for Phase 16/17 population"
  - "CSS height animation pattern for collapsible regions: height:0 + overflow:hidden + transition:height"
  - "DOM preservation pattern for Split.js recreation: save real DOM nodes, wipe container, re-insert before recreate"

requirements-completed: [WORK-04, WORK-05]

# Metrics
duration: ~60min (including UAT bug fixes)
completed: 2026-02-24
---

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
