# T02: 13-dark-mode-and-visual-polish 02

**Slice:** S13 — **Milestone:** M001

## Description

Integrate dark mode with all third-party libraries: CodeMirror 6 (Compartment reconfigure), Cytoscape.js (programmatic style rebuild), ninja-keys (class toggle + CSS variables), Split.js (already CSS-tokenized from Plan 01), and highlight.js (stylesheet swap).

Purpose: The base CSS tokens from Plan 01 handle all custom UI elements, but third-party libraries each have their own theming mechanism that must be wired to the theme-changed event.

Output: All third-party components respond to theme switches. Editor stays dark/light matching the rest of the UI.

## Must-Haves

- [ ] "CodeMirror editor switches between light and dark themes when the user toggles the theme, without losing cursor position or undo history"
- [ ] "Cytoscape graph nodes, edges, and background update to dark colors when theme switches"
- [ ] "ninja-keys command palette renders with correct dark/light styling"
- [ ] "Split.js gutters render with theme-appropriate colors"
- [ ] "highlight.js code blocks in read-only Markdown view switch between github and github-dark stylesheets"

## Files

- `frontend/static/js/editor.js`
- `frontend/static/js/graph.js`
- `frontend/static/js/theme.js`
- `frontend/static/css/theme.css`
