---
id: S01
parent: M032
milestone: M032
provides:
  - form-group block type in BlockRegistry (7th type)
  - "@slot:name" IRI resolution in batch command execution
  - form-group render handler with htmx-loaded SHACL sub-forms per slot
  - _submitFormGroup() JS for batch command submission
  - form-group builder config UI with dynamic slot/edge management
requires: []
affects:
  - S03
key_files:
  - backend/app/dashboard/registry.py
  - backend/app/commands/schemas.py
  - backend/app/commands/router.py
  - backend/app/dashboard/router.py
  - backend/app/templates/browser/dashboard_form_group.html
  - frontend/static/js/workspace.js
  - frontend/static/css/workspace.css
  - backend/app/templates/browser/dashboard_builder.html
  - backend/tests/test_form_group.py
key_decisions:
  - Slot resolution uses object.__setattr__ to mutate frozen Pydantic params in-place
  - Edge source/target dropdowns use slot names (not indices) matching the slot-based resolution convention
  - Hidden SHACL form submit buttons via CSS rather than modifying the shared object_form.html template
  - Single-quoted data-edges HTML attribute to avoid Jinja2 autoescape double-quote conflicts
patterns_established:
  - "@slot:name" prefix convention for cross-command IRI references in batch payloads
  - slot_map accumulator pattern in execute_commands for sequential dependency resolution
  - "[form-group]" console prefix for all form-group JS logging
  - _collectFormFields() helper for extracting SHACL form field values
  - Builder config helper functions (_fgSlotRowHTML/_fgEdgeRowHTML) for reusable row generation
observability_surfaces:
  - "logger.info('Resolved @slot:%s → %s', slot_name, resolved_iri) in commands router"
  - "HTTP 400 with 'Unresolved slot reference: @slot:X' for missing slots"
  - "console.error('[form-group]', ...) in browser console for submission errors"
  - ".form-group-error / .form-group-success divs visible in block DOM after submission"
  - "data-slot/data-slot-index/data-target-class attributes on slot containers"
drill_down_paths:
  - .gsd/milestones/M032/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M032/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M032/slices/S01/tasks/T03-SUMMARY.md
duration: 47min
verification_result: passed
completed_at: 2026-03-22
---

# S01: Multi-Object Form Groups with Slot IRI Resolution

**Added form-group dashboard block type enabling multi-object creation with SHACL sub-forms, slot-based IRI resolution for cross-command edge references, and builder config UI with dynamic slot/edge management.**

## What Happened

T01 registered the form-group block type in BlockRegistry (7 types total) and implemented the core `@slot:name` IRI resolution in the batch command router. The `slot_map` accumulator tracks minted IRIs from `object.create` commands keyed by slot name, then resolves `@slot:X` references in subsequent `edge.create` commands. Unresolved references return HTTP 400 with a descriptive error.

T02 added the form-group render handler in `render_block()`, a Jinja2 template that renders slot containers with `hx-get="/browser/objects/new?type=..."` for htmx-loaded SHACL sub-forms, and the `_submitFormGroup()` JS function that collects all sub-form data and POSTs a batch command payload with `@slot:` references.

T03 completed the builder config UI — a `getTypeConfigHTML('form-group')` case with dynamic slot list (name + class autocomplete per slot), edge list (source/target slot dropdowns + predicate input), and sync logic that updates edge dropdowns when slot names change. Integration tests verify dashboard round-trip (create → get → edit) preserves form-group config.

## Verification

- `test_form_group.py`: 28 tests pass (15 unit + 8 render + 5 integration)
- `test_block_registry.py`: 38 tests pass (10 types registered)
- `test_dashboard.py`: 27 tests pass (no regressions)
- `test_dashboard_builder.py`: 6/9 pass (3 pre-existing failures from prior GridStack migration, not introduced here)

## Requirements Advanced

- DASH-01 — Dashboard block types expanded from 6 to 7 (form-group adds multi-object creation capability)

## Requirements Validated

None in this slice alone — the form-group feature is validated as part of the full M032 milestone.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

- Used `/browser/objects/new?type=` for sub-form loading instead of the non-existent `/browser/objects/create-form` path — the plan's endpoint doesn't exist, but the actual SHACL form endpoint works correctly.
- Single-quoted `data-edges` attribute instead of double-quoted with `| e` filter — Jinja2 autoescape creates broken attributes with double quotes around JSON.

## Known Limitations

- Multiple form-group blocks in the same builder use `#fg-slots-list` / `#fg-edges-list` IDs that would conflict. Fine for current single-block-at-a-time editing, but would need scoping for parallel editing.
- 3 pre-existing test failures in `test_dashboard_builder.py` (layout radio button assertions) from prior GridStack migration.

## Follow-ups

None.

## Files Created/Modified

- `backend/app/dashboard/registry.py` — Added form-group BlockTypeSpec
- `backend/app/commands/schemas.py` — Added optional `slot` field to ObjectCreateCommand
- `backend/app/commands/router.py` — Added slot_map accumulator and @slot:name resolution
- `backend/app/dashboard/router.py` — Added form-group case to render_block()
- `backend/app/templates/browser/dashboard_form_group.html` — New template for form-group block
- `frontend/static/js/workspace.js` — Added _submitFormGroup() and _collectFormFields()
- `frontend/static/css/workspace.css` — Added form-group block and builder config styles
- `backend/app/templates/browser/dashboard_builder.html` — Added form-group builder config UI
- `backend/tests/test_form_group.py` — 28 tests (unit + render + integration)
- `backend/tests/test_block_registry.py` — Updated to expect 7→10 types (includes S02 additions)

## Forward Intelligence

### What the next slice should know
- The form-group block's sub-forms are loaded via htmx `hx-trigger="load"`, so they're async. E2E tests need to wait for the forms to appear before interacting.
- Edge dropdowns in the builder use slot names as values, matching the `@slot:name` convention in the command router.

### What's fragile
- `_collectFormFields()` iterates `[name]` inputs and skips hidden meta fields by pattern match — if a model adds form fields with unusual name patterns, they might be skipped or double-collected.

### Authoritative diagnostics
- `grep "Resolved @slot:" <log>` shows slot resolution during batch execution
- `document.querySelectorAll('.form-group-slot')` in DevTools shows loaded sub-forms

### What assumptions changed
- The `create-form` block type references a URL (`/browser/objects/create-form`) that doesn't exist — the real endpoint is `/browser/objects/new?type=`. This pre-existing bug was noted but not fixed.
