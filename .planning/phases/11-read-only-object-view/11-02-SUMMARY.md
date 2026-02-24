---
phase: 11-read-only-object-view
plan: 02
subsystem: ui
tags: [flip-animation, mode-toggle, save-flow, body-predicate-unification, tooltip-popover, cards-view, collapsible-sections]

# Dependency graph
requires:
  - phase: 11-read-only-object-view
    plan: 01
    provides: read-only template, flip container, reference pills, markdown rendering
provides:
  - Mode toggle with Edit/Done button and Ctrl+E shortcut
  - JS midpoint visibility swap for reliable flip animation
  - Unified body predicate handling (model-specific + canonical)
  - Lazy-loaded reference pill popovers matching graph view style
  - Auto-update dcterms:modified on save
  - Collapsible property sections in read and edit views
  - Type badge in toolbar with click-to-copy IRI
  - Fresh read face on flip back (no stale data)
affects: [12-sidebar-and-navigation, 13-dark-mode-visual-polish, 14-split-panes]

# Tech tracking
tech-stack:
  added: []
  patterns: [JS midpoint visibility swap, body predicate detection, lazy popover with cache, read face refresh on flip back]

key-files:
  created:
    - backend/app/templates/browser/ref_tooltip.html
  modified:
    - backend/app/browser/router.py
    - backend/app/commands/handlers/body_set.py
    - backend/app/commands/schemas.py
    - backend/app/templates/browser/object_read.html
    - backend/app/templates/browser/object_tab.html
    - backend/app/templates/forms/_field.html
    - backend/app/templates/forms/_group.html
    - backend/app/templates/forms/object_form.html
    - backend/app/views/service.py
    - frontend/static/css/workspace.css
    - frontend/static/js/workspace.js

key-decisions:
  - "JS setTimeout at animation midpoint (300ms of 600ms) for face visibility swap -- CSS backface-visibility broken by DOM context"
  - "Body predicate unification: detect SHACL 'Body' property by name, use its path for save, clean up canonical urn:sempkm:body"
  - "Lazy-loaded ref-pill popovers reuse graph-popover CSS classes for visual consistency"
  - "dcterms:created and dcterms:modified excluded from edit form, modified auto-updated on save"
  - "Form groups default collapsed in edit mode to save space"

patterns-established:
  - "Body predicate detection: scan form.properties for name.lower()=='body', redirect to body_text and body_predicate"
  - "Read face refresh: fetch fresh HTML on flip-back, extract .object-face-read, re-trigger renderMarkdownBody"
  - "Type badge pattern: resolve type label, show as pill in toolbar with hover=IRI, click=copy"

requirements-completed: [VIEW-02, VIEW-04]

# Metrics
duration: interactive-session
completed: 2026-02-23
---

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
