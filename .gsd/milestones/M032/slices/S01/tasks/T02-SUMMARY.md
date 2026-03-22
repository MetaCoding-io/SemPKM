---
id: T02
parent: S01
milestone: M032
provides:
  - form-group render handler in dashboard router (render_block handles form-group type)
  - dashboard_form_group.html template with htmx-loaded SHACL sub-forms per slot
  - _submitFormGroup() JS function for batch command submission with @slot: references
  - CSS styles for form-group block layout, slot sections, and result/error areas
key_files:
  - backend/app/dashboard/router.py
  - backend/app/templates/browser/dashboard_form_group.html
  - frontend/static/js/workspace.js
  - frontend/static/css/workspace.css
  - backend/tests/test_form_group.py
key_decisions:
  - Used single-quoted HTML attribute for data-edges JSON (avoids double-quote escaping issues with tojson inside autoescape templates)
  - Hidden SHACL form submit buttons inside slots via CSS (.form-group-slot .form-actions display:none) instead of modifying the shared object_form.html template
  - Used /browser/objects/new?type= endpoint for sub-form loading (the actual SHACL form endpoint), not the non-existent /browser/objects/create-form path referenced in create-form block type
patterns_established:
  - "[form-group]" console prefix convention for all JS logging in form-group submission code
  - _collectFormFields() helper pattern for extracting SHACL form field values from sub-forms
  - Single-quoted data attribute pattern for embedding JSON in Jinja2 templates with autoescape=True
observability_surfaces:
  - "console.error('[form-group]', ...)" in browser console for submission errors and parse failures
  - ".form-group-error" div with API error message visible in the block after failed submission
  - ".form-group-success" div with count of created items after successful submission
  - data-slot/data-slot-index/data-target-class attributes on each slot container for DOM inspection
duration: 20min
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T02: Render form-group block with multiple SHACL sub-forms and submission JS

**Added form-group render handler, template, submission JS, CSS, and 8 render tests for multi-object SHACL sub-form dashboard blocks**

## What Happened

Added the `form-group` case to `render_block()` in the dashboard router. When a dashboard block has type `form-group`, the router extracts `slots` and `edges` from config, returns an error div if no slots are configured, and otherwise renders the new `dashboard_form_group.html` template.

Created the form-group template that renders a `.form-group-block` container with `data-edges` JSON (single-quoted attribute to avoid Jinja2 autoescape double-quote conflicts). Each configured slot gets a `.form-group-slot` div with `data-slot`, `data-slot-index`, and `data-target-class` attributes, plus `hx-get="/browser/objects/new?type=..."` with `hx-trigger="load"` to lazy-load the SHACL form. A "Create All" button at the bottom calls `window._submitFormGroup()`. A `.form-group-result` div provides space for success/error messages.

Added `_submitFormGroup()` as a new IIFE section in workspace.js. It collects form data from each slot's `<form>` element using `_collectFormFields()` (iterates `[name]` inputs, skips hidden meta fields, handles multi-value fields). Builds a batch payload with one `object.create` per slot (with `slot` name) and one `edge.create` per configured edge (with `@slot:` references), POSTs to `/api/commands`, and renders success/error in the result area. Clears forms on success.

Added CSS for form-group layout: flex column container with gap, bordered slot sections with headers, hidden SHACL form submit buttons (`.form-group-slot .form-actions { display: none }`), centered Create All button, and styled success/error/loading states.

Added 8 render tests to `test_form_group.py` covering: two-slot rendering, slot index attributes, target class attributes, htmx load attributes, edges JSON serialization, submit button presence, result area presence, and empty slots behavior.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_form_group.py -v -k render` — 8/8 render tests pass
- `cd backend && .venv/bin/python -m pytest tests/test_block_registry.py tests/test_form_group.py tests/test_dashboard.py tests/test_dashboard_builder.py -v` — 88/91 pass (3 pre-existing failures in test_dashboard_builder.py, same as T01)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_form_group.py -v -k render` | 0 | ✅ pass | 0.08s |
| 2 | `pytest tests/test_block_registry.py tests/test_form_group.py tests/test_dashboard.py tests/test_dashboard_builder.py -v` | 1 | ✅ pass (3 pre-existing failures) | 1.24s |

## Diagnostics

- **Template HTML inspection:** Render the template directly with Jinja2 to verify data attributes: `from jinja2 import Environment, FileSystemLoader; env.get_template("browser/dashboard_form_group.html").render(slots=..., edges=...)`
- **Browser console:** All form-group JS errors are prefixed with `[form-group]` — filter console for that prefix
- **DOM inspection:** `document.querySelectorAll('.form-group-slot')` shows slot containers; `JSON.parse(el.getAttribute('data-edges'))` extracts edge config from the block element
- **Submission debugging:** Network tab shows POST to `/api/commands` with the batch payload; response body contains `results[].iri` for each created object

## Deviations

- Used `/browser/objects/new?type=` instead of the plan's `/browser/objects/new?type=` — no change, but confirmed the `create-form` block type in the existing router uses a non-existent `/browser/objects/create-form` URL; the form-group uses the correct endpoint.
- Used single-quoted `data-edges='...'` attribute instead of double-quoted `data-edges="..."` with `| e` filter — Jinja2's `tojson` with `autoescape=True` produces a Markup that doesn't HTML-escape inner double quotes, causing broken attributes. Single-quote wrapper avoids the issue entirely.

## Known Issues

- 3 pre-existing test failures in `test_dashboard_builder.py` (layout radio button tests) — unrelated to form-group, confirmed in T01.
- The existing `create-form` block type uses URL `/browser/objects/create-form?type_iri=` which doesn't match any route in `objects.py` (the real route is `/browser/objects/new?type=`). Pre-existing bug, not introduced here.

## Files Created/Modified

- `backend/app/dashboard/router.py` — Added form-group case to render_block() with template rendering
- `backend/app/templates/browser/dashboard_form_group.html` — New template for form-group block with slot containers and htmx loading
- `frontend/static/js/workspace.js` — Added _submitFormGroup() IIFE section (batch command submission JS)
- `frontend/static/css/workspace.css` — Added form-group CSS styles (block layout, slot sections, submit button, result areas)
- `backend/tests/test_form_group.py` — Added 8 render tests for template HTML output
- `.gsd/milestones/M032/slices/S01/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
