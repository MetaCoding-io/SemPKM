# S39: Edit Form Helptext And Bug Fixes

**Goal:** Add `sempkm:editHelpText` SHACL annotation support to edit forms.
**Demo:** Add `sempkm:editHelpText` SHACL annotation support to edit forms.

## Must-Haves


## Tasks

- [x] **T01: 39-edit-form-helptext-and-bug-fixes 01** `est:3min`
  - Add `sempkm:editHelpText` SHACL annotation support to edit forms. NodeShape-level helptext renders as a collapsible markdown section below the form title. PropertyShape-level helptext renders via a `?` icon next to the field label that expands inline markdown below the field.

Purpose: Users see contextual guidance about what to enter and why, reducing blank-field confusion and teaching the Mental Model's vocabulary.
Output: Working helptext rendering in edit forms with seed content on basic-pkm model shapes.
- [x] **T02: 39-edit-form-helptext-and-bug-fixes 02** `est:1min`
  - Make dockview tab accent bars reflect the object's type color from the Mental Model manifest. Update basic-pkm manifest colors to the decided warm/cool palette (Notes=teal, Projects=indigo, Concepts=amber, Persons=rose). BUG-05 through BUG-09 are already fixed; they are listed in requirements for traceability only (E2E verification in Phase 40).

Purpose: Users can visually distinguish object types in the tab bar at a glance, improving navigation efficiency.
Output: Type-colored active tab accent bars, updated manifest colors.

## Files Likely Touched

- `backend/app/services/shapes.py`
- `backend/app/templates/forms/object_form.html`
- `backend/app/templates/forms/_field.html`
- `frontend/static/css/workspace.css`
- `models/basic-pkm/shapes/basic-pkm.jsonld`
- `orig_specs/models/starter-basic-pkm/shapes.ttl`
- `models/basic-pkm/manifest.yaml`
- `orig_specs/models/starter-basic-pkm/manifest.yaml`
- `frontend/static/js/workspace-layout.js`
- `frontend/static/css/dockview-sempkm-bridge.css`
