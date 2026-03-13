---
estimated_steps: 4
estimated_files: 5
---

# T04: E2E test + delete UI + end-to-end verification

**Slice:** S08 — In-App Class Creation
**Milestone:** M003

## Description

Write the Playwright E2E test proving the full create-class → type-picker → object-creation pipeline. Add a delete button on user-created class nodes in the TBox tree for error recovery. This task closes the loop on both TYPE-01 and TYPE-02 requirements by exercising the complete integration in a real Docker Compose stack.

## Steps

1. **Create `e2e/tests/23-class-creation/class-creation.spec.ts`** with test cases:
   - **"user can create a class and it appears in TBox"**: navigate to ontology viewer → click "Create Class" → fill name "Test Widget", select an icon, pick a parent class, add one property (name: "Label", predicate: dcterms:title, datatype: xsd:string) → submit → verify class appears in TBox tree with "user" badge and label "Test Widget"
   - **"user-created type appears in type picker and supports object creation"**: (depends on first test creating the class, or repeat class creation) → navigate to "New Object" flow → verify "Test Widget" appears in type picker → click it → verify form renders with "Label" field → fill the field → submit → verify object is created and appears in explorer
   - **"user can delete a user-created class"**: create a class → verify it's in TBox → click delete button on that class node → confirm deletion → verify class is removed from TBox tree

2. **Add selectors to `e2e/helpers/selectors.ts`**:
   - `classCreation.createButton` — "Create Class" button in TBox header
   - `classCreation.nameInput` — class name text input
   - `classCreation.iconGrid` — icon picker grid container
   - `classCreation.parentSearch` — parent class search input
   - `classCreation.propertyRow` — property editor row
   - `classCreation.addPropertyButton` — "Add Property" button
   - `classCreation.submitButton` — form submit button
   - `classCreation.deleteButton` — delete button on TBox user-type node

3. **Add delete button to TBox tree nodes** in `tbox_tree.html` and `tbox_children.html`:
   - Only show for nodes whose IRI contains `user-types` (same check already used for badge)
   - Small trash icon button (Lucide `trash-2`) with `hx-delete="/browser/ontology/delete-class?class_iri={iri}"` and `hx-confirm="Delete this class? Objects of this type will lose their type."` for safety
   - `hx-swap="none"` since the TBox tree refreshes via `classDeleted` event trigger
   - Style the delete button as a subtle hover-reveal action (visible on row hover, like existing tree actions)

4. **Run full E2E suite and fix any integration gaps**:
   - Verify the complete pipeline works in the Docker Compose test stack
   - Fix any timing issues (htmx swap races, TBox refresh delays)
   - Ensure the test is stable and doesn't depend on test ordering

## Must-Haves

- [ ] E2E test proves class creation → TBox visibility (TYPE-01)
- [ ] E2E test proves type picker inclusion → object creation with auto-generated form (TYPE-02)
- [ ] E2E test proves class deletion removes it from TBox
- [ ] Delete button shown only on user-created class nodes
- [ ] Delete button has confirmation dialog for safety
- [ ] All E2E tests pass reliably in Docker Compose test stack

## Verification

- `cd e2e && npx playwright test tests/23-class-creation/ --headed` — all 3 test cases pass
- `cd backend && .venv/bin/pytest tests/test_class_creation.py -v` — all unit tests still pass (no regressions)

## Observability Impact

- Signals added/changed: None (E2E tests observe existing signals; delete button uses existing endpoint from T02)
- How a future agent inspects this: Run the E2E test with `--headed` to see the browser interaction; check test output for assertion failures; selectors in helpers.ts map test locators to DOM elements
- Failure state exposed: Playwright test failures include screenshots and trace files; each assertion specifies what it expects

## Inputs

- `backend/app/ontology/router.py` — POST create-class and DELETE delete-class endpoints from T02
- `backend/app/templates/browser/ontology/create_class_form.html` — form UI from T03
- `backend/app/templates/browser/ontology/tbox_tree.html` — TBox tree with user badge from S07
- `e2e/helpers/selectors.ts` — existing selector patterns
- `e2e/tests/22-ontology/ontology-viewer.spec.ts` — reference for ontology viewer test patterns

## Expected Output

- `e2e/tests/23-class-creation/class-creation.spec.ts` — 3 passing E2E test cases
- `e2e/helpers/selectors.ts` — extended with classCreation selectors block
- `backend/app/templates/browser/ontology/tbox_tree.html` — delete button for user-type nodes
- `backend/app/templates/browser/ontology/tbox_children.html` — delete button for user-type child nodes
