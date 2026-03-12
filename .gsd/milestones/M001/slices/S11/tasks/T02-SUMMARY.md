---
id: T02
parent: S11
milestone: M001
provides:
  - Mode toggle with Edit/Done button and Ctrl+E shortcut
  - JS midpoint visibility swap for reliable flip animation
  - Unified body predicate handling (model-specific + canonical)
  - Lazy-loaded reference pill popovers matching graph view style
  - Auto-update dcterms:modified on save
  - Collapsible property sections in read and edit views
  - Type badge in toolbar with click-to-copy IRI
  - Fresh read face on flip back (no stale data)
requires: []
affects: []
key_files: []
key_decisions: []
patterns_established: []
observability_surfaces: []
drill_down_paths: []
duration: interactive-session
verification_result: passed
completed_at: 2026-02-23
blocker_discovered: false
---
# T02: 11-read-only-object-view 02

**# Phase 11 Plan 02: Mode Toggle, Save Flow, and Polish Summary**

## What Happened

# Phase 11 Plan 02: Mode Toggle, Save Flow, and Polish Summary

**Mode toggle with flip animation, save flow fixes, body predicate unification, reference popovers, and UI polish through iterative human verification**

## Performance

- **Duration:** Interactive session (~2 hours with human verification)
- **Completed:** 2026-02-23
- **Tasks:** 3 planned + 12 bug fixes/enhancements during checkpoint
- **Files modified:** 12

## Accomplishments

### Core Features (from plan)
- Edit/Done toggle button with Ctrl+E keyboard shortcut
- Smooth CSS 3D flip animation with JS midpoint visibility swap
- Unsaved changes confirmation dialog on mode switch
- Deferred edit mode initialization (CodeMirror/Split.js loaded on first flip)
- Body editor maximize/restore toggle via Split.js

### Bug Fixes (from checkpoint verification)
- Fixed Jinja2 variable scoping bug (namespace pattern for loop-scoped has_values)
- Fixed backface-visibility failure with JS setTimeout midpoint swap (5 iterations to solve)
- Fixed empty edit form fields (single-valued props receiving list values)
- Fixed save flow (htmx form submission + hx-target scoping)
- Fixed saveCurrentObject not exported globally
- Fixed 500 error on tooltip endpoint (missing templates variable)

### Enhancements (from checkpoint feedback)
- Unified body predicates: model-specific body properties detected and used consistently
- Lazy-loaded reference pill popovers matching graph view style
- Auto-update dcterms:modified on property and body saves
- Exclude Body/Created/Modified from edit form
- DateTime values properly formatted for datetime-local inputs
- Fresh read face content on flip back (no stale data)
- Markdown re-rendered after read face refresh
- Collapsible properties section in read view
- Collapse/expand all toggle in edit form (groups default collapsed)
- Type badge in toolbar (replaces raw IRI display)
- Green Edit button, red Save button
- Darker form input borders for visibility
- Removed redundant Save Changes button from edit form
- Removed HR separator between properties and markdown
- Cards view recognizes model-specific body predicates (300 char snippets)

## Task Commits

1. **Plan tasks (mode toggle, maximize, deferred init)** - `df3137e`, `c02d19d`
2. **Jinja2 scoping + flip animation fix** - `5ff5e58`
3. **Checkpoint fixes (all enhancements)** - `d99ff0c`

## Deviations from Plan

- **Backface-visibility approach abandoned** — CSS backface-visibility was broken by DOM context (overflow, stacking contexts). After 5 iterations, replaced with JS setTimeout at animation midpoint. More reliable across browsers.
- **Body predicate unification not in plan** — Discovered during testing that model-specific body predicates (urn:sempkm:model:basic-pkm:body) and canonical predicate (urn:sempkm:body) were divergent. Added detection, unified save path, and cleanup logic.
- **Significant polish beyond plan scope** — Type badge, collapsible sections, auto-modified timestamps, and cards view fixes were all added during interactive checkpoint verification.

## Issues Encountered

- Jinja2 `{% set %}` inside `{% for %}` creates loop-scoped variables, not modifying outer scope — required namespace() pattern
- CSS backface-visibility unreliable in complex DOM contexts — fallback to JS visibility swap
- htmx form hx-target="#editor-area" destroyed the flip container on save — changed to "closest .object-form-section"
- Two different body predicates in the system caused confusion — unified with detection logic

---
*Phase: 11-read-only-object-view*
*Completed: 2026-02-23*
