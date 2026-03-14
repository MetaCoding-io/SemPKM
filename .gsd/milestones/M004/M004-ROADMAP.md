# M004: Ontology & Type System Completion

**Vision:** Users can create, edit, and delete custom classes and properties entirely in-app, manage them from a dedicated "Custom" section on Mental Models, and create new objects without losing their current tab.

## Success Criteria

- User creates an OWL Object Property from the RBox tab with domain, range, and description — it appears in the RBox table
- User edits a previously created class (rename, change icon/color, reparent, add/remove properties) — changes reflected in TBox and object forms
- User deletes a custom class — warned if instances exist, class removed from TBox tree and forms
- User edits a previously created property (rename, change domain/range) — changes reflected in RBox
- User deletes a custom property — removed from RBox
- Mental Models page shows three sections: Upper Ontology (gist), Installed Models, Custom (user types/properties)
- "Create New Object" opens in a fresh dockview tab instead of overwriting the active tab
- All custom type CRUD operations are reflected immediately in the Ontology Viewer without page reload

## Key Risks / Unknowns

- **SHACL shape updates on class edit** — editing properties on an existing class requires updating or replacing the SHACL NodeShape. Partial shape updates (add/remove individual sh:property) are more complex than full replacement. Risk: ordering/identity of existing shapes.
- **Instance migration on class edit** — if a property is removed from a class, existing instances still have that triple. Risk: orphaned data, confusing validation results.
- **Delete cascade semantics** — deleting a class that has instances or subclasses needs clear UX. Risk: data loss if not handled carefully.

## Proof Strategy

- SHACL shape updates → retire in S01 by proving edit-class round-trips (create → edit properties → verify shape changed)
- Delete cascade → retire in S02 by proving delete with instances shows warning and handles gracefully

## Verification Classes

- Contract verification: pytest unit tests for service methods (create/edit/delete property, edit class, delete class)
- Integration verification: live browser testing of RBox property creation, TBox class edit, Mental Models custom section
- Operational verification: none (no new services)
- UAT / human verification: full CRUD flow walkthrough in browser

## Milestone Definition of Done

This milestone is complete only when all are true:

- All slice deliverables complete and verified
- Custom classes and properties can be created, edited, and deleted from the Ontology Viewer
- Mental Models page shows Custom section with user types/properties
- Create-new-object opens fresh tab
- User guide updated for all new features
- Unit tests cover all new service methods

## Slices

- [x] **S01: Property Creation + Class Edit** `risk:high` `depends:[]`
  > After this: user creates a property from RBox tab and edits an existing class (rename, change icon, add/remove properties) — both reflected live in Ontology Viewer

- [x] **S02: Delete + Instance Warnings** `risk:medium` `depends:[S01]`
  > After this: user deletes custom classes and properties with instance-count warnings, confirmation dialogs, and clean removal from TBox/RBox

- [ ] **S03: Custom Section on Mental Models** `risk:low` `depends:[S01]`
  > After this: Mental Models page shows "Custom" section listing all user-created types and properties with edit/delete actions inline

- [ ] **S04: Create-New-Object Tab Fix** `risk:low` `depends:[]`
  > After this: clicking "New Object" always opens a fresh dockview tab, preserving the user's current view

- [ ] **S05: Docs & Test Coverage** `risk:low` `depends:[S01,S02,S03,S04]`
  > After this: user guide pages updated for property creation, type CRUD, Custom section; unit tests cover all new service methods

## Boundary Map

### S01 → S02

Produces:
- `OntologyService.create_property()` — creates OWL ObjectProperty/DatatypeProperty in user-types graph
- `OntologyService.edit_class()` — updates label, icon, color, parent, properties (replaces SHACL shape)
- `POST /browser/ontology/create-property` route
- `POST /browser/ontology/edit-class` route
- `create_property_form.html` modal template
- `edit_class_form.html` modal template

Consumes:
- nothing (first slice)

### S01 → S03

Produces:
- `OntologyService.list_user_types()` — returns all classes/properties in user-types graph
- Edit/delete service methods from S01+S02

Consumes:
- nothing (first slice)

### S02 → S05

Produces:
- `OntologyService.delete_property()` — removes property triples
- `OntologyService.delete_class()` updated with instance count check and confirmation flow
- Delete confirmation modal/dialog

Consumes:
- S01 create/edit methods

### S04 (independent)

Produces:
- Fixed `openTab()` / create-new-object flow in workspace.js

Consumes:
- nothing (independent bug fix)
