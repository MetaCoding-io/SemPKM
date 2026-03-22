---
estimated_steps: 5
estimated_files: 5
skills_used: []
---

# T02: Render form-group block with multiple SHACL sub-forms and submission JS

**Slice:** S01 — Multi-Object Form Groups with Slot IRI Resolution
**Milestone:** M032

## Description

Add the `form-group` case to `render_block()` in the dashboard router so it renders a dedicated template showing one SHACL sub-form per configured slot. Each sub-form loads via htmx into a namespaced container. A combined Submit button fires JS that collects all sub-form data, builds a batch command payload (object.create per slot + edge.create per configured edge with `@slot:` references), and POSTs to `/api/commands`.

DOM isolation is critical: each sub-form is loaded independently via htmx GET to `/browser/objects/new?type={target_class}`, but into a scoped container with `data-slot` and `data-slot-index` attributes. The form elements use the existing SHACL form template — we don't modify it, we just load multiple instances and override the submit behavior with JS.

## Steps

1. **Add form-group case to `render_block()`** (`backend/app/dashboard/router.py`):
   - Before the final `return HTMLResponse('Unknown block type')` fallback, add an `elif block_type == "form-group":` branch.
   - Extract `slots` and `edges` from config. If no slots, return an error div.
   - Return an HTML template response for `browser/dashboard_form_group.html` with context: `dashboard_id`, `block_index`, `slots` (list of `{name, target_class}`), `edges` (list of `{source_slot, target_slot, predicate}`).

2. **Create form-group template** (`backend/app/templates/browser/dashboard_form_group.html`):
   - Render a container div with class `form-group-block` and `data-edges="{{ edges | tojson | e }}"`.
   - For each slot, render a section with: heading showing slot name, a div with `class="form-group-slot"`, `data-slot="{{ slot.name }}"`, `data-slot-index="{{ loop.index0 }}"`, `data-target-class="{{ slot.target_class }}"`, and an htmx `hx-get="/browser/objects/new?type={{ slot.target_class }}"` + `hx-trigger="load"` + `hx-swap="innerHTML"` to lazy-load the SHACL form.
   - At the bottom, render a "Create All" submit button that calls `window._submitFormGroup(this.closest('.form-group-block'))`.
   - Add a status/result area div for success/error messages.

3. **Add form-group submission JS** (`frontend/static/js/workspace.js`):
   - Add `window._submitFormGroup = function(blockEl) { ... }`.
   - For each `.form-group-slot` inside `blockEl`, collect form data from the `<form>` element (using the same field extraction as the existing object create — iterate `[name]` inputs, skip hidden meta fields).
   - Build the batch payload: one `{"command": "object.create", "slot": slotName, "params": {"type": target_class, "properties": {...}}}` per slot, then one `{"command": "edge.create", "params": {"source": "@slot:SOURCE", "target": "@slot:TARGET", "predicate": PRED}}` per configured edge.
   - POST to `/api/commands` as JSON array.
   - On success: show success message in the result area, optionally clear forms. On error: show error message.

4. **Add CSS for form-group layout** (`frontend/static/css/workspace.css`):
   - `.form-group-block` — flex column layout, gap between slots.
   - `.form-group-slot` — border, padding, section appearance with slot label header.
   - `.form-group-submit` — centered submit button styling.
   - `.form-group-result` — success/error message area.

5. **Add render tests** (`backend/tests/test_form_group.py`):
   - Test that render_block for form-group with 2 slots returns HTML containing two `.form-group-slot` divs with correct `data-slot` attributes.
   - Test that render_block for form-group with empty slots returns error div.
   - Test that the edges config is serialized into the template as `data-edges` JSON.

## Must-Haves

- [ ] `render_block()` handles `form-group` type and returns template HTML
- [ ] Template renders one htmx-loaded SHACL sub-form per configured slot
- [ ] Each sub-form container has `data-slot`, `data-slot-index`, `data-target-class` attributes
- [ ] JS `_submitFormGroup` collects all slot forms into a batch command payload with `@slot:` references
- [ ] Edge config from the block is embedded in the DOM as `data-edges` JSON for JS to read
- [ ] CSS provides visual separation between slot sub-forms

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_form_group.py -v -k render` — render tests pass
- Manual: Load a dashboard with a form-group block in a running stack and verify sub-forms render for each slot.

## Inputs

- `backend/app/dashboard/router.py` — existing render_block function to extend (from T01: form-group now in registry)
- `backend/app/dashboard/registry.py` — form-group BlockTypeSpec (from T01)
- `backend/app/templates/forms/object_form.html` — existing SHACL form template (loaded via htmx, not modified)
- `backend/app/browser/objects.py` — existing `/browser/objects/new` endpoint that renders SHACL form
- `backend/tests/test_form_group.py` — test file created in T01, to extend with render tests

## Expected Output

- `backend/app/dashboard/router.py` — form-group case added to render_block
- `backend/app/templates/browser/dashboard_form_group.html` — new template for form-group block
- `frontend/static/js/workspace.js` — `_submitFormGroup()` function added
- `frontend/static/css/workspace.css` — form-group CSS styles added
- `backend/tests/test_form_group.py` — render tests added

## Observability Impact

- **Browser console:** `[form-group]` prefix on all console.warn/console.error messages from `_submitFormGroup()` — e.g., slot parse failures, submission errors, missing form elements.
- **Network inspection:** Batch submission POSTs to `/api/commands` as a JSON array — visible in browser dev tools Network tab. Response includes `results[].iri` for each created object.
- **DOM inspection:** Each slot container has `data-slot`, `data-slot-index`, `data-target-class` attributes for debugging which slot maps to which form. Edge config is embedded as `data-edges` JSON on the `.form-group-block` container.
- **Failure visibility:** `.form-group-error` div renders inside the block with the error message from the API (including `@slot:` resolution failures). `.form-group-loading` indicator shows during submission.
