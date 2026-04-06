---
id: T01
parent: S03
milestone: M051
key_files:
  - frontend/static/js/workspace.js
  - frontend/static/css/workspace.css
key_decisions:
  - Used <dialog> element with existing .confirm-dialog base styling for input dialogs, keeping visual consistency
duration: 
verification_result: passed
completed_at: 2026-04-06T01:28:36.677Z
blocker_discovered: false
---

# T01: Fixed command palette scroll jump by freezing body overflow on open, replaced shadow-DOM input hacks for persona-create and layout-save-as with proper showInputDialog() modal dialogs

**Fixed command palette scroll jump by freezing body overflow on open, replaced shadow-DOM input hacks for persona-create and layout-save-as with proper showInputDialog() modal dialogs**

## What Happened

Three coordinated changes: (1) Added _savedOverflow to ninja-keys open/close patch to prevent scrollIntoView() page jump by setting body overflow to hidden while palette is open. (2) Created reusable showInputDialog(title, placeholder, onConfirm, confirmText) function using <dialog> element with .confirm-dialog styling, text input, Enter/Escape handling, exported on window.SemPKM. (3) Removed persona-create-confirm and layout-save-confirm child entries that extracted text from ninja-keys shadow DOM, replaced with handlers that close palette and open the new input dialog.

## Verification

All grep-based verification checks pass: persona-create-confirm count 0, layout-save-confirm count 0, showInputDialog present (4 occurrences), _savedOverflow present (3 occurrences), btn-primary present in CSS (6 lines).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -c 'persona-create-confirm' ... && grep -c 'layout-save-confirm' ... && grep -q 'showInputDialog' ... && grep -q '_savedOverflow' ... && grep -q 'btn-primary' ... && echo 'PASS'` | 0 | ✅ pass | 80ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/workspace.js`
- `frontend/static/css/workspace.css`
