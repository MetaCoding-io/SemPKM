# Appendix B: Keyboard Shortcut Reference

This appendix lists all keyboard shortcuts available in the SemPKM workspace. SemPKM uses the `Alt` modifier key to avoid conflicts with browser-reserved shortcuts.

## Global Shortcuts

These shortcuts work from anywhere in the workspace.

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Alt+K` (or `F1`) | Open command palette | Opens the command palette for quick access to actions, views, and recently opened objects. |
| `Alt+S` | Save current object | Saves both form properties and Markdown body content of the active tab. |
| `Alt+W` | Close current tab | Closes the active tab in the active editor group. |
| `Alt+N` | New object | Opens the type picker to create a new object. Available via the command palette. |
| `Alt+E` | Toggle edit mode | Switches the active object between read mode and edit mode. |
| `Alt+,` | Open Settings | Opens the Settings tab in the active editor group. |
| `Alt+J` | Toggle bottom panel | Opens or closes the bottom panel (SPARQL console, event log). |

## Editor Group Shortcuts

These shortcuts manage the split editor layout.

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Alt+\` | Split right | Creates a new editor group to the right of the active group. |
| `Alt+1` | Focus group 1 | Switches focus to the first (leftmost) editor group. |
| `Alt+2` | Focus group 2 | Switches focus to the second editor group. |
| `Alt+3` | Focus group 3 | Switches focus to the third editor group. |
| `Alt+4` | Focus group 4 | Switches focus to the fourth editor group. |

## Panel Shortcuts

These shortcuts control the visibility of workspace panels.

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Alt+[` | Toggle Explorer panel | Shows or hides the left navigation pane (Explorer tree). |
| `Alt+]` | Toggle Details panel | Shows or hides the right details pane (Relations and Lint). |
| `Alt+J` | Toggle bottom panel | Shows or hides the bottom panel. |

## Command Palette Actions

The following actions are available through the command palette (`Alt+K`) and may also have direct keyboard shortcuts.

| Action | Palette Section | Shortcut |
|--------|----------------|----------|
| New Object | Objects | `Alt+N` |
| Toggle Edit Mode | Objects | `Alt+E` |
| Run Validation | Tools | -- |
| Split Right | View | `Alt+\` |
| Close Group | View | -- |
| Toggle Panel | View | `Alt+J` |
| Maximize Panel | View | -- |
| Toggle Explorer Panel | View | `Alt+[` |
| Toggle Details Panel | View | `Alt+]` |
| Open View Menu | Views | -- |
| Theme: Light | Appearance | -- |
| Theme: Dark | Appearance | -- |
| Theme: System Default | Appearance | -- |
| Browse: (view name) | Views | -- |
| Open: (object name) | Objects | -- |

> **Tip:** The command palette dynamically adds entries for views and recently opened objects. As you work with more objects, the palette becomes a quick launcher for jumping to anything in your workspace.

## Platform Notes

SemPKM uses the `Alt` modifier key on all platforms. Unlike `Ctrl`-based shortcuts, `Alt` shortcuts do not conflict with browser defaults (`Ctrl+W`, `Ctrl+N`, `Ctrl+T`, etc.), so the same bindings work consistently across Windows, macOS, and Linux.

## See Also

- [Keyboard Shortcuts and Command Palette](08-keyboard-shortcuts.md) -- detailed usage guide
- [The Workspace Interface](04-workspace-interface.md) -- workspace layout overview

---

**Previous:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md) | **Next:** [Appendix C: Command API Reference](appendix-c-command-api-reference.md)
