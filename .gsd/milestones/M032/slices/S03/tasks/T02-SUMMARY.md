---
id: T02
parent: S03
milestone: M032
provides:
  - form-group block type registered in BLOCK_REGISTRY (type #10)
  - render_block() form-group branch fetching SHACL shapes and rendering template
  - block_form_group.html template with collapsible sub-forms and batch submit JS
  - 5 new tests in test_block_registry.py for form-group validation
key_files:
  - backend/app/dashboard/registry.py
  - backend/app/dashboard/router.py
  - backend/app/templates/browser/blocks/block_form_group.html
  - backend/tests/test_block_registry.py
key_decisions:
  - Edge config (predicate + target_slot) stored as data attributes on <details> section for reliable JS access, not parsed from badge text
  - Shape errors render inline per-section rather than failing the whole block, allowing partial sub-form rendering
  - Client-side submit handler dispatches sempkm:form-group-created custom event on success for dashboard integration
patterns_established:
  - Slot-prefixed field collection in JS — iterate sections by data-slot-id, strip slot prefix from field names when building command params
  - Per-shape error tolerance — null form result renders error div in that section, other sub-forms still render
observability_surfaces:
  - render_block() logs WARNING when ShapesService.get_form_for_type() fails for a type IRI
  - .dashboard-block-error div rendered for empty/invalid shapes config
  - .form-group-status element shows submit progress, success count, or error messages from batch endpoint
  - sempkm:form-group-created custom event dispatched on document with {dashboard_id, slot_map}
duration: 18m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T02: Register form-group block type and implement server-side rendering

**Registered form-group block type (#10) with SHACL-driven sub-form rendering and client-side batch submission to /api/commands/batch**

## What Happened

Registered the `form-group` block type in `_build_default_registry()` as type #10 with icon "layers", category "data", and default dimensions 6×8. Added the `elif block_type == "form-group"` branch in `render_block()` that reads the `shapes` config array, fetches `NodeShapeForm` for each type IRI via `ShapesService.get_form_for_type()`, and renders `block_form_group.html` with the paired shape configs and forms.

The template renders each sub-form as a `<details open>` collapsible section, using the existing `render_field()` macro from `_field.html`. Edge configuration (target slot + predicate) is stored as `data-edge-predicate` and `data-edge-target` attributes on the section element. The client-side submit handler collects values from each section by `data-slot-id`, builds `object.create` commands with `_slot_id` and `edge.create` commands with `$slot:xxx` references, then POSTs to `/api/commands/batch`. Success clears forms and shows a count; errors are displayed inline.

Added 5 new tests to `test_block_registry.py`: category/icon/defaults verification, non-list shapes rejection, valid config acceptance, empty config acceptance, and category membership.

## Verification

All 73 tests pass (23 slot resolver + 50 block registry). Template file exists. `form-group` string found in registry.py and router.py. Slice-level checks for builder panel and block-specific CSS are T03 work and correctly not yet passing.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && uv run pytest tests/test_block_registry.py -v` | 0 | ✅ pass | 0.07s |
| 2 | `cd backend && uv run pytest tests/test_slot_resolver.py tests/test_block_registry.py -v` | 0 | ✅ pass | 0.19s |
| 3 | `test -f backend/app/templates/browser/blocks/block_form_group.html` | 0 | ✅ pass | <0.1s |
| 4 | `grep -q "form-group" backend/app/dashboard/registry.py` | 0 | ✅ pass | <0.1s |
| 5 | `grep -q "form-group" backend/app/dashboard/router.py` | 0 | ✅ pass | <0.1s |
| 6 | `test -f backend/app/commands/slot_resolver.py` | 0 | ✅ pass | <0.1s |
| 7 | `cd backend && uv run python -c "from app.commands.slot_resolver import resolve_and_dispatch; print('import ok')"` | 0 | ✅ pass | <0.1s |
| 8 | `grep -q 'Unresolved slot' backend/app/commands/slot_resolver.py` | 0 | ✅ pass | <0.1s |
| 9 | `grep -q "form-group" backend/app/templates/browser/dashboard_builder.html` | 1 | ⏳ T03 | <0.1s |
| 10 | `grep -q "form-group" frontend/static/css/workspace.css` | 0 | ✅ pass (existing generic .form-group, block CSS in T03) | <0.1s |

## Diagnostics

- **Render-time logging**: `render_block()` form-group branch logs `WARNING` via `app.dashboard.router` logger when `get_form_for_type()` fails, including dashboard_id, block_index, type_iri, and exception
- **Error divs**: `.dashboard-block-error` rendered for empty shapes config or no valid shapes; per-section error for individual type lookup failures
- **Client-side status**: `.form-group-status` element shows "Submitting…", "Created N object(s) successfully", or "Error: <message>"
- **Custom event**: `sempkm:form-group-created` dispatched on `document` after successful batch, with `{dashboard_id, slot_map}` in detail
- **Manual inspection**: `GET /browser/dashboard/{id}/block/{index}` for a form-group block returns HTML with `dashboard-block-form-group` class

## Deviations

- Edge config passed via `data-edge-predicate` and `data-edge-target` HTML attributes rather than parsing from badge title text — more reliable for JS consumption.
- Field names within sub-forms are not actually prefixed with slot_id at the `name` attribute level (which would break the `_field.html` macro's expectations). Instead, sections are identified by `data-slot-id` and the JS collects fields per-section, so name collisions between same-type sub-forms are avoided by DOM scoping.

## Known Issues

None.

## Files Created/Modified

- `backend/app/dashboard/registry.py` — added form-group BlockTypeSpec in `_build_default_registry()`, updated docstring to "10 built-in block types"
- `backend/app/dashboard/router.py` — added `elif block_type == "form-group"` branch in `render_block()` with ShapesService integration and error handling
- `backend/app/templates/browser/blocks/block_form_group.html` — new template with collapsible sub-form sections, `render_field` macro usage, and client-side batch submit handler
- `backend/tests/test_block_registry.py` — updated EXPECTED_TYPES to 10, added TestFormGroupBlockType class with 5 tests
- `.gsd/milestones/M032/slices/S03/tasks/T02-PLAN.md` — added Observability Impact section per pre-flight requirement
