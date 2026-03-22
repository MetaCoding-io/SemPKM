---
estimated_steps: 4
estimated_files: 4
skills_used: []
---

# T03: Builder config form for form-group and integration verification

**Slice:** S01 — Multi-Object Form Groups with Slot IRI Resolution
**Milestone:** M032

## Description

Add the form-group block configuration UI to the dashboard builder so users can define slots (name + target class per slot) and edges (source slot → target slot + predicate) when adding a form-group block to their dashboard. This completes the end-to-end flow: build a form-group in the builder → save → load dashboard → form-group renders sub-forms → submit creates linked objects.

The builder template (`dashboard_builder.html`) uses a `getTypeConfigHTML()` switch statement to return config fields per block type. The form-group case needs a dynamic list of slots (each with a name input and class search autocomplete) and a dynamic list of edges (each with source/target slot dropdowns and a predicate input). The existing `_builderAutocomplete` pattern handles class search. The save collector already gathers all `[data-key]` elements — slot/edge lists need to be collected via a custom JS function since they're dynamic arrays.

## Steps

1. **Add form-group case to `getTypeConfigHTML()`** (`backend/app/templates/browser/dashboard_builder.html`):
   - Add `case 'form-group':` returning HTML with:
     - A "Slots" section: a container div `#fg-slots-list` with an "Add Slot" button. Each slot row has: text input for slot name (`data-fg-slot-name`), a reference-field with class search autocomplete (`data-fg-slot-class`) using the existing `_builderClassSearch` pattern, and a remove button.
     - An "Edges" section: a container div `#fg-edges-list` with an "Add Edge" button. Each edge row has: two `<select>` dropdowns for source and target slot (populated from the current slot name inputs), a text input for predicate IRI (`data-fg-edge-pred`), and a remove button.
   - Pre-populate from `config.slots` and `config.edges` if editing an existing form-group block.

2. **Add form-group config collection to save logic** (`backend/app/templates/browser/dashboard_builder.html`):
   - In `_builderSave()`, after the generic `[data-key]` collection, add a special case for form-group blocks:
     - If `typeName === 'form-group'`, override `block.config` by collecting slots from `#fg-slots-list` rows and edges from `#fg-edges-list` rows into `{slots: [{name, target_class}], edges: [{source_slot, target_slot, predicate}]}`.
   - When a slot name changes, update the edge dropdown options to reflect current slot names.

3. **Add CSS for form-group builder config** (`frontend/static/css/workspace.css`):
   - `.fg-slot-row`, `.fg-edge-row` — flex row with gap, inputs, and remove button.
   - `.fg-add-btn` — "Add Slot" / "Add Edge" button style.
   - Consistent with existing builder config styling patterns.

4. **Add integration test** (`backend/tests/test_form_group.py`):
   - Test creating a dashboard via API with a form-group block containing slots and edges config → verify it saves and loads correctly.
   - Test that the block's config round-trips through create → get (slots and edges are preserved in blocks_json).
   - Test that the builder edit route for a dashboard with form-group returns 200 (not crash on the new template code).

## Must-Haves

- [ ] `getTypeConfigHTML('form-group', config)` returns slot list + edge list HTML with correct data attributes
- [ ] Builder save collects form-group config into `{slots: [...], edges: [...]}` structure
- [ ] Slot add/remove updates edge source/target dropdown options
- [ ] Existing form-group config pre-populates when editing a dashboard
- [ ] Integration test: dashboard with form-group block round-trips through API create → get

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_form_group.py tests/test_dashboard_builder.py -v` — all tests pass
- `cd backend && .venv/bin/python -m pytest tests/test_dashboard.py -v` — regression pass

## Inputs

- `backend/app/templates/browser/dashboard_builder.html` — existing builder with `getTypeConfigHTML()` switch (read the existing create-form and view-embed cases as patterns)
- `backend/app/dashboard/registry.py` — form-group BlockTypeSpec (from T01)
- `backend/app/dashboard/router.py` — form-group render_block handler (from T02)
- `frontend/static/css/workspace.css` — existing builder CSS to extend (from T02: form-group display CSS)
- `backend/tests/test_form_group.py` — test file with slot resolution + render tests (from T01, T02)

## Expected Output

- `backend/app/templates/browser/dashboard_builder.html` — form-group case in getTypeConfigHTML + save collection
- `frontend/static/css/workspace.css` — form-group builder config CSS
- `backend/tests/test_form_group.py` — integration tests for form-group dashboard round-trip
