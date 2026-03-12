# T03: 13-dark-mode-and-visual-polish 03

**Slice:** S13 — **Milestone:** M001

## Description

Implement rounded tab styling with recessed tab bar and teal accent, and create a styled 403 error panel replacing the current minimal error page.

Purpose: Visual polish items that complete the phase requirements — tabs get a modern rounded look matching VS Code style, and the 403 error page becomes a first-class UI experience with clear messaging and navigation.

Output: Updated tab CSS with rounded corners and accent styling, redesigned 403 page with lock icon and action buttons.

## Must-Haves

- [ ] "Tabs have subtle 4px top border-radius with recessed tab bar background"
- [ ] "Active tab has lighter background matching editor area plus a teal bottom accent line"
- [ ] "Inactive tabs are visually muted/recessed"
- [ ] "Tab close button (x) shows on hover only; active tab always shows close button"
- [ ] "403 Forbidden page displays a styled panel with lock icon, role explanation, Go Home button, and Go Back button"
- [ ] "403 page renders correctly in both light and dark mode"

## Files

- `frontend/static/css/workspace.css`
- `backend/app/templates/errors/403.html`
- `frontend/static/css/theme.css`
