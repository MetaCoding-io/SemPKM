---
estimated_steps: 5
estimated_files: 4
---

# T02: Add edit-property routes + edit_property_form.html template

**Slice:** S03 — Custom Section on Mental Models + Property Edit
**Milestone:** M004

## Description

Create the HTTP routes and form template for property editing. `GET /ontology/edit-property-form` renders a pre-populated form. `POST /ontology/edit-property` processes the edit. The form template (`edit_property_form.html`) is based on `create_property_form.html` but shows current values, makes property type read-only, initializes the correct range field (class picker for object, datatype dropdown for datatype), and submits to the new POST endpoint. Both routes have the `USER_TYPES_GRAPH:` namespace guard. Route tests validate guard, success, and error responses.

## Steps

1. **Add `GET /ontology/edit-property-form` route** — Takes `property_iri` query param. Guards on `USER_TYPES_GRAPH:` prefix (return 403 if not). Calls `ontology_service.get_property_for_edit(unquote(property_iri))`. Returns 404 HTML if None. Otherwise renders `edit_property_form.html` with property data. Follow `edit_class_form()` route pattern.

2. **Add `POST /ontology/edit-property` route** — Takes form fields: `property_iri`, `name`, `prop_type`, `domain_iri`, `range_iri`, `description`. Guards on `USER_TYPES_GRAPH:` prefix. Calls `ontology_service.edit_property()`. Returns 200 with success message and `HX-Trigger: propertyEdited` header. Returns 403/422/500 on guard/validation/error. Follow `edit_class()` route pattern.

3. **Create `edit_property_form.html`** — Based on `create_property_form.html` structure. Pre-populate name input, description textarea. Show property type as read-only (styled disabled radio with hidden input preserving value). Pre-populate domain with selected item display (IRI in hidden input, label visible). Initialize range field based on prop_type: object shows class picker with selected range, datatype shows dropdown with selected option. Use `epf-` ID prefix to avoid collision with `cpf-` create form IDs. Include `htmx.process(form)` call in script block.

4. **Wire form JS** — Domain/range search result click handlers (reuse pattern from create form but with `epf-` prefixed IDs). `epfClearField()` for clearing selected domain/range. `propertyEdited` event listener to close modal and show toast. Initialize lucide icons.

5. **Add route-level tests** — Test namespace guard returns 403 for non-user IRI. Test successful form render returns 200. Test successful edit returns 200 with HX-Trigger header. Test validation error returns 422.

## Must-Haves

- [ ] `GET /ontology/edit-property-form` renders pre-populated form for user properties, 403 for non-user
- [ ] `POST /ontology/edit-property` edits property and returns HX-Trigger, 403 for non-user
- [ ] `edit_property_form.html` shows current values, read-only type, correct range field
- [ ] Domain/range search pickers work (reuse tbox/search endpoint)
- [ ] `htmx.process(form)` called in script block for dynamically loaded form
- [ ] Route tests pass

## Verification

- `docker exec sempkm-backend pytest tests/test_ontology_service.py -x -q` — all tests pass
- Manual template check: `edit_property_form.html` exists with correct structure

## Observability Impact

- Signals added/changed: `logger.warning` on namespace guard violations; `logger.error` on SPARQL failures with `exc_info`
- How a future agent inspects this: Network tab shows `/ontology/edit-property-form` and `/ontology/edit-property` requests; HX-Trigger `propertyEdited` header confirms success
- Failure state exposed: HTTP 403 (namespace violation), 404 (property not found), 422 (validation error), 500 (server error) with descriptive HTML bodies

## Inputs

- `backend/app/ontology/service.py` — `get_property_for_edit()` and `edit_property()` from T01
- `backend/app/ontology/router.py` — existing `edit_class_form()` / `edit_class()` routes as pattern (lines ~630-730)
- `backend/app/templates/browser/ontology/create_property_form.html` — basis for edit form structure, domain/range picker JS

## Expected Output

- `backend/app/ontology/router.py` — two new route handlers added (~60 lines each)
- `backend/app/templates/browser/ontology/edit_property_form.html` — new template (~180 lines)
- `backend/tests/test_ontology_service.py` — ≥4 new route-level tests
