# Chapter 13: Settings

SemPKM has a layered settings system that lets you personalize your workspace while keeping sensible defaults for new users and new features. Settings are defined by the system core and by installed Mental Models, resolved through a clear priority chain, and applied instantly when you change them.

## Accessing Settings

There are two ways to open the Settings page:

- **Keyboard shortcut:** Press `Ctrl+,` (comma) to jump directly to Settings.
- **User menu:** Click your user avatar or name in the top-right corner to open the user popover, then select **Settings**.

The Settings page opens within the workspace, replacing the current content area.

<!-- Screenshot: Settings page showing the search bar, category sidebar on the left, and settings detail panel on the right -->

## The Settings Interface

The Settings page uses a **two-column layout**:

- **Left sidebar** -- A vertical list of category buttons. Click a category to show its settings in the detail panel. The active category is highlighted with an accent-colored left border.
- **Right panel** -- The settings for the selected category, displayed as rows. Each row shows the setting's label, an optional description, and the input control.

### Searching Settings

At the top of the Settings page is a **search bar** with a magnifying glass icon. Type to filter settings across all categories. As you type:

- Settings whose label or description does not match are hidden.
- Category buttons in the sidebar are hidden if all their settings are filtered out.
- If the currently active category becomes fully filtered, the view automatically switches to the first visible category.

Clear the search field to show all settings again.

### Input Types

Settings use different input controls depending on their type:

| Input Type | Control | Example |
|---|---|---|
| `select` | Dropdown menu | Theme: light / dark / system |
| `toggle` | On/off switch | A boolean setting |
| `text` | Text field | A free-form string value |
| `color` | Color picker | A color value |

All settings take effect **instantly** when you change them. There is no save button -- the value is persisted to the database as soon as you interact with the control.

## How Settings Resolution Works

SemPKM resolves settings through a three-layer priority chain. Higher layers override lower ones:

```
User Override  (highest priority -- your personal choice)
     |
Model Manifest Default  (the Mental Model's recommended value)
     |
System Default  (lowest priority -- the built-in fallback)
```

### Layer 1: System Defaults

System defaults are defined in the SemPKM source code and always exist as a baseline. The core system defines a single setting:

| Key | Label | Type | Default | Description |
|---|---|---|---|---|
| `core.theme` | Theme | select | `system` | Color theme for the workspace |

System defaults cannot be changed by the user -- they serve as the ultimate fallback if no other layer provides a value.

### Layer 2: Model Manifest Defaults

When a Mental Model is installed, SemPKM reads its `manifest.yaml` for a `settings` section. Each setting in the manifest becomes a new entry in the Settings page, namespaced under the model's ID.

For example, if the "Basic PKM" model (`basic-pkm`) defines a setting with key `defaultNoteType`, it appears in the Settings system as `basic-pkm.defaultNoteType`. These model-contributed settings are grouped under their own category (named after the model ID) in the sidebar.

Model defaults override system defaults for settings with the same key, but in practice, model settings use unique keys prefixed by the model ID, so conflicts do not arise.

### Layer 3: User Overrides

When you change a setting in the Settings page, your choice is stored in the `user_settings` table in the database, keyed by your user ID and the setting key. This override takes highest priority.

User overrides are per-user. Each person on the instance can have different settings without affecting anyone else.

### The "Modified" Indicator

When a setting has a user override that differs from its default, the Settings page shows a **"Modified" badge** (a small accent-colored label) next to the input control, along with a **Reset** link.

<!-- Screenshot: A settings row showing the "Modified" badge and Reset link next to a changed setting -->

- **Reset** (per-setting) -- Click the underlined "Reset" text next to a modified setting to delete your override and revert to the default value. The Modified badge disappears and the input updates to show the default.
- **Reset to defaults** (per-category) -- Each category panel has a **Reset to defaults** button in its header. Clicking it resets all modified settings in that category back to their defaults.

## Theme Settings

The theme system is the most visible setting in SemPKM. It controls the visual appearance of the entire workspace.

### Three Theme Modes

The **Theme** setting (`core.theme`) offers three options:

| Value | Behavior |
|---|---|
| **system** | Follows your operating system's color scheme preference. If your OS is set to dark mode, SemPKM uses the dark theme. If your OS switches (e.g., at sunset), SemPKM follows. |
| **light** | Always uses the light color scheme, regardless of OS setting. |
| **dark** | Always uses the dark color scheme, regardless of OS setting. |

The default is `system`, which means SemPKM respects your OS preference out of the box.

### How Theme Switching Works

When you change the theme, several things happen simultaneously:

1. The `data-theme` attribute on the HTML root element is updated, which triggers all CSS custom properties to switch between light and dark values.
2. Third-party libraries are updated to match:
   - The **command palette** (ninja-keys) gets or loses its `dark` class.
   - The **syntax highlighting** stylesheet (highlight.js) switches between `github.min.css` and `github-dark.min.css`.
   - **CodeMirror** editors switch their theme compartment.
   - **Cytoscape** graph visualizations switch their style variables.
3. The preference is stored in `localStorage` under the key `sempkm_theme`.
4. A `sempkm:theme-changed` custom event is dispatched on the document, so any other components can react.

### Anti-FOUC Behavior

FOUC (Flash of Unstyled Content) is when the page briefly shows the wrong theme before JavaScript loads. SemPKM prevents this with a two-stage approach:

1. **Inline script in `<head>`** -- Before the page renders, a small inline script reads the theme preference from `localStorage` and sets the `data-theme` attribute immediately. This happens before any CSS is applied, so you never see a flash.
2. **No-transition class** -- The HTML root starts with a `no-transition` class that disables all CSS transitions. After the first paint, a `requestAnimationFrame` callback removes this class, enabling smooth transitions for subsequent theme changes. This prevents the initial theme application from showing visible color transitions.

### Server Sync

When the page loads, the theme system checks whether the `localStorage` value matches the server-side setting (from the settings service). If they differ -- for example, if you changed the theme on another device -- the server value takes precedence and `localStorage` is updated to match. This sync happens after a short delay (300ms) to ensure the settings API response has arrived.

> **Tip:** If you use SemPKM on multiple devices, your theme preference follows you. Change it once, and it syncs everywhere the next time the page loads.

## Mental Model-Contributed Settings

One of the powerful features of the settings system is that Mental Models can contribute their own settings. This means installing a new model can add new configuration options without any code changes to SemPKM itself.

### How It Works

Each Mental Model's `manifest.yaml` can include a `settings` section that defines additional settings. When the Settings page loads, SemPKM:

1. Scans the `models/` directory for all installed models.
2. Reads each model's `manifest.yaml`.
3. Extracts any settings definitions.
4. Merges them into the settings list, grouped under a category named after the model ID.

### Example

If the "Basic PKM" model defines settings in its manifest:

```yaml
settings:
  - key: defaultNoteType
    label: Default Note Type
    description: The note type used when creating new notes
    input_type: select
    options: ["Fleeting", "Literature", "Permanent"]
    default: "Fleeting"
```

This appears in the Settings page as:

- **Category:** basic-pkm (in the left sidebar)
- **Label:** Default Note Type
- **Description:** The note type used when creating new notes
- **Control:** A dropdown with options Fleeting, Literature, and Permanent

The setting key in the database is `basic-pkm.defaultNoteType`, ensuring no collision with core settings or settings from other models.

### Model Removal and Settings

When a Mental Model is uninstalled, any user overrides for that model's settings can be cleaned up. The settings service provides a method to remove all user overrides whose keys start with the model's ID prefix (e.g., all keys matching `basic-pkm.%`). This prevents orphaned settings from accumulating in the database.

## Settings API

For advanced use or automation, settings can be managed through the HTTP API.

### Read Resolved Settings

```
GET /browser/settings/data
```

Returns a JSON object with all settings resolved for the current user (system defaults merged with model defaults merged with user overrides).

### Set a Setting

```
PUT /browser/settings/{key}
Content-Type: application/json

{"value": "dark"}
```

Creates or updates a user override for the specified key. The change takes effect immediately.

### Reset a Setting

```
DELETE /browser/settings/{key}
```

Deletes the user override for the specified key, reverting to the default. Returns the default value in the response so the UI can update.

## What is Next

The final chapter in Part IV covers system health monitoring and the debug tools available for troubleshooting and advanced exploration.

[System Health and Debugging](14-system-health-and-debugging.md)
