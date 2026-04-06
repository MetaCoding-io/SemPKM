---
id: S03
parent: M051
milestone: M051
provides:
  - showInputDialog() function on window.SemPKM for reuse by future commands needing text input
requires:
  []
affects:
  []
key_files:
  - frontend/static/js/workspace.js
  - frontend/static/css/workspace.css
  - backend/app/templates/admin/model_ontology_diagram.html
key_decisions:
  - Used native <dialog> element with existing .confirm-dialog styling for input dialogs — consistent with existing confirm dialog pattern
  - Fixed edge hover popover alongside node hover since both had identical panelRect positioning bug
patterns_established:
  - showInputDialog(title, placeholder, onConfirm, confirmText) — reusable input dialog exported on window.SemPKM for any future command that needs a single text input from the user
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M051/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M051/slices/S03/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-06T01:31:12.106Z
blocker_discovered: false
---

# S03: Command Palette & Persona/Layout Dialog UX

**Fixed command palette scroll jump, replaced shadow-DOM input hacks with proper modal dialogs for persona-create and layout-save-as, and fixed admin graph popover positioning.**

## What Happened

Two tasks addressed three UX paper-cuts in the workspace.

**T01 — Command palette scroll jump + input dialogs.** The ninja-keys component calls `scrollIntoView()` on highlighted actions, which propagated to `document.body` and caused visible page jumps. Fixed by saving and restoring `document.body.style.overflow` (set to `hidden`) in the existing open/close monkey-patch. Additionally, the persona-create and layout-save-as commands used an antipattern where users typed a name into the ninja-keys search field and selected a "confirm" child entry that extracted text from the shadow DOM. This was fragile and confusing. Replaced with a reusable `showInputDialog(title, placeholder, onConfirm, confirmText)` function that opens a native `<dialog>` with a text input, using the existing `.confirm-dialog` styling plus a new `.btn-primary` class. Both commands now close the palette and open the input dialog. The `persona-create-confirm` and `layout-save-confirm` child entries were deleted entirely.

**T02 — Admin graph popover positioning.** The ontology diagram popover (`.graph-popover`) has `position: fixed` in CSS but the JS computed panel-relative coordinates by subtracting `panelRect` offsets — double-transforming the position. Removed all `panelRect` subtraction from both node hover (`showPopover`) and edge hover (setTimeout callback), switched overflow boundary checks from panel bounds to `window.innerWidth`/`window.innerHeight`. The edge hover had the identical bug even though the plan only mentioned nodes — both were fixed.

## Verification

T01 verification: grep confirms persona-create-confirm count 0, layout-save-confirm count 0, showInputDialog present (4 occurrences), _savedOverflow present (3 occurrences), btn-primary in CSS (6 lines). T02 verification: grep confirms zero panelRect references in positioning code, containerRect.left + pos present for viewport-relative coords, window.innerWidth present for viewport overflow checks.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

T02 fixed the edge hover popover in addition to the node hover — the plan only specified the showPopover function but an identical panelRect bug existed in the edge hover callback.

## Known Limitations

None.

## Follow-ups

None.

## Files Created/Modified

- `frontend/static/js/workspace.js` — Added _savedOverflow scroll-jump fix, showInputDialog() function, rewired persona-create and layout-save-as commands to use input dialogs, deleted shadow-DOM confirm child entries
- `frontend/static/css/workspace.css` — Added .btn-primary and .confirm-dialog input[type=text] styles for input dialog
- `backend/app/templates/admin/model_ontology_diagram.html` — Removed panelRect offset subtraction from node and edge hover popover positioning, switched overflow checks to viewport bounds
