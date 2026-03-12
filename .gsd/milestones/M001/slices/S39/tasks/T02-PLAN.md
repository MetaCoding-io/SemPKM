# T02: 39-edit-form-helptext-and-bug-fixes 02

**Slice:** S39 — **Milestone:** M001

## Description

Make dockview tab accent bars reflect the object's type color from the Mental Model manifest. Update basic-pkm manifest colors to the decided warm/cool palette (Notes=teal, Projects=indigo, Concepts=amber, Persons=rose). BUG-05 through BUG-09 are already fixed; they are listed in requirements for traceability only (E2E verification in Phase 40).

Purpose: Users can visually distinguish object types in the tab bar at a glance, improving navigation efficiency.
Output: Type-colored active tab accent bars, updated manifest colors.

## Must-Haves

- [ ] "Active tab for a Note shows teal accent bar"
- [ ] "Active tab for a Project shows indigo accent bar"
- [ ] "Active tab for a Concept shows amber accent bar"
- [ ] "Active tab for a Person shows rose accent bar"
- [ ] "Inactive tabs show no type-colored accent"
- [ ] "When no type color is available, accent falls back to default teal"

## Files

- `models/basic-pkm/manifest.yaml`
- `orig_specs/models/starter-basic-pkm/manifest.yaml`
- `frontend/static/js/workspace-layout.js`
- `frontend/static/css/dockview-sempkm-bridge.css`
