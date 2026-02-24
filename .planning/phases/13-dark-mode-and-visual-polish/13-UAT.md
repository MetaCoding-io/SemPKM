---
status: diagnosed
phase: 13-dark-mode-and-visual-polish
source: [13-01-SUMMARY.md, 13-02-SUMMARY.md, 13-03-SUMMARY.md]
started: 2026-02-24T03:20:00Z
updated: 2026-02-24T03:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Theme Toggle via User Popover
expected: Click your avatar/user icon in the sidebar to open the popover. You should see a row of 3 theme icons (Sun/Monitor/Moon). Clicking each one switches the theme immediately with a subtle crossfade. Active icon has accent highlight.
result: pass

### 2. Theme Toggle via Command Palette
expected: Press Ctrl+K to open the command palette. Search for "Theme". You should see three entries: "Theme: Light", "Theme: Dark", "Theme: System Default". Selecting one switches the theme, same as using the popover icons.
result: issue
reported: "The command palette no longer comes up. Ctrl+K does something in FF now"
severity: major

### 3. Theme Persistence Across Reload
expected: Set dark mode via popover or command palette. Hard refresh the page (Ctrl+F5). The page should load directly in dark mode with zero flash of white/light theme — no FOUC.
result: pass

### 4. Dark Mode — Sidebar and Layout
expected: In dark mode, the sidebar should have dark surfaces with readable light text. Borders between sidebar and content area should be visible (not lost in darkness). The overall feel should be warm dark grays, not pure black.
result: pass

### 5. Dark Mode — Tab Bar and Tabs
expected: In dark mode with multiple tabs open: tab bar has a recessed (darker) background. Active tab is lighter with a teal accent bottom line. Inactive tabs blend with the recessed bar. Tabs have subtle rounded top corners (4px). Close button (x) is hidden on inactive tabs, appears on hover.
result: issue
reported: "The teal accent appears at the bottom but also sometimes the left side. The tabs aren't really rounded either"
severity: cosmetic

### 6. Dark Mode — Forms and Buttons
expected: Open any SHACL form (edit an object). Form fields, labels, buttons, validation states, and autocomplete dropdowns should all render with dark backgrounds and light text. No white "holes" or unthemed elements.
result: pass

### 7. Dark Mode — Views (Tables, Cards)
expected: Browse objects in table view and card view. Both should render with dark surfaces, light text, and visible borders. Pagination controls, filter dropdowns, and sort headers should all be themed.
result: issue
reported: "Cards need to have a more distinctive border in both dark and light mode"
severity: cosmetic

### 8. Dark Mode — CodeMirror Editor
expected: Open an object with a Markdown body to get the CodeMirror editor. In dark mode: editor background should be dark, text light, gutters dark, cursor/caret teal. Toggle theme — editor switches without losing your cursor position or undo history (type something, switch theme, undo should still work).
result: pass

### 9. Dark Mode — Cytoscape Graph
expected: Open a graph view. In dark mode: graph background is dark, node labels are light, edges are muted gray, selected node border is teal. Toggle back to light — graph returns to light colors. No errors in console.
result: pass

### 10. Dark Mode — Command Palette Styling
expected: In dark mode, open the command palette (Ctrl+K). The ninja-keys modal should render with dark background, light text, and themed search input. Not a white box floating over a dark UI.
result: pass

### 11. Light Mode — Visual Parity
expected: Switch back to light mode. The UI should look essentially identical to how it looked before dark mode was added — same colors, same feel, just now powered by CSS tokens instead of hardcoded values. No obvious regressions.
result: pass

### 12. 403 Error Page
expected: Navigate to a page you don't have permission to access (or visit a protected admin route while logged out). You should see a styled card panel with a lock icon, "Access Denied" title, role explanation text, a "Go Home" button (teal/accent), and a "Go Back" button (outline style). If you had dark mode set, the 403 page should also render in dark mode.
result: skipped
reason: Admin routes redirect to login page instead of showing 403. Noted login page needs border around box in light mode.

## Summary

total: 12
passed: 8
issues: 3
pending: 0
skipped: 1

## Gaps

- truth: "Command palette opens via Ctrl+K and shows theme entries"
  status: failed
  reason: "User reported: The command palette no longer comes up. Ctrl+K does something in FF now"
  severity: major
  test: 2
  root_cause: "hotkeys-js (used by ninja-keys) silently ignores keydown events when focus is on INPUT/TEXTAREA/SELECT. Firefox then intercepts unhandled Ctrl+K to focus its search bar. App has no Ctrl+K case in initKeyboardShortcuts() to preventDefault."
  artifacts:
    - path: "frontend/static/js/workspace.js"
      issue: "initKeyboardShortcuts() missing Ctrl+K case with preventDefault"
    - path: "backend/app/templates/base.html"
      issue: "ninja-keys CDN reference is unpinned (no version)"
  missing:
    - "Add Ctrl+K case to initKeyboardShortcuts() keydown handler that calls preventDefault and ninja-keys .open()"
  debug_session: ".planning/debug/firefox-ctrlk-ninja-keys.md"

- truth: "Active tab has teal bottom accent line only, tabs have 4px rounded top corners"
  status: failed
  reason: "User reported: The teal accent appears at the bottom but also sometimes the left side. The tabs aren't really rounded either"
  severity: cosmetic
  test: 5
  root_cause: "Two bugs: (1) views.css .workspace-tab.view-tab has border-left: 2px solid var(--color-primary) that bleeds on all view tabs. (2) Tab bar overflow-y:hidden + align-items:flex-end clips 4px border-radius — only 2px headroom between tab top and clip boundary."
  artifacts:
    - path: "frontend/static/css/views.css"
      issue: ".workspace-tab.view-tab adds permanent border-left: 2px solid teal, never removed"
    - path: "frontend/static/css/workspace.css"
      issue: "overflow-y:hidden on .tab-bar-workspace clips the 4px top border-radius"
  missing:
    - "Remove border-left from .workspace-tab.view-tab in views.css"
    - "Add padding-top: 4px to .tab-bar-workspace so border-radius has room above clip boundary"
  debug_session: ".planning/debug/tab-accent-bleed-and-border-radius.md"

- truth: "Card views have distinctive visible borders in both dark and light mode"
  status: failed
  reason: "User reported: Cards need to have a more distinctive border in both dark and light mode"
  severity: cosmetic
  test: 7
  root_cause: "Flip card faces (.flip-card-front, .flip-card-back, .card-focus-front, .card-focus-back) have no border — rely only on box-shadow: var(--shadow) which is too faint (8% opacity light, 30% dark). The .card class in style.css already has the correct pattern: border + shadow."
  artifacts:
    - path: "frontend/static/css/views.css"
      issue: "Card face selectors missing border: 1px solid var(--color-border)"
  missing:
    - "Add border: 1px solid var(--color-border) to .flip-card-front, .flip-card-back, .card-focus-front, .card-focus-back"
  debug_session: ".planning/debug/card-view-borders-not-distinctive.md"
