---
id: M004
provides:
  - Full CRUD for user-created OWL classes (create/edit/delete with SHACL shape management)
  - Full CRUD for user-created OWL properties (ObjectProperty and DatatypeProperty)
  - Custom section on Mental Models page listing user types/properties with inline edit/delete
  - Create-new-object opens fresh dockview tab preserving current view
  - Instance-count and subclass-count warnings on class deletion
  - Cross-graph label resolution for domain/range display
key_decisions:
  - D070: Two-step class delete confirmation via check endpoint (hx-confirm can't show dynamic content)
  - D071: _property_source returns 'user' for user-types IRIs (prefix ordering matters)
  - D072: Property deletion uses simple hx-confirm, no modal (no cascade concerns)
  - D073: Property type immutable on edit (switching would break SHACL shapes)
  - D074: Custom section server-rendered in admin_models(), not htmx lazy-load
  - D075: SHACL shapes NOT updated on property edit (acceptable — shapes reference by IRI)
  - D076: Edit property form uses epf- ID prefix to avoid collision with create form cpf- IDs
patterns_established:
  - Full replacement pattern for class/shape editing (delete all triples → re-insert)
  - HX-Trigger event-driven refresh (classCreated/Deleted, propertyCreated/Deleted/Edited)
  - Namespace guard pattern on all mutation endpoints (user-types IRI prefix check)
  - Two-step delete confirmation for entities with dependent data (check endpoint → modal → delete)
  - epf-/cpf- ID prefixing to avoid DOM collision when multiple modals coexist
observability_surfaces:
  - logger.info on property creation, edit, deletion with IRI and triple counts
  - logger.warning on namespace guard violations (delete/edit of non-user types rejected)
  - HX-Trigger headers on all mutation responses for downstream refresh
  - SPARQL console can query urn:sempkm:user-types for all user types/properties
requirement_outcomes:
  - id: PROP-01
    from_status: active
    to_status: validated
    proof: create_property() service method + POST /ontology/create-property endpoint + create_property_form.html modal on RBox tab. Unit tests in test_class_creation.py and test_ontology_service.py. Browser-verified in S01 and S02.
  - id: PROP-02
    from_status: active
    to_status: validated
    proof: edit_property() + get_property_for_edit() service methods + GET/POST /ontology/edit-property routes + edit_property_form.html. Accessible from RBox tab and Custom section. 7 route-level tests. Browser-verified in S03 T03.
  - id: PROP-03
    from_status: active
    to_status: validated
    proof: delete_property() service method + DELETE /ontology/delete-property endpoint with namespace guard + HX-Trigger. hx-confirm on RBox delete buttons. 2 service + 3 endpoint unit tests. Browser-verified in S02 T03.
  - id: TYPE-05
    from_status: active
    to_status: validated
    proof: edit_class() + get_class_for_edit() service methods + POST /ontology/edit-class endpoint + edit_class_form.html modal. Full SHACL shape replacement on edit. Browser-verified in S01.
  - id: TYPE-06
    from_status: active
    to_status: validated
    proof: delete_class() + get_delete_class_info() service methods + GET /delete-class-check + DELETE /delete-class endpoints + delete_class_confirm.html template with instance/subclass count warnings. 11 unit tests. Browser-verified in S02 T03.
  - id: TYPE-07
    from_status: active
    to_status: validated
    proof: list_user_types() service method + Custom section in admin/models.html with classes/properties tables and inline edit/delete. Property-edit modal on admin page. Browser-verified in S03 T04.
  - id: TAB-01
    from_status: active
    to_status: validated
    proof: showTypePicker() refactored to always create fresh __new-object-{timestamp} panel. _newObjectPanelId tracker + cleanup in objectCreated handler. E2E tests in new-object-tab.spec.ts (4 tests, 2 browsers). Browser-verified in S04 T01.
duration: ~1 day
verification_result: passed
completed_at: 2026-03-14T14:54:31.919Z
---

# M004: Ontology & Type System Completion

**Users can create, edit, and delete custom OWL classes and properties entirely in-app, manage them from a dedicated "Custom" section on Mental Models, and create new objects without losing their current tab.**

## What Happened

M004 completed the in-app type authoring story that M003 started with class creation. Five slices delivered full CRUD for the ontology type system:

**S01 (Property Creation + Class Edit)** — Added `create_property()` for minting OWL ObjectProperty/DatatypeProperty with domain, range, and description in the user-types graph. Added `edit_class()` with full SHACL shape replacement (delete all existing triples → re-insert with new values). Frontend: "+ Create Property" button on RBox tab with modal form, pencil icon on TBox nodes for editing custom classes with pre-populated edit form.

**S02 (Delete + Instance Warnings)** — Added `delete_property()` (simple DELETE WHERE) and `delete_class()` with a two-step confirmation flow: `get_delete_class_info()` queries instance count and subclass count, rendered in a confirmation modal with red/amber warnings. Fixed `_property_source()` to correctly badge user-created types as "user" instead of "sempkm". RBox got delete buttons with browser-native confirmation for properties.

**S03 (Custom Section + Property Edit)** — Added `list_user_types()` to query all user-created classes and properties from the user-types graph. Added `edit_property()` with `get_property_for_edit()` including cross-graph label resolution for domain/range display. Mental Models page extended with a "Custom" section showing classes and properties in separate tables with inline edit/delete actions. Property edit modal accessible from both RBox tab and Custom section.

**S04 (Create-New-Object Tab Fix)** — Fixed `showTypePicker()` which was overwriting the active tab's content. Now always creates a fresh dockview panel with `__new-object-{timestamp}` ID. Temp panel cleaned up automatically when the real object tab opens. E2E regression tests guard against recurrence.

**S05 (Docs & Test Coverage)** — Added 6 new documentation sections to user guide chapter 10 covering all M004 features. Fixed 4 broken tests from S01's Form parameter additions. Registered all 7 M004 requirements as validated. All 386 backend tests pass.

## Cross-Slice Verification

| Success Criterion | Status | Evidence |
|---|---|---|
| User creates OWL Object Property from RBox tab with domain, range, description — appears in RBox table | ✅ | `create_property()` service + `POST /ontology/create-property` + browser-verified in S01/S02. HX-Trigger: propertyCreated refreshes RBox. |
| User edits a previously created class (rename, icon/color, reparent, add/remove properties) — reflected in TBox and object forms | ✅ | `edit_class()` with full shape replacement + `POST /ontology/edit-class` + browser-verified in S01. HX-Trigger: classEdited refreshes TBox. |
| User deletes a custom class — warned if instances exist, class removed from TBox tree and forms | ✅ | `get_delete_class_info()` returns counts + `delete_class_confirm.html` shows warnings + `DELETE /ontology/delete-class` removes triples. Browser-verified in S02 T03. |
| User edits a previously created property (rename, change domain/range) — reflected in RBox | ✅ | `edit_property()` + `GET/POST /ontology/edit-property` + browser-verified in S03 T03. HX-Trigger: propertyEdited refreshes RBox. |
| User deletes a custom property — removed from RBox | ✅ | `delete_property()` + `DELETE /ontology/delete-property` + hx-confirm + browser-verified in S02 T03. HX-Trigger: propertyDeleted refreshes RBox. |
| Mental Models page shows three sections: Upper Ontology (gist), Installed Models, Custom | ✅ | `list_user_types()` called in `admin_models()` + Custom section in models.html + browser-verified in S03 T04 with assertions. |
| "Create New Object" opens fresh dockview tab instead of overwriting active tab | ✅ | `showTypePicker()` refactored + `_newObjectPanelId` cleanup + browser-verified in S04 T01 + E2E tests pass (4 tests, 2 browsers). |
| All custom type CRUD reflected immediately without page reload | ✅ | HX-Trigger events on all mutation responses: classCreated, classDeleted, propertyCreated, propertyDeleted, propertyEdited. TBox/RBox panes include these in hx-trigger attributes. |

**Unit tests:** 114 ontology-specific tests pass (test_class_creation.py + test_ontology_service.py). 386 total backend tests pass, 0 failures.

**E2E tests:** new-object-tab.spec.ts with 2 tests × 2 browsers = 4 passing tests for S04 tab fix.

**Documentation:** 6 new sections in docs/guide/10-managing-mental-models.md covering Creating Properties, Editing Classes, Editing Properties, Deleting Classes, Deleting Properties, and Custom Section on Mental Models.

## Requirement Changes

- PROP-01: active → validated — create_property() service + endpoint + form + unit tests
- PROP-02: active → validated — edit_property() service + endpoint + form + unit tests
- PROP-03: active → validated — delete_property() service + endpoint + unit tests
- TYPE-05: active → validated — edit_class() with SHACL shape replacement + endpoint + form
- TYPE-06: active → validated — delete_class() with instance/subclass count warnings + confirmation modal
- TYPE-07: active → validated — list_user_types() + Custom section on Mental Models page
- TAB-01: active → validated — showTypePicker() fresh tab fix + E2E regression tests

## Forward Intelligence

### What the next milestone should know
- The user-types graph (`urn:sempkm:user-types`) is now the sole source of truth for user-created types and properties. All CRUD goes through `OntologyService` methods with direct SPARQL (not EventStore).
- SHACL shapes are fully replaced on class edit (delete all → re-insert). There is no incremental shape update.
- Property type (ObjectProperty vs DatatypeProperty) is immutable after creation (D073). Users must delete and re-create to switch.
- The HX-Trigger event pattern (classCreated, classDeleted, propertyCreated, propertyDeleted, propertyEdited) is the standard for ontology mutation UI refresh.

### What's fragile
- **SHACL shapes not updated on property domain/range edit** (D075) — existing shapes referencing the property still point to the correct IRI, but OWL-level domain/range constraints may not match what the shape expects. This could confuse users if they edit a property's domain after using it in a class shape.
- **S01 has no slice summary** — task summaries exist via git history but the formal S01-SUMMARY.md was never written. The doctor did not create a placeholder for S01 (it did for S02-S05).
- **3 pre-existing test failures in TestCreateClassEndpoint** were caused by S01 adding Form parameters without updating tests — fixed in S05 T02 but indicates that router-level tests calling handlers directly are brittle when signatures change.

### Authoritative diagnostics
- `cd backend && .venv/bin/pytest tests/test_class_creation.py tests/test_ontology_service.py -v` — 114 tests covering all ontology service methods and routes
- SPARQL console: `SELECT * FROM <urn:sempkm:user-types> WHERE { ?s ?p ?o }` — inspect all user-created types and properties
- Browser: Mental Models page → Custom section shows current user types/properties

### What assumptions changed
- **SHACL shape updates on class edit** (listed as key risk) — resolved by full shape replacement strategy rather than incremental updates. Simpler and more reliable than partial shape editing.
- **Delete cascade semantics** (listed as key risk) — resolved with two-step confirmation showing counts rather than actual cascade. Classes are deleted but instances remain (orphaned data is acceptable; no auto-cascade).
- **Instance migration on class edit** (listed as key risk) — not addressed and not needed. Editing a class's properties updates the shape but existing instance data is unchanged. Validation will flag mismatches.

## Files Created/Modified

- `backend/app/ontology/service.py` — added create_property, edit_class, delete_property, get_delete_class_info, get_class_for_edit, edit_property, list_user_types, get_property_for_edit, _resolve_cross_graph_label
- `backend/app/ontology/router.py` — added create-property, edit-class, delete-property, delete-class-check, edit-property-form, edit-property routes
- `backend/app/templates/browser/ontology/create_property_form.html` — new: property creation modal
- `backend/app/templates/browser/ontology/edit_class_form.html` — new: class edit modal
- `backend/app/templates/browser/ontology/edit_property_form.html` — new: property edit modal
- `backend/app/templates/browser/ontology/delete_class_confirm.html` — new: delete confirmation with counts
- `backend/app/templates/browser/ontology/ontology_page.html` — added delete-confirm and property-edit overlays
- `backend/app/templates/browser/ontology/tbox_tree.html` — rewired delete buttons to confirmation modal, added edit buttons
- `backend/app/templates/browser/ontology/tbox_children.html` — rewired delete buttons to confirmation modal
- `backend/app/templates/browser/ontology/rbox_legend.html` — added edit/delete buttons for user properties
- `backend/app/admin/router.py` — added list_user_types() call and custom_types context
- `backend/app/templates/admin/models.html` — added Custom section with classes/properties tables
- `frontend/static/js/workspace.js` — fixed showTypePicker() fresh tab + _newObjectPanelId cleanup
- `frontend/static/css/workspace.css` — added rbox-edit-btn, rbox-delete-btn, delete-confirm-content styles
- `frontend/static/css/style.css` — added admin custom section styles
- `backend/tests/test_class_creation.py` — added 20+ tests for delete/edit endpoints, fixed 4 broken tests
- `backend/tests/test_ontology_service.py` — added 19+ tests for new service methods
- `e2e/tests/12-bug-fixes/new-object-tab.spec.ts` — new: E2E regression tests for tab fix
- `docs/guide/10-managing-mental-models.md` — added 6 sections for M004 features
