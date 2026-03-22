# S03 Research: Multi-Object Form Groups

**Depth:** Targeted  
**Slice risk:** Medium  
**Depends on:** S01 (BlockRegistry + GridStack), S02 (new block type pattern)

## Summary

S03 adds a `form-group` block type that composes multiple SHACL forms into a single dashboard widget. Submitting the form creates all objects atomically via the existing `/api/commands/bulk` endpoint, extended with a server-side **slot map** to resolve cross-object IRI references (e.g., "Task 1 links to the Project I just created"). The core technical challenge is slot-based IRI resolution—the existing bulk endpoint dispatches commands independently with no cross-referencing between them. Everything else (form rendering, block registration, config panel) follows established patterns from S01/S02.

## Recommendation

1. **Register `form-group` block type** in `registry.py` following the S02 pattern (stat-card, chart, heading are the reference).
2. **Add a new server endpoint** `POST /api/commands/batch` (or extend `/api/commands/bulk`) that accepts a slot map: each command carries a `_slot_id`, and edge commands can reference `from_slot`/`to_slot` placeholders instead of real IRIs. The server processes commands in order, resolving slot IDs to minted IRIs as it goes.
3. **Render the form-group block** via a new Jinja2 template (`block_form_group.html`) that iterates over the configured shapes, calling `ShapesService.get_form_for_type()` for each and rendering sub-forms as collapsible `<details>` sections using the existing `_field.html` macro.
4. **Client-side submission** collects all sub-form data, builds the slot-mapped command array, and POSTs to the batch endpoint. On success, show a toast/banner; on failure, show per-sub-form errors.

## Implementation Landscape

### What Exists (reuse as-is)

| Component | Location | How S03 Uses It |
|-----------|----------|-----------------|
| `BlockRegistry` singleton | `dashboard/registry.py` | `BLOCK_REGISTRY.register(BlockTypeSpec(...))` to add `form-group` |
| `_field.html` macro | `templates/forms/_field.html` | Renders individual SHACL property fields (10+ widget types, multi-value, reference search) |
| `_group.html` macro | `templates/forms/_group.html` | Renders collapsible property groups within a form |
| `object_form.html` | `templates/forms/object_form.html` | Reference pattern for full SHACL form rendering (required/optional split, groups, actions) |
| `ShapesService.get_form_for_type()` | `services/shapes.py` | Fetches `NodeShapeForm` with `PropertyShape` list for any type IRI |
| `ShapesService.get_types()` | `services/shapes.py` | Lists available types for the config panel's type picker |
| `handle_object_create()` | `commands/handlers/object_create.py` | Creates a single object → `Operation` with triples |
| `handle_edge_create()` | `commands/handlers/edge_create.py` | Creates a first-class edge resource → `Operation` with triples |
| `EventStore.commit_bulk()` | `events/store.py` | Atomic batch commit with summary metadata (~10 triples) |
| `/api/commands/bulk` endpoint | `commands/router.py` | Accepts `{commands: [...], summary, source}` → dispatches + commit_bulk |
| `_builderClassSearch()` | `dashboard_builder.html` | Autocomplete for class IRIs (reuse in form-group config panel) |
| Builder `getTypeConfigHTML()` | `dashboard_builder.html` | Switch-case pattern for per-type config panels |
| Builder `_builderSave()` | `dashboard_builder.html` | Collects `[data-key]` elements from widgets for save payload |
| Dashboard page block rendering | `dashboard/router.py` `render_block()` | Switch-case for block type → HTMLResponse (add `form-group` branch) |

### What Needs Building

| Component | Description | Complexity |
|-----------|-------------|------------|
| **Slot-based IRI resolution** | Server-side logic: process commands in order, mint IRIs for `object.create` commands, store in `slot_map[slot_id] → iri`, substitute `from_slot`/`to_slot` in edge commands before dispatch | Medium — ~60 lines of Python |
| **`form-group` BlockTypeSpec** | Registry entry with config_schema for `shapes` (list) | Trivial |
| **Config panel for form-group** | JS in `getTypeConfigHTML()`: repeatable shape entries with type IRI picker + slot ID + edge_to config | Medium — ~80 lines of JS |
| **`block_form_group.html` template** | Server-rendered Jinja2: iterates shapes, calls `get_form_for_type()` per shape, renders collapsible sections with `_field.html`, single submit button | Medium — ~80 lines of template |
| **`render_block()` branch for form-group** | In `dashboard/router.py`: fetch shapes, render template | Small — ~30 lines |
| **Client-side submit handler** | JS in the form-group template: collect all sub-form data with slot prefixes, build command array, POST to batch endpoint, handle response | Medium — ~60 lines of JS |
| **Unit tests for slot resolution** | pytest: valid resolution, missing slot refs, ordering, rollback on error | Small — ~15 tests |

### Key Code Patterns to Follow

#### Adding a Block Type (S01/S02 established pattern)

1. Register in `registry.py` → `_build_default_registry()`:
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

2. Add config panel in `dashboard_builder.html` → `getTypeConfigHTML()`:
```javascript
case 'form-group':
    return '<div class="block-config-fields">...(shape entries with type picker + slot + edge)...</div>';
```

3. Add render branch in `dashboard/router.py` → `render_block()`:
```python
elif block_type == "form-group":
    # Fetch shapes, render template
```

4. Create template in `templates/browser/blocks/block_form_group.html`

5. Update tests in `test_block_registry.py` → `EXPECTED_TYPES` set

#### IRI Minting (from `rdf/iri.py`)
```python
object_iri = mint_object_iri(base_namespace, type_local_name, slug=None)
# Returns: "{namespace}/{Type}/{uuid}"
```
The key insight: `handle_object_create()` returns an `Operation` whose `affected_iris[0]` is the minted IRI. The slot resolver reads this after dispatch to populate the slot map.

#### Form Data Extraction (from `browser/objects.py` create_object)
The existing create flow extracts properties from `request.form()` data, filtering out `type_iri`, `object_iri`, `q` fields and stripping `[]` array suffixes. The form-group client-side code must prefix field names with slot IDs to disambiguate which sub-form each field belongs to.

### Slot-Based IRI Resolution Design

The existing `/api/commands/bulk` endpoint dispatches all commands independently—no command can reference another command's output. The research (M032-RESEARCH.md §5.3) proposes `_slot_id` metadata on commands and `from_slot`/`to_slot` on edge commands.

**Recommended approach:** Add a thin resolution layer in the batch endpoint handler (or a new `/api/commands/batch` endpoint) that:

1. Accepts an extended payload:
```json
{
    "commands": [
        {"command": "object.create", "_slot_id": "project", "params": {"type": "...", "properties": {...}}},
        {"command": "object.create", "_slot_id": "task1", "params": {"type": "...", "properties": {...}}},
        {"command": "edge.create", "params": {"source": "$slot:task1", "target": "$slot:project", "predicate": "bpkm:assignedTo"}}
    ],
    "summary": "Form group: Project + 2 Tasks",
    "source": "form-group"
}
```

2. Processes commands sequentially:
   - For each `object.create` with a `_slot_id`: dispatch → read `operation.affected_iris[0]` → store in `slot_map[slot_id] = iri`
   - For `edge.create` commands: before dispatch, replace any `$slot:xxx` references in `source`/`target` params with the resolved IRI from `slot_map`
   - If a referenced slot hasn't been resolved yet → error (commands must be ordered correctly)

3. Commits all operations atomically via `commit_bulk()`

**Why not modify the existing `/api/commands/bulk`:** The bulk endpoint is already used by other callers (canvas, obsidian import). Adding slot resolution logic there risks breaking those callers if the `_slot_id` field collides. A separate endpoint or an opt-in `resolve_slots: true` flag is safer.

**Implementation location:** A new function `resolve_slots_and_dispatch()` in `commands/router.py` (or a new `commands/slot_resolver.py` module) that wraps the existing `dispatch()` call with slot map bookkeeping. The endpoint handler calls this instead of the bare dispatch loop.

### Form Rendering Architecture

The form-group block renders server-side via htmx `hx-get` (same as every other dashboard block). The endpoint:

1. Reads the block's `config.shapes` array from the dashboard spec
2. For each shape entry, calls `ShapesService.get_form_for_type(type_iri)` to get the `NodeShapeForm`
3. Passes the list of forms + slot metadata to `block_form_group.html`
4. Template renders each sub-form as a `<details open>` section with:
   - Section header showing the label + "→ links to {parent}" badge if `edge_to` is configured
   - `_field.html` macros for each property (same as `object_form.html`)
   - Field names prefixed with slot ID to disambiguate: `name="{slot_id}:{property_path}"`
5. Single "Create All" submit button at the bottom

**Client-side submission flow:**
1. Collect all form inputs, grouped by slot ID prefix
2. For each slot: build an `object.create` command with the properties
3. For each slot with `edge_to`: build an `edge.create` command with `$slot:` references
4. POST the command array to the batch endpoint
5. On success: show success message, optionally clear/reset forms
6. On error: show error message (the batch is atomic, so partial creation can't happen)

### SHACL Validation

Each sub-form validates independently via standard HTML5 validation (`required` attributes from `min_count > 0` in PropertyShape). The `_field.html` macro already adds `required` to inputs when `is_required` is true. No additional client-side SHACL validation is needed for MVP.

Cross-form validation (e.g., "at least one Task required") is explicitly out of scope per M032-RESEARCH.md §5.5.

### Config Panel Design

The form-group config panel in the dashboard builder needs to let users:
1. Add/remove shape entries (sub-forms)
2. For each entry: select a type IRI (using the existing class autocomplete), set a slot ID, optionally configure edge_to (slot reference + predicate)

This is more complex than other config panels but follows the same `[data-key]` pattern. The config is serialized as:
```json
{
    "shapes": [
        {"type_iri": "urn:...:Project", "label": "New Project", "slot_id": "project"},
        {"type_iri": "urn:...:Task", "label": "Task 1", "slot_id": "task1",
         "edge_to": {"slot_id": "project", "predicate": "bpkm:assignedTo"}}
    ]
}
```

Since the `shapes` config is a nested array (not simple key-value pairs like other blocks), the save logic in `_builderSave()` needs a special case for `form-group` blocks to serialize the shape entries from their DOM structure rather than just reading `[data-key]` values.

### CSS Considerations

The form-group block renders inside a GridStack widget's `.grid-stack-item-content` div, which has constrained dimensions. The sub-forms need to be scrollable within the widget. Key CSS:
- The form-group container should be `overflow-y: auto` with `height: 100%`
- Sub-form sections use `<details>` for collapse (matching `_group.html` pattern)
- Reference search dropdowns (`.suggestions-dropdown`) need `position: absolute` and `z-index` above the GridStack widget

**CLAUDE.md rule applies:** Lucide icons in the form-group template must use CSS sizing with `flex-shrink: 0`, not inline styles.

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Slot resolution ordering: edge commands dispatched before their referenced objects are created | High | Server-side: validate all `$slot:` references exist in `slot_map` before dispatch; client-side: always emit object.create commands before edge.create commands |
| Form field name collision: two sub-forms of the same type have identical `name` attributes | Medium | Prefix all field names with `{slot_id}:` (e.g., `project:dcterms:title`) |
| htmx attribute conflicts: `_field.html` macro generates `hx-get` for reference search with hardcoded target IDs | Medium | Generate unique IDs per sub-form by incorporating slot_id into `field_id` computation |
| GridStack widget overflow: form content exceeds widget height | Low | CSS `overflow-y: auto` on the form container; users can resize the widget |
| Suggestion dropdown z-index: `.suggestions-dropdown` rendered inside GridStack widget may be clipped | Low | CSS `z-index` override for dropdowns inside `.grid-stack-item-content` |

## File Change Inventory

| File | Change Type | Description |
|------|-------------|-------------|
| `backend/app/dashboard/registry.py` | Modify | Add `form-group` BlockTypeSpec to `_build_default_registry()` |
| `backend/app/commands/router.py` | Modify | Add `POST /api/commands/batch` endpoint (or extend `/bulk`) with slot resolution |
| `backend/app/dashboard/router.py` | Modify | Add `form-group` branch in `render_block()` |
| `backend/app/templates/browser/blocks/block_form_group.html` | **New** | Form-group block template with sub-form sections |
| `backend/app/templates/browser/dashboard_builder.html` | Modify | Add `form-group` case in `getTypeConfigHTML()` + save serialization |
| `backend/app/templates/browser/dashboard_page.html` | No change | Block rendering is via htmx `hx-get` to `render_block()` — no template change needed |
| `frontend/static/css/workspace.css` | Modify | Add form-group block styles (sub-form sections, scrollable container) |
| `backend/tests/test_block_registry.py` | Modify | Add `form-group` to `EXPECTED_TYPES`, add form-group validation tests |
| `backend/tests/test_slot_resolver.py` | **New** | Unit tests for slot-based IRI resolution logic |

## Natural Seams (Task Decomposition)

**T01: Slot-based IRI resolution (backend, testable without Docker)**
- Create `commands/slot_resolver.py` with `resolve_and_dispatch()` function
- Add/extend endpoint in `commands/router.py`
- Write `tests/test_slot_resolver.py` with unit tests mocking `dispatch()`
- Verifies: slot map population, `$slot:` substitution, ordering validation, error cases

**T02: Form-group block registration + rendering (backend + template)**
- Register `form-group` in `registry.py`
- Add `render_block()` branch in `dashboard/router.py` that calls `ShapesService`
- Create `block_form_group.html` template with sub-form sections using `_field.html`
- Add client-side submit handler JS in the template
- Update `test_block_registry.py` EXPECTED_TYPES

**T03: Builder config panel + CSS (frontend)**
- Add `form-group` case in `getTypeConfigHTML()` in `dashboard_builder.html`
- Add special-case save serialization for nested shapes config
- Add CSS for form-group block in `workspace.css`

## Skill Observations

No additional skills needed. The work uses:
- Python/FastAPI for the backend endpoint (established codebase pattern)
- Jinja2 for server-rendered templates (reusing `_field.html` macro)
- Vanilla JS for client-side form collection (no framework)
- pytest for unit tests (mocking `dispatch()` for slot resolution tests)
