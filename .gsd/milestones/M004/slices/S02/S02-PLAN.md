# S02: Delete + Instance Warnings

**Goal:** User can delete custom classes and properties from the Ontology Viewer, with instance-count warnings on class deletion, confirmation dialogs, and clean removal from TBox/RBox.
**Demo:** User opens Ontology Viewer → clicks delete on a user-created class → sees confirmation modal with instance/subclass counts → confirms → class disappears from TBox tree. User switches to RBox → clicks delete on a user-created property → confirms via browser dialog → property disappears from RBox table.

## Must-Haves

- `OntologyService.get_delete_class_info()` returns instance count and subclass count for a given class IRI
- `OntologyService.delete_property()` removes all triples for a property from user-types graph
- `GET /ontology/delete-class-check` route returns HTML confirmation fragment with instance/subclass counts
- `DELETE /ontology/delete-property` route deletes a user property with namespace guard
- TBox delete buttons open a confirmation modal (not `hx-confirm`) showing dynamic instance/subclass counts
- RBox shows delete buttons for user-created properties with `hx-confirm` confirmation
- RBox `hx-trigger` includes `propertyDeleted` for auto-refresh after property deletion
- `_property_source()` returns `'user'` for `urn:sempkm:user-types:` IRIs (not `'sempkm'`)
- Unit tests cover `delete_property()`, `get_delete_class_info()`, delete-property endpoint, and delete-class-check endpoint
- Delete confirmation overlay added to `ontology_page.html` with Escape-to-close support

## Proof Level

- This slice proves: contract + integration
- Real runtime required: yes (browser verification of modal flow and htmx refresh)
- Human/UAT required: no

## Verification

- `cd backend && python -m pytest tests/test_class_creation.py -v` — all new and existing delete tests pass
- `cd backend && python -m pytest tests/test_ontology_service.py -v` — existing tests unbroken
- Browser: create a class → delete it → confirmation modal shows instance count → TBox auto-refreshes
- Browser: create a property → switch to RBox → delete it → RBox auto-refreshes

## Observability / Diagnostics

- Runtime signals: `logger.info("Deleted property %s", prop_iri)` in service; existing class delete logging preserved
- Inspection surfaces: HX-Trigger headers (`classDeleted`, `propertyDeleted`) confirm delete completed; confirmation modal shows instance/subclass counts before action
- Failure visibility: 403 on namespace guard violation, 500 on SPARQL failure, both logged with `logger.error`
- Redaction constraints: none (no secrets involved)

## Integration Closure

- Upstream surfaces consumed: `OntologyService.delete_class()` (existing), `_build_delete_class_sparql()` / `_build_delete_shape_sparql()` (existing), `get_class_detail()` instance/subclass count pattern (existing), overlay modal pattern from `ontology_page.html` (existing)
- New wiring introduced in this slice: `GET /ontology/delete-class-check` → confirmation modal overlay → `DELETE /ontology/delete-class`; `DELETE /ontology/delete-property` → `HX-Trigger: propertyDeleted` → RBox auto-refresh; `_property_source` fix for user-types IRIs
- What remains before the milestone is truly usable end-to-end: S03 (Custom section on Mental Models), S04 (Create-New-Object tab fix), S05 (Docs & Test Coverage)

## Tasks

- [x] **T01: Add delete_property() service + get_delete_class_info() + unit tests** `est:1h`
  - Why: The service layer has no property deletion and no pre-delete class inspection. Both are needed before routes and UI.
  - Files: `backend/app/ontology/service.py`, `backend/tests/test_class_creation.py`
  - Do: Add `delete_property()` (single DELETE WHERE on property IRI in user-types graph), `get_delete_class_info()` (queries instance count + subclass count using patterns from `get_class_detail()`), fix `_property_source()` to return `'user'` for user-types IRIs. Write unit tests for all three.
  - Verify: `cd backend && python -m pytest tests/test_class_creation.py -v -k "delete_property or delete_class_info or property_source"` — all pass
  - Done when: `delete_property()` generates correct SPARQL, `get_delete_class_info()` returns `{instance_count, subclass_count, label}`, `_property_source` returns `'user'` for user-types IRIs, all tests green

- [x] **T02: Add delete-property route + delete-class-check route + endpoint tests** `est:1h`
  - Why: UI needs HTTP endpoints to call. delete-property mirrors delete-class pattern; delete-class-check provides the dynamic confirmation data.
  - Files: `backend/app/ontology/router.py`, `backend/app/templates/browser/ontology/delete_class_confirm.html`, `backend/tests/test_class_creation.py`
  - Do: Add `DELETE /ontology/delete-property` with user-types namespace guard, returning `HX-Trigger: propertyDeleted`. Add `GET /ontology/delete-class-check` that calls `get_delete_class_info()` and renders a confirmation HTML fragment. Create `delete_class_confirm.html` template showing label, instance count, subclass count, warning text, and a Confirm Delete button that calls the existing `DELETE /ontology/delete-class`. Write endpoint tests for both routes.
  - Verify: `cd backend && python -m pytest tests/test_class_creation.py -v -k "delete_property_endpoint or delete_class_check"` — all pass
  - Done when: delete-property returns 200 + HX-Trigger on success, 403 on non-user IRI; delete-class-check returns HTML with instance/subclass counts; confirmation template has a working delete button

- [x] **T03: Wire delete confirmation modal + RBox delete buttons in templates** `est:1h`
  - Why: The UI currently uses static `hx-confirm` for class deletion (can't show counts) and has no delete buttons for properties. This task replaces TBox delete flow with the confirmation modal and adds RBox delete buttons.
  - Files: `backend/app/templates/browser/ontology/ontology_page.html`, `backend/app/templates/browser/ontology/tbox_tree.html`, `backend/app/templates/browser/ontology/tbox_children.html`, `backend/app/templates/browser/ontology/rbox_legend.html`, `frontend/static/css/workspace.css`
  - Do: (1) Add delete-confirmation overlay div to `ontology_page.html` with JS functions `openDeleteClassConfirm(classIri)` and `closeDeleteConfirm()`, wired to fetch `/ontology/delete-class-check` into the overlay. (2) Replace `hx-delete`/`hx-confirm` on TBox delete buttons in both `tbox_tree.html` and `tbox_children.html` with `onclick="openDeleteClassConfirm('{{ cls.iri }}')"`. (3) Add delete buttons for user properties in `rbox_legend.html` (rows where IRI contains 'user-types') with `hx-delete` + `hx-confirm`. (4) Update RBox `hx-trigger` to include `propertyDeleted`. (5) Add `.rbox-delete-btn` CSS styles.
  - Verify: Docker up → open Ontology Viewer → TBox delete button opens modal → confirm deletes class → TBox refreshes. RBox delete button removes property → RBox refreshes.
  - Done when: Class deletion uses confirmation modal with dynamic counts, property deletion works from RBox with auto-refresh, both TBox and RBox update after deletions

## Files Likely Touched

- `backend/app/ontology/service.py`
- `backend/app/ontology/router.py`
- `backend/tests/test_class_creation.py`
- `backend/app/templates/browser/ontology/ontology_page.html`
- `backend/app/templates/browser/ontology/tbox_tree.html`
- `backend/app/templates/browser/ontology/tbox_children.html`
- `backend/app/templates/browser/ontology/rbox_legend.html`
- `backend/app/templates/browser/ontology/delete_class_confirm.html`
- `frontend/static/css/workspace.css`
