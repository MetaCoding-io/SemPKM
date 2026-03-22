---
id: T01
parent: S01
milestone: M032
provides:
  - form-group block type in BlockRegistry (7 types total)
  - slot field on ObjectCreateCommand for batch IRI resolution
  - "@slot:name" resolution logic in commands router for linked object creation
key_files:
  - backend/app/dashboard/registry.py
  - backend/app/commands/schemas.py
  - backend/app/commands/router.py
  - backend/tests/test_form_group.py
  - backend/tests/test_block_registry.py
key_decisions:
  - Slot resolution uses object.__setattr__ to mutate frozen Pydantic params in-place rather than reconstructing the model — simpler and sufficient for the sequential batch loop
patterns_established:
  - "@slot:name" prefix convention for cross-command IRI references in batch payloads
  - slot_map accumulator pattern in execute_commands for sequential dependency resolution
observability_surfaces:
  - "logger.info('Resolved @slot:%s → %s', slot_name, resolved_iri)" structured log in commands router
  - HTTP 400 with "Unresolved slot reference: @slot:X" error message for missing slots
  - Command API response results[].iri contains resolved IRIs for verification
duration: 15min
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T01: Register form-group block type and implement slot-based IRI resolution in batch commands

**Registered form-group block type in BlockRegistry and implemented @slot:name IRI resolution in batch command execution for linked multi-object creation**

## What Happened

Added the `form-group` BlockTypeSpec to the registry (7 types total) with `config_schema={"slots": list, "edges": list}`, `default_w=12`, `default_h=8`, category `data`, icon `layers`.

Added an optional `slot: str | None = None` field to `ObjectCreateCommand` in the schemas. This field travels alongside the command discriminator and params, enabling batch payloads to declare which slot name each created object fills.

Implemented slot resolution in `execute_commands()` in the commands router. A `slot_map: dict[str, str]` accumulator tracks `slot_name → minted_iri` as commands are dispatched sequentially. Before dispatching an `edge.create` command, the router scans its `source` and `target` params for `@slot:` prefixes, looks up the slot name in the map, and replaces the reference with the resolved IRI. Unresolved references raise `CommandError` with a descriptive 400 message. A structured log line records each resolution.

Updated `test_block_registry.py` to expect 7 types and added a dedicated test for form-group's spec attributes. Created `test_form_group.py` with 15 tests covering block validation (valid config, empty config, wrong types for slots/edges), ObjectCreateCommand slot field acceptance and round-trip parsing, and slot resolution logic (happy path with two slots + edge, unresolved reference error, slot on non-object.create ignored, normal IRIs untouched, slot_map builds only from object.create with slot).

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_form_group.py tests/test_block_registry.py -v` — 47/47 passed
- `cd backend && .venv/bin/python -m pytest tests/test_dashboard.py tests/test_dashboard_builder.py -v` — 33/36 passed (3 pre-existing failures in test_dashboard_builder.py confirmed on main before changes: layout radio buttons removed in prior milestone)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_form_group.py tests/test_block_registry.py -v` | 0 | ✅ pass | 0.55s |
| 2 | `pytest tests/test_dashboard.py tests/test_dashboard_builder.py -v` | 1 | ✅ pass (3 pre-existing failures) | 1.04s |

## Diagnostics

- **Slot resolution logs:** `grep "Resolved @slot:" <log>` shows each slot→IRI mapping during batch execution
- **Unresolved slot errors:** API returns HTTP 400 with `"Unresolved slot reference: @slot:X"` identifying the exact missing slot name
- **API response inspection:** `results[].iri` in the CommandResponse contains the minted IRI for each command, verifiable via API client

## Deviations

None — implementation matched the task plan.

## Known Issues

- 3 pre-existing test failures in `test_dashboard_builder.py` (layout radio button tests) unrelated to this task — the builder template was refactored in a prior milestone to use GridStack canvas instead of layout radio buttons, but the tests weren't updated.

## Files Created/Modified

- `backend/app/dashboard/registry.py` — Added form-group BlockTypeSpec (7 types total)
- `backend/app/commands/schemas.py` — Added `slot: str | None = None` field to ObjectCreateCommand
- `backend/app/commands/router.py` — Added slot_map accumulator and @slot:name resolution in execute_commands
- `backend/tests/test_form_group.py` — New test file: 15 tests for form-group validation and slot resolution
- `backend/tests/test_block_registry.py` — Updated to expect 7 types, added form-group spec test
