---
id: T01
parent: S05
milestone: M004
provides:
  - Six new subsections in chapter 10 documenting all M004 CRUD features
key_files:
  - docs/guide/10-managing-mental-models.md
key_decisions: []
patterns_established:
  - Documentation style matches existing chapter 10 conventions (numbered steps, bold UI elements, tip/warning blocks)
observability_surfaces:
  - none — documentation only
duration: 5m
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T01: Update user guide chapter 10 with M004 feature documentation

**Added six new subsections to chapter 10 documenting property CRUD, class edit/delete, and the Custom section on Mental Models.**

## What Happened

Extended `docs/guide/10-managing-mental-models.md` with six new `###` subsections inserted after the existing "Creating Custom Classes" section and before the chapter footer navigation:

1. **Creating Properties** — Step-by-step instructions for the "+ Create Property" button on the RBox tab: choosing Object vs Datatype property, setting name/domain/range/description, and how the property appears in the RBox table with a "user" badge. Notes that property type is permanent.

2. **Editing Classes** — Describes the pencil icon on user-created TBox nodes, the pre-populated edit form (name, description, example, icon/color, parent, properties), and that changes reflect immediately in TBox and object forms. Notes that only user-badged classes are editable.

3. **Editing Properties** — Describes edit action on user-created properties in RBox, the pre-populated form, and that property type (Object/Datatype) is shown read-only and cannot be changed (D073). Includes warning about SHACL shapes not auto-updating on domain/range changes (D075).

4. **Deleting Classes** — Documents the two-step confirmation flow (D070): trash icon opens modal showing instance count (red) and subclass count (amber), with explanation of data implications. Confirm Delete vs Cancel. Warning about permanent deletion.

5. **Deleting Properties** — Documents the simple browser `hx-confirm` dialog (D072) and automatic RBox refresh after deletion.

6. **Custom Section on Mental Models** — Describes the "Custom" section on `/admin/models` (D074) showing all user-created classes, object properties, and datatype properties with inline edit/delete actions.

No M003 features were re-documented — existing "Creating Custom Classes" section left untouched.

## Verification

- `grep -c "### Creating Properties\|### Editing Classes\|### Editing Properties\|### Deleting Classes\|### Deleting Properties\|### Custom Section" docs/guide/10-managing-mental-models.md` → **6** ✅
- All heading levels are `###`, consistent with existing chapter structure ✅
- Deleting Classes section includes instance-count warning flow with two-step confirmation ✅
- Editing Properties section notes property type is immutable after creation ✅
- No re-documentation of M003 class creation or gist loading ✅

### Slice-level verification status (intermediate task):
- ✅ grep returns 6 for all section headings
- ⏳ `cd backend && .venv/bin/pytest tests/ -q` → requires T02 (test fixes)
- ⏳ `cd backend && .venv/bin/pytest tests/test_class_creation.py::TestCreateClassEndpoint -q` → requires T02
- ⏳ REQUIREMENTS.md entries → requires T02

## Diagnostics

- Grep for `### ` headings in chapter 10 to verify section structure
- No runtime diagnostics — documentation only

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/10-managing-mental-models.md` — Added 6 new subsections documenting M004 features (Creating Properties, Editing Classes, Editing Properties, Deleting Classes, Deleting Properties, Custom Section on Mental Models)
