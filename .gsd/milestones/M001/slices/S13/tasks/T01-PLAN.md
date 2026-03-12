# T01: 13-dark-mode-and-visual-polish 01

**Slice:** S13 — **Milestone:** M001

## Description

Create the CSS custom property token system with light and dark theme definitions, the anti-FOUC inline script, the theme toggle UI in the user popover, command palette theme entries, and migrate all hardcoded colors across the four CSS files to use tokens.

Purpose: Establish the foundational theming infrastructure so every UI element responds to theme changes via CSS custom properties. This is the largest task in the phase -- the ~385 hardcoded hex + 45 rgba values must all become token references.

Output: theme.css with full token set, anti-FOUC script in base.html, theme.js toggle logic, sidebar popover 3-icon row, command palette entries, and all four CSS files migrated to tokens.

## Must-Haves

- [ ] "User can click Sun/Monitor/Moon icons in user popover to switch between Light/System/Dark themes"
- [ ] "Theme preference persists in localStorage and survives page reload with zero flash of wrong theme"
- [ ] "Dark mode surfaces use warmer grays with teal/cyan accents (softer VS Code Dark+ palette)"
- [ ] "Light mode uses the same CSS custom property token system as dark mode"
- [ ] "All panel edges (sidebar, editor, tab bar, right panel) have visible 1px borders in dark mode"
- [ ] "Theme can also be toggled via command palette (Theme: Light / Theme: Dark / Theme: System)"

## Files

- `frontend/static/css/theme.css`
- `frontend/static/css/style.css`
- `frontend/static/css/workspace.css`
- `frontend/static/css/forms.css`
- `frontend/static/css/views.css`
- `backend/app/templates/base.html`
- `backend/app/templates/components/_sidebar.html`
- `frontend/static/js/theme.js`
- `frontend/static/js/workspace.js`
