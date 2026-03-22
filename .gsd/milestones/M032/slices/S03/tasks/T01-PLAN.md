---
estimated_steps: 4
estimated_files: 3
skills_used:
  - test
---

# T01: Implement slot-based IRI resolution and batch endpoint

**Slice:** S03 — Multi-Object Form Groups
**Milestone:** M032

## Description

Create the server-side slot resolution engine that enables atomic multi-object creation with cross-references. The existing `/api/commands/bulk` endpoint dispatches commands independently — no command can reference another command's output IRI. This task adds a `slot_resolver.py` module with `resolve_and_dispatch()` that processes commands sequentially, tracks minted IRIs in a slot map, and substitutes `$slot:xxx` placeholders in edge commands before dispatch. A new `POST /api/commands/batch` endpoint exposes this to clients.

## Steps

1. **Create `backend/app/commands/slot_resolver.py`** with:
   - `async def resolve_and_dispatch(commands: list[dict], base_namespace: str) -> tuple[list[Operation], dict[str, str]]`
   - Process commands sequentially. For each command:
     - If it has a `_slot_id` key and is `object.create`: dispatch it, read `operation.affected_iris[0]` to get the minted IRI, store in `slot_map[_slot_id] = iri`
     - If it's `edge.create`: scan `params.source` and `params.target` for `$slot:xxx` patterns. Replace with resolved IRIs from `slot_map`. If a referenced slot hasn't been resolved yet, raise `CommandError` with descriptive message.
     - For any other command type with `_slot_id`, still dispatch and track the IRI.
   - Strip `_slot_id` from the command dict before passing to `dispatch()` (it's metadata, not a command field).
   - Return `(operations, slot_map)`.

2. **Add `POST /api/commands/batch` endpoint in `backend/app/commands/router.py`**:
   - Accept a `BatchCommandRequest` body (reuse existing `BulkCommandRequest` schema or create a similar one with `commands`, `summary`, `source`).
   - Call `resolve_and_dispatch()` to get operations and slot_map.
   - Commit via `event_store.commit_bulk()` (same as existing `/bulk` endpoint).
   - Return JSON with `event_iri`, `timestamp`, `operation_count`, `affected_count`, and `slot_map` dict.
   - Handle `CommandError` for slot resolution failures (HTTP 400).

3. **Write unit tests in `backend/tests/test_slot_resolver.py`**:
   - Mock `dispatch()` to return fake `Operation` objects with controlled `affected_iris`.
   - Test cases:
     - Valid slot resolution: 2 `object.create` + 1 `edge.create` with `$slot:` refs → all resolve correctly
     - Slot map population: verify `slot_map` dict has correct slot_id→IRI mappings
     - Missing slot reference: `$slot:nonexistent` in edge.create → raises `CommandError`
     - No slot refs: commands without `_slot_id` or `$slot:` pass through unchanged
     - Order matters: edge.create referencing a slot defined by a later command → error
     - `_slot_id` stripped before dispatch: mock checks that dispatched commands don't have `_slot_id` in params
     - Empty commands list: raises ValueError
     - Mixed commands: some with slots, some without — all dispatch correctly
   - Target: 10+ test functions.

4. **Verify** by running `cd backend && uv run pytest tests/test_slot_resolver.py -v`.

## Must-Haves

- [ ] `slot_resolver.py` module with `resolve_and_dispatch()` function
- [ ] `$slot:xxx` pattern substitution in `edge.create` `source` and `target` params
- [ ] `_slot_id` metadata stripped before dispatch (not passed to command handlers)
- [ ] Descriptive error on unresolved `$slot:` reference
- [ ] `POST /api/commands/batch` endpoint returning slot_map in response
- [ ] 10+ unit tests covering valid, error, and edge cases

## Verification

- `cd backend && uv run pytest tests/test_slot_resolver.py -v` — all tests pass
- `grep -q "resolve_and_dispatch" backend/app/commands/slot_resolver.py` — function exists
- `grep -q "/commands/batch" backend/app/commands/router.py` — endpoint registered

## Observability Impact

- Signals added/changed: `logger.info()` on successful slot resolution with slot count and map; `logger.warning()` on unresolved slot references
- How a future agent inspects this: batch endpoint response includes `slot_map` dict; error responses include the missing slot ID
- Failure state exposed: HTTP 400 with error message naming the unresolved `$slot:xxx` reference

## Inputs

- `backend/app/commands/router.py` — existing bulk endpoint pattern to follow
- `backend/app/commands/dispatcher.py` — `dispatch()` function that handlers call
- `backend/app/commands/schemas.py` — `Command` model, `EdgeCreateParams` with source/target fields
- `backend/app/commands/exceptions.py` — `CommandError` exception class
- `backend/app/events/store.py` — `Operation` dataclass with `affected_iris` field

## Expected Output

- `backend/app/commands/slot_resolver.py` — new module with resolve_and_dispatch()
- `backend/app/commands/router.py` — modified with POST /api/commands/batch endpoint
- `backend/tests/test_slot_resolver.py` — new test file with 10+ tests
