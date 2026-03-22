---
estimated_steps: 5
estimated_files: 5
skills_used: []
---

# T02: Register form-group block type and implement server-side rendering

**Slice:** S03 — Multi-Object Form Groups
**Milestone:** M032

## Description

Register the `form-group` block type in the BlockRegistry (type #10), add its rendering branch in `render_block()`, and create the Jinja2 template that renders SHACL-driven sub-forms as collapsible sections. The template includes a client-side submit handler that collects all sub-form data, builds slot-mapped command payloads, and POSTs to the `/api/commands/batch` endpoint created in T01.

## Steps

1. **Register `form-group` in `backend/app/dashboard/registry.py`**:
   - Add a `BlockTypeSpec` in `_build_default_registry()`:
     ```python
     registry.register(BlockTypeSpec(
         type_name="form-group",
         label="Form Group",
         icon="layers",
         category="data",
         config_schema={"shapes": list},
         default_w=6,
         default_h=8,
     ))
     ```
   - Update the docstring comment to say "10 built-in block types".

2. **Add `render_block()` branch in `backend/app/dashboard/router.py`**:
   - Import `get_shapes_service` from `app.dependencies` and add `ShapesService` dependency to `render_block()` (or instantiate it from the `client` already available).
   - Add `elif block_type == "form-group":` branch that:
     - Reads `config.get("shapes", [])` — a list of shape dicts with `type_iri`, `label`, `slot_id`, and optional `edge_to`.
     - For each shape entry, calls `shapes_service.get_form_for_type(shape["type_iri"])` to get the `NodeShapeForm`.
     - Pairs each shape config with its form data.
     - Renders `browser/blocks/block_form_group.html` with the shapes+forms list and dashboard_id/block_index context.
   - Handle errors: if shapes config is empty → error block. If `get_form_for_type()` returns None for a type → skip or show error for that sub-form.
   - Note: `ShapesService` is available via `request.app.state.shapes_service` (same as `get_shapes_service` dependency).

3. **Create `backend/app/templates/browser/blocks/block_form_group.html`**:
   - Import the `_field.html` macro: `{% from "forms/_field.html" import render_field %}`
   - Render a scrollable container div with class `dashboard-block dashboard-block-form-group`.
   - For each shape entry, render a `<details open>` section with:
     - Summary showing the label (e.g., "New Project") and optional "→ links to {parent}" badge if `edge_to` is configured.
     - A hidden input for `type_iri` prefixed with slot_id.
     - Each property rendered via `render_field(prop)` macro, but with field names prefixed by `{slot_id}:` to disambiguate between sub-forms of the same type. Override the field `name` attribute by wrapping in a div with `data-slot-prefix`.
   - Add a single "Create All" submit button at the bottom.
   - Add inline `<script>` with the client-side submit handler:
     - On submit, iterate over each sub-form section (identified by `data-slot-id`).
     - For each section, collect all input/select/textarea values, stripping the slot prefix.
     - Build an `object.create` command for each slot: `{command: "object.create", _slot_id: slotId, params: {type: typeIri, properties: {...}}}`.
     - For each slot with `edge_to` config, build an `edge.create` command: `{command: "edge.create", params: {source: "$slot:slotId", target: "$slot:targetSlotId", predicate: predicateIri}}`.
     - POST to `/api/commands/batch` with `{commands: [...], summary: "Form group: ...", source: "form-group"}`.
     - On success: show a success toast/banner, optionally clear the forms.
     - On error: show the error message.
   - Note: use the Lucide icon pattern from CLAUDE.md — CSS sizing with `flex-shrink: 0`, not inline styles.

4. **Update `backend/tests/test_block_registry.py`**:
   - Change `EXPECTED_TYPES` count from 9 to 10 and add `"form-group"` to the set.
   - Add a `TestFormGroupBlockType` class with tests:
     - `test_form_group_is_data_category` — verify category, icon, defaults
     - `test_form_group_rejects_non_list_shapes` — config with `shapes: "not a list"` raises ValueError
     - `test_form_group_valid_config_passes` — config with `shapes: [...]` validates

5. **Verify** by running `cd backend && uv run pytest tests/test_block_registry.py -v` and checking the template file exists.

## Must-Haves

- [ ] `form-group` registered in BLOCK_REGISTRY with icon "layers", category "data", default_w=6, default_h=8
- [ ] `render_block()` has `form-group` branch that fetches SHACL shapes and renders template
- [ ] Template renders collapsible sub-form sections with `_field.html` macro
- [ ] Field names prefixed with slot_id to prevent collisions between sub-forms
- [ ] Client-side submit handler builds slot-mapped commands and POSTs to `/api/commands/batch`
- [ ] Registry tests updated with form-group in EXPECTED_TYPES (total: 10)

## Verification

- `cd backend && uv run pytest tests/test_block_registry.py -v` — all tests pass (46+)
- `test -f backend/app/templates/browser/blocks/block_form_group.html` — template exists
- `grep -q "form-group" backend/app/dashboard/registry.py` — registered
- `grep -q "form-group" backend/app/dashboard/router.py` — render branch exists

## Inputs

- `backend/app/dashboard/registry.py` — BlockRegistry with 9 existing types (S01/S02)
- `backend/app/dashboard/router.py` — render_block() with existing block type branches
- `backend/app/templates/forms/_field.html` — field rendering macro to reuse
- `backend/app/templates/forms/object_form.html` — reference pattern for SHACL form rendering
- `backend/app/services/shapes.py` — ShapesService with get_form_for_type() method
- `backend/app/commands/slot_resolver.py` — batch endpoint from T01 (client-side JS calls it)
- `backend/tests/test_block_registry.py` — existing test file to extend

## Expected Output

- `backend/app/dashboard/registry.py` — modified with form-group BlockTypeSpec
- `backend/app/dashboard/router.py` — modified with form-group render branch
- `backend/app/templates/browser/blocks/block_form_group.html` — new template
- `backend/tests/test_block_registry.py` — modified with form-group tests

## Observability Impact

- **New render-time logging**: `render_block()` form-group branch logs `WARNING` when `ShapesService.get_form_for_type()` fails for a specific type IRI, including dashboard ID, block index, type IRI, and exception details.
- **Error visibility**: Empty/invalid `shapes` config renders `.dashboard-block-error` div visible to the user. Per-shape errors (type not found in SHACL) render inline error within the specific sub-form section while allowing other sub-forms to render.
- **Client-side status**: The `form-group-status` element shows submission progress ("Submitting…"), success ("Created N object(s)"), or error messages from the batch endpoint. Errors from `/api/commands/batch` (including unresolved slot references) are surfaced directly.
- **Custom event**: `sempkm:form-group-created` dispatched on `document` after successful batch creation, with `{dashboard_id, slot_map}` in detail — other dashboard blocks can listen and refresh.
- **Inspection**: A future agent can verify form-group rendering by hitting `GET /browser/dashboard/{id}/block/{index}` for a form-group block and checking for `dashboard-block-form-group` class in the HTML response.
