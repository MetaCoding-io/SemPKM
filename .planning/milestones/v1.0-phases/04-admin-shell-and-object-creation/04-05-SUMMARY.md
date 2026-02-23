---
phase: 04-admin-shell-and-object-creation
plan: 05
subsystem: ui
tags: [shacl, jinja2, htmx, forms, type-picker, codemirror, split-js, object-creation]

# Dependency graph
requires:
  - phase: 04-admin-shell-and-object-creation
    provides: "ShapesService for SHACL form metadata, IDE workspace layout with tabs and command palette"
provides:
  - "SHACL-driven Jinja2 form macros dispatching fields by datatype, constraints, and property shape attributes"
  - "Type picker dialog listing available object types from installed Mental Models"
  - "Create object flow: type selection -> SHACL form -> command dispatch -> object created"
  - "Edit object flow: open object -> form with values -> save -> object.patch dispatch"
  - "Reference search endpoint for sh:class fields with search-as-you-type suggestions"
  - "CodeMirror 6 Markdown body editor with syntax highlighting and dirty tracking"
  - "Object tab split view: SHACL properties form on top, Markdown editor below"
affects: [04-admin-shell-and-object-creation]

# Tech tracking
tech-stack:
  added: [codemirror-6]
  patterns:
    - "Jinja2 macro dispatch by SHACL property shape attributes (datatype, in_values, target_class)"
    - "HX-Trigger response header for cross-component communication (objectCreated, objectSaved)"
    - "Form data parsing with skip fields and array suffix handling for multi-valued properties"
    - "CodeMirror 6 via esm.sh CDN with markdown syntax highlighting"

key-files:
  created:
    - backend/app/templates/forms/_field.html
    - backend/app/templates/forms/_group.html
    - backend/app/templates/forms/object_form.html
    - backend/app/templates/browser/type_picker.html
    - backend/app/templates/browser/search_suggestions.html
    - backend/app/templates/browser/object_tab.html
    - frontend/static/js/editor.js
    - frontend/static/css/forms.css
  modified:
    - backend/app/browser/router.py
    - frontend/static/js/workspace.js
    - backend/app/templates/browser/workspace.html
    - frontend/static/css/workspace.css

key-decisions:
  - "Type name extracted from full IRI by splitting on last / or # for command handler compatibility"
  - "HX-Trigger headers used for objectCreated and objectSaved events to update tab state client-side"
  - "CodeMirror 6 loaded via esm.sh CDN for zero-install markdown editing"
  - "Object tab uses vertical Split.js for resizable form/editor split within center pane"
  - "Reference search uses SPARQL query on urn:sempkm:current with LabelService for display names"

patterns-established:
  - "SHACL-to-HTML field dispatch pattern: Jinja2 macro checks prop.in_values, prop.target_class, prop.datatype in priority order"
  - "Browser router form processing: parse form data, build command params, dispatch handler, re-render with result"
  - "HX-Trigger custom events pattern for server-to-client communication after htmx form submission"

requirements-completed: [SHCL-03, SHCL-04, OBJ-01, OBJ-02]

# Metrics
duration: 10min
completed: 2026-02-22
---

# Phase 04 Plan 05: SHACL-Driven Forms and Object Creation Summary

**SHACL-driven Jinja2 form macros with type picker, create/edit object flows, CodeMirror Markdown editor, and reference search for sh:class fields**

## Performance

- **Duration:** 10 min
- **Started:** 2026-02-22T07:14:53Z
- **Completed:** 2026-02-22T07:25:07Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments
- Jinja2 form macros dispatch SHACL property shapes to correct HTML widgets (text, number, date, boolean, select, URL, reference search) based on datatype, sh:in constraints, and sh:class references
- Type picker dialog lists all available object types from installed Mental Models with type cards linked to create forms
- Complete create flow: type selection -> SHACL-driven form -> object.create command dispatch -> object created in triplestore
- Complete edit flow: open object -> form populated with current values -> modify -> object.patch dispatch -> changes persisted
- Reference search endpoint returns matching instances for sh:class fields with search-as-you-type and "Create new..." option
- CodeMirror 6 Markdown editor with syntax highlighting, Ctrl+S save, and dirty state tracking
- Object tab split view with resizable form/editor panes via vertical Split.js

## Task Commits

Each task was committed atomically:

1. **Task 1: Jinja2 form macros and SHACL-driven form rendering** - `50d3608` (feat)
2. **Task 2: Type picker, create/edit object flows, and CodeMirror editor** - `0fed7b1` (feat)

## Files Created/Modified
- `backend/app/templates/forms/_field.html` - Jinja2 macro dispatching form fields by SHACL property shape attributes
- `backend/app/templates/forms/_group.html` - Collapsible property group section template
- `backend/app/templates/forms/object_form.html` - Complete SHACL-driven form with required/grouped/optional sections
- `backend/app/templates/browser/type_picker.html` - Type selection grid listing available object types
- `backend/app/templates/browser/search_suggestions.html` - Reference search dropdown for sh:class fields
- `backend/app/templates/browser/object_tab.html` - Object editor with split form/editor view
- `backend/app/browser/router.py` - Routes for type picker, create form, create object, save object, and reference search
- `frontend/static/js/workspace.js` - showTypePicker() wired to htmx, objectCreated/objectSaved event listeners
- `frontend/static/js/editor.js` - CodeMirror 6 Markdown editor with save and dirty tracking
- `frontend/static/css/forms.css` - Form field, group, type picker, reference dropdown, and multi-value styles
- `frontend/static/css/workspace.css` - Object tab, editor toolbar, and CodeMirror container styles
- `backend/app/templates/browser/workspace.html` - Added forms.css link

## Decisions Made
- Type name extracted from full IRI (e.g., `https://example.org/data/Person` -> `Person`) for object.create command handler which expects a local name
- HX-Trigger response headers used for objectCreated and objectSaved custom events, enabling tab management updates without additional server requests
- CodeMirror 6 loaded via esm.sh CDN (`https://esm.sh/@codemirror/`) for zero-install Markdown editing with syntax highlighting
- Object tab uses vertical Split.js (40/60 split) for resizable form section on top, editor section below
- Reference search uses full SPARQL query on `urn:sempkm:current` with LIMIT 20 and client-side label filtering

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- SHACL-driven forms complete and functional for all Basic PKM types
- Create/edit flows ready for production use
- Type picker accessible from command palette (Ctrl+K -> New Object) and programmatically via showTypePicker()
- Reference search ready for sh:class property fields
- Plan 06 can build on the object tab for related objects panel and lint integration

## Self-Check: PASSED

All 12 created/modified files verified present. Both task commits (50d3608, 0fed7b1) confirmed in git log.

---
*Phase: 04-admin-shell-and-object-creation*
*Completed: 2026-02-22*
