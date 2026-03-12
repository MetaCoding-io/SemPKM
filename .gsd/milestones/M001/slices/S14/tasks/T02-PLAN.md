# T02: 14-split-panes-and-bottom-panel 02

**Slice:** S14 — **Milestone:** M001

## Description

Implement tab drag-and-drop between editor groups and within the same group, plus the right-click context menu on tabs. Uses the HTML5 Drag-and-Drop API patterns from 14-RESEARCH.md verbatim.

Purpose: Makes editor groups genuinely useful — users can reorganize their tabs across groups and access group management actions via right-click.
Output: DnD handlers and context menu logic added to workspace-layout.js; drag/drop/context-menu CSS added to workspace.css.

## Must-Haves

- [ ] "User can drag a tab from one group's tab bar and drop it onto another group's tab bar; the tab moves (not copies)"
- [ ] "A semi-transparent ghost tab follows the cursor during drag"
- [ ] "The target tab bar shows a highlighted state and a vertical insertion line showing where the tab will land"
- [ ] "Tabs can be reordered within the same group by dragging"
- [ ] "Dragging a tab to the right edge of the editor area (last 80px) creates a new group and moves the tab into it"
- [ ] "Right-clicking a tab shows a context menu with: Close, Close Others, Split Right, Move to Group (when multiple groups exist)"
- [ ] "A short drag that doesn't complete does not accidentally trigger a tab switch (isDragging guard)"

## Files

- `frontend/static/js/workspace-layout.js`
- `frontend/static/css/workspace.css`
