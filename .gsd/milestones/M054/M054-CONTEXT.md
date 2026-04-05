---
depends_on: [M051]
---

# M054: Explorer Composable Filter/Group/Sort

**Gathered:** 2026-04-05
**Status:** Ready for planning

## Project Description

Replace the flat OBJECTS dropdown with a composable explorer where filtering, grouping, and sorting are independent stackable layers. Give users the power to define how objects are organized in the explorer — like VFS MountSpec strategies but for the object tree.

## Why This Milestone

The current OBJECTS section has a flat dropdown with raw model IDs (`basic-pkm (by-type)`) and a broken VFS Mounts entry. The "By Type" mode dumps all 37 types in a flat list with " Shape" suffixes. Users can't filter to see just their Contacts grouped by Company, or Tasks grouped by status then sorted by due date. The explorer is the primary navigation surface and it's not doing its job.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Define a custom explorer configuration: pick a filter (type, tag, saved query), then group by a property, then sort within groups
- Stack multiple levels: e.g. filter by "Tasks" → group by "Status" → within each status, sort by "Due Date"
- Save and name explorer configurations for quick switching
- Have multiple OBJECTS panels open simultaneously with different configurations
- See only relevant objects (no " Shape" suffixes, no raw model IDs)

### Entry point / environment

- Entry point: http://localhost:4000/browser/ → Explorer panel
- Environment: Docker Compose dev stack
- Live dependencies involved: RDF4J triplestore

## Completion Class

- Contract complete means: composable filter/group/sort produces correct SPARQL queries, E2E tests for multi-level configurations
- Integration complete means: explorer configurations save/restore, multiple panels work
- Operational complete means: none

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- Create a configuration: Filter=Tasks, Group=Status, Sort=Due Date → see tasks organized in groups
- Create a second configuration: Filter=Contacts, Group=Company → see contacts grouped
- Both configurations open as separate OBJECTS panels simultaneously
- Save a configuration → close browser → reopen → configuration restored

## Risks and Unknowns

- **SPARQL complexity** — multi-level group-by queries may be expensive. May need query optimization or result caching.
- **UI design** — how to present the configuration builder without it being overwhelming. MountSpec strategies UI is a reference but may need simplification.
- **Performance** — grouping 1000+ objects by arbitrary properties could be slow

## Existing Codebase / Prior Art

- `backend/app/browser/workspace.py` — explorer tree endpoint with mode registry (by-type, hierarchy, by-tag)
- `backend/app/vfs/` — VFS MountSpec with composable strategy chains (up to 3 levels). This is the pattern reference.
- `frontend/static/js/workspace.js` — explorer mode switching, tree rendering

## Scope

### In Scope

- Filter layer: subset by type, saved query, tag, or model
- Group layer: organize by property, tag, type, model — multi-level
- Sort layer: within each group, sort by time, label, property value
- Configuration builder UI
- Save/restore named configurations
- Multiple OBJECTS panels (duplicate button)
- Clean type labels (no "Shape" suffix)
- Remove VFS Mounts from mode dropdown

### Out of Scope / Non-Goals

- Replacing VFS MountSpec (that's a separate system for file access)
- Advanced SPARQL filter expressions (keep it property-based)
- Drag-drop reordering within groups

## Open Questions

- How many levels of grouping should be supported? VFS allows 3. Probably sufficient here too.
- Should configurations be stored in localStorage (like current mode) or server-side (like personas)?
