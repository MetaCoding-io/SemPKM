# Chapter 8: Keyboard Shortcuts and Command Palette

SemPKM's workspace is built for keyboard-driven productivity. Every frequent action has a shortcut, and the command palette gives you instant access to every command in the system. This chapter documents all available shortcuts and the full list of command palette actions.

> **Note:** SemPKM uses `Alt` as its modifier key to avoid conflicts with browser shortcuts (`Ctrl+W`, `Ctrl+N`, etc.). The `Alt` key works consistently across all platforms and browsers.

## Global Keyboard Shortcuts

These shortcuts work anywhere in the workspace, regardless of which pane or panel is focused.

### Navigation and Panels

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Alt+K` (or `F1`) | Open Command Palette | Opens the searchable command palette. Start typing to filter commands, then press Enter to execute. |
| `Alt+J` | Toggle Bottom Panel | Shows or hides the bottom panel (SPARQL console, Event Log). |
| `Alt+[` | Toggle Explorer Pane | Collapses or expands the left explorer pane. |
| `Alt+]` | Toggle Details Pane | Collapses or expands the right details pane (Relations, Lint). |
| `Alt+,` | Open Settings | Opens the Settings tab in the editor area. |

### Editor and Tabs

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Alt+S` | Save | Saves the current object -- both form properties and body content. After saving, the lint panel refreshes automatically. |
| `Alt+E` | Toggle Edit Mode | Switches the current object between read mode and edit mode. In read mode, you see rendered properties and formatted markdown. In edit mode, you get the editable form and the code editor. A crossfade animation shows the transition. |
| `Alt+W` | Close Tab | Closes the currently active tab. If the tab has unsaved changes, you are not prompted (dirty state is tracked but closure is immediate). |
| `Alt+N` | New Object | Opens the type picker, letting you choose which type of object to create. |
| `Alt+\` | Split Right | Creates a new editor group to the right of the current one, splitting the editor area. Useful for viewing two objects or views side by side. |
| `Alt+1` through `Alt+4` | Focus Editor Group | Switches keyboard focus to editor group 1, 2, 3, or 4 (if that many groups exist). |

## The Command Palette

The **command palette** is a searchable overlay that gives you access to every action in SemPKM. Press `Alt+K` (or `F1`) to open it. It uses the ninja-keys web component, providing a familiar experience similar to VS Code's Command Palette or Spotlight on macOS.

![Command palette open with search results and keyboard shortcuts](images/09-command-palette.png)

### How to Use the Palette

1. Press `Alt+K` (or `F1`) to open the palette.
2. Start typing to filter commands. The palette matches against command titles using fuzzy search.
3. Use the arrow keys to navigate the results list.
4. Press Enter to execute the selected command.
5. Press Escape to close the palette without executing anything.

### Full Command List

The command palette organizes commands into sections. Here is the complete list of built-in commands:

**Objects**

| Command | Shortcut | Description |
|---------|----------|-------------|
| New Object | `Alt+N` | Opens the type picker to create a new object. |
| Toggle Edit Mode | `Alt+E` | Switches the active object between read and edit mode. |

**Tools**

| Command | Shortcut | Description |
|---------|----------|-------------|
| Run Validation | -- | Saves and validates the current object against SHACL shapes. |

**View**

| Command | Shortcut | Description |
|---------|----------|-------------|
| Split Right | `Alt+\` | Splits the editor area by adding a new group to the right. |
| Close Group | -- | Closes the current editor group (only available if more than one group exists). |
| Toggle Panel | `Alt+J` | Shows or hides the bottom panel. |
| Maximize Panel | -- | Toggles the bottom panel between normal and maximized height. |
| Toggle Lint Dashboard | -- | Opens the lint dashboard in the bottom panel. |
| Toggle Explorer Panel | `Alt+[` | Collapses or expands the left explorer pane. |
| Toggle Details Panel | `Alt+]` | Collapses or expands the right details pane. |

**Layout**

| Command | Description |
|---------|-------------|
| Layout: Save As... | Saves the current workspace arrangement (groups, tabs, sizes) as a named layout. Type the name in the search field, then confirm. |
| Layout: Restore... | Restores a previously saved named layout. Shows a list of saved layouts to choose from. |
| Layout: Delete... | Deletes a saved named layout. |

**Navigation**

| Command | Description |
|---------|-------------|
| Import Vault | Opens the Obsidian vault import wizard. |

**Views**

| Command | Description |
|---------|-------------|
| Open View Menu | Opens the full view menu showing all available views grouped by source model. |

In addition to the static commands above, the command palette dynamically registers entries for:

- **All available views** -- each installed view specification appears as a "Browse:" command (e.g., "Browse: Table: Projects Table", "Browse: Cards: People Cards", "Browse: Graph: Notes Graph"). Selecting one opens the view in a new tab.
- **Recently opened objects** -- as you open objects from the explorer tree, they are added to the palette as searchable commands for quick re-access.

**Appearance**

| Command | Description |
|---------|-------------|
| Theme: Light | Switches to the light color theme. |
| Theme: Dark | Switches to the dark color theme. |
| Theme: System Default | Uses your operating system's preferred color scheme. |

## Tips for Keyboard-First Workflows

Here are some practical patterns for working efficiently with keyboard shortcuts.

### Quick Object Creation

1. Press `Alt+K` to open the palette.
2. Type "new" and select "New Object".
3. Choose a type from the picker (e.g., Note).
4. The new object opens directly in edit mode. Fill in the form fields.
5. Press `Alt+S` to save.

### Switching Between Views and Objects

1. Press `Alt+K` and type part of a view name (e.g., "proj table") to find "Browse: Table: Projects Table".
2. Press Enter to open the view.
3. Click a row in the table to open an object.
4. Press `Alt+K` and type part of the object's name to switch back to it later.

### Side-by-Side Comparison

1. Open the first object you want to compare.
2. Press `Alt+\` to split the editor.
3. The new editor group becomes active. Press `Alt+K` and open the second object.
4. Use `Alt+1` and `Alt+2` to switch focus between the two groups.

### Quick Validation Workflow

1. Open an object and press `Alt+E` to enter edit mode.
2. Make your changes.
3. Press `Alt+S` to save. Validation runs automatically after saving.
4. Check the right panel's Lint section for any issues.
5. If a lint issue points to a specific field, click it to jump directly to that field in the form.

### Managing Screen Space

- Press `Alt+[` to hide the explorer when you do not need the navigation tree.
- Press `Alt+]` to hide the details pane when you do not need relations or lint.
- Press `Alt+J` to toggle the bottom panel for SPARQL queries or the event log.
- These shortcuts let you maximize the editor area on smaller screens and restore the panels when needed.

> **Tip:** All pane sizes are remembered across sessions. When you toggle a panel open or closed, SemPKM saves the layout to your browser's local storage and restores it on your next visit.

### Saving and Restoring Layouts

- Use `Alt+K` and select **Layout: Save As...** to name and save your current workspace arrangement.
- Use `Alt+K` and select **Layout: Restore...** to switch between saved layouts.
- This is useful for maintaining different workspaces for different tasks -- a research layout, a review layout, a writing layout.

## Customization

Keyboard shortcuts in SemPKM are currently fixed and cannot be remapped through the UI. SemPKM uses the `Alt` modifier key instead of `Ctrl` to avoid conflicts with browser-reserved shortcuts (like `Ctrl+W` closing tabs or `Ctrl+N` opening new windows). The key letters mirror VS Code conventions where possible:

- `Alt+K` for command palette (VS Code uses `Ctrl+K`)
- `Alt+S` for save (VS Code uses `Ctrl+S`)
- `Alt+E` for edit mode toggle
- `Alt+J` for bottom panel toggle (VS Code uses `Ctrl+J`)
- `Alt+,` for settings (VS Code uses `Ctrl+,`)
- `Alt+\` for split editor (VS Code uses `Ctrl+\`)

The `F1` key also opens the command palette, matching the VS Code convention.

---

**Previous:** [Chapter 7: Browsing and Visualizing Data](07-browsing-and-visualizing.md) | **Next:** [Chapter 9: Understanding Mental Models](09-understanding-mental-models.md)
