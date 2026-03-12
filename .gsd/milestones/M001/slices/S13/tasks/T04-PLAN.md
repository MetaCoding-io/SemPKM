# T04: 13-dark-mode-and-visual-polish 04

**Slice:** S13 — **Milestone:** M001

## Description

Fix three UAT gaps from Phase 13 user acceptance testing: (1) Ctrl+K command palette broken in Firefox, (2) teal accent bleeding onto tab left side plus border-radius clipping, (3) card views lacking distinctive borders.

Purpose: Close all remaining Phase 13 UAT issues so the phase can be marked fully accepted.
Output: Three targeted fixes across workspace.js, views.css, and workspace.css.

## Must-Haves

- [ ] "Ctrl+K opens the command palette in Firefox (and all browsers)"
- [ ] "Active tab has teal bottom accent only, no left border bleed on view tabs"
- [ ] "Tabs have visible rounded top corners (not clipped by tab bar overflow)"
- [ ] "Card views have distinctive borders in both dark and light mode"

## Files

- `frontend/static/js/workspace.js`
- `frontend/static/css/views.css`
- `frontend/static/css/workspace.css`
