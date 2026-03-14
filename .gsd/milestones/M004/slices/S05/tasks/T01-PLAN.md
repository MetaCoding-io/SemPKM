---
estimated_steps: 4
estimated_files: 1
---

# T01: Update user guide chapter 10 with M004 feature documentation

**Slice:** S05 — Docs & Test Coverage
**Milestone:** M004

## Description

Extend chapter 10 (`docs/guide/10-managing-mental-models.md`) with six new subsections documenting all M004 features. The existing "Creating Custom Classes" section (from M003/S08) stays as-is. New sections are inserted after it, before the chapter footer navigation.

The documentation covers: creating OWL properties from the RBox tab, editing existing classes (rename, icon, parent, properties), editing properties (name, domain, range), deleting classes with instance-count warnings, deleting properties, and the Custom section on the Mental Models page.

## Steps

1. Read the current state of `docs/guide/10-managing-mental-models.md` to identify the exact insertion point (after "Creating Custom Classes", before the `---` footer separator)
2. Add `### Creating Properties` subsection: describe opening the "+ Create Property" button on the RBox tab, choosing Object Property vs Datatype Property, setting name/domain/range/description, and how the property appears in the RBox table with a "user" badge
3. Add `### Editing Classes` subsection: describe right-click or edit button on a user-created class in TBox, the edit form (rename, change icon/color, reparent, add/remove properties), and how changes reflect immediately in TBox and object forms
4. Add `### Editing Properties` subsection: describe edit action on a user-created property in RBox or Custom section, the edit form (rename, change domain/range — type is immutable per D073), and how changes reflect in RBox
5. Add `### Deleting Classes` subsection: describe the delete flow — the two-step confirmation (D070) showing instance count and subclass count, the warning about data implications, and clean removal from TBox
6. Add `### Deleting Properties` subsection: describe the simple `hx-confirm` delete (D072), removal from RBox
7. Add `### Custom Section on Mental Models` subsection: describe the new "Custom" section on the Mental Models admin page showing all user-created types and properties with inline edit/delete actions

## Must-Haves

- [ ] Six new subsections added: Creating Properties, Editing Classes, Editing Properties, Deleting Classes, Deleting Properties, Custom Section on Mental Models
- [ ] Each section has step-by-step instructions matching as-built behavior from S01-S04
- [ ] Deleting Classes section includes the instance-count warning flow (two-step confirmation)
- [ ] Editing Properties section notes that property type (Object/Datatype) is immutable after creation
- [ ] No re-documentation of M003 features (class creation, gist loading already covered)
- [ ] Heading levels consistent with existing chapter structure (### for subsections)

## Verification

- `grep -c "### Creating Properties\|### Editing Classes\|### Editing Properties\|### Deleting Classes\|### Deleting Properties\|### Custom Section" docs/guide/10-managing-mental-models.md` returns 6
- Visual review: sections follow the same style as "Creating Custom Classes" (numbered steps, bold UI element names, tip/warning blocks where appropriate)

## Observability Impact

- Signals added/changed: None — documentation only
- How a future agent inspects this: grep for section headings in the docs file
- Failure state exposed: None

## Inputs

- `docs/guide/10-managing-mental-models.md` — existing chapter 10 with Ontology Viewer sections through "Creating Custom Classes"
- S01-S04 summaries and research (preloaded) — describe what was built and how the UI works
- D070 (two-step class delete), D072 (simple property delete), D073 (property type immutable on edit), D074 (Custom section server-rendered) — decision constraints

## Expected Output

- `docs/guide/10-managing-mental-models.md` — extended with 6 new subsections covering all M004 CRUD features, inserted between "Creating Custom Classes" and the chapter footer
