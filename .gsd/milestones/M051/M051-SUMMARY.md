---
id: M051
title: "Workspace UX Improvements"
status: complete
completed_at: 2026-04-06T01:34:18.850Z
key_decisions:
  - D391: Strip ' Shape' suffix in backend get_types() rather than client-side — fixes all downstream consumers at once
  - Used mousedown instead of click for dropdown dismiss — fires before focus shift so dropdown clears before click target receives focus
  - Used position:fixed with containing-block correction instead of appending to document.body — simpler and preserves htmx targeting
  - Used native <dialog> element with existing .confirm-dialog styling for input dialogs — consistent with existing workspace patterns
  - Fixed edge hover popover alongside node hover since both had identical panelRect positioning bug
key_files:
  - frontend/static/js/dropdown-dismiss.js
  - frontend/static/js/workspace.js
  - frontend/static/css/workspace.css
  - backend/app/services/shapes.py
  - backend/app/vfs/mount_router.py
  - backend/app/templates/browser/object_tab.html
  - backend/app/templates/browser/object_tab_app.html
  - backend/app/templates/admin/model_ontology_diagram.html
  - backend/app/templates/base.html
  - backend/app/templates/browser/workspace.html
lessons_learned:
  - dockview uses contain:layout which creates a new containing block for position:fixed elements — coordinates must be adjusted relative to this containing block, not the viewport
  - mousedown fires before focus shift while click fires after — for dismiss-on-click-outside patterns, mousedown is correct so the dropdown clears before the click target receives focus
  - MutationObserver on document.body with subtree:true is effective for detecting dynamically-populated dropdowns from htmx swaps, but must skip builder dropdowns that render in modal containers
---

# M051: Workspace UX Improvements

**Fixed six workspace interaction paper-cuts: dropdown dismiss/escape, stale labels, object tab refresh, command palette scroll jump, persona/layout input dialogs, and admin graph popover positioning.**

## What Happened

M051 addressed a batch of workspace-level UX annoyances that individually were minor but collectively made the workspace feel unpolished.

**S01 (Autocomplete Dismiss & Dropdown Escape)** created `dropdown-dismiss.js` — a global document-level handler that dismisses all `.suggestions-dropdown` elements on click-outside (via mousedown, not click, to fire before focus shift) and Escape. A MutationObserver detects when htmx populates dropdowns and repositions them to `position:fixed` so they escape dockview panel overflow clipping. A non-obvious discovery: dockview's `contain:layout` creates a new containing block for fixed-position elements, requiring coordinate correction via `_getFixedContainingBlockRect()`. Scroll and resize listeners dismiss orphaned dropdowns.

**S02 (Explorer & Nav Cleanup + Object Tab Refresh)** made four targeted fixes: (1) added `.removesuffix(' Shape')` in `get_types()` so the explorer shows 'Project' instead of 'Project Shape', (2) replaced the stale event log placeholder with 'Loading event log...', (3) enriched VFS mount dropdown labels with `dcterms:title` via OPTIONAL SPARQL, and (4) added a refresh button to object tabs using `refreshObjectTab()` delegating to existing `loadObjectContent()`.

**S03 (Command Palette & Persona/Layout Dialog UX)** fixed the command palette scroll jump by saving/restoring `document.body.style.overflow` in the ninja-keys open/close monkey-patch. Replaced the fragile shadow-DOM input hack for persona-create and layout-save-as with a reusable `showInputDialog(title, placeholder, onConfirm, confirmText)` function using native `<dialog>`. Fixed admin graph popover positioning by removing erroneous `panelRect` offset subtraction from both node and edge hover handlers.

All three slices completed without blockers or replans. 10 files changed with 388 insertions.

## Success Criteria Results

Success criteria are derived from the "After this" column of each slice:

- **S01: Click outside dismisses suggestions** — ✅ Met. `dropdown-dismiss.js` mousedown listener dismisses all open `.suggestions-dropdown` elements when click target is outside the dropdown and its input wrapper.
- **S01: Escape dismisses suggestions** — ✅ Met. Keydown listener on Escape clears all open dropdowns.
- **S01: Dropdown visible outside overflow** — ✅ Met. MutationObserver switches dropdowns to `position:fixed` with containing-block correction, escaping dockview panel overflow clipping.
- **S02: Explorer shows 'Project' not 'Project Shape'** — ✅ Met. `shapes.py get_types()` applies `.removesuffix(' Shape')` at the source.
- **S02: Event Log tab shows actual content** — ✅ Met. Stale placeholder text replaced with 'Loading event log...' matching the htmx lazy-load behavior.
- **S02: VFS mount dropdown has clean labels** — ✅ Met. SPARQL query fetches `dcterms:title` with fallback to modelId.
- **S02: Object tab has refresh button** — ✅ Met. `refresh-cw` Lucide icon button added to both `object_tab.html` and `object_tab_app.html`, wired to `refreshObjectTab()`.
- **S03: Persona create via input dialog** — ✅ Met. `showInputDialog('Create Persona', ...)` replaces shadow-DOM hack.
- **S03: Layout save-as via input dialog** — ✅ Met. `showInputDialog('Save Layout', ...)` replaces shadow-DOM hack.
- **S03: Command palette opens without scroll jump** — ✅ Met. `_savedOverflow` mechanism freezes body overflow during palette open.
- **S03: Admin graph popover positions near the node** — ✅ Met. panelRect subtraction removed, viewport-relative positioning used.

## Definition of Done Results

- **All slices complete** — ✅ S01, S02, S03 all marked ✅ in roadmap
- **All slice summaries exist** — ✅ S01-SUMMARY.md, S02-SUMMARY.md, S03-SUMMARY.md all present
- **Code changes on integration branch** — ✅ 10 files, 388 insertions verified via `git diff --stat 7b5958e2..HEAD -- ':!.gsd/'`
- **No cross-slice integration issues** — ✅ S01 (dropdown-dismiss.js) operates independently of S02/S03 changes; no shared state between slices
- **No blockers discovered** — ✅ All three slices completed without replans

## Requirement Outcomes

No requirements changed status during M051. R001 (lazy-loaded panels) remains validated from M049. This milestone addressed UX paper-cuts without touching requirement-level functionality.

## Deviations

S01/T02 added _getFixedContainingBlockRect() to handle dockview's contain:layout — not anticipated by the plan. S03/T02 fixed edge hover popover in addition to node hover — plan only mentioned node hover but both had the same bug. No CSS changes to forms.css were needed (S01 plan expected some).

## Follow-ups

None.
