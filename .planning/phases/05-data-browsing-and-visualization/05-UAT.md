---
status: testing
phase: 05-data-browsing-and-visualization
source: [05-01-SUMMARY.md, 05-02-SUMMARY.md, 05-03-SUMMARY.md]
started: 2026-02-22T23:00:00Z
updated: 2026-02-22T23:00:00Z
---

## Current Test

number: 9
name: Graph View Renders Nodes and Edges
expected: |
  Open the graph view for a type. You should see a 2D graph with nodes (objects) and edges (relationships) rendered by Cytoscape.js. Nodes should be colored by type — either using colors from the model or auto-assigned from a palette.
awaiting: user response

## Tests

### 1. Table View Loads with Columns
expected: Navigate to a table view for any type. You should see a table with column headers from SHACL properties. Rows list objects of that type with values in each column.
result: pass

### 2. Table Column Sorting
expected: Click a column header in the table view. Rows should reorder ascending by that column. Click again to toggle to descending. A sort indicator should show the current sort direction.
result: pass

### 3. Table Text Filter
expected: Type text in the filter input above the table. After a brief debounce (~300ms), the table should update to show only rows matching the filter text. Clearing the filter restores all rows.
result: pass (fixed: filter input lost focus on swap — added htmx:afterSwap refocus listener)

### 4. Table Pagination
expected: With enough objects to exceed one page, the table shows numbered page links at the bottom with prev/next navigation. You can click page numbers to jump between pages. A jump-to-page input allows entering a specific page number.
result: pass (limited data — pagination controls visible on single page, multi-page not fully tested)

### 5. Column Visibility Preferences
expected: Click the gear icon in the toolbar. A dropdown/panel appears letting you toggle which columns are visible. Hide a column — it disappears from the table. Reload the page — the hidden column stays hidden (persisted in localStorage per type).
result: pass (fixed: onclick attribute quote conflict with tojson, label wrapping caused double-toggle, data-col selector matched checkboxes)

### 6. Cards View with Flip Animation
expected: Open the cards view for a type. You should see a grid of cards. Each card front shows the object title/label and a body snippet (~100 chars). Click the flip toggle button (upper-right corner) — the card flips with a CSS 3D animation to reveal the back side.
result: pass (fixed: workspace.js used /cards/ plural but router is /card/ singular)

### 7. Card Back Shows Properties and Relationships
expected: On the back of a flipped card, you should see all properties of the object plus its outbound and inbound relationships displayed as clickable links.
result: pass (added focus/zoom portal with separate focus and flip buttons)

### 8. Card Grouping
expected: In the cards view toolbar, select a property from the Group By dropdown. Cards should rearrange into groups with group headers. Selecting no grouping returns to the flat grid.
result: pass (fixed: dropdown not rendering due to empty spec.columns, moved to top, comma-split for tags, CSS specificity fix for width)

### 9. Graph View Renders Nodes and Edges
expected: Open the graph view for a type. You should see a 2D graph with nodes (objects) and edges (relationships) rendered by Cytoscape.js. Nodes should be colored by type — either using colors from the model or auto-assigned from a palette.
result: [pending]

### 10. Graph Node Interaction
expected: Click a node in the graph — it should become selected and show details in the right pane. Double-click a node — its neighbors should expand into the graph with new nodes and edges appearing.
result: [pending]

### 11. Graph Layout Picker
expected: The graph view has a layout picker with at least three options: force-directed, hierarchical, and radial. Switching layouts rearranges the graph nodes accordingly.
result: [pending]

### 12. Graph Pan and Zoom
expected: In the graph view, use scroll wheel or pinch to zoom in/out. Click and drag on empty space to pan the view. The graph should respond smoothly.
result: [pending]

### 13. Views Open as Tabs
expected: Opening a view (table, cards, or graph) adds a tab in the center pane tab bar alongside any object tabs. You can have a table view and a graph view open simultaneously as separate tabs.
result: [pending]

### 14. View Menu Grouped by Model
expected: Click the Views button in the Explorer pane. A view menu appears listing available views grouped by source model name (e.g., "Basic PKM"). Each entry can be clicked to open that view.
result: [pending]

### 15. Command Palette View Discovery
expected: Open the command palette and type "Open view" or "Browse". You should see entries for available views that you can select to open.
result: [pending]

### 16. Filter/Sort State Persists on View Switch
expected: In a table view, apply a filter and/or sort by a column. Then switch to the cards view using the type switcher in the toolbar. The filter and sort should carry over to the cards view.
result: [pending]

### 17. Clicking Object Opens Editor Tab
expected: In any view (table row, card, or graph node), click an object. It should open in a new editor tab in the center pane. The view tab stays where it is — you don't lose your place.
result: [pending]

## Summary

total: 17
passed: 8
issues: 0
pending: 9
skipped: 0

## Gaps

[none yet]
