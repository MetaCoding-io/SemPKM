---
estimated_steps: 5
estimated_files: 4
skills_used: []
---

# T01: Register form-group block type and implement slot-based IRI resolution in batch commands

**Slice:** S01 — Multi-Object Form Groups with Slot IRI Resolution
**Milestone:** M032

## Description

Register the `form-group` block type in BlockRegistry so it can be validated, appear in the builder palette, and be stored in dashboards. Then implement `@slot:name` IRI resolution in the `/api/commands` endpoint so batch payloads can reference IRIs minted by earlier commands in the same batch — this is the core mechanism that enables form-group to create linked objects in one submission.

The existing `/api/commands` already supports batch (array) payloads and dispatches them sequentially. Slot resolution adds a pre-processing step: before dispatching each command, scan its params for `@slot:name` patterns and replace them with the actual IRI minted by a prior command that declared that slot name.

## Steps

1. **Register `form-group` in BlockRegistry** (`backend/app/dashboard/registry.py`):
   - Add a new `BlockTypeSpec` for `form-group` with `type_name="form-group"`, `label="Form Group"`, `icon="layers"`, `category="data"`, `config_schema={"slots": list, "edges": list}`, `default_w=12`, `default_h=8`.

2. **Extend Command schema for slot declarations** (`backend/app/commands/schemas.py`):
   - Add an optional `slot: str | None = None` field to `ObjectCreateCommand` (not on the Params — on the command-level model). This lets the batch payload declare which slot name this object.create fills. Example payload: `{"command": "object.create", "slot": "note", "params": {...}}`.

3. **Implement slot resolution in the commands router** (`backend/app/commands/router.py`):
   - In `execute_commands()`, after parsing commands, process them sequentially with a `slot_map: dict[str, str]` accumulator.
   - For each command: (a) if it has a `slot` field, after dispatch, record `slot_map[slot] = operation.affected_iris[0]`. (b) Before dispatch, if the command is `edge.create` and its `source` or `target` starts with `@slot:`, look up the rest of the string in `slot_map` and replace. If not found, return 400 with `"Unresolved slot reference: @slot:X"`.
   - Add a structured log line: `logger.info("Resolved @slot:%s → %s", slot_name, resolved_iri)`.

4. **Update existing block registry test** (`backend/tests/test_block_registry.py`):
   - Change `EXPECTED_TYPES` set to include `"form-group"` (7 types total).
   - Add a test that `form-group` has the correct config_schema, category, and dimensions.

5. **Write slot resolution tests** (`backend/tests/test_form_group.py`):
   - Test batch payload with two `object.create` (slot "note" and slot "task") + one `edge.create` using `@slot:note` as source and `@slot:task` as target → all three commands succeed, edge uses resolved IRIs.
   - Test unresolved slot reference → 400 error with descriptive message.
   - Test slot declared on non-object.create command → ignored (no crash).
   - Test form-group block validates in BlockRegistry with correct config shape.
   - Test form-group block rejects invalid config types (e.g., slots as string instead of list).

## Must-Haves

- [ ] `form-group` block type registered in `BLOCK_REGISTRY` with `config_schema={"slots": list, "edges": list}`
- [ ] `ObjectCreateCommand` accepts optional `slot: str | None` field
- [ ] Batch commands with `@slot:name` references in `edge.create` source/target resolve to minted IRIs
- [ ] Unresolved `@slot:name` returns HTTP 400 with clear error message
- [ ] Existing block registry tests updated and passing (7 types)
- [ ] New `test_form_group.py` covers slot resolution happy path and error cases

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_form_group.py tests/test_block_registry.py -v` — all tests pass
- `cd backend && .venv/bin/python -m pytest tests/test_dashboard.py tests/test_dashboard_builder.py -v` — regression pass

## Inputs

- `backend/app/dashboard/registry.py` — existing BlockRegistry with 6 built-in types
- `backend/app/commands/router.py` — existing batch command execution logic
- `backend/app/commands/schemas.py` — existing Command discriminated union
- `backend/app/commands/dispatcher.py` — existing dispatch function
- `backend/app/commands/handlers/object_create.py` — returns Operation with `affected_iris[0]` = minted IRI
- `backend/app/commands/handlers/edge_create.py` — uses `params.source` and `params.target` as IRIs
- `backend/tests/test_block_registry.py` — existing 6-type tests to update

## Expected Output

- `backend/app/dashboard/registry.py` — form-group BlockTypeSpec added (7 types total)
- `backend/app/commands/schemas.py` — `slot` field added to ObjectCreateCommand
- `backend/app/commands/router.py` — slot resolution logic in execute_commands
- `backend/tests/test_form_group.py` — new test file with slot resolution + block validation tests
- `backend/tests/test_block_registry.py` — updated EXPECTED_TYPES to include form-group
