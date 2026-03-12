---
id: T01
parent: S39
milestone: M001
provides:
  - "sempkm:editHelpText SHACL annotation support in ShapesService"
  - "Form-level collapsible helptext rendering in edit forms"
  - "Field-level ? icon toggle helptext rendering in edit forms"
  - "Helptext seed content on all basic-pkm shapes"
requires: []
affects: []
key_files: []
key_decisions: []
patterns_established: []
observability_surfaces: []
drill_down_paths: []
duration: 3min
verification_result: passed
completed_at: 2026-03-05
blocker_discovered: false
---
# T01: 39-edit-form-helptext-and-bug-fixes 01

**# Phase 39 Plan 01: Edit Form Helptext Summary**

## What Happened

# Phase 39 Plan 01: Edit Form Helptext Summary

**SHACL sempkm:editHelpText annotation support with collapsible form-level and toggleable field-level markdown helptext in edit forms**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-05T03:38:20Z
- **Completed:** 2026-03-05T03:42:05Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Added SEMPKM_EDIT_HELPTEXT constant and helptext field to PropertyShape/NodeShapeForm dataclasses
- ShapesService extracts sempkm:editHelpText from SHACL shapes graph for both node shapes and property shapes
- Form-level helptext renders as collapsible details/summary section below form title with Lucide help-circle icon
- Field-level helptext renders via ? icon next to label, expanding inline markdown on click with lazy rendering
- All basic-pkm shapes annotated: Note (form + all 7 fields), Project/Concept/Person (form-level only)
- CSS follows CLAUDE.md Lucide flex-shrink: 0 rule for all SVG icons

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend helptext extraction + shapes annotation** - `e767744` (feat)
2. **Task 2: Frontend helptext rendering + CSS** - `1335fbe` (feat)

## Files Created/Modified
- `backend/app/services/shapes.py` - Added SEMPKM_EDIT_HELPTEXT constant, helptext fields on dataclasses, extraction logic
- `backend/app/templates/forms/object_form.html` - Form-level helptext section, toggleFieldHelp JS function
- `backend/app/templates/forms/_field.html` - Field-level ? icon toggle button and helptext content block
- `frontend/static/css/workspace.css` - Helptext styling (form-level, field-level toggle, field-level content)
- `models/basic-pkm/shapes/basic-pkm.jsonld` - Added sempkm prefix, helptext annotations on all shapes
- `orig_specs/models/starter-basic-pkm/shapes.ttl` - Added sempkm prefix, helptext annotations on all shapes

## Decisions Made
- Used HTML details/summary for form-level helptext -- native collapsible, no extra JS needed
- Lazy markdown rendering for field helptext -- only calls renderMarkdownBody on first toggle open, avoids processing hidden content

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Helptext infrastructure is extensible: any model can add sempkm:editHelpText to shapes
- Ready for visual verification and any follow-up plans in phase 39

---
*Phase: 39-edit-form-helptext-and-bug-fixes*
*Completed: 2026-03-05*
