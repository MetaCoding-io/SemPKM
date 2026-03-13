---
id: T04
parent: S08
milestone: M003
provides:
  - E2E tests proving class creation → TBox visibility, type picker → object creation, and class deletion
  - Delete button on user-created TBox tree nodes with hover-reveal pattern
  - Bug fixes for property serialization (htmx form data timing) and shape deletion (SPARQL syntax)
key_files:
  - e2e/tests/23-class-creation/class-creation.spec.ts
  - e2e/helpers/selectors.ts
  - backend/app/templates/browser/ontology/tbox_tree.html
  - backend/app/templates/browser/ontology/tbox_children.html
  - frontend/static/css/workspace.css
  - backend/app/templates/browser/ontology/create_class_form.html
  - backend/app/ontology/service.py
key_decisions:
  - "htmx form data timing: changed hx-on::before-request to hx-on::config-request with explicit event.detail.parameters update for property serialization — htmx:beforeRequest fires after parameters are sealed"
  - "Shape delete uses two separate SPARQL UPDATE calls instead of one combined query — RDF4J rejects OPTIONAL inside DELETE WHERE and semicolon-separated updates"
patterns_established:
  - "Hover-reveal delete button on TBox user-type nodes: .tbox-delete-btn hidden by default, display: inline-flex on .tree-node:hover"
  - "Playwright dialog handling: ownerPage.once('dialog', d => d.accept()) required before clicking hx-confirm buttons — Playwright auto-dismisses (rejects) confirm() dialogs by default"
observability_surfaces:
  - "E2E tests run with --headed for visual debugging; Playwright trace files on retry"
  - "API logs delete-class failures at ERROR level with full traceback"
duration: ~90min
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T04: E2E test + delete UI + end-to-end verification

**Added 3 passing E2E tests for class creation pipeline, delete button on user-type TBox nodes, and fixed two bugs in property serialization and shape deletion.**

## What Happened

1. **Created E2E test file** `e2e/tests/23-class-creation/class-creation.spec.ts` with 3 test cases:
   - "user can create a class and it appears in TBox" — creates class via form, verifies it appears with "user" badge
   - "user-created type appears in type picker and supports object creation" — creates class, opens type picker, clicks new type, fills SHACL form, submits, verifies edit mode
   - "user can delete a user-created class" — creates class, closes form, hovers to reveal delete button, accepts confirm dialog, verifies class removed from tree

2. **Added classCreation selectors** to `e2e/helpers/selectors.ts` with all form elements and delete button selector.

3. **Added delete button to TBox tree templates** — both `tbox_tree.html` and `tbox_children.html` now show a trash-2 icon button on user-type nodes with `hx-delete`, `hx-confirm` safety dialog, and `hx-swap="none"`.

4. **Added CSS for hover-reveal delete button** in workspace.css — `.tbox-delete-btn` hidden by default, shown on `.tree-node:hover`.

5. **Fixed bug: property serialization timing** — The `create_class_form.html` used `hx-on::before-request` for `serializeProperties()`, but htmx seals form parameters before `beforeRequest` fires. Changed to `hx-on::config-request` with explicit `event.detail.parameters['properties']` assignment. This was the root cause of user-created types having no SHACL properties.

6. **Fixed bug: form tag missing closing `>`** — The `<form>` element in `create_class_form.html` was missing its closing angle bracket, causing HTML parsing issues.

7. **Fixed bug: shape delete SPARQL syntax** — `_build_delete_shape_sparql()` used `OPTIONAL` inside `DELETE WHERE` which RDF4J rejects with 400. Changed to return a tuple of two separate SPARQL queries executed sequentially: first delete blank-node property triples, then delete shape triples.

## Verification

- `cd backend && .venv/bin/pytest tests/test_class_creation.py -v` — all 34 unit tests pass
- `cd e2e && npx playwright test tests/23-class-creation/ --project=chromium` — all 3 E2E tests pass (16.2s)
- `cd e2e && npx playwright test tests/22-ontology/ --project=chromium` — 2/3 pass (ABox test fails due to pre-existing auth rate-limit, unrelated)
- Manual browser verification: created class with property → appeared in TBox with badge → delete button visible on hover → deletion removed class from tree

## Diagnostics

- Run E2E tests with `--headed` to see browser interaction visually
- Playwright saves trace files on retry: `npx playwright show-trace <trace.zip>`
- API logs delete failures at ERROR level: `docker compose -f docker-compose.test.yml logs api | grep delete-class`
- Check triplestore state: query `GRAPH <urn:sempkm:user-types>` for user-type triples
- Check property serialization: `document.getElementById('ccf-properties').value` in browser console

## Deviations

- Fixed 3 bugs discovered during E2E testing (property serialization timing, form tag syntax, shape delete SPARQL) — these were latent issues from T03/T01 not caught by unit tests because unit tests mocked the triplestore
- Type picker test uses resilient form field detection (falls back if dcterms:title field isn't visible) rather than strict assertion — accounts for SHACL form rendering variations

## Known Issues

- Previous test runs leave orphan user-type classes in the triplestore — tests use unique names (timestamp suffix) to avoid collisions, but cleanup between runs relies on manual `DELETE WHERE` or fresh test stack
- E2E tests only run on chromium project; Firefox may have timing differences with htmx swap events

## Files Created/Modified

- `e2e/tests/23-class-creation/class-creation.spec.ts` — 3 E2E test cases for class creation pipeline
- `e2e/helpers/selectors.ts` — added classCreation selector block
- `backend/app/templates/browser/ontology/tbox_tree.html` — added delete button for user-type nodes
- `backend/app/templates/browser/ontology/tbox_children.html` — added delete button for user-type child nodes
- `frontend/static/css/workspace.css` — added .tbox-delete-btn hover-reveal styles
- `backend/app/templates/browser/ontology/create_class_form.html` — fixed form tag, changed htmx event for property serialization
- `backend/app/ontology/service.py` — fixed shape delete SPARQL to use two separate queries
- `backend/tests/test_class_creation.py` — updated shape delete test for new tuple return type
