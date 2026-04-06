# M051: Workspace UX Improvements

## Vision
Fix workspace-level interaction paper-cuts: autocomplete dropdowns that trap focus, stale placeholder text, missing explorer hover actions, broken persona/layout creation UX, command palette scroll jump, and missing object tab refresh. Collectively these make the workspace feel polished and trustworthy.

## Slice Overview
| ID | Slice | Risk | Depends | Done | After this |
|----|-------|------|---------|------|------------|
| S01 | Autocomplete Dismiss & Dropdown Escape | high | — | ✅ | Open edit form → click reference field → type → see suggestions → click outside → dismissed. Tag field near bottom of panel → type → dropdown visible outside overflow → Escape → dismissed. |
| S02 | Explorer & Nav Cleanup + Object Tab Refresh | moderate | — | ✅ | Explorer shows 'Project' not 'Project Shape'. Event Log tab shows actual event content. VFS mount dropdown has clean labels. Object tab has a refresh button that reloads content. |
| S03 | Command Palette & Persona/Layout Dialog UX | moderate | — | ⬜ | F1 → 'Persona: Create New' → input dialog → type name → Create → persona saved. F1 → 'Layout: Save As' → input dialog → type name → Save → layout saved. Command palette opens without scroll jump. Admin graph popover positions near the node. |
