# Phase 13: Dark Mode and Visual Polish - Research

**Researched:** 2026-02-23
**Domain:** CSS theming, anti-FOUC, third-party library dark mode integration
**Confidence:** HIGH

## Summary

This phase requires building a tri-state theme system (System/Light/Dark) using CSS custom properties as the single source of truth for all color values. The project already has a partial custom property system in `style.css` (11 color tokens in `:root`), but the three other CSS files (workspace.css, forms.css, views.css) contain approximately 385 hardcoded hex colors and 45 hardcoded rgba() values that bypass the token system entirely. The core work is: (1) expand the token set to cover all surfaces, (2) replace every hardcoded color with a token reference, (3) create dark-mode overrides on `html[data-theme="dark"]`, and (4) wire up an anti-FOUC inline script + toggle UI.

Third-party integration is straightforward but each library uses a different mechanism: CodeMirror 6 uses `Compartment.reconfigure()` for runtime theme switching, ninja-keys has a built-in `class="dark"` toggle plus 20+ CSS custom properties, Cytoscape.js requires programmatic `cy.style()` calls (no native CSS theming), and Split.js gutters are pure CSS (just reference tokens). The highlight.js theme for Markdown code blocks must switch its CSS stylesheet link between `github.min.css` and `github-dark.min.css`.

**Primary recommendation:** Define all color tokens on `:root` (light) and `html[data-theme="dark"]` (dark) in a single new file `theme.css` loaded first, then systematically replace hardcoded colors across all four existing CSS files with token references. Use a `data-theme` attribute on `<html>` rather than a class for clean CSS specificity.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Inspired by VS Code Dark+ but softer -- warmer grays, less saturated accents
- Teal/cyan accent colors (not pure blue) for links, active states, focus rings
- Subtle but visible borders between all regions -- no "flat sea of darkness." Every panel edge (sidebar, editor, right panel, tab bar) should be delineated with 1px borders ~10-15% lighter than surface
- Light mode also gets refreshed to use the same CSS custom property token system (both themes share tokens)
- Toggle lives in both the user menu popover AND the command palette
- User popover shows a 3-icon row: Sun / Monitor / Moon -- click to select
- Theme changes use a quick ~150ms crossfade transition on background and text colors
- "System" mode reads OS preference on page load only -- does not react to mid-session OS prefers-color-scheme changes
- Preference persists in localStorage; anti-FOUC inline script applies theme before first paint
- Subtle 4px top border-radius on tabs -- minimal change from current flat tabs
- Active tab gets both a lighter background (matching editor area) AND a teal bottom accent line
- Inactive tabs are muted/recessed
- Tab bar has a recessed/darker background behind the tabs, making tabs pop forward
- Close button (x) shows on hover only; active tab always shows close button

### Claude's Discretion
- Exact color hex values within the "softer Dark+" direction
- Anti-FOUC script implementation details
- How to handle CodeMirror theme compartment reconfiguration
- Cytoscape and ninja-keys dark mode integration approach
- 403 error panel layout and copy (roadmap says: lock icon, role explanation, navigation buttons)
- Split.js gutter styling in dark mode

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DARK-01 | User can toggle between System, Light, and Dark theme modes via the user menu or command palette | Anti-FOUC script pattern, localStorage persistence, popover 3-icon row, command palette ninja-keys integration |
| DARK-02 | Theme preference persists across page reloads with no flash of wrong theme (anti-FOUC inline script) | Inline `<script>` in `<head>` reads localStorage before first paint, sets `data-theme` attribute |
| DARK-03 | Dark mode applies to all UI components including CodeMirror editor, Cytoscape graph, command palette, and Split.js gutters | CodeMirror Compartment reconfigure, Cytoscape cy.style() rebuild, ninja-keys class="dark" toggle, Split.js pure CSS via tokens |
| DARK-04 | Dark mode color tokens follow VS Code "Dark+" palette (dark surface, muted text, blue accents) | Color palette derived from VS Code Dark+ but softer per user decision: warmer grays, teal/cyan accents |
| WORK-06 | Tab styling uses rounded top corners (border-radius 8px) with a recessed tab bar background | Changed to 4px per user decision; recessed tab bar + teal accent line pattern documented |
| ERR-01 | 403 Forbidden responses display a styled permission panel with lock icon, role explanation, and navigation buttons | Pure template + CSS task; Lucide lock icon, semantic error panel design |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| CSS Custom Properties | native | Color token system | Zero-dependency, inherited across shadow DOM boundaries, works with all CSS files |
| `data-theme` attribute | native | Theme state on `<html>` | Clean specificity, no class collision, standard pattern |
| localStorage | native | Theme persistence | Synchronous read in inline script prevents FOUC |

### Supporting (already in project)
| Library | Version | Purpose | Dark Mode Mechanism |
|---------|---------|---------|---------------------|
| CodeMirror 6 | @6 (esm.sh) | Markdown editor | `Compartment.reconfigure()` with `EditorView.theme({...}, {dark: true})` |
| ninja-keys | latest (unpkg) | Command palette | `class="dark"` toggle + CSS custom properties (`--ninja-*`) |
| Cytoscape.js | 3.33.1 | Graph visualization | Programmatic `cy.style()` rebuild with new color arrays |
| Split.js | 1.6.5 | Resizable panes | Pure CSS via `.gutter` selector referencing tokens |
| highlight.js | 11.11.1 | Code block highlighting | Swap CSS link: `github.min.css` <-> `github-dark.min.css` |
| Lucide | 0.575.0 | Icons | SVG icons inherit `currentColor`; no theme work needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `data-theme` attr | `.dark` class on body | Class is fine too, but `data-theme` is more semantic and allows 3+ values |
| Custom dark theme for CodeMirror | `@codemirror/theme-one-dark` package | One Dark is too saturated/cool for the "softer Dark+" direction; custom theme gives full control |
| `prefers-color-scheme` media queries | `data-theme` attribute selectors | Media queries alone don't support user override; attribute approach is strictly necessary for tri-state |

**No new packages required.** All theming uses native CSS and existing library APIs.

## Architecture Patterns

### Recommended File Structure
```
frontend/static/css/
├── theme.css            # NEW: all CSS custom property definitions (light + dark)
├── style.css            # Base layout (existing, tokens replaced)
├── workspace.css        # Workspace layout (existing, tokens replaced)
├── forms.css            # SHACL forms (existing, tokens replaced)
└── views.css            # View system (existing, tokens replaced)

frontend/static/js/
├── theme.js             # NEW: theme toggle logic, localStorage, command palette entry
├── sidebar.js           # Modified: theme icon row in user popover
├── editor.js            # Modified: Compartment for theme switching
├── graph.js             # Modified: dark/light style sets for Cytoscape
├── workspace.js         # Modified: theme command palette entries
└── ...

backend/app/templates/
├── base.html            # Modified: inline anti-FOUC script in <head>, theme.css link
├── components/
│   └── _sidebar.html    # Modified: theme toggle 3-icon row in user popover
└── errors/
    └── 403.html         # NEW: styled 403 permission panel
```

### Pattern 1: CSS Custom Property Token System
**What:** All colors defined as CSS custom properties on `:root` (light) with dark overrides on `html[data-theme="dark"]`
**When to use:** Every color value in every CSS file
**Example:**
```css
/* theme.css */
:root {
  /* Surfaces */
  --color-bg: #fafafa;
  --color-surface: #ffffff;
  --color-surface-raised: #f8f9fb;
  --color-surface-recessed: #f4f5f7;
  --color-surface-hover: rgba(0, 0, 0, 0.04);

  /* Text */
  --color-text: #1a1a2e;
  --color-text-muted: #666666;
  --color-text-faint: #999999;

  /* Borders */
  --color-border: #e0e0e0;
  --color-border-subtle: #f0f0f0;

  /* Accent (teal/cyan per user decision) */
  --color-accent: #0d9488;
  --color-accent-hover: #0f766e;
  --color-accent-subtle: rgba(13, 148, 136, 0.08);
  --color-accent-muted: rgba(13, 148, 136, 0.15);

  /* Primary (for links, existing blue kept for backward compat, then migrated) */
  --color-primary: #2d5a9e;
  --color-primary-hover: #1e3f7a;

  /* Semantic status */
  --color-success: #2a8a4a;
  --color-error: #c0392b;
  --color-warning: #d4a017;

  /* Code/editor */
  --color-code-bg: #f5f5f5;

  /* Shadows */
  --shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  --shadow-elevated: 0 4px 12px rgba(0, 0, 0, 0.15);
}

html[data-theme="dark"] {
  /* Surfaces -- softer Dark+ inspired */
  --color-bg: #1e2127;
  --color-surface: #282c34;
  --color-surface-raised: #2c313a;
  --color-surface-recessed: #21252b;
  --color-surface-hover: rgba(255, 255, 255, 0.06);

  /* Text */
  --color-text: #abb2bf;
  --color-text-muted: #7d8799;
  --color-text-faint: #5c6370;

  /* Borders -- 10-15% lighter than surface per user decision */
  --color-border: #3e4452;
  --color-border-subtle: #2c313a;

  /* Accent (teal/cyan) */
  --color-accent: #56b6c2;
  --color-accent-hover: #6bc5cf;
  --color-accent-subtle: rgba(86, 182, 194, 0.12);
  --color-accent-muted: rgba(86, 182, 194, 0.20);

  /* Primary */
  --color-primary: #61afef;
  --color-primary-hover: #82c0f2;

  /* Semantic status */
  --color-success: #98c379;
  --color-error: #e06c75;
  --color-warning: #e5c07b;

  /* Code/editor */
  --color-code-bg: #2c313a;

  /* Shadows */
  --shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  --shadow-elevated: 0 4px 12px rgba(0, 0, 0, 0.4);
}
```

### Pattern 2: Anti-FOUC Inline Script
**What:** Synchronous inline script in `<head>` that reads localStorage and sets `data-theme` before CSS renders
**When to use:** Every page load, before any stylesheet takes effect
**Example:**
```html
<!-- In base.html <head>, BEFORE any <link rel="stylesheet"> -->
<script>
(function() {
  var stored = localStorage.getItem('sempkm_theme');
  var theme = 'light';
  if (stored === 'dark') {
    theme = 'dark';
  } else if (stored === 'system' || !stored) {
    theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  document.documentElement.setAttribute('data-theme', theme);
})();
</script>
```

### Pattern 3: Theme Toggle with Crossfade Transition
**What:** 150ms CSS transition on theme-sensitive properties; toggle sets `data-theme` and persists to localStorage
**When to use:** User clicks Sun/Monitor/Moon in popover, or selects theme in command palette
**Example:**
```css
/* Crossfade transition */
html {
  transition: background-color 150ms ease, color 150ms ease;
}

html * {
  transition: background-color 150ms ease, color 150ms ease, border-color 150ms ease;
}
```
Note: The `*` selector transition should be applied carefully -- it can cause performance issues on large DOMs. A better approach is to apply the transition only to key layout elements (body, .sidebar, .content-area, .workspace-tab, etc.) rather than universally.

### Pattern 4: CodeMirror 6 Compartment Theme Switching
**What:** Store a `Compartment` for the theme extension, reconfigure when theme changes
**When to use:** Every CodeMirror editor instance
**Example:**
```javascript
import { Compartment } from "https://esm.sh/@codemirror/state@6";
import { EditorView } from "https://esm.sh/@codemirror/view@6";

// Global compartment shared across all editor instances
var themeCompartment = new Compartment();

// Custom dark theme matching the project palette
var darkEditorTheme = EditorView.theme({
  "&": { color: "#abb2bf", backgroundColor: "#282c34" },
  ".cm-content": { caretColor: "#56b6c2" },
  ".cm-cursor": { borderLeftColor: "#56b6c2" },
  ".cm-gutters": { backgroundColor: "#21252b", color: "#5c6370", borderRight: "1px solid #3e4452" },
  ".cm-activeLine": { backgroundColor: "#2c313a" },
  ".cm-activeLineGutter": { backgroundColor: "#2c313a" },
  "&.cm-focused .cm-selectionBackground, .cm-selectionBackground": { backgroundColor: "#3E4451" }
}, { dark: true });

var lightEditorTheme = EditorView.theme({
  "&": { color: "#1a1a2e", backgroundColor: "#ffffff" },
  ".cm-gutters": { backgroundColor: "#f8f9fb", color: "#666", borderRight: "1px solid #e0e0e0" }
});

// On editor init: include themeCompartment.of(currentTheme) in extensions
// On theme switch:
function switchEditorTheme(view, isDark) {
  view.dispatch({
    effects: themeCompartment.reconfigure(isDark ? darkEditorTheme : lightEditorTheme)
  });
}
```

### Pattern 5: Cytoscape Dark Mode Style Rebuild
**What:** Maintain two style arrays (light/dark), call `cy.style(newStyles)` on theme change
**When to use:** When Cytoscape graph instances exist
**Example:**
```javascript
// In graph.js, define dark variants
var darkNodeDefaults = {
  'color': '#abb2bf',        // label text
  'text-background-color': '#282c34',
  'text-background-opacity': 0.8,
  'border-color': '#3e4452'
};

var darkEdgeDefaults = {
  'line-color': '#3e4452',
  'target-arrow-color': '#3e4452',
  'color': '#7d8799',
  'text-background-color': '#282c34'
};

// On theme switch, if cy instance exists:
function switchGraphTheme(isDark) {
  var cy = window._sempkmGraph;
  if (!cy) return;
  var styles = buildSemanticStyle(window._sempkmTypeColors, isDark);
  cy.style(styles);
}
```

### Pattern 6: ninja-keys Dark Mode Toggle
**What:** Toggle `dark` class on the `<ninja-keys>` element when theme changes
**When to use:** On theme switch
**Example:**
```javascript
function switchNinjaTheme(isDark) {
  var ninja = document.querySelector('ninja-keys');
  if (!ninja) return;
  if (isDark) {
    ninja.classList.add('dark');
  } else {
    ninja.classList.remove('dark');
  }
}
```

Additionally, override ninja-keys CSS variables to match the project palette:
```css
ninja-keys {
  --ninja-accent-color: var(--color-accent);
  --ninja-text-color: var(--color-text);
  --ninja-secondary-background-color: var(--color-surface-raised);
  --ninja-secondary-text-color: var(--color-text-muted);
  --ninja-selected-background: var(--color-surface-hover);
  --ninja-modal-background: var(--color-surface);
  --ninja-modal-shadow: var(--shadow-elevated);
  --ninja-group-text-color: var(--color-text-faint);
  --ninja-footer-background: var(--color-surface-recessed);
  --ninja-separate-border: 1px solid var(--color-border);
  --ninja-z-index: 1000;
}
```

### Pattern 7: highlight.js Theme Switching
**What:** Swap the highlight.js CSS stylesheet link between light and dark variants
**When to use:** On theme switch
**Example:**
```javascript
function switchHighlightTheme(isDark) {
  var link = document.getElementById('hljs-theme');
  if (!link) return;
  var base = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/styles/';
  link.href = base + (isDark ? 'github-dark.min.css' : 'github.min.css');
}
```
The existing `<link>` in base.html needs an `id="hljs-theme"` attribute for this to work.

### Anti-Patterns to Avoid
- **Using `prefers-color-scheme` media queries as the primary mechanism:** This does not support user override. Use `data-theme` attribute selectors as the primary mechanism, with `prefers-color-scheme` only in the anti-FOUC script for "system" mode detection.
- **Applying `transition: *` to all elements:** This causes janky animations on complex DOMs. Target specific layout elements only.
- **Duplicating color values across dark theme definitions:** All dark colors should be defined ONCE in theme.css and referenced everywhere via tokens.
- **Recreating CodeMirror instances on theme change:** Use Compartment.reconfigure() instead -- recreating is expensive and loses editor state (cursor position, undo history).
- **Hardcoded colors in JavaScript:** Graph.js and editor.js should reference a shared theme config object rather than inline hex values.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Anti-FOUC script | Custom solution from scratch | Standard inline-script-sets-attribute pattern | Well-established, works in all browsers, 10 lines of code |
| CodeMirror dark theme | Custom syntax highlighting from scratch | `EditorView.theme({...}, {dark: true})` + custom colors | CM6's `{dark: true}` enables built-in dark defaults for unstyled elements |
| ninja-keys dark mode | Custom shadow DOM piercing | `class="dark"` + CSS variable overrides | ninja-keys has built-in dark mode support |
| Color palette design | Guessing hex values | Derive from VS Code Dark+ color reference + user's "softer" direction | VS Code Dark+ is a proven, contrast-tested palette |

**Key insight:** Every third-party library in this project already has a dark mode mechanism. The work is integration, not invention.

## Common Pitfalls

### Pitfall 1: Hardcoded Colors Causing Dark Mode "Holes"
**What goes wrong:** After enabling dark mode, certain elements still show white/light backgrounds because their colors are hardcoded in CSS rather than using tokens
**Why it happens:** The current codebase has ~430 hardcoded color values across 4 CSS files. It is easy to miss some during migration.
**How to avoid:** After migration, grep for any remaining hex colors in CSS files. All hex/rgb values should be in theme.css only (the token definitions). All other CSS files should reference `var(--color-*)` tokens exclusively.
**Warning signs:** Light-colored patches in dark mode, especially in explorer headers (#eef0f4), tab bar (#f4f5f7), editor toolbar (#f8f9fb)

### Pitfall 2: FOUC on Page Load
**What goes wrong:** User sees a flash of light theme before dark theme applies
**Why it happens:** The inline script runs AFTER stylesheets, or the script is in `<body>` instead of `<head>`, or it is loaded as an external script (which is async)
**How to avoid:** The anti-FOUC script MUST be an inline `<script>` tag in `<head>` BEFORE any `<link rel="stylesheet">` tags. It must be synchronous (no defer/async).
**Warning signs:** Brief white flash when loading dark-themed pages

### Pitfall 3: CodeMirror Compartment Not Initialized
**What goes wrong:** Theme switch fails silently because the Compartment was not included in the editor's initial extension list
**Why it happens:** Compartment.reconfigure() only works if the compartment was part of the initial EditorState.create() extensions
**How to avoid:** Always include `themeCompartment.of(initialTheme)` in the extensions array during editor creation. Create the compartment once at module scope, not per-editor.
**Warning signs:** Editor stays light when rest of UI switches to dark

### Pitfall 4: Cytoscape Colors Not Updating
**What goes wrong:** Graph nodes/edges retain old colors after theme switch
**Why it happens:** Cytoscape.js does not observe CSS changes -- it reads style values once at initialization. Must explicitly call `cy.style(newStylesheet)` to update.
**How to avoid:** Listen for the `sempkm:theme-changed` custom event and rebuild Cytoscape styles
**Warning signs:** Graph background/labels stay light-colored in dark mode

### Pitfall 5: Auth Pages Missing Dark Mode
**What goes wrong:** Login, setup, and invite pages render in light mode only
**Why it happens:** Auth pages may have different base templates or may not include the anti-FOUC script
**How to avoid:** Ensure the anti-FOUC script and theme.css are loaded in ALL templates including auth pages
**Warning signs:** Login page always shows light theme even when preference is dark

### Pitfall 6: Transition Flash on Initial Load
**What goes wrong:** Even with anti-FOUC, there is a brief color transition animation on first load
**Why it happens:** The CSS transition property applies to the initial style application too
**How to avoid:** Add a `.no-transition` class to `<html>` in the anti-FOUC script, remove it after first paint with `requestAnimationFrame`
**Warning signs:** Colors "fade in" on page load instead of appearing instantly

### Pitfall 7: Error/Success Background Colors Still Hardcoded
**What goes wrong:** `.form-success`, `.form-error`, `.error-box`, `.success-box` show light-mode-only background colors
**Why it happens:** These use hardcoded light backgrounds (#e8f5e9, #ffebee, etc.) that look jarring in dark mode
**How to avoid:** Convert to semantic tokens like `--color-success-bg`, `--color-error-bg` with dark-mode overrides
**Warning signs:** Bright green/red boxes in an otherwise dark UI

## Code Examples

### Theme Toggle UI (User Popover 3-Icon Row)
```html
<!-- In _sidebar.html user popover, replace the disabled theme link -->
<div class="popover-theme-row">
  <button class="theme-btn" data-theme-value="light" onclick="setTheme('light')" title="Light">
    <i data-lucide="sun" class="popover-icon"></i>
  </button>
  <button class="theme-btn" data-theme-value="system" onclick="setTheme('system')" title="System">
    <i data-lucide="monitor" class="popover-icon"></i>
  </button>
  <button class="theme-btn" data-theme-value="dark" onclick="setTheme('dark')" title="Dark">
    <i data-lucide="moon" class="popover-icon"></i>
  </button>
</div>
```

### Theme JS Module
```javascript
// theme.js - loaded after other scripts
(function() {
  var THEME_KEY = 'sempkm_theme';

  function getStoredPreference() {
    return localStorage.getItem(THEME_KEY) || 'system';
  }

  function resolveTheme(preference) {
    if (preference === 'dark') return 'dark';
    if (preference === 'light') return 'light';
    // System: check once on load
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function applyTheme(resolved) {
    document.documentElement.setAttribute('data-theme', resolved);

    // Third-party integrations
    switchNinjaTheme(resolved === 'dark');
    switchEditorThemes(resolved === 'dark');
    switchGraphTheme(resolved === 'dark');
    switchHighlightTheme(resolved === 'dark');

    // Update toggle UI active state
    document.querySelectorAll('.theme-btn').forEach(function(btn) {
      btn.classList.toggle('active', btn.dataset.themeValue === getStoredPreference());
    });

    // Dispatch event for any other listeners
    document.dispatchEvent(new CustomEvent('sempkm:theme-changed', {
      detail: { theme: resolved, preference: getStoredPreference() }
    }));
  }

  window.setTheme = function(preference) {
    localStorage.setItem(THEME_KEY, preference);
    applyTheme(resolveTheme(preference));
  };

  // On load, apply stored preference
  // (Anti-FOUC script already set data-theme, but this wires up third-party libs)
  var pref = getStoredPreference();
  applyTheme(resolveTheme(pref));
})();
```

### Command Palette Theme Entries
```javascript
// In workspace.js initCommandPalette(), add theme commands:
{
  id: 'theme-light',
  title: 'Theme: Light',
  section: 'Appearance',
  handler: function() { setTheme('light'); }
},
{
  id: 'theme-dark',
  title: 'Theme: Dark',
  section: 'Appearance',
  handler: function() { setTheme('dark'); }
},
{
  id: 'theme-system',
  title: 'Theme: System',
  section: 'Appearance',
  handler: function() { setTheme('system'); }
}
```

### Styled 403 Error Panel
```html
<!-- 403.html template fragment -->
<div class="error-panel error-panel-403">
  <div class="error-panel-icon">
    <i data-lucide="lock" class="error-panel-lock"></i>
  </div>
  <h2 class="error-panel-title">Access Denied</h2>
  <p class="error-panel-message">
    You don't have permission to access this resource.
    Your current role does not include the required privileges.
  </p>
  <div class="error-panel-actions">
    <a href="/" class="btn btn-primary">Go Home</a>
    <button onclick="history.back()" class="btn btn-secondary">Go Back</button>
  </div>
</div>
```

### Tab Styling Updates (4px radius, teal accent)
```css
/* Rounded tabs with recessed bar */
.tab-bar-workspace {
  background: var(--color-surface-recessed);
}

.workspace-tab {
  border-radius: 4px 4px 0 0;
  border-right: none;
  margin: 0 1px;
}

.workspace-tab.active {
  background: var(--color-surface);
  border-bottom: 2px solid var(--color-accent);
}

/* Close button: hover-only for inactive, always for active */
.workspace-tab .tab-close {
  opacity: 0;
  transition: opacity 0.1s;
}
.workspace-tab:hover .tab-close,
.workspace-tab.active .tab-close {
  opacity: 0.5;
}
.workspace-tab .tab-close:hover {
  opacity: 1;
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@media (prefers-color-scheme)` only | `data-theme` attribute + inline script | ~2020-2021 | Supports user override + system detection |
| Separate dark.css file | CSS custom properties on attribute selectors | ~2019-2020 | Single file, no stylesheet swapping, zero specificity battles |
| Recreating CodeMirror on theme change | Compartment.reconfigure() | CM6 launch (2021) | Preserves editor state, instant switch |
| `light-dark()` CSS function | Limited browser support (~85%) | 2024 | Not ready for production; custom properties are universally supported |

**Deprecated/outdated:**
- `light-dark()` CSS function: While elegant, browser support is ~85% as of early 2026. Stick with attribute selectors.
- `color-scheme: dark light` meta tag: This only affects browser chrome and form controls, not custom UI. Use alongside but not instead of custom properties.

## Open Questions

1. **Exact dark-mode color values**
   - What we know: User wants "softer Dark+" with warmer grays and teal accents
   - What's unclear: Exact hex values for all ~30 token slots
   - Recommendation: Start with VS Code Dark+ palette as base, shift grays warmer (+5 red channel), use teal (#56b6c2) as accent, iterate visually. The token values in theme.css can be fine-tuned after initial implementation.

2. **Auth pages template structure**
   - What we know: There is a base.html that includes the sidebar
   - What's unclear: Whether auth pages (login, setup, invite) use a different base template that would need separate anti-FOUC integration
   - Recommendation: Examine auth templates during planning; the anti-FOUC script should be in every `<head>`

3. **Color contrast accessibility**
   - What we know: WCAG AA requires 4.5:1 contrast ratio for normal text
   - What's unclear: Whether the "softer" dark palette maintains sufficient contrast
   - Recommendation: Verify key combinations (text on surface, muted text on surface, accent on surface) meet WCAG AA after choosing final colors

## Sources

### Primary (HIGH confidence)
- CodeMirror 6 Styling Documentation (codemirror.net/examples/styling/) -- EditorView.theme() with {dark: true}, baseTheme with &dark/&light selectors
- CodeMirror 6 Dynamic Theme Forum Discussion (discuss.codemirror.net/t/4709) -- Compartment pattern for runtime theme switching
- ninja-keys GitHub (github.com/ssleptsov/ninja-keys) -- class="dark" toggle, 20+ CSS custom properties, ::part selectors
- @codemirror/theme-one-dark source (github.com/codemirror/theme-one-dark) -- VS Code Dark+ color palette reference, {dark: true} pattern
- Cytoscape.js Discussion #3188 (github.com/cytoscape/cytoscape.js/discussions/3188) -- No native CSS theming; must use programmatic cy.style() updates

### Secondary (MEDIUM confidence)
- MDN prefers-color-scheme docs (developer.mozilla.org) -- Media query semantics
- highlight.js CDN styles (cdnjs.cloudflare.com) -- github.min.css and github-dark.min.css availability confirmed
- Anti-FOUC inline script pattern -- Multiple sources confirm inline `<script>` in `<head>` before stylesheets as standard approach

### Tertiary (LOW confidence)
- None -- all findings verified with primary or secondary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- All libraries already in the project, dark mode mechanisms documented in official sources
- Architecture: HIGH -- CSS custom property theming is the universally standard approach; anti-FOUC is well-established
- Pitfalls: HIGH -- Known from codebase analysis (430 hardcoded colors) and official library documentation

**Token migration scope estimate:**
- style.css: ~29 hex values (many already use tokens; ~15 remaining hardcoded)
- workspace.css: ~181 hex values (most hardcoded, largest migration effort)
- forms.css: ~56 hex values (moderate migration)
- views.css: ~119 hex values (significant migration)
- Total: ~385 hex + 45 rgba values to audit and convert

**Research date:** 2026-02-23
**Valid until:** 2026-03-23 (stable domain, all libraries well-established)