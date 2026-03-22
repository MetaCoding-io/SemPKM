# S03: Multi-Object Form Groups

**Goal:** A `form-group` dashboard block creates multiple linked objects atomically via a slot-based batch transaction endpoint, with SHACL-driven sub-forms rendered as collapsible sections.
**Demo:** A dashboard with a form-group block configured for "Project + Task" shows two sub-forms. Submitting creates both objects with an edge linking the Task to the Project, all in one atomic transaction.

## Must-Haves

- `form-group` block type registered in `BLOCK_REGISTRY` (type #10)
- `POST /api/commands/batch` endpoint with slot-based IRI resolution (`$slot:xxx` references)
- `block_form_group.html` Jinja2 template rendering SHACL sub-forms via `_field.html` macro
- Client-side submit handler that collects sub-form data, builds slot-mapped commands, POSTs to batch endpoint
- Builder config panel for form-group with repeatable shape entries (type picker + slot ID + edge config)
- Builder save serialization for nested `shapes` config array
- Unit tests for slot resolution logic (valid resolution, missing refs, ordering, error cases)
- CSS styles for form-group block (scrollable container, sub-form sections, z-index for dropdowns)

## Proof Level

- This slice proves: integration (server-side slot resolution + template rendering + client-side form collection)
- Real runtime required: yes (SHACL form rendering needs triplestore with shapes data)
- Human/UAT required: yes (form submission UX, sub-form layout, edge linking correctness)

## Verification

- `cd backend && uv run pytest tests/test_slot_resolver.py tests/test_block_registry.py -v` — all tests pass, including slot resolver unit tests and form-group in EXPECTED_TYPES
- `test -f backend/app/commands/slot_resolver.py` — slot resolver module exists
- `test -f backend/app/templates/browser/blocks/block_form_group.html` — form-group template exists
- `grep -q "form-group" backend/app/dashboard/registry.py` — block type registered
- `grep -q "form-group" backend/app/dashboard/router.py` — render branch exists
- `grep -q "form-group" backend/app/templates/browser/dashboard_builder.html` — builder config panel exists
- `grep -q "form-group" frontend/static/css/workspace.css` — CSS styles added
- `cd backend && uv run python -c "from app.commands.slot_resolver import resolve_and_dispatch; print('import ok')"` — slot resolver module importable
- `grep -q 'slot.*not resolved\|Unresolved slot' backend/app/commands/slot_resolver.py` — failure-path error message for unresolved slots exists

## Observability / Diagnostics

- Runtime signals: `logger.info()` on slot resolution success with slot count; `logger.warning()` on resolution failures with slot details
- Inspection surfaces: `POST /api/commands/batch` returns `{event_iri, operation_count, affected_count, slot_map}` — slot_map shows slot_id→IRI mappings for debugging
- Failure visibility: unresolved `$slot:` references return HTTP 400 with error message naming the missing slot; SPARQL failures in form rendering show `.dashboard-block-error` div

## Integration Closure

- Upstream surfaces consumed: `BLOCK_REGISTRY` from S01, `render_block()` pattern from S01/S02, `_field.html` macro, `ShapesService.get_form_for_type()`, `dispatch()` from commands, `EventStore.commit_bulk()`
- New wiring introduced in this slice: `POST /api/commands/batch` endpoint, `slot_resolver.py` module, form-group block in builder+viewer
- What remains before the milestone is truly usable end-to-end: nothing — S03 is the final slice

## Tasks

- [x] **T01: Implement slot-based IRI resolution and batch endpoint** `est:45m`
  - Why: The core technical challenge — creating linked objects requires resolving cross-references between commands. This is the #1 risk and must be built and tested first, independent of UI work.
  - Files: `backend/app/commands/slot_resolver.py`, `backend/app/commands/router.py`, `backend/tests/test_slot_resolver.py`
  - Do: Create `slot_resolver.py` with `resolve_and_dispatch()` that processes commands sequentially, populates a `slot_map[slot_id] → IRI` from `object.create` operations, and substitutes `$slot:xxx` references in `edge.create` params. Add `POST /api/commands/batch` endpoint in `router.py` that uses this function. Write comprehensive unit tests mocking `dispatch()`.
  - Verify: `cd backend && uv run pytest tests/test_slot_resolver.py -v` — all tests pass
  - Done when: slot resolver correctly handles valid resolution, missing slot refs, ordering validation, and error rollback; batch endpoint returns slot_map in response

- [x] **T02: Register form-group block type and implement server-side rendering** `est:45m`
  - Why: The form-group block needs to appear in the registry, render sub-forms via SHACL shapes on the dashboard page, and submit data to the batch endpoint from T01.
  - Files: `backend/app/dashboard/registry.py`, `backend/app/dashboard/router.py`, `backend/app/templates/browser/blocks/block_form_group.html`, `backend/tests/test_block_registry.py`
  - Do: Register `form-group` BlockTypeSpec in `_build_default_registry()`. Add `elif block_type == "form-group"` branch in `render_block()` that fetches shapes via `ShapesService`, renders `block_form_group.html`. Create the template with collapsible `<details>` sections per sub-form using `_field.html` macro, slot-prefixed field names, and client-side submit JS that POSTs to `/api/commands/batch`. Update `EXPECTED_TYPES` in test file.
  - Verify: `cd backend && uv run pytest tests/test_block_registry.py -v` — 46+ tests pass with form-group included; `test -f backend/app/templates/browser/blocks/block_form_group.html`
  - Done when: form-group block validates in registry, renders sub-forms from SHACL shapes, and client-side submit handler posts slot-mapped commands

- [x] **T03: Add builder config panel, save serialization, and CSS for form-group** `est:30m`
  - Why: Users need to configure form-group blocks in the dashboard builder (select types, define slots, wire edges) and the rendered block needs proper styling.
  - Files: `backend/app/templates/browser/dashboard_builder.html`, `frontend/static/css/workspace.css`
  - Do: Add `case 'form-group':` in `getTypeConfigHTML()` with repeatable shape entries (type IRI picker via class autocomplete, slot ID input, edge_to config). Add special-case save serialization in `_builderSave()` for nested `shapes` config. Add CSS for form-group block (scrollable container, sub-form sections, dropdown z-index).
  - Verify: `grep -q "case 'form-group'" backend/app/templates/browser/dashboard_builder.html` — config panel exists; `grep -q "form-group" frontend/static/css/workspace.css` — CSS added
  - Done when: form-group config panel renders in builder with type picker + slot ID + edge config; save serializes nested shapes array; form-group blocks have proper styling in both builder preview and dashboard page

## Files Likely Touched

- `backend/app/commands/slot_resolver.py` (new)
- `backend/app/commands/router.py`
- `backend/app/dashboard/registry.py`
- `backend/app/dashboard/router.py`
- `backend/app/templates/browser/blocks/block_form_group.html` (new)
- `backend/app/templates/browser/dashboard_builder.html`
- `frontend/static/css/workspace.css`
- `backend/tests/test_slot_resolver.py` (new)
- `backend/tests/test_block_registry.py`
