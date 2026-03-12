# T03: 14-split-panes-and-bottom-panel 03

**Slice:** S14 — **Milestone:** M001

## Description

Implement the collapsible bottom panel with tabbed interface (SPARQL, Event Log, AI Copilot placeholders), resize handle, maximize toggle, localStorage persistence, Ctrl+J keyboard shortcut, and command palette entries for panel actions.

Purpose: Provides the panel infrastructure that Phase 16 (Event Log) and Phase 17 (LLM Copilot) will populate. The SPARQL tab embeds a placeholder but can be wired to the existing SPARQL console in a future phase.
Output: Bottom panel DOM in workspace.html, panel JS in workspace.js, panel CSS in workspace.css.

## Must-Haves

- [ ] "Pressing Ctrl+J toggles the bottom panel open and closed"
- [ ] "The bottom panel opens at ~30% of editor-column height; height persists across reloads via localStorage"
- [ ] "The panel has three tabs: SPARQL, Event Log, AI Copilot — compact toolbar-tab style distinct from editor tabs"
- [ ] "The panel has a maximize button (expands to full editor-column height, hiding editor groups) and a close button"
- [ ] "Dragging the resize handle above the panel adjusts panel height; minimum 80px, maximum 80% of workspace"
- [ ] "Panel open/closed state, height, and active tab persist across page reloads"
- [ ] "All panel actions are available in the command palette: Split Right, Close Group, Toggle Panel, Maximize Panel"

## Files

- `backend/app/templates/browser/workspace.html`
- `frontend/static/js/workspace.js`
- `frontend/static/css/workspace.css`
