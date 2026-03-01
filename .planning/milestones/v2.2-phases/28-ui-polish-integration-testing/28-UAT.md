---
status: diagnosed
phase: 28-ui-polish-integration-testing
source: [28-01-SUMMARY.md, 28-02-SUMMARY.md]
started: 2026-03-01T00:00:00Z
updated: 2026-03-01T00:10:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

[testing complete]

## Tests

### 1. Chevron icons visible in dark theme
expected: Open workspace in dark mode. Sidebar group header chevrons (VIEWS, TYPES), nav tree ▶ toggles, and workspace explorer section chevrons should all be clearly visible with sufficient contrast against the dark background. None should be invisible or near-invisible.
result: issue
reported: "VIEWS/TYPES sidebar chevrons work fine in both themes. The chevrons for the left, right, and bottom panel collapse/expand buttons are still invisible."
severity: major

### 2. Chevron icons visible in light theme
expected: Same chevrons/toggles as Test 1 but in light mode — all should be visible without blending into the light background.
result: pass

### 3. Drag Relations panel to left pane
expected: Open the workspace with an object. In the right sidebar, the Relations panel header should have a subtle grip handle (⠿ icon). Drag the Relations panel header to the left nav pane — it should move there and render correctly, nestled below the nav tree content.
result: pass

### 4. Drag panel back to right pane
expected: After moving a panel to the left pane (Test 3), drag it back to the right sidebar. It should return to the right pane and look correct. Dropping on an invalid area should be a no-op with no broken state.
result: pass

### 5. Panel position persists on reload
expected: Move a panel to the left pane, then reload the page. The panel should remain in the left pane (position restored from localStorage) without requiring another drag.
result: pass

### 6. Contextual panel accent bar appears
expected: Open the workspace and open an object in the editor (click any object). The Relations and Lint panel headers in the right sidebar should show a teal 3px left border, indicating they are scoped to the current object.
result: issue
reported: "Mostly works, but it might be nice when opening up a view to clear out those panels until the user selects a node in the view (especially for views like table where there is no notion of a currently selected node)"
severity: minor

### 7. Contextual panel accent bar disappears on close
expected: With the accent bar visible (Test 6), close all editor tabs. The teal left border on Relations and Lint panels should disappear, indicating no active object context.
result: issue
reported: "Teal stayed when closing the note tab while settings tab was still open — only disappeared once all tabs were closed. Also: when all tabs are closed, the teal went away but the Relations and Lint panels were not cleared of their content — still showing data from the previously open object."
severity: major

## Summary

total: 7
passed: 4
issues: 3
pending: 0
skipped: 0

## Gaps

- truth: "Chevrons on the left, right, and bottom workspace panel collapse/expand buttons are visible in both light and dark themes"
  status: failed
  reason: "User reported: VIEWS/TYPES sidebar chevrons work fine in both themes. The chevrons for the left, right, and bottom panel collapse/expand buttons are still invisible."
  severity: major
  test: 1
  root_cause: "Phase 28-01 added `stroke: currentColor` to `.group-chevron svg` and `.right-section-chevron svg` but missed `.panel-btn svg`. The `.panel-btn` rule at workspace.css:1831 already sets `color: var(--color-text-muted)` but Lucide SVG icons use `stroke` not `fill` — without `stroke: currentColor`, the SVG stroke defaults to black which is invisible in dark mode."
  artifacts:
    - path: "frontend/static/css/workspace.css"
      issue: "Missing `.panel-btn svg { stroke: currentColor; }` rule — .panel-btn targets left/right pane close buttons and bottom panel maximize/close buttons"
  missing:
    - "Add `.panel-btn svg { stroke: currentColor; }` to the Phase 28 fix block in workspace.css (after line 2544)"
  debug_session: ".planning/debug/workspace-panel-chevrons-invisible-dark.md"

- truth: "Closing the last object tab deactivates the accent bar even if non-object tabs (settings, SPARQL) remain open; Relations and Lint panel content clears when no object is active"
  status: failed
  reason: "User reported: Teal stayed when closing note while settings tab was open (only cleared when ALL tabs gone). After all tabs closed teal went away but Relations/Lint still showed stale content. Also: switching to SPARQL browser and back caused teal to disappear even though object tab was still open."
  severity: major
  test: 7
  root_cause: "Three issues share one root: no tab-type awareness. (1) `removeTabFromGroup` dispatches `sempkm:tabs-empty` only when ALL tabs are gone (not when last object tab closes). (2) `switchTabInGroup` dispatches `sempkm:tab-activated` for every tab type with no `isObjectTab` field, so switching to SPARQL activates the bar; the no-op guard on the return switch suppresses the corrective re-dispatch. (3) `setContextualPanelActive(false)` only removes the CSS class — never clears `#relations-content` or `#lint-content` innerHTML."
  artifacts:
    - path: "frontend/static/js/workspace-layout.js"
      issue: "removeTabFromGroup:228-232 checks all tabs not object tabs; switchTabInGroup:890-891 dispatches sempkm:tab-activated without isObjectTab field"
    - path: "frontend/static/js/workspace.js"
      issue: "setContextualPanelActive() at 1645-1653 doesn't clear panel content; tab-activated listener at 1656-1658 ignores event.detail; restore setTimeout at 1666-1672 doesn't check tab type"
  missing:
    - "Add isObjectTab field to sempkm:tab-activated dispatch in switchTabInGroup"
    - "Change removeTabFromGroup empty guard from all-tabs to object-tabs-only"
    - "Make tab-activated listener in workspace.js check isObjectTab before activating"
    - "Make restore setTimeout check active tab is an object tab, not just any tab"
    - "Clear #relations-content and #lint-content innerHTML in setContextualPanelActive(false)"
  debug_session: ".planning/debug/accent-bar-tab-type-awareness.md"

- truth: "Contextual panel accent bar is aware of tab type — deactivates only when no object tab is active, not when switching to non-object tabs (settings, SPARQL browser, views)"
  status: failed
  reason: "User reported: Opening a view tab activates the bar incorrectly; switching to SPARQL browser and back clears the teal even though the object tab is still open"
  severity: minor
  test: 6
  root_cause: "Same root cause as gap 2 — tab-type-blind event dispatch. openViewTab() calls switchTabInGroup() which dispatches sempkm:tab-activated unconditionally; the page-restore setTimeout activates the bar for any active tab regardless of type."
  artifacts:
    - path: "frontend/static/js/workspace.js"
      issue: "openTab() dispatches sempkm:tab-activated without isObjectTab; restore setTimeout doesn't filter by tab type"
    - path: "frontend/static/js/workspace-layout.js"
      issue: "switchTabInGroup dispatches sempkm:tab-activated for all tab types"
  missing:
    - "Covered by gap 2 fixes — same code changes resolve both gaps"
  debug_session: ".planning/debug/accent-bar-tab-type-awareness.md"
