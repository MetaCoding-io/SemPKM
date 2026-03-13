# S08: In-App Class Creation

**Goal:** Users can create a new RDF class through a form (name, icon, parent class, properties with datatypes), and the system generates OWL class triples + a SHACL NodeShape that integrates with the existing form generation pipeline. Created classes appear in the ontology viewer and type picker, and objects of that type can be created with auto-generated SHACL forms.
**Demo:** User opens the ontology viewer TBox tab, clicks "Create Class", fills in a name/icon/parent/properties, submits → class appears in TBox tree with "user" badge → user goes to "New Object", sees the new type in the type picker → creates an object of that type with the auto-generated form → object appears in the explorer.

## Must-Haves

- Class creation form with name, Lucide icon picker, parent class selector (from TBox), and dynamic property editor (name, predicate, datatype)
- `POST /browser/ontology/create-class` endpoint generating OWL class + SHACL NodeShape triples
- Triples written to `urn:sempkm:user-types` named graph via batched INSERT DATA
- ShapesService extended to include `urn:sempkm:user-types` in FROM clauses so created shapes are discoverable
- IconService extended with SPARQL-based fallback for user-created type icons
- Created classes visible in TBox ontology viewer with "user" badge
- Created classes visible in type picker for object creation
- Objects of user-created types can be created with auto-generated SHACL forms
- IRI collision prevention via UUID suffix on class IRIs
- Delete endpoint for user-created classes (minimum error recovery)

## Proof Level

- This slice proves: integration
- Real runtime required: yes (Docker Compose stack with triplestore)
- Human/UAT required: no (integration tests prove SHACL→form pipeline end-to-end; E2E proves user flow)

## Verification

- `cd backend && .venv/bin/pytest tests/test_class_creation.py -v` — unit tests for OWL+SHACL triple generation, ShapesService FROM clause extension, IRI minting, input validation, delete logic
- `cd e2e && npx playwright test tests/23-class-creation/` — E2E test covering create class → appears in TBox → create object of that type → object appears in explorer
- Manual smoke: in Docker stack, create a class, verify it appears in TBox and type picker, create an object of that type

## Observability / Diagnostics

- Runtime signals: structured logging on class creation (class IRI, triple count, property count) and deletion (class IRI, triples deleted count) in OntologyService
- Inspection surfaces: TBox viewer shows user-created classes with "user" badge; SPARQL console can query `urn:sempkm:user-types` graph directly
- Failure visibility: HTTP 422 with structured JSON error on validation failure (missing name, invalid parent IRI, duplicate class name); HTTP 500 with logged traceback on triplestore write failure
- Redaction constraints: none (no secrets involved)

## Integration Closure

- Upstream surfaces consumed:
  - `OntologyService` — `_build_insert_data_sparql()`, `_rdf_term_to_sparql()`, `get_ontology_graph_iris()`, `get_root_classes()`, `get_subclasses()` (from S07)
  - `ShapesService` — `_fetch_shapes_graph()`, `get_node_shapes()`, `get_types()`, `get_form_for_type()` (existing)
  - `IconService` — `get_type_icon()`, `get_icon_map()` (existing, needs extension)
  - `ontology_router` — existing TBox/ABox/RBox endpoints (from S07)
  - `browser/router.py` — sub-router coordinator (from S01/D014)
  - `templates/forms/object_form.html` + `_field.html` — generic SHACL form renderer (existing)
  - `templates/browser/type_picker.html` — type picker grid (existing)
- New wiring introduced in this slice:
  - `create_class()` / `delete_class()` methods on OntologyService
  - `POST /browser/ontology/create-class` and `DELETE /browser/ontology/delete-class` endpoints on ontology_router
  - `urn:sempkm:user-types` FROM clause added to `ShapesService._fetch_shapes_graph()`
  - SPARQL-based icon fallback in IconService for user-created types
  - Class creation form template + icon picker UI component
  - `HX-Trigger: classCreated` / `classDeleted` for TBox refresh
- What remains before the milestone is truly usable end-to-end:
  - S09 (admin stats/charts) and S10 (E2E coverage gaps) — independent of this slice

## Tasks

- [x] **T01: Unit tests + ShapesService FROM clause fix + OWL/SHACL triple generation** `est:2h`
  - Why: The #1 integration risk is ShapesService not seeing user-created shapes. This task writes failing tests first, then fixes the FROM clause and builds the core triple generation logic that everything else depends on.
  - Files: `backend/tests/test_class_creation.py`, `backend/app/services/shapes.py`, `backend/app/ontology/service.py`
  - Do: Create test file with assertions for: (1) ShapesService FROM clauses include `urn:sempkm:user-types`, (2) OWL class triple generation produces valid owl:Class + rdfs:label + rdfs:subClassOf, (3) SHACL NodeShape generation produces valid sh:NodeShape + sh:targetClass + sh:property blocks that ShapesService can parse, (4) IRI minting uses UUID suffix, (5) input validation rejects empty names and invalid parent IRIs. Then fix `_fetch_shapes_graph()` to add the FROM clause, and add `create_class()` + `delete_class()` methods to OntologyService.
  - Verify: `cd backend && .venv/bin/pytest tests/test_class_creation.py -v` — all tests pass
  - Done when: Triple generation produces shapes that `ShapesService._extract_node_shape()` can parse into valid `NodeShapeForm`, verified by round-trip test with rdflib Graph

- [x] **T02: IconService SPARQL fallback + create-class/delete-class endpoints** `est:1.5h`
  - Why: The backend needs HTTP endpoints for the UI to call, and IconService needs to resolve user-type icons from the triplestore instead of filesystem manifests.
  - Files: `backend/app/ontology/router.py`, `backend/app/services/icons.py`, `backend/app/browser/_helpers.py`, `backend/tests/test_class_creation.py`
  - Do: Add `POST /browser/ontology/create-class` and `DELETE /browser/ontology/delete-class` to ontology_router. Wire to OntologyService methods from T01. Add icon triple storage (sempkm:typeIcon, sempkm:typeColor) in the class creation triples. Extend IconService with async `get_user_type_icon()` method that queries `urn:sempkm:user-types` for icon metadata, called as fallback when filesystem cache misses. Return `HX-Trigger: classCreated`/`classDeleted` headers. Add endpoint-level tests.
  - Verify: `cd backend && .venv/bin/pytest tests/test_class_creation.py -v` — endpoint and icon tests pass
  - Done when: POST endpoint returns 200 with class IRI; DELETE endpoint cleans up triples; IconService resolves user-type icons from triplestore

- [x] **T03: Class creation form UI with icon picker and property editor** `est:2h`
  - Why: Users need a form to create classes. This is the primary UI surface for TYPE-01.
  - Files: `backend/app/templates/browser/ontology/create_class_form.html`, `backend/app/templates/browser/ontology/ontology_page.html`, `backend/app/templates/browser/ontology/tbox_tree.html`, `frontend/static/css/workspace.css`, `frontend/static/js/workspace.js`
  - Do: Build the create-class form template with: text input for name, searchable icon picker (curated list of ~40 common Lucide icons), parent class selector (htmx search-as-you-type against TBox classes), dynamic property list (add/remove rows with name, predicate dropdown of common predicates + custom IRI, datatype selector). Add "Create Class" button to ontology viewer TBox tab header. Wire form submission via htmx POST. Add `classCreated`/`classDeleted` event listeners on TBox tree for auto-refresh. Add CSS for form layout, icon picker grid, property editor rows.
  - Verify: Start Docker stack, navigate to ontology viewer, click "Create Class", fill form, submit → class appears in TBox tree with "user" badge
  - Done when: Form renders, validates client-side, submits successfully, and TBox tree refreshes to show the new class

- [x] **T04: E2E test + delete UI + end-to-end verification** `est:1.5h`
  - Why: Proves the full integration: create class → TBox visibility → type picker → object creation → explorer. Also adds delete button for error recovery.
  - Files: `e2e/tests/23-class-creation/class-creation.spec.ts`, `e2e/helpers/selectors.ts`, `backend/app/templates/browser/ontology/tbox_tree.html`, `backend/app/templates/browser/ontology/tbox_children.html`
  - Do: Write E2E test that: (1) opens ontology viewer, (2) creates a class with name, icon, parent, and one property, (3) verifies class appears in TBox with "user" badge, (4) navigates to "New Object" flow, (5) verifies new type appears in type picker, (6) creates an object of the new type, (7) verifies object appears in explorer. Add delete button on user-type TBox nodes (only for `urn:sempkm:user-types:` IRIs) that calls DELETE endpoint. Add selectors to helpers.
  - Verify: `cd e2e && npx playwright test tests/23-class-creation/ --headed` — test passes
  - Done when: E2E test passes proving create-class → type-picker → object-creation pipeline works end-to-end

## Files Likely Touched

- `backend/app/ontology/service.py` — `create_class()`, `delete_class()` methods + triple generation helpers
- `backend/app/ontology/router.py` — `POST /browser/ontology/create-class`, `DELETE /browser/ontology/delete-class` endpoints
- `backend/app/services/shapes.py` — `_fetch_shapes_graph()` FROM clause for `urn:sempkm:user-types`
- `backend/app/services/icons.py` — SPARQL-based icon fallback for user-created types
- `backend/app/browser/_helpers.py` — possible icon service extension wiring
- `backend/tests/test_class_creation.py` — unit tests for triple generation, ShapesService integration, validation
- `backend/app/templates/browser/ontology/create_class_form.html` — class creation form
- `backend/app/templates/browser/ontology/ontology_page.html` — "Create Class" button integration
- `backend/app/templates/browser/ontology/tbox_tree.html` — classCreated refresh listener, delete button for user types
- `backend/app/templates/browser/ontology/tbox_children.html` — delete button for user types in children
- `frontend/static/css/workspace.css` — form, icon picker, property editor styles
- `frontend/static/js/workspace.js` — icon picker interaction, property editor add/remove
- `e2e/tests/23-class-creation/class-creation.spec.ts` — E2E test
- `e2e/helpers/selectors.ts` — class creation selectors
