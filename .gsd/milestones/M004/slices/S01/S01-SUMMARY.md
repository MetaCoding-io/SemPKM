---
id: S01
parent: M004
milestone: M004
provides:
  - OntologyService.create_property() — creates OWL ObjectProperty/DatatypeProperty with domain, range, description
  - OntologyService.edit_class() — updates label, icon, color, parent, properties via full SHACL shape replacement
  - OntologyService.get_class_for_edit() — queries existing class state for form pre-population
  - POST /browser/ontology/create-property endpoint with form validation
  - GET /browser/ontology/edit-class-form and POST /browser/ontology/edit-class endpoints
  - create_property_form.html modal with name, type radio, domain/range pickers, description
  - edit_class_form.html modal pre-populated from existing triples
requires: []
affects:
  - backend/app/ontology/service.py
  - backend/app/ontology/router.py
  - backend/app/templates/browser/ontology/create_property_form.html
  - backend/app/templates/browser/ontology/edit_class_form.html
  - backend/app/templates/browser/ontology/rbox_legend.html
  - backend/app/templates/browser/ontology/ontology_page.html
  - backend/app/templates/browser/ontology/tbox_tree.html
  - backend/app/templates/browser/ontology/tbox_children.html
  - backend/tests/test_ontology_service.py
  - frontend/static/css/workspace.css
  - frontend/static/js/workspace.js
key_files:
  - backend/app/ontology/service.py
  - backend/app/ontology/router.py
  - backend/app/templates/browser/ontology/create_property_form.html
  - backend/app/templates/browser/ontology/edit_class_form.html
key_decisions: []
patterns_established:
  - Full replacement pattern for class/shape editing (delete all triples → re-insert new triples)
  - Property IRI minting with camelCase slug + UUID suffix (urn:sempkm:user-types:{slug}-{uuid8})
  - Modal overlay reuse (ccf-overlay/ccf-modal pattern) for ontology forms
  - htmx configRequest event for dynamic form parameter injection
observability_surfaces:
  - logger.info for property creation and class edit with IRI and triple counts
  - ValueError with descriptive messages on invalid input; HTTP 422 responses
  - SPARQL console can query urn:sempkm:user-types for all user properties
drill_down_paths:
  - git show d4e74e5 — completion commit with all 6 tasks
duration: ~3h
verification_result: passed
completed_at: 2026-03-14T03:06:40Z
---

# S01: Property Creation + Class Edit

**Users can create OWL properties from the RBox tab and edit existing custom classes — both reflected live in the Ontology Viewer.**

## What Happened

Six tasks delivered property creation and class editing end-to-end:

**Backend service methods (T01–T02):** Added `create_property()` which mints a property IRI with `_mint_property_iri()` (camelCase slug + 8-char UUID), generates OWL triples via `_generate_property_triples()` (rdf:type, rdfs:label, rdfs:domain, rdfs:range, rdfs:comment), and INSERT DATA into `urn:sempkm:user-types`. Added `edit_class()` which deletes all existing triples for the class IRI and its SHACL shape, then re-inserts with new values — full replacement, not incremental update. Added `get_class_for_edit()` to query current class state (label, parent, icon, color, description, example, shape properties) for pre-populating the edit form.

**Routes (T03):** Added `GET /ontology/create-property-form` (renders modal), `POST /ontology/create-property` (validates and creates), `GET /ontology/edit-class-form` (pre-populated modal), and `POST /ontology/edit-class` (validates and updates). All return htmx-compatible HTML with HX-Trigger headers for downstream refresh.

**Frontend (T04–T05):** Added "+ Create Property" button to RBox tab header, opening `create_property_form.html` modal with name field, Object/Datatype radio toggle, domain class picker (reusing TBox search), range picker (class autocomplete for object props, datatype dropdown for datatype props), and description textarea. Added pencil icon edit button on TBox nodes with `data-source="user"`, loading `edit_class_form.html` with all fields pre-populated. Both modals close on success with toast notification and trigger TBox/RBox refresh.

**Unit tests (T06):** 15 tests across 5 test classes: `TestMintPropertyIri` (4), `TestGeneratePropertyTriples` (3), `TestCreatePropertyValidation` (4), `TestEditClass` (2), `TestGetClassForEdit` (2). All pass.

## Verification

- `pytest tests/test_ontology_service.py -k "MintPropertyIri or GeneratePropertyTriples or CreatePropertyValidation or EditClass or GetClassForEdit"` — **15/15 passed**
- Browser: created property from RBox "+" button → appeared in RBox table (count 71→72)
- Browser: clicked edit on user class in TBox → form pre-populated → changed name → saved → TBox refreshed
- Browser: modals close on success with toast, Escape key closes modals

## Deviations

- The `create_class` route handler gained `description` and `example` Form parameters but 4 existing tests in `TestCreateClassEndpoint` weren't updated — caused pre-existing failures fixed later in S05/T02.
- No separate slice summary was written at completion time; task-level work was captured only in the git commit message.

## Known Limitations

- Edit class uses full replacement (delete all → re-insert). If the delete succeeds but insert fails, the class is lost. No transactional rollback within RDF4J's HTTP API.
- `htmx:configRequest` event used for dynamic form fields (D063) is less intuitive than standard form submission.

## Follow-ups

- S02 consumed create_property/edit_class for delete flows
- S03 consumed get_class_for_edit pattern for property editing
- S05/T02 fixed the 4 broken tests caused by new Form parameters

## Files Created/Modified

- `backend/app/ontology/service.py` — added create_property, edit_class, get_class_for_edit, _mint_property_iri, _generate_property_triples
- `backend/app/ontology/router.py` — added create-property-form, create-property, edit-class-form, edit-class routes
- `backend/app/templates/browser/ontology/create_property_form.html` — new: property creation modal
- `backend/app/templates/browser/ontology/edit_class_form.html` — new: class edit modal
- `backend/app/templates/browser/ontology/rbox_legend.html` — added "+ Create Property" button
- `backend/app/templates/browser/ontology/ontology_page.html` — added class-edit overlay, wiring for modals
- `backend/app/templates/browser/ontology/tbox_tree.html` — added edit button on user nodes
- `backend/app/templates/browser/ontology/tbox_children.html` — added edit button on user children
- `backend/tests/test_ontology_service.py` — added 15 tests for new service methods
- `frontend/static/css/workspace.css` — modal and edit button styles
- `frontend/static/js/workspace.js` — openClassEditForm, closeClassEditForm, modal event wiring

## Forward Intelligence

### What the next slice should know
- create_property() and edit_class() are the foundation — S02 delete methods follow the same DELETE WHERE pattern.
- get_class_for_edit() response shape is the contract for the edit form. Property editing (S03) followed the same pattern with get_property_for_edit().
- The 4 broken tests in TestCreateClassEndpoint are a known issue until S05 fixes them.

### What's fragile
- Direct handler tests calling route functions with mock Form objects — any new Form parameter breaks them silently.

### Authoritative diagnostics
- `pytest tests/test_ontology_service.py -v -k "MintPropertyIri or GeneratePropertyTriples or CreatePropertyValidation or EditClass or GetClassForEdit"` — 15 tests
- git show d4e74e5 — completion commit

### What assumptions changed
- SHACL shape update risk (from roadmap) resolved: full replacement is simpler and more reliable than incremental updates.
