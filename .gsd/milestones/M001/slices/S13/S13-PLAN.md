# S13: Dark Mode And Visual Polish

**Goal:** Create the CSS custom property token system with light and dark theme definitions, the anti-FOUC inline script, the theme toggle UI in the user popover, command palette theme entries, and migrate all hardcoded colors across the four CSS files to use tokens.
**Demo:** Create the CSS custom property token system with light and dark theme definitions, the anti-FOUC inline script, the theme toggle UI in the user popover, command palette theme entries, and migrate all hardcoded colors across the four CSS files to use tokens.

## Must-Haves


## Tasks

- [x] **T01: 13-dark-mode-and-visual-polish 01** `est:8min`
  - Create the CSS custom property token system with light and dark theme definitions, the anti-FOUC inline script, the theme toggle UI in the user popover, command palette theme entries, and migrate all hardcoded colors across the four CSS files to use tokens.

Purpose: Establish the foundational theming infrastructure so every UI element responds to theme changes via CSS custom properties. This is the largest task in the phase -- the ~385 hardcoded hex + 45 rgba values must all become token references.

Output: theme.css with full token set, anti-FOUC script in base.html, theme.js toggle logic, sidebar popover 3-icon row, command palette entries, and all four CSS files migrated to tokens.
- [x] **T02: 13-dark-mode-and-visual-polish 02** `est:2min`
  - Integrate dark mode with all third-party libraries: CodeMirror 6 (Compartment reconfigure), Cytoscape.js (programmatic style rebuild), ninja-keys (class toggle + CSS variables), Split.js (already CSS-tokenized from Plan 01), and highlight.js (stylesheet swap).

Purpose: The base CSS tokens from Plan 01 handle all custom UI elements, but third-party libraries each have their own theming mechanism that must be wired to the theme-changed event.

Output: All third-party components respond to theme switches. Editor stays dark/light matching the rest of the UI.
- [x] **T03: 13-dark-mode-and-visual-polish 03** `est:2min`
  - Implement rounded tab styling with recessed tab bar and teal accent, and create a styled 403 error panel replacing the current minimal error page.

Purpose: Visual polish items that complete the phase requirements — tabs get a modern rounded look matching VS Code style, and the 403 error page becomes a first-class UI experience with clear messaging and navigation.

Output: Updated tab CSS with rounded corners and accent styling, redesigned 403 page with lock icon and action buttons.
- [x] **T04: 13-dark-mode-and-visual-polish 04** `est:2min`
  - Fix three UAT gaps from Phase 13 user acceptance testing: (1) Ctrl+K command palette broken in Firefox, (2) teal accent bleeding onto tab left side plus border-radius clipping, (3) card views lacking distinctive borders.

Purpose: Close all remaining Phase 13 UAT issues so the phase can be marked fully accepted.
Output: Three targeted fixes across workspace.js, views.css, and workspace.css.

## Files Likely Touched

- `frontend/static/css/theme.css`
- `frontend/static/css/style.css`
- `frontend/static/css/workspace.css`
- `frontend/static/css/forms.css`
- `frontend/static/css/views.css`
- `backend/app/templates/base.html`
- `backend/app/templates/components/_sidebar.html`
- `frontend/static/js/theme.js`
- `frontend/static/js/workspace.js`
- `frontend/static/js/editor.js`
- `frontend/static/js/graph.js`
- `frontend/static/js/theme.js`
- `frontend/static/css/theme.css`
- `frontend/static/css/workspace.css`
- `backend/app/templates/errors/403.html`
- `frontend/static/css/theme.css`
- `frontend/static/js/workspace.js`
- `frontend/static/css/views.css`
- `frontend/static/css/workspace.css`
