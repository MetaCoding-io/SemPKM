# S14: Split Panes And Bottom Panel

**Goal:** Build the WorkspaceLayout foundation: a new workspace-layout.
**Demo:** Build the WorkspaceLayout foundation: a new workspace-layout.

## Must-Haves


## Tasks

- [x] **T01: 14-split-panes-and-bottom-panel 01**
  - Build the WorkspaceLayout foundation: a new workspace-layout.js module implementing the EditorGroup data model, Split.js destroy-and-recreate strategy, sessionStorage migration from old tab keys, and DOM restructure to support multiple editor groups. Wires workspace.js global functions to delegate to WorkspaceLayout and reassigns keyboard shortcuts.

Purpose: All subsequent Phase 14 work (tab DnD, bottom panel) depends on this multi-group DOM structure and state model existing.
Output: workspace-layout.js module, updated workspace.html DOM structure, updated workspace.css group styles, updated workspace.js delegation wiring.
- [x] **T02: 14-split-panes-and-bottom-panel 02**
  - Implement tab drag-and-drop between editor groups and within the same group, plus the right-click context menu on tabs. Uses the HTML5 Drag-and-Drop API patterns from 14-RESEARCH.md verbatim.

Purpose: Makes editor groups genuinely useful — users can reorganize their tabs across groups and access group management actions via right-click.
Output: DnD handlers and context menu logic added to workspace-layout.js; drag/drop/context-menu CSS added to workspace.css.
- [x] **T03: 14-split-panes-and-bottom-panel 03** `est:~60min (including UAT bug fixes)`
  - Implement the collapsible bottom panel with tabbed interface (SPARQL, Event Log, AI Copilot placeholders), resize handle, maximize toggle, localStorage persistence, Ctrl+J keyboard shortcut, and command palette entries for panel actions.

Purpose: Provides the panel infrastructure that Phase 16 (Event Log) and Phase 17 (LLM Copilot) will populate. The SPARQL tab embeds a placeholder but can be wired to the existing SPARQL console in a future phase.
Output: Bottom panel DOM in workspace.html, panel JS in workspace.js, panel CSS in workspace.css.

## Files Likely Touched

- `frontend/static/js/workspace-layout.js`
- `frontend/static/js/workspace.js`
- `frontend/static/css/workspace.css`
- `backend/app/templates/browser/workspace.html`
- `frontend/static/js/workspace-layout.js`
- `frontend/static/css/workspace.css`
- `backend/app/templates/browser/workspace.html`
- `frontend/static/js/workspace.js`
- `frontend/static/css/workspace.css`
