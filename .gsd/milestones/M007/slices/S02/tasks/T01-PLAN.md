---
estimated_steps: 6
estimated_files: 3
---

# T01: Add type_filter to MountDefinition and build_scope_filter

**Slice:** S02 — VFS Quick Wins — Type Filter, Query IRI, Preview
**Milestone:** M007

## Description

Add `type_filter` field to `MountDefinition` dataclass and extend `build_scope_filter()` in strategies.py to generate a VALUES clause constraining `?type` when type filter IRIs are provided. The type filter composes with the existing scope filter via AND — both clauses end up in the same WHERE block.

This is the backend foundation for VFS-07. No UI or router changes yet — those come in T04.

## Steps

1. In `backend/app/vfs/mount_service.py`:
   - Add `type_filter: list[str] | None = None` field to `MountDefinition` (after `saved_query_id` / before `created_by`)
   - Add vocab constant: `TYPE_FILTER = f"{NS_SEMPKM}typeFilter"`
   - Update `to_dict()` to include `"type_filter": self.type_filter`

2. In `backend/app/vfs/strategies.py`:
   - Extend `build_scope_filter()` to accept type_filter from mount. When `mount.type_filter` is a non-empty list, generate a VALUES clause: `VALUES ?type { <iri1> <iri2> ... }` and add `?iri a ?type .` binding. This ensures only objects of those types are included.
   - The type filter is AND-composed with scope: both the type VALUES clause and the scope sub-select appear in the returned filter fragment. If only type_filter is set (no scope), return just the VALUES + type binding. If both, concatenate them.

3. In `backend/tests/test_vfs_scope.py`:
   - Add test class `TestTypeFilter` with tests for:
     - `test_type_filter_single_type` — one IRI → VALUES with one entry
     - `test_type_filter_multiple_types` — three IRIs → VALUES with all three
     - `test_type_filter_empty_list` — empty list → no VALUES clause (same as None)
     - `test_type_filter_none` — None → no VALUES clause
     - `test_type_filter_with_scope_composes` — type_filter + sparql_scope → both appear in output
     - `test_type_filter_with_resolved_query_composes` — type_filter + resolved_query_text → both appear

4. Run tests and verify all pass, including existing tests.

## Must-Haves

- [ ] `MountDefinition` has `type_filter: list[str] | None = None` field
- [ ] `build_scope_filter()` generates `VALUES ?type { ... }` when type_filter is non-empty
- [ ] Type filter AND scope compose (both present → both in output)
- [ ] Empty list and None both result in no type filter clause
- [ ] All existing `test_vfs_scope.py` tests still pass

## Verification

- `cd backend && python -m pytest tests/test_vfs_scope.py -v` — all tests pass including new type filter tests
- Confirm the VALUES clause includes `?iri a ?type .` binding (otherwise the VALUES is unconnected)

## Inputs

- `backend/app/vfs/mount_service.py` — existing `MountDefinition` dataclass (line 50)
- `backend/app/vfs/strategies.py` — existing `build_scope_filter()` function (line 45)
- `backend/tests/test_vfs_scope.py` — existing 10 tests for scope filter and WHERE body extraction

## Observability Impact

- `build_scope_filter()` emits a log line at DEBUG level when a type_filter VALUES clause is generated, including the count of IRIs. This lets a future agent grep logs for `type_filter VALUES` to confirm the clause is being applied at runtime.
- The `MountDefinition.to_dict()` output now includes `type_filter`, making it inspectable via the mount API response without needing triplestore queries.
- No new failure states introduced — empty/None type_filter is a no-op, not an error.

## Expected Output

- `backend/app/vfs/mount_service.py` — updated with `type_filter` field and `TYPE_FILTER` constant
- `backend/app/vfs/strategies.py` — `build_scope_filter()` handles type_filter VALUES clause
- `backend/tests/test_vfs_scope.py` — 6+ new tests for type_filter behavior
