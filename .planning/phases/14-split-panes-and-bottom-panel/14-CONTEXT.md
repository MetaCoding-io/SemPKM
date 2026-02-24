# Phase 14: Split Panes and Bottom Panel - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

VS Code-style editor groups allowing users to work with multiple objects side-by-side, with tab drag between groups, and a collapsible bottom panel for tool tabs (SPARQL, Event Log, AI Copilot). Maximum 4 horizontal editor groups.

</domain>

<decisions>
## Implementation Decisions

### Split visual design
- When splitting, all groups resize to equal proportional widths (e.g., 3 groups = 33% each)
- Users can freely resize groups by dragging the divider, with a minimum width (~200px) per group
- Dividers use thin line style (1-2px subtle border), widening on hover to indicate draggability — VS Code style, not the thicker Split.js gutter
- Adding or removing groups uses a brief ~150ms smooth resize transition animation

### Tab drag behavior
- Dragging a tab shows both a semi-transparent ghost tab following the cursor AND highlights the target tab bar's insertion point
- Dragging a tab toward the right edge of the editor area creates a new split group (like VS Code)
- Tabs are reorderable within the same group using the same drag mechanism
- Duplicate objects are allowed — the same object can be open in multiple groups independently

### Bottom panel layout
- Default height is ~30% of editor area when first opened
- Panel has a maximize toggle button that expands to full editor height; click again to restore
- Panel tabs (SPARQL, Event Log, AI Copilot) use a different, more compact toolbar-tab style distinct from editor tabs — similar to VS Code's panel tabs
- Full state persistence across page reloads: open/closed state, height, and active tab all saved to localStorage

### Keyboard & discovery
- All split/panel actions available in the command palette (Ctrl+K): Split Right, Close Group, Toggle Panel, Maximize Panel
- Full right-click context menu on tabs: Close, Close Others, Split Right, Move to Group →
- Ctrl+1/2/3/4 shortcuts to focus editor group by number (VS Code convention)
- No visual hints for splitting in default single-group view — power users discover via shortcuts, context menu, or command palette

### Claude's Discretion
- Exact drop zone highlighting colors and ghost tab opacity
- How "Move to Group →" submenu works when there's only one other group
- Exact minimum panel height when collapsed vs hidden
- Tab overflow behavior when too many tabs in a group

</decisions>

<specifics>
## Specific Ideas

- Split dividers should feel like VS Code — nearly invisible until you hover, then clearly draggable
- Bottom panel tabs should be visually distinct from editor tabs to avoid confusion about what's an "object" vs a "tool"
- The overall experience should feel like a lightweight VS Code workspace — familiar to developers

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 14-split-panes-and-bottom-panel*
*Context gathered: 2026-02-23*
