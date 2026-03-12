# T01: 39-edit-form-helptext-and-bug-fixes 01

**Slice:** S39 — **Milestone:** M001

## Description

Add `sempkm:editHelpText` SHACL annotation support to edit forms. NodeShape-level helptext renders as a collapsible markdown section below the form title. PropertyShape-level helptext renders via a `?` icon next to the field label that expands inline markdown below the field.

Purpose: Users see contextual guidance about what to enter and why, reducing blank-field confusion and teaching the Mental Model's vocabulary.
Output: Working helptext rendering in edit forms with seed content on basic-pkm model shapes.

## Must-Haves

- [ ] "Edit form shows collapsible form-level helptext below the title row when NodeShape has sempkm:editHelpText"
- [ ] "Edit form shows ? icon next to field label when PropertyShape has sempkm:editHelpText"
- [ ] "Clicking ? icon expands markdown helptext inline below the field"
- [ ] "Note shape has both form-level and field-level helptext on all fields"
- [ ] "Project, Concept, Person shapes have form-level helptext only"

## Files

- `backend/app/services/shapes.py`
- `backend/app/templates/forms/object_form.html`
- `backend/app/templates/forms/_field.html`
- `frontend/static/css/workspace.css`
- `models/basic-pkm/shapes/basic-pkm.jsonld`
- `orig_specs/models/starter-basic-pkm/shapes.ttl`
