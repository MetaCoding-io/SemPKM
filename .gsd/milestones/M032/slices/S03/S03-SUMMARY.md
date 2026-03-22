# S03: Multi-Object Form Groups — Summary

**Status:** Complete
**Duration:** ~55 minutes across 3 tasks
**Tests:** 73 pass (23 slot resolver + 50 block registry)

## What This Slice Delivered

A `form-group` dashboard block that creates multiple linked objects in a single atomic transaction, with SHACL-driven sub-forms rendered as collapsible sections and cross-object IRI references resolved via a slot-based mechanism.

### Core Capabilities

1. **Slot-based IRI resolution engine** (`backend/app/commands/slot_resolver.py`): `resolve_and_dispatch()` processes commands sequentially, accumulates a `slot_map[slot_id] → IRI` from `object.create` results, and substitutes `$slot:xxx` placeholders in downstream commands (e.g., `edge.create` targeting a just-created object). Recursive substitution handles nested dicts/lists. Unresolved references produce HTTP 400 with descriptive error.

2. **Batch command endpoint** (`POST /api/commands/batch`): New endpoint in `commands/router.py` accepts an array of commands with optional `_slot_id` fields. Returns `{event_iri, timestamp, operation_count, affected_count, slot_map}` — the slot_map enables client-side debugging of IRI resolution.

3. **Form-group block type** (type #10 in BLOCK_REGISTRY): Registered with icon "layers", category "data", default 6×8 grid dimensions. Config schema validates `shapes` as a list. `render_block()` branch fetches SHACL `NodeShapeForm` per sub-form type via `ShapesService.get_form_for_type()`, renders `block_form_group.html` template with collapsible `<details>` sections using the existing `_field.html` `render_field()` macro.

4. **Client-side batch submission**: JavaScript in the template collects field values per `data-slot-id` section, builds `object.create` commands with `_slot_id` and `edge.create` commands with `$slot:xxx` references, POSTs to `/api/commands/batch`. Success dispatches `sempkm:form-group-created` custom event with `{dashboard_id, slot_map}`.

5. **Builder config panel**: `case 'form-group':` in `getTypeConfigHTML()` with repeatable shape entries — type IRI picker (reusing `_builderClassSearch` autocomplete), label, slot ID, and collapsible edge-linking config (target slot + predicate IRI). Save serialization in `_builderSave()` builds nested `{shapes: [{type_iri, label, slot_id, edge_to?}]}`.

6. **CSS styling**: ~180 lines for `.dashboard-block-form-group` (scrollable container), `.form-group-section` (border-left accent), `.form-group-edge-badge` (pill), `.form-group-actions` (submit row), builder `.shape-entry` cards, and a global GridStack `.suggestions-dropdown` z-index fix (1000).

## Key Patterns Established

- **`$slot:xxx` placeholder pattern**: Cross-command IRI references in batch operations. Commands declare `_slot_id`, later commands use `$slot:xxx` in any string field. Sequential dispatch guarantees ordering.
- **DOM-based config serialization override**: `_builderSave()` checks `typeName` after generic `[data-key]` collection and overrides `block.config` for block types with nested config structures (like the `shapes` array).
- **Per-shape error tolerance**: If `get_form_for_type()` fails for one sub-form, that section renders an error div while other sub-forms still render. Avoids all-or-nothing rendering.
- **Edge config via data attributes**: `data-edge-predicate` and `data-edge-target` on `<details>` sections — more reliable for JS access than parsing badge text.

## Files Created

| File | Purpose |
|------|---------|
| `backend/app/commands/slot_resolver.py` | `resolve_and_dispatch()` + `_substitute_slots()` for slot-based IRI resolution |
| `backend/app/templates/browser/blocks/block_form_group.html` | Form-group template with collapsible sub-forms and batch submit JS |
| `backend/tests/test_slot_resolver.py` | 23 tests across 6 test classes |

## Files Modified

| File | Change |
|------|--------|
| `backend/app/commands/router.py` | Added `POST /api/commands/batch` endpoint with `BatchCommandRequest` schema |
| `backend/app/dashboard/registry.py` | Registered form-group BlockTypeSpec (type #10, icon "layers", category "data") |
| `backend/app/dashboard/router.py` | Added `elif block_type == "form-group"` branch with ShapesService integration |
| `backend/app/templates/browser/dashboard_builder.html` | Added form-group config panel, `_buildShapeEntryHTML()`, save serialization |
| `frontend/static/css/workspace.css` | ~180 lines: form-group rendering + builder config + z-index fix |
| `backend/tests/test_block_registry.py` | Updated EXPECTED_TYPES to 10, added 5 form-group tests |

## Verification Results

All 9 slice-level checks pass:
- ✅ `pytest tests/test_slot_resolver.py` — 23 passed
- ✅ `pytest tests/test_block_registry.py` — 50 passed
- ✅ `slot_resolver.py` exists and importable
- ✅ `block_form_group.html` exists
- ✅ `form-group` in registry.py, router.py, dashboard_builder.html, workspace.css
- ✅ Unresolved slot error message present in slot_resolver.py

## Observability

- **Batch endpoint response**: Returns `slot_map` dict for client debugging
- **Error responses**: HTTP 400 with descriptive message naming unresolved `$slot:xxx` and listing resolved slots
- **Render-time logging**: WARNING on `get_form_for_type()` failures with dashboard_id, block_index, type_iri
- **Client-side**: `.form-group-status` shows submit progress/success/error; `sempkm:form-group-created` event dispatched on success
- **Builder save**: `console.info` logs full block array including nested shapes config

## What the Next Slice/Milestone Should Know

- S03 completes M032. All 10 block types are registered, the GridStack layout engine is operational, and the batch command endpoint supports multi-object atomic creation.
- The `$slot:xxx` pattern is reusable for any future batch operation needing cross-command references.
- The batch endpoint (`POST /api/commands/batch`) is a general-purpose facility — not form-group-specific. Any client needing atomic multi-object creation can use it directly.
- Form-group rendering requires the triplestore to have SHACL shapes for configured types. Empty shapes config renders an error div, not a crash.
- The builder config panel uses the same `_builderClassSearch` autocomplete for type IRI selection that other create-form blocks use.
