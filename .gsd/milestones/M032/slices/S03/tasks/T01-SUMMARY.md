---
id: T01
parent: S03
milestone: M032
provides:
  - slot_resolver.py module with resolve_and_dispatch() for atomic multi-object creation
  - POST /api/commands/batch endpoint with slot_map in response
  - 23 unit tests covering valid, error, and edge cases
key_files:
  - backend/app/commands/slot_resolver.py
  - backend/app/commands/router.py
  - backend/tests/test_slot_resolver.py
key_decisions:
  - Used deepcopy of input commands before stripping _slot_id to avoid mutating caller data
  - Used Pydantic TypeAdapter for discriminated union parsing (matches existing router.py pattern)
  - Recursive _substitute_slots handles nested dicts/lists, not just top-level source/target
patterns_established:
  - $slot:xxx placeholder pattern for cross-command IRI references in batch operations
  - Sequential dispatch with slot_map accumulation for dependent command chains
observability_surfaces:
  - logger.info on slot resolution completion with slot count and map
  - logger.warning when slotted command produces no affected_iris
  - HTTP 400 with descriptive error naming the unresolved $slot:xxx reference
  - Batch endpoint response includes slot_map dict for client-side debugging
duration: 25m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T01: Implement slot-based IRI resolution and batch endpoint

**Added slot_resolver.py with resolve_and_dispatch() and POST /api/commands/batch endpoint for atomic multi-object creation with $slot:xxx cross-references**

## What Happened

Created the slot resolution engine that enables atomic multi-object creation with cross-references between commands. The `slot_resolver.py` module processes commands sequentially, tracks minted IRIs in a slot map, and substitutes `$slot:xxx` placeholders before dispatch. A new `POST /api/commands/batch` endpoint in `router.py` exposes this to clients, returning the slot_map in the response for debugging.

Key implementation details:
- `_substitute_slots()` recursively handles strings, lists, and nested dicts — not just top-level `source`/`target` fields
- Input commands are deepcopied before `_slot_id` is stripped, preventing mutation of caller data
- Used `TypeAdapter(Command).validate_python()` for discriminated union parsing, matching the existing pattern in `router.py`
- Unresolved slot references produce a descriptive `CommandError` listing available slots

## Verification

All 23 unit tests pass covering: valid resolution (2 creates + 1 edge), slot map population, missing slot refs, forward references, _slot_id stripping, empty commands, mixed slotted/unslotted, nested property substitution, no-affected-IRIs edge case, hyphenated slot IDs, and input immutability.

Task-level verification commands all pass. Slice-level verification: test suite passes (67 tests including slot resolver + block registry), module exists, endpoint registered. T02/T03 checks are expectedly not yet passing.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && uv run pytest tests/test_slot_resolver.py -v` | 0 | ✅ pass | 0.14s |
| 2 | `cd backend && uv run pytest tests/test_slot_resolver.py tests/test_block_registry.py -v` | 0 | ✅ pass | 0.18s |
| 3 | `grep -q "resolve_and_dispatch" backend/app/commands/slot_resolver.py` | 0 | ✅ pass | <0.1s |
| 4 | `grep -q "/commands/batch" backend/app/commands/router.py` | 0 | ✅ pass | <0.1s |
| 5 | `test -f backend/app/commands/slot_resolver.py` | 0 | ✅ pass | <0.1s |
| 6 | `uv run python -c "from app.commands.slot_resolver import resolve_and_dispatch; print('import ok')"` | 0 | ✅ pass | <0.1s |
| 7 | `grep -q 'Unresolved slot' backend/app/commands/slot_resolver.py` | 0 | ✅ pass | <0.1s |

## Diagnostics

- **Batch endpoint response**: `POST /api/commands/batch` returns `{event_iri, timestamp, operation_count, affected_count, slot_map}` — the `slot_map` dict shows `slot_id → IRI` mappings
- **Error responses**: Unresolved `$slot:xxx` references return HTTP 400 with error message naming the missing slot and listing resolved slots so far
- **Logs**: `app.commands.slot_resolver` logger emits INFO on successful resolution (slot count + map) and WARNING when a slotted command produces no affected IRIs
- **Unit tests**: Run `cd backend && uv run pytest tests/test_slot_resolver.py -v` to verify all 23 tests pass

## Deviations

None — implementation matches the task plan.

## Known Issues

None.

## Files Created/Modified

- `backend/app/commands/slot_resolver.py` — new module with `resolve_and_dispatch()` and `_substitute_slots()` for slot-based IRI resolution
- `backend/app/commands/router.py` — added `POST /api/commands/batch` endpoint with `BatchCommandRequest` schema, import of `resolve_and_dispatch`
- `backend/tests/test_slot_resolver.py` — new test file with 23 tests across 6 test classes covering valid resolution, errors, stripping, substitution, and edge cases
- `.gsd/milestones/M032/slices/S03/S03-PLAN.md` — added diagnostic verification checks, marked T01 done
