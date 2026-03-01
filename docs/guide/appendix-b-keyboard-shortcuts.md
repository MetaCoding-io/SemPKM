# Appendix B: Keyboard Shortcut Reference

This appendix lists all keyboard shortcuts available in the SemPKM workspace. On macOS, substitute `Cmd` for `Ctrl` in all shortcuts.

## Global Shortcuts

These shortcuts work from anywhere in the workspace.

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl+K` | Open command palette | Opens the command palette for quick access to actions, views, and recently opened objects. |
| `Ctrl+S` | Save current object | Saves both form properties and Markdown body content of the active tab. |
| `Ctrl+W` | Close current tab | Closes the active tab in the active editor group. Prompts if there are unsaved changes. |
| `Ctrl+N` | New object | Opens the type picker to create a new object. Available via the command palette. |
| `Ctrl+E` | Toggle edit mode | Switches the active object between read mode and edit mode. |
| `Ctrl+,` | Open Settings | Opens the Settings tab in the active editor group. |
| `Ctrl+J` | Toggle bottom panel | Opens or closes the bottom panel (SPARQL console, event log). |

## Editor Group Shortcuts

These shortcuts manage the split editor layout.

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl+\` | Split right | Creates a new editor group to the right of the active group. |
| `Ctrl+1` | Focus group 1 | Switches focus to the first (leftmost) editor group. |
| `Ctrl+2` | Focus group 2 | Switches focus to the second editor group. |
| `Ctrl+3` | Focus group 3 | Switches focus to the third editor group. |
| `Ctrl+4` | Focus group 4 | Switches focus to the fourth editor group. |

## Panel Shortcuts

These shortcuts control the visibility of workspace panels.

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl+[` | Toggle Explorer panel | Shows or hides the left navigation pane (Explorer tree). |
| `Ctrl+]` | Toggle Details panel | Shows or hides the right details pane (Relations and Lint). |
| `Ctrl+J` | Toggle bottom panel | Shows or hides the bottom panel. |

## Command Palette Actions

The following actions are available through the command palette (`Ctrl+K`) and may also have direct keyboard shortcuts.

| Action | Palette Section | Shortcut |
|--------|----------------|----------|
| New Object | Objects | `Ctrl+N` |
| Toggle Edit Mode | Objects | `Ctrl+E` |
| Run Validation | Tools | `Ctrl+Shift+V` |
| Split Right | View | `Ctrl+\` |
| Close Group | View | -- |
| Toggle Panel | View | `Ctrl+J` |
| Maximize Panel | View | -- |
| Toggle Explorer Panel | View | `Ctrl+[` |
| Toggle Details Panel | View | `Ctrl+]` |
| Open View Menu | Views | -- |
| Theme: Light | Appearance | -- |
| Theme: Dark | Appearance | -- |
| Theme: System Default | Appearance | -- |
| Browse: (view name) | Views | -- |
| Open: (object name) | Objects | -- |

> **Tip:** The command palette dynamically adds entries for views and recently opened objects. As you work with more objects, the palette becomes a quick launcher for jumping to anything in your workspace.

## macOS Notes

On macOS, all `Ctrl` shortcuts use `Cmd` instead:

- `Cmd+K` opens the command palette
- `Cmd+S` saves the current object
- `Cmd+W` closes the current tab
- `Cmd+E` toggles edit mode
- `Cmd+\` splits right
- `Cmd+J` toggles the bottom panel
- `Cmd+,` opens Settings

The detection is automatic based on the `navigator.platform` value.

## See Also

- [Keyboard Shortcuts and Command Palette](08-keyboard-shortcuts.md) -- detailed usage guide
- [The Workspace Interface](04-workspace-interface.md) -- workspace layout overview

---

**Previous:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md) | **Next:** [Appendix C: Command API Reference](appendix-c-command-api-reference.md)
