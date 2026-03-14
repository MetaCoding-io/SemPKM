# S03: Custom Section on Mental Models + Property Edit

**Goal:** Mental Models page shows a "Custom" section listing all user-created types and properties, and users can edit a property's name, domain, and range from both the Custom section and the RBox tab.
**Demo:** Navigate to Mental Models — see Custom section with tables of user classes and properties. Click edit on a property — form opens pre-populated. Change the property name and range, submit. RBox tab and Custom section both show updated data.

## Must-Haves

- `list_user_types()` service method returns classes and properties from `urn:sempkm:user-types` graph
- `get_property_for_edit()` service method returns property metadata for pre-populating edit form
- `edit_property()` service method deletes old triples and re-inserts with updated values (preserving IRI)
- Custom section renders in `models.html` with classes table and properties table (or empty state)
- `edit_property_form.html` template with pre-populated fields, read-only property type, domain/range pickers
- `GET /ontology/edit-property-form` and `POST /ontology/edit-property` routes with namespace guard
- Edit button in RBox table for user-source properties (hover-reveal, same pattern as delete)
- Property-edit modal overlay in `ontology_page.html`
- Edit/delete actions on Custom section link to correct endpoints
- Unit tests for all new service methods

## Proof Level

- This slice proves: integration (service ↔ route ↔ template round-trip, verified in live browser)
- Real runtime required: yes (Docker stack for browser verification)
- Human/UAT required: no (agent browser verification is sufficient)

## Verification

- `docker exec sempkm-backend pytest tests/test_ontology_service.py -x -q` — new tests for `list_user_types`, `get_property_for_edit`, `edit_property` all pass
- Browser: navigate to Mental Models page → Custom section visible with classes/properties or empty state
- Browser: create a property in Ontology Viewer → navigate to Mental Models → property appears in Custom section
- Browser: click edit on a user property in RBox → edit form opens pre-populated → change name → submit → RBox shows updated name
- Browser: Custom section edit/delete actions trigger correct endpoints

## Observability / Diagnostics

- Runtime signals: `logger.info("Edited property %s", prop_iri)` in `edit_property()`; `logger.info("list_user_types: %d classes, %d properties", ...)` in `list_user_types()`
- Inspection surfaces: HX-Trigger `propertyEdited` header on successful edit; `/ontology/edit-property-form?property_iri=...` returns 404 if property not found
- Failure visibility: HTTP 403 on namespace guard violation (non-user property edit attempt); HTTP 422 on validation errors; HTTP 500 with `exc_info` on SPARQL failures
- Redaction constraints: none (no secrets involved)

## Integration Closure

- Upstream surfaces consumed: `OntologyService.create_property()`, `_generate_property_triples()`, `delete_property()` from S01/S02; `_property_source()` fix from S02; modal overlay system in `ontology_page.html`; admin page `admin_models()` handler and `models.html` template
- New wiring introduced in this slice: `admin_models()` calls `list_user_types()` and passes to template; edit-property routes added to ontology router; property-edit overlay added to ontology page; Custom section template added to models.html; edit button added to RBox table
- What remains before the milestone is truly usable end-to-end: S04 (create-new-object tab fix), S05 (docs & test coverage)

## Tasks

- [x] **T01: Add list_user_types(), get_property_for_edit(), edit_property() service methods + unit tests** `est:45m`
  - Why: All three service methods are required before any route or template can be built. Tests validate SPARQL queries and delete-then-reinsert pattern.
  - Files: `backend/app/ontology/service.py`, `backend/tests/test_ontology_service.py`
  - Do: Add `list_user_types()` querying classes and properties from `urn:sempkm:user-types`; add `get_property_for_edit()` following `get_class_for_edit()` pattern; add `edit_property()` using delete-then-reinsert with `_generate_property_triples()`. Add unit tests covering happy paths, not-found, validation errors.
  - Verify: `docker exec sempkm-backend pytest tests/test_ontology_service.py -x -q` passes
  - Done when: All three service methods exist with unit tests passing; `edit_property()` preserves IRI and uses `_generate_property_triples()`

- [x] **T02: Add edit-property routes + edit_property_form.html template** `est:35m`
  - Why: Routes and form template wire the service methods to the UI. The edit form must be accessible from both RBox and Custom section modals.
  - Files: `backend/app/ontology/router.py`, `backend/app/templates/browser/ontology/edit_property_form.html`, `backend/tests/test_ontology_service.py`
  - Do: Add `GET /ontology/edit-property-form` route (namespace guard, calls `get_property_for_edit()`, renders template). Add `POST /ontology/edit-property` route (namespace guard, calls `edit_property()`, returns HX-Trigger `propertyEdited`). Create `edit_property_form.html` based on `create_property_form.html` with pre-populated values, read-only prop_type, correct range field initialization. Add route-level tests.
  - Verify: Tests pass; form renders when fetched via htmx
  - Done when: Both routes respond correctly; form shows pre-populated values with correct range field visible

- [x] **T03: Add RBox edit button + property-edit modal overlay in ontology page** `est:25m`
  - Why: Wires the edit form into the Ontology Viewer — edit button in RBox table, modal overlay in ontology page, JS open/close functions, CSS for the edit button.
  - Files: `backend/app/templates/browser/ontology/rbox_legend.html`, `backend/app/templates/browser/ontology/ontology_page.html`, `frontend/static/css/workspace.css`
  - Do: Add edit button alongside delete button in RBox `{% if is_user %}` block. Add `#property-edit-overlay` div in `ontology_page.html` (same pattern as class-edit overlay). Add `openPropertyEditForm(iri)` / `closePropertyEditForm()` JS functions. Add CSS for `.rbox-edit-btn` matching delete button pattern. Wire `propertyEdited` event to close modal and refresh RBox.
  - Verify: Browser: open Ontology Viewer → RBox tab → hover user property → edit button visible → click → modal opens with pre-populated form
  - Done when: Edit button appears on hover for user properties; clicking it opens the edit modal; submitting refreshes RBox

- [x] **T04: Add Custom section to Mental Models page** `est:30m`
  - Why: The Custom section on Mental Models is the main new UI surface of this slice — it shows all user-created types and properties with inline edit/delete actions.
  - Files: `backend/app/admin/router.py`, `backend/app/templates/admin/models.html`, `frontend/static/css/style.css`
  - Do: Extend `admin_models()` to call `ontology_service.list_user_types()` and pass result to template. Add Custom section in `models.html` after Installed Models: classes table (name, icon, parent, actions) and properties table (name, type, domain, range, actions). Handle empty state with encouraging message directing to Ontology Viewer. Edit buttons open edit modals (classes link to Ontology Viewer; properties open inline htmx modal). Delete buttons use `hx-delete` with `hx-confirm`. Add CSS for custom section tables.
  - Verify: Browser: navigate to Mental Models → Custom section visible; if user types exist, tables populated with correct data; edit/delete actions work
  - Done when: Custom section renders with tables or empty state; edit/delete buttons trigger correct endpoints; page refreshes after mutations

## Files Likely Touched

- `backend/app/ontology/service.py`
- `backend/app/ontology/router.py`
- `backend/app/admin/router.py`
- `backend/tests/test_ontology_service.py`
- `backend/app/templates/admin/models.html`
- `backend/app/templates/browser/ontology/edit_property_form.html`
- `backend/app/templates/browser/ontology/rbox_legend.html`
- `backend/app/templates/browser/ontology/ontology_page.html`
- `frontend/static/css/workspace.css`
- `frontend/static/css/style.css`
