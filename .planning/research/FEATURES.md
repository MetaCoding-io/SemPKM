# Feature Landscape: v2.0 Tighten Web UI

**Domain:** IDE-style web application UX polish (VS Code / Obsidian reference patterns)
**Researched:** 2026-02-23
**Mode:** Ecosystem (UX patterns and interaction flows for each feature)

---

## Table Stakes

Features users expect in a polished IDE-style web app. Missing = product feels unfinished.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Bug fixes (body loading, editor, autocomplete, views) | Broken core flows destroy trust | Low-Med | Must ship first |
| Read-only object view | Every tool shows data before editing | Medium | Currently edit-only is jarring |
| Dark mode | Universal expectation in dev/knowledge tools | Medium | CSS custom properties already in place |
| Collapsible sidebar | Screen real estate is sacred in IDEs | Low-Med | Current 220px fixed sidebar wastes space |
| Rounded tab styling | Modern visual polish signal | Low | Pure CSS change |
| Styled 403 panel | Broken-looking errors undermine professionalism | Low | Currently raw htmx error fragment |

## Differentiators

Features that elevate beyond "works fine" into "this feels like a real product."

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| VS Code-style split panes | Power users need side-by-side editing | High | Biggest engineering effort in v2.0 |
| Bottom panel infrastructure | Foundation for SPARQL/AI copilot future | Medium | Tabbed, resizable, collapsible |
| Global settings system | Extensible configuration via mental models | Medium | VS Code-style layered settings |
| Event log explorer | Unique differentiator: time-travel through knowledge changes | High | Timeline + filtering + diff + undo |
| Node type icons | Visual richness in graph and explorer | Low-Med | Mental model can declare icon mappings |
| LLM connection config | AI features are table stakes in 2026 | Low-Med | Generic OpenAI-compatible endpoint |
| Shepherd.js tutorials | Onboarding reduces abandonment | Medium | Infrastructure + 1-2 starter tours |
| VS Code-style user menu | Polished account/settings access | Low | Bottom-of-sidebar pattern |

## Anti-Features

Features to explicitly NOT build in v2.0.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Full AI copilot chat | Scope explosion; connection config is the foundation | Build LLM connection config only; copilot is a future milestone |
| Real-time collaborative editing | CRDT/OT complexity is months of work | Single-user editing with event log for history |
| Drag-and-drop file upload | No file storage backend exists | Keep knowledge entry via forms and markdown editor |
| Floating/detachable panels | VS Code has this but implementation cost is extreme | Fixed panel positions with resize handles |
| Mobile-responsive split panes | Split panes on mobile is a bad UX | Collapse to single-pane on narrow viewports |
| WYSIWYG Markdown editor | CodeMirror 6 with markdown syntax is sufficient | Keep current CM6 setup; rendered view is in read-only mode |

---

## Feature Specifications

### 1. Bug Fixes: Body Loading, Editor Editability, Autocomplete, Views Explorer

**Priority:** P0 -- ship before anything else
**Complexity:** Low-Medium
**Confidence:** HIGH (issues are visible in current codebase)

**Current Problems:**
- Body content fails to load because `initEditor` has a race condition: the retry loop gives up after 20 tries (1s total) but the ESM dynamic import from esm.sh can take longer on cold loads
- Editor may render non-editable because CodeMirror container gets zero height from the flex layout when the split has not initialized
- Autocomplete dropdown (reference search) positions incorrectly due to `position: absolute` inside overflow-hidden scroll containers
- Views explorer shows "Loading..." forever because the `hx-trigger="click once"` on the section header fires the toggle AND the htmx request, but the collapsed state hides the target before content arrives

**UX Fix Patterns:**
- **Body loading:** Increase retry budget to 40 tries (2s), add a visible "Loading editor..." skeleton placeholder in the container during load, and show the fallback textarea after timeout with a "Rich editor unavailable" message rather than silent failure
- **Editor editability:** Set explicit `min-height: 200px` on `.codemirror-container` and ensure the Split.js vertical instance initializes with a `setTimeout(0)` to let the DOM settle before measuring
- **Autocomplete:** Use `position: fixed` with JavaScript-computed coordinates for the suggestions dropdown (same pattern as VS Code's IntelliSense), or attach to `document.body` as a portal
- **Views explorer:** Separate the htmx load trigger from the collapse toggle; use `hx-trigger="revealed"` or fire the htmx request on DOMContentLoaded rather than on click, since VIEWS should load eagerly

**Interaction Flow:**
1. User opens workspace -- editor skeleton shows while CM6 loads
2. Fallback textarea appears only after genuine failure (>3s), with a clear message
3. Autocomplete dropdowns render on top of all content, never clipped
4. Views explorer loads its tree on workspace init, not on first click

---

### 2. Read-Only Object View with Edit Toggle

**Priority:** P0
**Complexity:** Medium
**Confidence:** HIGH (well-established pattern from Carbon Design System, Notion, Obsidian)

**Reference Pattern:** Obsidian's reading view / editing view toggle; Notion's page view with "Edit" affordance; Carbon Design System's read-only state pattern.

**Current State:** Objects open directly into the SHACL form editor with CodeMirror. There is no way to simply *view* an object's data without entering edit mode.

**UX Specification:**

```
+------------------------------------------------------------------+
| [icon] Project: SemPKM Research        [Edit] [...]              |
+------------------------------------------------------------------+
|                                                                  |
|  Type: Project                                                   |
|  Status: Active                                                  |
|  Created: 2026-01-15                                             |
|  Priority: High                                                  |
|  Related People: Alice Johnson, Bob Smith                        |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  # Project Notes                                                 |
|                                                                  |
|  This is the **rendered Markdown** body of the object.           |
|  Links, headings, lists, and code blocks all render properly.    |
|                                                                  |
|  - First item                                                    |
|  - Second item with [a link](https://example.com)               |
|                                                                  |
+------------------------------------------------------------------+
```

**Interaction Flow:**

1. **Default: Read-only mode.** When a user clicks an object in the explorer or opens a tab, they see the read-only view. Properties are rendered as styled key-value pairs (not form inputs). The Markdown body is rendered as HTML.
2. **Edit button in toolbar.** A prominent "Edit" button in the object toolbar (top-right). Clicking it swaps the view to the current SHACL form + CodeMirror editor.
3. **Edit mode toolbar changes.** In edit mode, the "Edit" button becomes "Done" (or "View"). The Save button appears. The dirty dot indicator works as before.
4. **Keyboard shortcut.** `Ctrl+E` or `E` (when not in an input) toggles between read and edit mode.
5. **URL/state preservation.** The mode (read/edit) is NOT persisted in the URL. Reopening a tab always defaults to read mode. The mode IS stored per-tab in sessionStorage so switching tabs remembers which mode each tab was in.
6. **New objects.** Newly created objects open in edit mode (since they need initial data entry). After the first save, they switch to read mode.

**Property Rendering in Read Mode:**
- Each SHACL property displays as: `Label: Value` on a single line
- Reference properties render as clickable links that open the target object in a new tab
- Boolean values show as "Yes" / "No" rather than "true" / "false"
- Date values formatted as human-readable (e.g., "January 15, 2026")
- Empty/unset optional properties are hidden (not shown as blank)
- Required empty properties show as "-- not set --" in muted text
- Multi-value properties show as comma-separated inline list, or bulleted if >3 values
- Properties grouped the same way as in edit mode (collapsible groups preserved)

**Markdown Rendering:**
- Use a lightweight Markdown-to-HTML library (marked.js or markdown-it) on the server side via Jinja2 filter, or client-side via a small library
- Render inside a `.markdown-body` container with GitHub-flavored-markdown-like styling
- Support: headings, bold, italic, links, images, code blocks, lists, blockquotes, tables, horizontal rules
- Internal wiki-style links (if any) should be clickable

**Technical Approach:**
- New Jinja2 template: `object_view.html` (read-only) alongside existing `object_tab.html` (edit)
- Backend endpoint: `/browser/object/{iri}` returns `object_view.html` by default; `/browser/object/{iri}?mode=edit` returns `object_tab.html`
- Toggle via htmx: the "Edit" button does `hx-get="/browser/object/{iri}?mode=edit"` swapping into `#editor-area`
- "Done" button does `hx-get="/browser/object/{iri}"` to swap back to read mode

---

### 3. Resizable Body Textarea in Edit Mode

**Priority:** P1
**Complexity:** Low
**Confidence:** HIGH

**Current State:** The form-to-editor split uses Split.js vertical mode with 40/60 ratio. This works but the editor area can feel cramped for long notes.

**UX Specification:**
- The vertical split between form section and editor section remains (Split.js)
- Add a CSS `resize: vertical` on the fallback textarea (already present)
- For CodeMirror, the Split.js gutter is the resize handle -- no additional work needed
- Add a "maximize editor" button (expand icon) in the editor toolbar that collapses the form section to 0% and gives 100% to the editor
- Clicking it again (or pressing Escape) restores the previous split ratio

**Interaction Flow:**
1. User drags the gutter between form and editor to resize
2. User clicks maximize icon -- editor fills the entire object tab area
3. User clicks minimize icon or presses Escape -- form reappears at previous ratio

---

### 4. VS Code-Style Split Panes (Editor Groups)

**Priority:** P1
**Complexity:** HIGH
**Confidence:** MEDIUM (conceptually straightforward but tricky with htmx partial swaps)

**Reference Pattern:** VS Code editor groups -- arbitrary horizontal/vertical splits, tabs within each group, drag tabs between groups.

**Current State:** The workspace has three fixed panes: nav (left), editor (center), right panel. The editor pane has a single tab bar and single editor area. Only one object displays at a time.

**UX Specification:**

```
+--------------------------------------------------+
| Tab Bar Group 1            | Tab Bar Group 2     |
| [Project A*] [Note B]     | [Person C] [View D]  |
+--------------------------------------------------+
|                            |                      |
|  Object A content          |  Person C content    |
|  (edit mode, dirty)        |  (read-only mode)    |
|                            |                      |
+--------------------------------------------------+
```

**Interaction Patterns:**

1. **Split by dragging a tab.** User drags a tab toward the right edge of the editor area. A blue overlay indicator appears showing where the new group will form (left half, right half, top half, bottom half). Releasing the tab creates a new editor group with that tab.

2. **Split via context menu.** Right-clicking a tab shows: "Split Right", "Split Down", "Close", "Close Others", "Close All". "Split Right" duplicates that tab into a new group to the right.

3. **Split via keyboard.** `Ctrl+\` splits the active tab to the right (VS Code default).

4. **Move tabs between groups.** Drag a tab from one group's tab bar to another group's tab bar. The tab moves (not copies) to the target group.

5. **Close a group.** When the last tab in a group is closed, the group is removed and remaining groups expand to fill the space.

6. **Maximum groups.** Limit to 4 editor groups (2x2 grid) to prevent UX chaos. Attempting to create a 5th shows a toast: "Maximum 4 editor groups."

7. **Active group.** Clicking anywhere in a group makes it the "active" group. The active group has a subtle blue top-border on its tab bar. New tabs opened from the explorer open in the active group.

8. **Resize between groups.** Groups are separated by draggable gutters (same Split.js style as existing pane gutters).

**Data Model:**

```javascript
// Editor group state (sessionStorage)
{
  groups: [
    {
      id: "group-1",
      tabs: [
        { iri: "http://...", label: "Project A", dirty: true, mode: "edit" },
        { iri: "http://...", label: "Note B", dirty: false, mode: "read" }
      ],
      activeTab: "http://...",
    },
    {
      id: "group-2",
      tabs: [...],
      activeTab: "http://...",
    }
  ],
  activeGroup: "group-1",
  layout: "horizontal",  // or "vertical" or "grid"
  sizes: [50, 50]        // Split.js percentages
}
```

**Technical Approach:**
- Replace the single `#editor-area` with a dynamic container that can hold multiple editor group divs
- Each editor group is a self-contained unit: tab bar + content area
- Use Split.js to manage the gutter between groups (nested Split.js instances)
- Tab drag uses the HTML5 Drag and Drop API with custom drop zones on group areas and edge indicators
- The workspace.js `openTab()` function targets `groups[activeGroupIndex]` instead of the single editor area
- Each group's content area has its own ID pattern: `editor-area-{groupId}`
- htmx swaps target the specific group's editor area

**Drop Zone Indicators:**
When dragging a tab, hovering over different regions of the editor area shows overlay indicators:
- **Center of existing group:** Drop into that group's tab bar
- **Left 25%:** Create new group to the left
- **Right 25%:** Create new group to the right
- **Top 25%:** Create new group above
- **Bottom 25%:** Create new group below

The indicators use a semi-transparent blue overlay (same as VS Code) with a subtle border.

**Simplification for v2.0:** Start with only horizontal splits (side-by-side). Vertical splits and grid can come later. This reduces the layout complexity significantly while delivering the core value.

---

### 5. Bottom Panel (Tabbed, Placeholder)

**Priority:** P1
**Complexity:** Medium
**Confidence:** HIGH (VS Code Panel pattern is well-documented)

**Reference Pattern:** VS Code's bottom panel (Terminal, Problems, Output, Debug Console).

**Current State:** No bottom panel exists. The workspace is nav-pane | editor-pane | right-pane horizontally.

**UX Specification:**

```
+-----------------------------------------------------------+
| [Nav]  |  [Editor Groups]                | [Right Panel]  |
|        |                                 |                 |
|        |                                 |                 |
|        +---------------------------------+-----------------+
|        |  [SPARQL] [Event Log] [AI] [+]       [x] [^]     |
|        |                                                   |
|        |  > Bottom panel content here                      |
|        |  (placeholder: "SPARQL console coming soon")      |
+-----------------------------------------------------------+
```

**Layout:**
- The bottom panel sits below the editor area but still within the main content region (not below the sidebar)
- It spans the full width of the content area (editor + right panel)
- Default height: 200px, resizable via a horizontal gutter (Split.js vertical)
- Minimum height: 100px. Maximum: 60% of viewport height.

**Interaction Patterns:**

1. **Toggle visibility.** `Ctrl+J` toggles the bottom panel (VS Code default). Also toggleable via command palette ("Toggle Bottom Panel") and via a toolbar icon.
2. **Tab switching.** Tabs along the top of the panel: initially "SPARQL", "Event Log". Clicking a tab switches content. Future tabs: "AI Copilot".
3. **Collapse button.** A chevron-down icon at the right of the panel tab bar collapses the panel. Clicking it again (chevron-up) restores it.
4. **Maximize button.** A square icon maximizes the panel to fill the editor area. Clicking again restores to previous size.
5. **Close button.** An "x" icon hides the panel entirely (same as toggle).
6. **Default state.** Panel is collapsed/hidden on first visit. User must explicitly open it.

**Panel Tab Content:**
- **SPARQL tab:** Placeholder text: "SPARQL console -- coming in a future update." Shows a disabled textarea and run button for visual preview.
- **Event Log tab:** When the event log explorer is built, it lives here.
- **AI Copilot tab:** Placeholder: "AI Copilot -- configure your LLM connection in Settings to enable."

**Technical Approach:**
- Restructure the workspace layout: the current horizontal 3-pane split needs a nested vertical split for the editor area (editor groups on top, bottom panel below)
- The bottom panel is a new `#bottom-panel` div with its own tab bar and content area
- Panel state (open/closed, active tab, height) persists in localStorage
- Panel tabs are registered declaratively: each feature that adds a panel tab adds an entry to a registry

---

### 6. Collapsible Sidebar with Reorganized Navigation

**Priority:** P1
**Complexity:** Medium
**Confidence:** HIGH (VS Code Activity Bar pattern)

**Reference Pattern:** VS Code's Activity Bar (icon rail) + Primary Sidebar (expanded content).

**Current State:** Fixed 220px sidebar with flat navigation links: Home, Admin, Object Browser, Health Check, Debug Tools section (SPARQL, Commands, API Docs x2).

**New Structure:**

```
COLLAPSED (48px icon rail):        EXPANDED (220px with labels):
+------+                           +------------------------+
| [S]  |                           | SemPKM                 |
+------+                           +------------------------+
| [H]  |                           | > Home                 |
| [A]  |                           | > Admin                |
| [M]  |                           | > Meta                 |
| [B]  |                           |   - Docs & Tutorials   |
| [D]  |                           | > Apps                 |
|      |                           |   - Object Browser     |
|      |                           |   - SPARQL Console     |
|      |                           | > Debug                |
|      |                           |   - Commands           |
|      |                           |   - API Docs           |
|      |                           |   - Health Check       |
|      |                           |   - Event Log          |
|      |                           |                        |
|      |                           |                        |
|      |                           |                        |
+------+                           +------------------------+
| [U]  |                           | [avatar] James    [v]  |
+------+                           +------------------------+
```

**Navigation Groups:**

| Group | Icon | Contains | Rationale |
|-------|------|----------|-----------|
| Home | House | Dashboard/landing page | Entry point |
| Admin | Gear | Model management, webhook config, system status | Admin functions grouped |
| Meta | Book | Docs & Tutorials page | User help resources |
| Apps | Grid/Squares | Object Browser, SPARQL Console | Primary user-facing tools |
| Debug | Bug | Commands, API Docs (ReDoc/Swagger), Health Check, Event Log | Developer/debug tools |

**Interaction Patterns:**

1. **Toggle collapse.** `Ctrl+B` toggles sidebar between collapsed (48px icon rail) and expanded (220px with labels). Same shortcut as VS Code.
2. **Collapsed state.** Shows only icons in a vertical rail. Hovering an icon shows a tooltip with the label. Clicking navigates directly.
3. **Expanded state.** Shows icons + labels. Groups are collapsible sections with chevrons (like current explorer sections). Group collapsed state persists in localStorage.
4. **Smooth transition.** The sidebar animates between collapsed/expanded with a 200ms CSS transition on width. Content area adjusts its `margin-left` accordingly.
5. **Responsive behavior.** On viewports <768px, sidebar auto-collapses to icon rail. Below 480px, sidebar hides completely with a hamburger menu button.

**Sidebar Bottom: User Menu (see feature 7 below)**

**Technical Approach:**
- Modify `_sidebar.html` to use a grouped structure with collapsible sections
- Add a `.sidebar-collapsed` class to the `<aside>` that switches to the icon-rail layout
- CSS transitions handle the width animation
- JavaScript in a small `sidebar.js` manages toggle state, persists to localStorage
- The sidebar brand in collapsed mode shows just the logo icon (first letter "S" in a circle, or a small SVG)

---

### 7. VS Code-Style User Menu at Bottom of Sidebar

**Priority:** P1
**Complexity:** Low
**Confidence:** HIGH (standard VS Code pattern)

**Reference Pattern:** VS Code's bottom-left account button and settings gear.

**UX Specification:**

```
Expanded sidebar:
+------------------------+
|                        |
| (navigation above)     |
|                        |
+------------------------+
| [avatar] James     [v] |
+------------------------+

Collapsed sidebar:
+------+
| [av] |
+------+
```

**Menu Items (on click/hover):**
```
+------------------------+
| James                  |
| james@example.com      |
+------------------------+
| Settings               |
| Theme: Light  [toggle] |
+------------------------+
| Keyboard Shortcuts     |
+------------------------+
| Logout                 |
+------------------------+
```

**Interaction Flow:**
1. The user menu sits at the very bottom of the sidebar, pinned via `flex-grow` on the nav area above it.
2. In expanded mode: shows avatar circle (initials or gravatar), display name, and a chevron.
3. In collapsed mode: shows just the avatar circle.
4. Clicking opens a popover menu above the button (positioned upward since it is at the bottom).
5. Menu contains: user info (name, email), Settings link, Theme toggle (inline), Keyboard Shortcuts link, Logout.
6. The theme toggle is an inline switch (light/dark) that changes immediately without closing the menu.
7. Clicking outside the menu closes it.
8. The menu is positioned using `position: absolute` with `bottom: 100%` relative to the user menu button.

**Technical Approach:**
- Add a `sidebar-user-menu` div at the bottom of `_sidebar.html`
- The popover is a hidden div that toggles on click
- User info comes from the session/auth context already available in Jinja2 templates
- Logout triggers the existing `/auth/logout` endpoint

---

### 8. Dark Mode with Theme Toggle

**Priority:** P1
**Complexity:** Medium
**Confidence:** HIGH (CSS custom properties already used throughout)

**Reference Pattern:** VS Code, Obsidian, and GitHub's theme switching. The "system/light/dark" tri-state pattern.

**Current State:** The app uses CSS custom properties (`:root` vars) for all colors: `--color-bg`, `--color-surface`, `--color-text`, `--color-border`, `--color-primary`, etc. This is the perfect foundation for dark mode.

**Color Tokens (Dark Mode):**

```css
:root {
  /* Light mode (default -- same as current) */
  --color-bg: #fafafa;
  --color-surface: #ffffff;
  --color-text: #1a1a2e;
  --color-text-muted: #666666;
  --color-border: #e0e0e0;
  --color-primary: #2d5a9e;
  --color-primary-hover: #1e3f7a;
  --color-success: #2a8a4a;
  --color-error: #c0392b;
  --color-warning: #d4a017;
  --color-code-bg: #f5f5f5;
}

[data-theme="dark"] {
  --color-bg: #1e1e1e;
  --color-surface: #252526;
  --color-text: #cccccc;
  --color-text-muted: #858585;
  --color-border: #3c3c3c;
  --color-primary: #569cd6;
  --color-primary-hover: #6fb3f2;
  --color-success: #4ec9b0;
  --color-error: #f44747;
  --color-warning: #dcdcaa;
  --color-code-bg: #2d2d2d;
}
```

These dark-mode values follow VS Code's "Dark+" theme, which is the most recognized dark theme in developer tools.

**Theme Toggle Placement:**
- **Primary location:** User menu at bottom of sidebar (inline toggle switch)
- **Secondary location:** Settings page (with system/light/dark tri-state selector)
- **Keyboard shortcut:** None by default (too easy to trigger accidentally), but available via command palette: "Toggle Theme"

**Three-State Preference:**
1. **System** (default): follows `prefers-color-scheme` media query
2. **Light**: always light
3. **Dark**: always dark

**Interaction Flow:**
1. On first visit, theme = "system". The app checks `prefers-color-scheme` and applies accordingly.
2. User clicks the toggle in the user menu. It cycles: system -> light -> dark -> system.
3. The toggle shows the current state with an icon: sun (light), moon (dark), monitor (system).
4. Theme change is instant with a subtle 150ms CSS transition on `background-color` and `color` properties.
5. Preference persists in localStorage under key `sempkm_theme`.

**Flash Prevention:**
```html
<script>
  // Inline in <head>, before any CSS loads
  (function() {
    var theme = localStorage.getItem('sempkm_theme') || 'system';
    if (theme === 'system') {
      theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    if (theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  })();
</script>
```

**Technical Approach:**
- Add dark mode CSS as `[data-theme="dark"]` overrides on `:root`
- Use `data-theme` attribute on `<html>` element (not class, for CSS specificity cleanliness)
- Small `theme.js` module handles: reading preference, applying theme, listening for system changes, toggling
- CodeMirror 6 has built-in dark mode via the `oneDark` theme extension -- switch this when theme changes
- Cytoscape graph styling needs dark mode variants (node colors, edge colors, background)
- Third-party components (ninja-keys, Split.js gutters) need dark mode overrides

**Components Requiring Dark Mode Attention:**

| Component | Approach |
|-----------|----------|
| Base layout (sidebar, content) | CSS variables handle it |
| Workspace panes (nav, editor, right) | CSS variables handle it |
| Tab bars | CSS variables + explicit dark overrides for hover states |
| SHACL forms | CSS variables handle it |
| CodeMirror 6 editor | Swap `oneDark` extension dynamically |
| Cytoscape graph | Dark node/edge palette in graph.js |
| ninja-keys command palette | Override `--ninja-*` CSS variables |
| Split.js gutters | Dark gutter color override |
| Markdown rendered content | `.markdown-body` dark mode styles (modeled on GitHub dark) |

---

### 9. Global Settings System

**Priority:** P2
**Complexity:** Medium
**Confidence:** MEDIUM (novel feature specific to SemPKM; pattern well-known from VS Code)

**Reference Pattern:** VS Code's settings system: User settings (global) > Workspace settings > Extension-contributed settings, with both GUI and JSON views.

**Current State:** No settings system exists. Theme preference lives in localStorage. No mechanism for mental models to contribute configuration.

**Settings Architecture:**

```
Settings Hierarchy (highest priority wins):
  1. User overrides (per-user, stored in auth DB or localStorage)
  2. Model defaults (contributed by installed Mental Models)
  3. System defaults (hardcoded in the app)
```

**Settings Categories:**

| Category | Example Settings | Source |
|----------|-----------------|--------|
| Appearance | theme, font-size, sidebar-collapsed | System defaults |
| Editor | tab-size, word-wrap, auto-save-delay | System defaults |
| Browser | default-view-type, items-per-page | System defaults |
| LLM | api-base-url, api-key, default-model | System defaults |
| Model: Basic PKM | project-default-status, note-template | Mental Model |

**Settings UI (VS Code-style):**

```
+------------------------------------------------------------------+
| Settings                                    [Search settings...] |
+------------------------------------------------------------------+
| Categories:        | Setting                           Value     |
|                    |                                             |
| > Appearance       | Theme                                       |
|   - Theme          | [System v]                                  |
|   - Font           |                                             |
| > Editor           | Editor Font Size                            |
|   - General        | [14] px                                     |
|   - Markdown       |                                             |
| > Browser          | Auto-save Delay                             |
|   - Display        | [1000] ms                                   |
|   - Defaults       |                                             |
| > LLM Connection   | Word Wrap                                   |
| > Basic PKM        | [x] On                                      |
|   (model settings) |                                             |
+------------------------------------------------------------------+
```

**Interaction Flow:**
1. User opens Settings from user menu or `Ctrl+,`
2. Settings page opens as a full tab in the editor area (like VS Code)
3. Left column: category tree. Right column: settings for selected category.
4. Each setting shows: label, description, current value input, and a "Modified" indicator if changed from default
5. Search bar at top filters settings across all categories
6. A "Reset to Default" option on each setting (gear icon context menu)
7. No JSON editor in v2.0 -- GUI only. JSON export/import can come later.

**Settings Storage (v2.0 -- keep it simple):**
- Store in localStorage as a JSON blob under `sempkm_settings`
- Mental Model contributed settings are declared in the model manifest and merged with system defaults at load time
- No server-side settings storage in v2.0 (defer to v3 when multi-device sync matters)
- Settings are read by JavaScript modules at init time via a `Settings.get(key, defaultValue)` API

**Settings Schema (for rendering the UI):**

```javascript
// Settings registry -- modules register their settings at load time
SettingsRegistry.register({
  key: "appearance.theme",
  label: "Theme",
  description: "Controls the color theme of the application.",
  type: "select",
  options: ["system", "light", "dark"],
  default: "system",
  category: "Appearance"
});

SettingsRegistry.register({
  key: "editor.fontSize",
  label: "Editor Font Size",
  description: "Font size in pixels for the Markdown editor.",
  type: "number",
  min: 10,
  max: 32,
  default: 14,
  category: "Editor"
});
```

**Technical Approach:**
- `settings-registry.js`: Central registry where modules declare their settings
- `settings-page.js`: Renders the settings UI as an htmx partial (or inline JS-generated DOM)
- `settings-store.js`: Read/write localStorage, merge with defaults, notify listeners on change
- Mental Models contribute settings via a `settings` key in their manifest JSON-LD
- Backend serves merged settings schema at `/api/settings/schema` (system defaults + installed model settings)

---

### 10. Node Type Icons in Graph View and Object Explorer

**Priority:** P2
**Complexity:** Low-Medium
**Confidence:** HIGH

**Reference Pattern:** Obsidian graph view with colored nodes by type; VS Code file icons by extension.

**Current State:** The explorer tree uses generic Unicode characters as icons. The graph view uses plain circles with no type differentiation.

**Icon System:**

| Type | Icon (Unicode/SVG) | Color | Explorer | Graph |
|------|--------------------|-------|----------|-------|
| Project | Kanban board | Blue | Yes | Yes |
| Person | User silhouette | Green | Yes | Yes |
| Note | Document | Yellow | Yes | Yes |
| Concept | Lightbulb | Purple | Yes | Yes |
| Edge (relation) | Arrow | Gray | No | Yes (edge style) |
| Unknown type | Circle | Gray | Yes | Yes |

**Icon Sources (choose one):**
- **Lucide Icons** (recommended): Open source, 1000+ icons, available as SVG sprite or individual SVGs. Tree-shakeable. MIT licensed. Used by Obsidian, shadcn/ui, and many modern tools.
- Include as an SVG sprite sheet loaded once, referenced via `<use href="#icon-name">`.

**Mental Model Icon Declarations:**
Models can declare type icons in their manifest:
```json
{
  "icons": {
    "pkm:Project": { "icon": "kanban", "color": "#569cd6" },
    "pkm:Person": { "icon": "user", "color": "#4ec9b0" },
    "pkm:Note": { "icon": "file-text", "color": "#dcdcaa" },
    "pkm:Concept": { "icon": "lightbulb", "color": "#c586c0" }
  }
}
```

**Explorer Tree Changes:**
- Replace the current Unicode `&#128196;` icons with SVG icon references
- Icons inherit the type color in both light and dark modes
- Fallback: circle icon for unknown types

**Graph View Changes:**
- Cytoscape nodes get a colored border and background based on type
- Node label positioned below the node
- Legend at bottom-right showing type -> color mapping
- Optional: node shape varies by type (circle for Person, rectangle for Project, diamond for Concept)

**Interaction Flow:**
1. Backend resolves type icons from installed Mental Models at startup
2. Icon mapping served at `/api/icons` or embedded in the workspace template
3. Explorer tree renders `<svg class="tree-icon"><use href="#icon-{name}"></svg>` for each node
4. Graph view reads icon/color mapping and applies to Cytoscape node styles

---

### 11. Event Log Explorer

**Priority:** P2
**Complexity:** HIGH
**Confidence:** MEDIUM (novel feature; no direct analogue in VS Code/Obsidian)

**Reference Pattern:** Git log viewer (GitLens, GitHub commits page); database audit log viewers; Appfarm event log design.

**Current State:** Events exist as RDF named graphs in the triplestore with full provenance (user, role, timestamp, operation type). No UI to browse them.

**UX Specification:**

```
+------------------------------------------------------------------+
| Event Log                                [Filter v] [Search...] |
+------------------------------------------------------------------+
| [Timeline]  [Table]                                              |
+------------------------------------------------------------------+
|                                                                  |
| Today                                                            |
|  12:45  object.patch   Project: SemPKM     james    [Diff] [Undo]|
|  12:30  body.set       Note: Research      james    [Diff] [Undo]|
|  11:15  object.create  Person: Alice       james    [View]       |
|                                                                  |
| Yesterday                                                        |
|  18:00  edge.create    SemPKM -> Alice     james    [View]       |
|  17:45  object.create  Project: SemPKM     james    [View]       |
|                                                                  |
+------------------------------------------------------------------+
```

**Two Display Modes:**

1. **Timeline mode (default):** Events grouped by date, most recent first. Each event shows: time, operation type badge, affected object link, user, and action buttons. Similar to a Git commit log.

2. **Table mode:** Flat table with sortable columns: Timestamp, Operation, Object, User, Details. Better for scanning large numbers of events.

**Filtering:**
- **By type:** Dropdown multi-select: object.create, object.patch, body.set, edge.create, edge.patch, validation.completed
- **By user:** Dropdown of known users
- **By object:** Search-as-you-type to filter to events about a specific object
- **Date range:** Start/end date pickers
- Filters combine with AND logic
- Active filters shown as removable chips above the results

**Diff View:**
- Clicking "Diff" on an `object.patch` or `body.set` event opens an inline diff panel below the event row
- The diff shows a side-by-side or unified diff of the changed properties/body
- For property changes: "Status: Draft -> Active" format
- For body changes: line-by-line diff with green (added) / red (removed) highlighting
- Use a lightweight diff library (jsdiff) for client-side diffing, or compute diffs server-side

**Undo:**
- Clicking "Undo" on a reversible event (object.patch, body.set, edge.create, edge.patch) creates a new compensating event that reverses the change
- Confirmation dialog: "Undo this change? This will create a new event that reverses [operation] on [object]."
- The undo itself appears in the event log as a new event with provenance `performed_by: user, undo_of: original_event_iri`
- Not all events are undoable: `object.create` cannot be undone (would require delete, which does not exist yet)

**Location:**
- The Event Log lives in the Bottom Panel as a tab (see feature 5)
- It can also be accessed as a standalone page via the sidebar Debug > Event Log link

**Technical Approach:**
- Backend endpoint: `GET /api/events?type=...&user=...&object=...&after=...&before=...&limit=50&offset=0`
- Events are read from the triplestore via SPARQL query on event named graphs
- Frontend: htmx-driven pagination (infinite scroll or "Load more" button)
- Diff computation: server-side (Python `difflib`) for body diffs, simple before/after for property diffs
- Undo: `POST /api/events/{event_iri}/undo` creates a compensating command

---

### 12. LLM Connection Configuration

**Priority:** P2
**Complexity:** Low-Medium
**Confidence:** HIGH (straightforward settings form; well-established patterns from LM Studio, Langfuse)

**Reference Pattern:** LM Studio endpoint config; Langfuse LLM Connections; Open WebUI settings.

**UX Specification:**

```
+------------------------------------------------------------------+
| LLM Connection                                                    |
+------------------------------------------------------------------+
|                                                                  |
| Provider: [OpenAI-Compatible v]                                  |
|                                                                  |
| API Base URL:                                                    |
| [https://api.openai.com/v1                    ]                  |
|                                                                  |
| API Key:                                                         |
| [sk-...                          ] [Show/Hide]                   |
|                                                                  |
| Default Model:                                                   |
| [gpt-4o                          ] [Fetch Models]                |
|                                                                  |
| Advanced:                                                        |
|   Temperature: [0.7    ]                                         |
|   Max Tokens:  [4096   ]                                         |
|                                                                  |
| [Test Connection]     Connection status: Not tested              |
|                                                                  |
| [Save]                                                           |
+------------------------------------------------------------------+
```

**Interaction Flow:**
1. User navigates to Settings > LLM Connection (or directly via sidebar)
2. User enters API base URL, API key, and optionally a default model name
3. "Fetch Models" button calls the `/v1/models` endpoint to populate a dropdown of available models
4. "Test Connection" sends a minimal completion request and reports success/failure with latency
5. Connection status persists: green dot "Connected", red dot "Error: [message]", gray dot "Not tested"
6. "Save" stores the configuration

**Configuration Storage:**
- API key is sensitive -- store server-side in the auth database (encrypted at rest), NOT in localStorage
- API base URL and model name can be in localStorage or server-side
- Backend endpoint: `POST /api/settings/llm` to save, `GET /api/settings/llm` to retrieve (returns masked key)
- Test endpoint: `POST /api/settings/llm/test` proxies a test request through the backend

**Security Considerations:**
- API key never sent to the browser after initial save (only `sk-...****` mask shown)
- API key encrypted in the database using a server-side secret
- All LLM API calls proxied through the backend (never direct from browser)
- The "Show" toggle only works before the first save; after save, the full key is never returned

---

### 13. Shepherd.js Tutorial Infrastructure

**Priority:** P2
**Complexity:** Medium
**Confidence:** HIGH (Shepherd.js is mature, well-documented, works with vanilla JS)

**Reference Pattern:** Shepherd.js official examples; product onboarding patterns.

**UX Specification:**

**Tutorial Access Points:**
- "Getting Started" button on the Home dashboard (for first-time users)
- Meta > Docs & Tutorials page in sidebar
- Command palette: "Start Tutorial: [name]"
- Auto-prompt on first login: "Welcome! Would you like a quick tour?" with "Yes, show me around" / "No thanks" buttons

**Tutorial 1: "Welcome to SemPKM" (workspace orientation)**
Steps:
1. **Sidebar** -- "This is your navigation. Browse models, objects, and debug tools here."
2. **Object Browser** -- "Click here to open the Object Browser, your main workspace."
3. **Explorer panel** -- "Objects are organized by type. Click a type to expand and see its objects."
4. **Opening an object** -- "Click an object to open it in a tab."
5. **Read/Edit toggle** -- "Objects open in read-only view. Click Edit to modify properties."
6. **Tab management** -- "Open multiple objects in tabs. Right-click for split options."
7. **Command palette** -- "Press Ctrl+K to open the command palette for quick actions."
8. **Saving** -- "Press Ctrl+S to save your changes."
9. **Done** -- "You are all set! Explore your knowledge base."

**Tutorial 2: "Creating Your First Object"**
Steps:
1. Open command palette (Ctrl+K)
2. Select "New Object"
3. Choose a type
4. Fill in required fields (highlight the form)
5. Add a markdown body
6. Save
7. View the object in read-only mode

**Shepherd.js Integration:**

```javascript
// Tour definition
const welcomeTour = new Shepherd.Tour({
  useModalOverlay: true,
  defaultStepOptions: {
    classes: 'sempkm-tour-step',
    scrollTo: true,
    cancelIcon: { enabled: true },
    exitOnEsc: true
  }
});

welcomeTour.addStep({
  id: 'sidebar',
  text: 'This is your navigation sidebar...',
  attachTo: { element: '.sidebar', on: 'right' },
  buttons: [
    { text: 'Skip', action: welcomeTour.cancel, secondary: true },
    { text: 'Next', action: welcomeTour.next }
  ]
});
```

**Technical Approach:**
- Add `shepherd.js` via CDN or npm (CSS + JS)
- Create `tours/` directory with one JS file per tutorial
- Tour definitions are loaded on demand (not bundled into every page)
- A `TourManager` singleton tracks completed tours in localStorage
- The auto-prompt on first login checks `localStorage.getItem('sempkm_tour_completed')` and shows the welcome prompt if null
- Shepherd's modal overlay dims everything except the highlighted element
- Custom CSS for tour steps matches the app's design language (respects dark mode)

**Docs & Tutorials Page:**
```
+------------------------------------------------------------------+
| Docs & Tutorials                                                 |
+------------------------------------------------------------------+
|                                                                  |
| Interactive Tutorials                                            |
|                                                                  |
|  [>] Welcome to SemPKM          ~2 min    [Start]               |
|  [>] Creating Your First Object ~3 min    [Start]               |
|                                                                  |
| Documentation                                                    |
|                                                                  |
|  - Keyboard Shortcuts                                            |
|  - Object Types & Properties                                     |
|  - Mental Models                                                 |
|  - SPARQL Queries (coming soon)                                  |
|                                                                  |
+------------------------------------------------------------------+
```

---

### 14. Styled 403 Permission Panel

**Priority:** P2
**Complexity:** Low
**Confidence:** HIGH

**Reference Pattern:** Styled error pages from modern web apps; consistent branding maintained during errors.

**Current State:** When a user lacks permission, the htmx swap shows a raw error fragment with minimal styling.

**UX Specification:**

```
+------------------------------------------------------------------+
|                                                                  |
|              [lock icon, large, muted]                           |
|                                                                  |
|              Access Restricted                                    |
|                                                                  |
|   You don't have permission to view this content.                |
|   Your current role: Guest                                       |
|                                                                  |
|   Contact an administrator to request access.                    |
|                                                                  |
|              [Go to Home]   [Go Back]                            |
|                                                                  |
+------------------------------------------------------------------+
```

**Design Details:**
- Centered vertically and horizontally in the content area
- Large lock icon (SVG, 64px, muted gray)
- "Access Restricted" heading (not "403 Forbidden" -- avoid technical jargon for end users)
- Explanation text in muted color
- Shows the user's current role so they understand why
- Two action buttons: "Go to Home" (primary) and "Go Back" (secondary, uses `history.back()`)
- Maintains full app chrome (sidebar, header) -- not a full-page error

**Technical Approach:**
- Create a Jinja2 template: `errors/403.html` that extends `base.html`
- Backend returns this template for 403 responses (both full page and htmx partials)
- For htmx partials: return just the inner content without the base layout
- Detect htmx requests via `HX-Request` header and return the partial version

---

### 15. Rounded Tab Styling

**Priority:** P3
**Complexity:** Low
**Confidence:** HIGH

**Current State:** Tabs have sharp corners with a bottom-border accent. The current styling uses `border-right: 1px solid` between tabs and `border-bottom: 2px solid` for the active indicator.

**New Style:**
- Tabs get `border-radius: 8px 8px 0 0` (top corners rounded)
- Active tab gets a subtle background color lift and no bottom border gap
- Tab close button gets `border-radius: 50%` on hover
- The tab bar background is slightly darker than the active tab (creating a "recessed" look)

**CSS Changes:**
```css
.workspace-tab {
  border-radius: 8px 8px 0 0;
  border-right: none;
  margin-right: 1px;
  border-bottom: 2px solid transparent;
}

.workspace-tab.active {
  background: var(--color-surface);
  border-bottom-color: var(--color-surface);
  /* Active tab connects to content below */
  position: relative;
  z-index: 1;
}

.tab-bar-workspace {
  background: color-mix(in srgb, var(--color-surface) 85%, var(--color-border));
  padding-top: 4px;
  gap: 1px;
}
```

---

## Feature Dependencies

```
Bug Fixes (P0)
  |
  v
Read-Only View (P0) --> requires new object_view.html template
  |
  v
Split Panes (P1) --> depends on read-only view for meaningful side-by-side
  |
  v
Bottom Panel (P1) --> depends on split panes layout refactor (nested splits)
  |
  v
Event Log Explorer (P2) --> lives in bottom panel

Collapsible Sidebar (P1) --> independent, can parallelize
  |
  v
User Menu (P1) --> sits inside sidebar
  |
  v
Dark Mode (P1) --> depends on sidebar refactor for icon-rail dark styling
  |
  v
Settings System (P2) --> dark mode is first consumer; settings page is a tab
  |
  v
LLM Config (P2) --> settings subsection

Node Type Icons (P2) --> independent, can parallelize

Shepherd.js Tutorials (P2) --> depends on read-only view existing (tours reference it)

Styled 403 (P2) --> independent

Rounded Tabs (P3) --> independent, pure CSS
```

## MVP Recommendation

**Phase 1 (Foundation):**
1. Bug fixes -- unblock core functionality
2. Read-only object view -- transforms the feel of the app
3. Collapsible sidebar + user menu -- navigation feels modern
4. Rounded tab styling -- quick visual polish

**Phase 2 (Layout):**
5. Dark mode -- high-demand feature, CSS variables already in place
6. VS Code-style split panes (horizontal only for v2.0)
7. Bottom panel infrastructure (with placeholders)

**Phase 3 (Features):**
8. Node type icons -- visual richness
9. Settings system -- needed for LLM config
10. LLM connection config -- AI readiness
11. Styled 403 panel

**Phase 4 (Experience):**
12. Event log explorer -- complex but unique differentiator
13. Shepherd.js tutorials -- polish/onboarding

**Defer:** Vertical/grid split panes, JSON settings editor, AI copilot chat, full mobile responsiveness.

## Sources

- [VS Code User Interface Guide](https://code.visualstudio.com/docs/getstarted/userinterface) -- HIGH confidence
- [VS Code Custom Layout](https://code.visualstudio.com/docs/configure/custom-layout) -- HIGH confidence
- [VS Code UX Guidelines: Activity Bar](https://code.visualstudio.com/api/ux-guidelines/activity-bar) -- HIGH confidence
- [VS Code UX Guidelines: Panel](https://code.visualstudio.com/api/ux-guidelines/panel) -- HIGH confidence
- [VS Code User and Workspace Settings](https://code.visualstudio.com/docs/configure/settings) -- HIGH confidence
- [Carbon Design System: Read-Only States](https://carbondesignsystem.com/patterns/read-only-states-pattern/) -- HIGH confidence
- [Dark Mode on the Web (CSS-Tricks)](https://css-tricks.com/a-complete-guide-to-dark-mode-on-the-web/) -- HIGH confidence
- [Best Light/Dark Mode Toggle (whitep4nth3r)](https://whitep4nth3r.com/blog/best-light-dark-mode-theme-toggle-javascript/) -- MEDIUM confidence
- [Shepherd.js Documentation](https://docs.shepherdjs.dev/guides/usage/) -- HIGH confidence
- [Shepherd.js GitHub](https://github.com/shipshapecode/shepherd) -- HIGH confidence
- [Split.js](https://split.js.org/) -- HIGH confidence (already in use)
- [Langfuse LLM Connections](https://langfuse.com/docs/administration/llm-connection) -- MEDIUM confidence
- [403 Page Design Best Practices](https://tunarabuzar.medium.com/a-403-forbidden-page-design-key-points-b70960379e03) -- MEDIUM confidence
- [Filter UI Patterns 2025 (BricxLabs)](https://bricxlabs.com/blogs/universal-search-and-filters-ui) -- MEDIUM confidence
