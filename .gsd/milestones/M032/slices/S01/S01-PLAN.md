# S01: Multi-Object Form Groups with Slot IRI Resolution

**Goal:** Users create multiple linked objects in one submission via a form-group dashboard block that renders multiple SHACL sub-forms and connects them with edges using slot-based IRI resolution.
**Demo:** User opens a dashboard with a form-group block, fills two SHACL sub-forms (e.g., Note + Task), submits once, and both objects are created with an edge linking them — visible in the object browser.

## Must-Haves

- `form-group` block type registered in BlockRegistry with config schema declaring slots (list of `{name, target_class}`) and edges (list of `{source_slot, target_slot, predicate}`)
- `POST /api/commands` batch payloads support `@slot:name` IRI references that resolve to the minted IRI of a prior command in the same batch
- `render_block()` handler for `form-group` renders multiple SHACL sub-forms in one block with namespaced IDs for DOM isolation
- Frontend JS collects all sub-forms, constructs the batch command payload with `@slot:` references for edges, and POSTs to `/api/commands`
- Builder config form for form-group allows defining slots (type picker per slot) and edges (slot-to-slot relationship wiring)
- Existing dashboard tests pass without regression

## Proof Level

- This slice proves: integration (backend slot resolution + frontend multi-form rendering + command API)
- Real runtime required: yes (SHACL form rendering needs ShapesService with triplestore data)
- Human/UAT required: yes (visual check of multi-form layout and create flow)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_block_registry.py tests/test_form_group.py tests/test_dashboard.py tests/test_dashboard_builder.py -v`
- `tests/test_form_group.py` covers: form-group block validation, slot resolution in batch commands (happy path + error cases), render_block output for form-group type
- Existing `tests/test_block_registry.py` updated to expect 7 block types (was 6)
- Existing `tests/test_dashboard.py` and `tests/test_dashboard_builder.py` pass unchanged (regression guard)

## Observability / Diagnostics

- Runtime signals: `[commands] Resolved @slot:X → <minted-iri>` structured log during batch slot resolution
- Inspection surfaces: Command API response includes `results[].iri` for each created object — verifiable via API
- Failure visibility: If a `@slot:name` references a slot not yet defined by a prior command, the API returns 400 with a clear error message identifying the unresolved slot name

## Integration Closure

- Upstream surfaces consumed: `backend/app/dashboard/registry.py` (BlockRegistry), `backend/app/commands/router.py` (batch command execution), `backend/app/browser/objects.py` (SHACL form rendering via `/objects/new`), `backend/app/templates/forms/object_form.html`
- New wiring introduced in this slice: form-group render handler in `dashboard/router.py`, slot resolution in `commands/router.py`, form-group builder config in `dashboard_builder.html`, form-group submission JS in `workspace.js`
- What remains before the milestone is truly usable end-to-end: S02 (data widgets), S03 (E2E + docs)

## Tasks

- [x] **T01: Register form-group block type and implement slot-based IRI resolution in batch commands** `est:2h`
  - Why: The form-group block type must exist in the registry for validation and builder palette. Slot-based IRI resolution is the core backend risk — it enables cross-command references so edge.create can target objects created in the same batch.
  - Files: `backend/app/dashboard/registry.py`, `backend/app/commands/router.py`, `backend/tests/test_form_group.py`, `backend/tests/test_block_registry.py`
  - Do: Register `form-group` BlockTypeSpec with config_schema `{slots: list, edges: list}`. In the `/api/commands` endpoint, after parsing commands, scan for `@slot:name` patterns in EdgeCreateParams source/target fields. Maintain a `slot_map: dict[str, str]` populated from each object.create's result IRI keyed by the command's `slot` field. Resolve all `@slot:` references before dispatching. Return 400 if any slot reference is unresolved.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_form_group.py tests/test_block_registry.py -v`
  - Done when: form-group validates in BlockRegistry, batch with `@slot:note` in edge.create source resolves to the minted IRI from a prior object.create with `slot: "note"`, and unresolved slots return 400.

- [x] **T02: Render form-group block with multiple SHACL sub-forms and submission JS** `est:2h`
  - Why: The form-group block needs to render in the dashboard viewer, showing one SHACL form per slot, and submit all forms as a single batch command with slot references for edges.
  - Files: `backend/app/dashboard/router.py`, `backend/app/templates/browser/dashboard_form_group.html`, `frontend/static/js/workspace.js`, `frontend/static/css/workspace.css`, `backend/tests/test_form_group.py`
  - Do: Add `form-group` handler in `render_block()` that returns an HTML template loading one SHACL sub-form per slot via htmx (each in a namespaced container with `data-slot="name"` and `data-slot-index="N"`). Add form-group template that renders slot sub-forms and a combined Submit button. Add JS function `_submitFormGroup(blockEl)` that collects form data from each slot, builds the batch payload (object.create per slot + edge.create per configured edge with `@slot:` references), POSTs to `/api/commands`, and handles success/error. Add CSS for form-group layout.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_form_group.py -v -k render` — render tests confirm HTML output contains sub-form containers per slot with correct data attributes.
  - Done when: A form-group block in a dashboard renders SHACL forms for each configured slot, and the submit button fires a batch command that creates objects and edges.

- [x] **T03: Builder config form for form-group and integration verification** `est:1.5h`
  - Why: Users need to configure form-group blocks in the dashboard builder — defining slots (type per slot) and edges (which slots to connect and with what predicate). This completes the end-to-end flow.
  - Files: `backend/app/templates/browser/dashboard_builder.html`, `frontend/static/css/workspace.css`, `backend/tests/test_form_group.py`
  - Do: Add `case 'form-group':` to `getTypeConfigHTML()` in the builder template. Render a dynamic slot list with "Add Slot" button (each slot has name input + class search). Render an edge list with "Add Edge" button (each edge has source slot dropdown, target slot dropdown, predicate input). Collect config into `{slots: [{name, target_class}], edges: [{source_slot, target_slot, predicate}]}`. Add integration test that creates a dashboard with form-group block via API and verifies it renders.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_form_group.py tests/test_dashboard_builder.py -v`
  - Done when: Form-group appears in builder palette, user can add/remove slots and edges, saving persists the config, and loading the dashboard renders the form-group block.

## Files Likely Touched

- `backend/app/dashboard/registry.py`
- `backend/app/commands/router.py`
- `backend/app/commands/schemas.py`
- `backend/app/dashboard/router.py`
- `backend/app/templates/browser/dashboard_builder.html`
- `backend/app/templates/browser/dashboard_form_group.html`
- `frontend/static/js/workspace.js`
- `frontend/static/css/workspace.css`
- `backend/tests/test_form_group.py`
- `backend/tests/test_block_registry.py`
