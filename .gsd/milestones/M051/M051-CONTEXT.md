---
depends_on: []
---

# M051: Workspace UX Improvements

**Gathered:** 2026-04-05
**Status:** Ready for planning

## Project Description

Fix workspace-level interaction issues discovered during the feature tour: stale placeholder text, autocomplete dropdowns that won't dismiss, command palette scroll bug, explorer hover actions, object tab refresh button, and persona/layout UX.

## Why This Milestone

These are paper-cut issues that individually are minor but collectively make the workspace feel unpolished. Autocomplete dropdowns that trap focus, stale "Phase 16" text, missing hover actions, and broken persona creation all erode user confidence.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Click outside an autocomplete dropdown to dismiss it, or press Escape
- See type names without " Shape" suffix in the explorer
- Hover over objects in the explorer to see action buttons (info tooltip, delete)
- Create a persona via a proper name input dialog (not the "type above then select" pattern)
- Click a refresh button on any object tab to reload it
- See the Event Log tab working (no "Phase 16" placeholder)

### Entry point / environment

- Entry point: http://localhost:4000/browser/
- Environment: Docker Compose dev stack
- Live dependencies involved: none

## Completion Class

- Contract complete means: E2E tests for autocomplete dismiss, explorer hover actions, refresh button
- Integration complete means: all interaction fixes work together without regressions
- Operational complete means: none

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- Open edit form → click a relation search field → type → click outside → dropdown dismissed
- Tag autocomplete dropdown renders fully visible (not clipped)
- Explorer shows "Project" not "Project Shape"
- Hover over an object in explorer → see info and delete buttons
- F1 → Persona: Create New → input dialog appears
- Object tab → click refresh icon → tab content reloads
- Bottom panel → Event Log tab → see actual event log (not placeholder)

## Risks and Unknowns

- **Autocomplete dismiss (#25)** — may need click-outside listener on document.body, which can conflict with other click handlers
- **Tag dropdown clipping (#26)** — needs to escape container's overflow, likely requires appending to document.body with position:fixed (same pattern as dockview popovers)
- **Command palette scroll (#24)** — ninja-keys shadow DOM makes debugging difficult
- **Persona/Layout merge (#35)** — conceptual question about whether to merge or just clarify the UX

## Existing Codebase / Prior Art

- `frontend/static/js/workspace.js` — autocomplete rendering, persona commands, explorer tree rendering
- `backend/app/templates/forms/_field.html` — autocomplete dropdown HTML
- `frontend/static/js/workspace-layout.js` — dockview panel management, tab creation
- `backend/app/templates/browser/workspace.html` — explorer section headers, bottom panel tabs

## Scope

### In Scope

- **#10** Replace "Event Log Explorer — coming in Phase 16" with actual event log content
- **#11** Remove " Shape" suffix from type names in explorer (use rdfs:label of the target class, not the shape)
- **#12** Clean up OBJECTS dropdown — human-readable model names, remove broken VFS Mounts entry
- **#24** Fix command palette scroll jump bug
- **#25** Autocomplete dropdowns dismiss on click-outside and Escape
- **#26** Tag autocomplete dropdown escapes container boundary (append to document.body)
- **#33, #34** Persona create / Layout save — replace "type above" pattern with proper input dialog
- **#35** Clarify or merge Personas vs Layouts (at minimum, improve labels and help text)
- **#42** Fix model detail graph popover positioning (far from node)
- **#65** Add refresh button to object tab header (cycle icon next to star)

### Out of Scope / Non-Goals

- Browser history integration (#27) — that's M055 (separate research milestone)
- Explorer composable filter/group/sort — that's M054
- Visual styling — that's M052

## Open Questions

- For #35, should we merge Personas and Layouts into one concept, or keep them separate with better labeling? Leaning toward merge — call them "Workspaces" with server-side storage.
