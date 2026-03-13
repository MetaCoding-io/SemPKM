---
estimated_steps: 4
estimated_files: 1
---

# T02: Backend unit tests for mount handler and children endpoint

**Slice:** S03 — VFS-Driven Explorer Modes
**Milestone:** M003

## Description

Create comprehensive unit tests for the mount explorer handler and children endpoint. Tests mock the triplestore client to verify SPARQL query structure, strategy dispatch routing, error handling, and edge cases — matching the established pattern from `test_hierarchy_explorer.py` (mock-capture SPARQL via `call_args`).

## Steps

1. **TestMountHandlerDispatch (4 tests).** Verify: (a) `explorer_tree` with `mode=mount:uuid` routes to mount handler (mock handler, check it's called), (b) `mode=mount:not-a-uuid` returns 400 with invalid format error, (c) `mode=mount:valid-but-nonexistent-uuid` returns 400 with unknown mount error, (d) existing modes (by-type, hierarchy) still route to their handlers (regression guard).

2. **TestMountStrategySPARQL (5 tests).** For each of the 5 strategies, create a mock `MountDefinition` with the strategy set, mock the triplestore to return empty bindings, call `_handle_mount`, and capture the SPARQL string passed to `client.query()`. Verify: (a) flat → SPARQL contains `query_flat_objects` pattern (no folders, direct objects), (b) by-type → SPARQL contains `?typeIri` and `DISTINCT`, (c) by-date → SPARQL contains year extraction and `date_property`, (d) by-tag → SPARQL contains `?tagValue` and `group_by_property`, (e) by-property → SPARQL contains `?groupValue` and `group_by_property`.

3. **TestMountChildrenEndpoint (4 tests).** Verify: (a) by-type folder expansion passes type IRI to `query_objects_by_type`, (b) by-date year folder expansion returns month folders (no `subfolder` param), (c) by-date year+month expansion returns objects (`subfolder` param present), (d) invalid mount_id returns 400. Mock triplestore and capture SPARQL to verify correct query builder is invoked.

4. **TestMountEdgeCases (3 tests).** Verify: (a) by-date mount with `date_property=None` returns empty tree with message (not a crash), (b) by-tag/by-property `_uncategorized` folder expansion calls `query_uncategorized_objects`, (c) triplestore error on mount fetch falls back gracefully (empty result or 400, not 500).

## Must-Haves

- [ ] ≥15 unit tests covering all test classes
- [ ] Each of the 5 strategies has at least one SPARQL structure test
- [ ] Children endpoint validation covers by-date 3-tier depth
- [ ] Edge cases cover null config and uncategorized folders
- [ ] All existing tests pass without regression (`python -m pytest tests/ -v`)

## Verification

- `cd backend && python -m pytest tests/test_mount_explorer.py -v` — all pass
- `cd backend && python -m pytest tests/ -v --tb=short` — no regressions (all existing tests still pass)

## Observability Impact

- Signals added/changed: None (tests are verification, not runtime)
- How a future agent inspects this: Run `pytest tests/test_mount_explorer.py -v` — test names map to mount handler behaviors
- Failure state exposed: Pytest failure output directly shows which strategy, endpoint, or edge case broke

## Inputs

- `backend/app/browser/workspace.py` — `_handle_mount`, `mount_children`, `_get_mount_definition` from T01
- `backend/app/vfs/strategies.py` — query builder function signatures
- `backend/app/vfs/mount_service.py` — `MountDefinition` dataclass for mock construction
- `backend/tests/test_hierarchy_explorer.py` — reference pattern for mock-capture SPARQL testing

## Expected Output

- `backend/tests/test_mount_explorer.py` — ≥15 unit tests across 4 test classes, all passing
