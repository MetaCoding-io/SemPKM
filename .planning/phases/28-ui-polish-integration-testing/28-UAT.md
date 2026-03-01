---
status: complete
phase: 28-ui-polish-integration-testing
source: [28-01-SUMMARY.md, 28-02-SUMMARY.md]
started: 2026-03-01T00:00:00Z
updated: 2026-03-01T00:00:00Z
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
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "Closing the last object tab deactivates the accent bar even if non-object tabs (settings, SPARQL) remain open; Relations and Lint panel content clears when no object is active"
  status: failed
  reason: "User reported: Teal stayed when closing note while settings tab was open (only cleared when ALL tabs gone). After all tabs closed teal went away but Relations/Lint still showed stale content. Also: switching to SPARQL browser and back caused teal to disappear even though object tab was still open."
  severity: major
  test: 7
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "Contextual panel accent bar is aware of tab type — deactivates only when no object tab is active, not when switching to non-object tabs (settings, SPARQL browser, views)"
  status: failed
  reason: "User reported: Opening a view tab activates the bar incorrectly; switching to SPARQL browser and back clears the teal even though the object tab is still open"
  severity: minor
  test: 6
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
