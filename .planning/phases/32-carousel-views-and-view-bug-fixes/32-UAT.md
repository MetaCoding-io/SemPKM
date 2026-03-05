---
status: testing
phase: 32-carousel-views-and-view-bug-fixes
source: [32-01-SUMMARY.md, 32-02-SUMMARY.md]
started: 2026-03-03T07:00:00Z
updated: 2026-03-03T07:00:00Z
---

## Current Test

number: 1
name: Views Load in Dockview Panels
expected: |
  Open a type that has views (e.g., Notes). The Table View should load correctly inside the dockview panel — toolbar, table rows, and pagination all visible without errors.
awaiting: user response

## Tests

### 1. Views Load in Dockview Panels
expected: Open a type that has views (e.g., Notes). The Table View should load correctly inside the dockview panel — toolbar, table rows, and pagination all visible without errors.
result: pass

### 2. Old View-Type-Switcher Removed
expected: The view toolbar should NOT contain the old dropdown/button view-type switcher. Only filter, group-by, and other controls remain.
result: [pending]

### 3. Carousel Tab Bar Appears for Multi-View Types
expected: For a type with multiple views (e.g., Notes with Table/Cards/Graph), a tab bar appears above the view body showing tabs like "Table View", "Cards View", "Graph View" with prettified labels.
result: [pending]

### 4. Carousel View Switching
expected: Clicking a different tab in the carousel (e.g., switching from Table View to Cards View) swaps the view body below. The clicked tab shows an active state (bottom border accent).
result: [pending]

### 5. Carousel Tab Persistence
expected: After switching to Cards View for a type, navigate away (open an object or different type), then return to that type. The carousel should restore your Cards View selection automatically.
result: [pending]

### 6. Single-View Type Hides Carousel
expected: For a type with only one view, the carousel tab bar should not appear at all — just the view content directly.
result: [pending]

### 7. Card Group Accordion Sections
expected: In Cards View with group-by active, card groups display as collapsible accordion sections. Each section has a chevron icon, group label, and count badge showing how many cards are in the group.
result: [pending]

### 8. Accordion Collapse and Expand
expected: Clicking a card group header toggles the group collapsed/expanded. The chevron rotates and the cards animate in/out smoothly.
result: [pending]

### 9. Ungrouped Cards Sort Last
expected: Cards without a value for the grouped property appear in an "Ungrouped" section. This section is sorted to the end of the group list, after all named groups.
result: [pending]

### 10. Loading Spinner During View Switch
expected: When switching views via the carousel tabs, a brief loading spinner overlay appears over the view body area while the new view is being fetched.
result: [pending]

## Summary

total: 10
passed: 1
issues: 0
pending: 9
skipped: 0

## Gaps

[none yet]
