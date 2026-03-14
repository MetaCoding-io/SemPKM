# S01: Property Creation + Class Edit

**Goal:** Users can create OWL properties from the RBox tab and edit existing custom classes (rename, change icon/color, reparent, modify properties).
**Demo:** Create a property from RBox "+" button → appears in RBox table. Edit a previously created class → changes visible in TBox tree and detail panel.

## Must-Haves

- "+ Create Property" button on RBox tab opens a modal
- Property modal: name, type (Object/Datatype), domain class, range class/datatype, description
- Created property stored in `urn:sempkm:user-types` graph
- "Edit" action on custom class nodes in TBox tree
- Edit class form pre-populates from existing triples
- Edit saves via delete-old + insert-new pattern (full replacement)
- RBox reloads after property creation to show new property
- TBox detail refreshes after class edit

## Proof Level

- This slice proves: integration (live SPARQL round-trip + UI)
- Real runtime required: yes
- Human/UAT required: yes (browser verification)

## Verification

- `docker compose exec api python -m pytest backend/tests/test_ontology_service.py -v` — unit tests for create_property, edit_class
- Browser: create property from RBox → appears in table
- Browser: edit class from TBox → name/icon/properties change reflected

## Observability / Diagnostics

- Runtime signals: logger.info for property creation and class edit with IRI and triple counts
- Inspection surfaces: SPARQL console can query `urn:sempkm:user-types` for all user properties
- Failure visibility: ValueError raised with descriptive message on invalid input; 422 HTTP response
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `OntologyService`, `ontology_router`, `rbox_legend.html`, `ontology_page.html`, `workspace.css`
- New wiring: `create_property` route + modal, `edit_class` route + modal, `get_class_for_edit` query
- What remains: delete (S02), Custom section (S03), docs (S05)

## Tasks

- [ ] **T01: Backend — create_property service method** `est:30m`
  - Why: Need the core logic for generating OWL property triples (ObjectProperty or DatatypeProperty) with domain, range, label, description
  - Files: `backend/app/ontology/service.py`
  - Do: Add `create_property(name, prop_type, domain_iri, range_iri, description)` method. Mint property IRI with UUID. Generate triples: `a owl:ObjectProperty/DatatypeProperty`, `rdfs:label`, `rdfs:domain`, `rdfs:range`, `rdfs:comment`. INSERT DATA into user-types graph. Add `_mint_property_iri()` and `_generate_property_triples()` helpers.
  - Verify: `pytest backend/tests/test_ontology_service.py -v`
  - Done when: Unit test creates a property and verifies triple generation

- [ ] **T02: Backend — edit_class service method** `est:45m`
  - Why: Need to update an existing class's metadata and SHACL shape. Strategy: delete all existing triples for the class + shape, then re-insert with new values (full replacement).
  - Files: `backend/app/ontology/service.py`
  - Do: Add `edit_class(class_iri, name, parent_iri, properties, icon_name, icon_color, description, example)`. Derive shape IRI from class IRI. Delete old class + shape triples (reuse existing delete helpers). Re-insert new triples via `_generate_class_triples` + `_generate_shape_triples`. Add `get_class_for_edit(class_iri)` that queries current state for pre-populating the edit form (label, parent, icon, color, description, example, shape properties).
  - Verify: `pytest backend/tests/test_ontology_service.py -v`
  - Done when: Unit test round-trips create → get_for_edit → edit → get_for_edit and verifies changes

- [ ] **T03: Routes — create-property and edit-class endpoints** `est:20m`
  - Why: Wire the service methods to HTTP endpoints for the frontend
  - Files: `backend/app/ontology/router.py`
  - Do: `POST /browser/ontology/create-property` accepting Form params (name, prop_type, domain_iri, range_iri, description). `GET /browser/ontology/edit-class-form?class_iri=...` returning pre-populated edit form. `POST /browser/ontology/edit-class` accepting Form params. Both return htmx-compatible HTML responses.
  - Verify: Restart API container, check routes registered
  - Done when: Both endpoints respond (can test via curl or browser)

- [ ] **T04: Frontend — create property modal** `est:30m`
  - Why: Users need a form to create properties from the RBox tab
  - Files: `backend/app/templates/browser/ontology/create_property_form.html`, `backend/app/templates/browser/ontology/rbox_legend.html`, `frontend/static/css/workspace.css`
  - Do: Add "+ Create Property" button to `rbox_legend.html` (in the section header area). Create `create_property_form.html` modal (reuse `.ccf-overlay`/`.ccf-modal` pattern from create class). Fields: name, type (radio: Object Property / Datatype Property), domain (class autocomplete reusing tbox-search), range (class autocomplete for object props, datatype dropdown for datatype props), description textarea. On submit, htmx POST to create-property. Success: close modal, trigger RBox reload.
  - Verify: Browser — open RBox tab, click "+", fill form, submit
  - Done when: Property appears in RBox table after creation

- [ ] **T05: Frontend — edit class modal** `est:30m`
  - Why: Users need to edit existing custom classes
  - Files: `backend/app/templates/browser/ontology/edit_class_form.html`, `backend/app/templates/browser/ontology/ontology_page.html`, `frontend/static/js/workspace.js`
  - Do: Add edit action (pencil icon) on TBox nodes with `data-source="user"`. Click triggers htmx GET to `/browser/ontology/edit-class-form?class_iri=...` which loads into the same `.ccf-overlay` modal. Form is identical to create-class but pre-populated. On submit, POST to edit-class. Success: close modal, refresh TBox tree + detail panel.
  - Verify: Browser — create a test class, click edit icon, change name/icon, submit, verify changes
  - Done when: Edited class shows new name and properties in TBox

- [ ] **T06: Unit tests** `est:20m`
  - Why: Cover new service methods
  - Files: `backend/tests/test_ontology_service.py`
  - Do: Add tests for `_generate_property_triples()` (object prop, datatype prop, with/without domain/range/description), `_mint_property_iri()`. Add tests for edit class triple generation (verify old triples removed pattern). Test `get_class_for_edit` response shape.
  - Verify: `pytest backend/tests/test_ontology_service.py -v`
  - Done when: All tests pass, coverage includes property creation and class edit helpers

## Files Likely Touched

- `backend/app/ontology/service.py`
- `backend/app/ontology/router.py`
- `backend/app/templates/browser/ontology/create_property_form.html` (new)
- `backend/app/templates/browser/ontology/edit_class_form.html` (new)
- `backend/app/templates/browser/ontology/rbox_legend.html`
- `backend/app/templates/browser/ontology/ontology_page.html`
- `backend/app/templates/browser/ontology/tbox_tree.html`
- `backend/app/templates/browser/ontology/tbox_children.html`
- `backend/tests/test_ontology_service.py`
- `frontend/static/css/workspace.css`
- `frontend/static/js/workspace.js`
