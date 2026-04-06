---
id: S01
parent: M051
milestone: M051
provides:
  - Global dismiss behavior for all .suggestions-dropdown elements
  - SemPKM.dismissAllDropdowns() programmatic API
  - Overflow-escape repositioning for suggestion dropdowns in dockview panels
requires:
  []
affects:
  []
key_files:
  - frontend/static/js/dropdown-dismiss.js
  - backend/app/templates/base.html
key_decisions:
  - Used mousedown instead of click for dismiss — fires before focus shift so dropdown clears before click target receives focus
  - MutationObserver on document.body with subtree:true to detect dropdown population from htmx swaps dynamically
  - Used position:fixed with containing-block correction instead of appending to document.body — simpler and preserves htmx targeting
patterns_established:
  - Global dropdown dismiss via document-level mousedown + Escape listeners in dropdown-dismiss.js — any new suggestion dropdown using .suggestions-dropdown class gets dismiss behavior automatically
  - position:fixed overflow escape with _getFixedContainingBlockRect() containing-block correction — reusable for any fixed-position overlay inside dockview panels
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M051/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M051/slices/S01/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-06T01:03:11.688Z
blocker_discovered: false
---

# S01: Autocomplete Dismiss & Dropdown Escape

**Added global dropdown-dismiss.js with click-outside/Escape dismiss and position:fixed repositioning that escapes dockview overflow clipping, covering all suggestion dropdowns (reference fields, tag fields, builder fields).**

## What Happened

This slice addressed two related UX issues with suggestion dropdowns across the workspace:

**T01 — Dismiss behavior:** Created `frontend/static/js/dropdown-dismiss.js` as an IIFE with two document-level listeners. A `mousedown` listener (not `click` — fires before focus shift) dismisses all non-empty `.suggestions-dropdown` elements when the click target is outside the dropdown and its associated input wrapper (`.reference-field`, `.tag-autocomplete-field`). A `keydown` listener clears all open dropdowns on Escape without calling `preventDefault()`, so Escape still bubbles for modal close. Exports `SemPKM.dismissAllDropdowns` for programmatic use. Added script tag to `base.html`.

**T02 — Overflow escape:** Extended the same file with a `MutationObserver` on `document.body` (subtree:true) that detects when htmx populates a `.suggestions-dropdown`. When children appear, `_repositionDropdown()` switches the dropdown to `position:fixed` with coordinates computed from the input's `getBoundingClientRect()`. If less than 220px of viewport space exists below the input, the dropdown flips above. A non-obvious discovery: dockview uses `contain:layout` which creates a new containing block for `position:fixed` elements — coordinates had to be adjusted relative to this containing block via `_getFixedContainingBlockRect()`. Added scroll (capture phase) and resize listeners that dismiss all dropdowns to prevent orphaned fixed-position elements. Builder dropdowns (`.builder-suggestions`) are explicitly skipped since they render in modal-like containers that don't clip.

All behavior was verified in-browser against running dockview panels with reference and tag fields at various positions.

## Verification

Slice-level verification checks all passed:
1. `rg 'dismissAllDropdowns' frontend/static/js/dropdown-dismiss.js` — 6 matches (function def, 4 call sites, export)
2. `rg 'dropdown-dismiss' backend/app/templates/base.html` — script tag present
3. `rg '_repositionDropdown' frontend/static/js/dropdown-dismiss.js` — function def + call site
4. `node -c frontend/static/js/dropdown-dismiss.js` — syntax valid
5. Browser verification: click-outside dismiss, Escape dismiss, suggestion selection still works, flip-above for near-bottom fields, scroll dismiss, style reset on dismiss

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

T02 added `_getFixedContainingBlockRect()` to handle dockview's `contain:layout` creating a new containing block for `position:fixed` — not anticipated by the plan. Also added `style.right='auto'` to override a CSS `right:0` conflict. No CSS changes to forms.css were needed (plan expected some).

## Known Limitations

None.

## Follow-ups

None.

## Files Created/Modified

- `frontend/static/js/dropdown-dismiss.js` — New file — IIFE with document-level mousedown/Escape dismiss, MutationObserver-driven position:fixed repositioning with flip-above and containing-block correction
- `backend/app/templates/base.html` — Added script tag for dropdown-dismiss.js between column-prefs.js and sempkm-shims.js
