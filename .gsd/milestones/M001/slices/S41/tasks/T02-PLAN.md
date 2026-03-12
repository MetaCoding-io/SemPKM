# T02: 41-gap-closure-rules-flip-vfs 02

**Slice:** S41 — **Milestone:** M001

## Description

Permanently fix the recurring flip card bleed-through bug and document the fix pattern.

Purpose: The CSS 3D flip card has broken 3 times due to `backface-visibility: hidden` being unreliable across browsers/GPU conditions. This plan adds `display: none` as a bulletproof second layer and changes the JS timeout from 300ms (midpoint) to 600ms (animation end) to prevent timing races. CLAUDE.md gets a pitfall section to prevent a 4th recurrence.
Output: CSS + JS fixes in workspace files, new CLAUDE.md section.

## Must-Haves

- [ ] "Edit form does not show read-only view content bleeding through after flip"
- [ ] "Flip card fix pattern is documented in CLAUDE.md"

## Files

- `frontend/static/css/workspace.css`
- `frontend/static/js/workspace.js`
- `CLAUDE.md`
