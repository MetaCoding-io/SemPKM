---
id: T02
parent: S03
milestone: M007
provides:
  - strategy_chain and is_chain properties on MountDefinition for pipe-delimited chain parsing
  - _validate_strategy_chain() enforcing max 3 levels and valid strategy names per segment
  - build_chain_narrowing_filter() returning SPARQL WHERE fragments for each strategy type
  - Chain-aware _resolve_mount_path() dispatching up to 6 path segments
  - Chain-aware StrategyFolderCollection with chain/chain_depth/chain_folder_values params
  - Cumulative scope narrowing — each chain depth inherits all parent grouping constraints
key_files:
  - backend/app/vfs/mount_service.py
  - backend/app/vfs/mount_collections.py
  - backend/app/vfs/provider.py
  - backend/app/vfs/strategies.py
  - backend/tests/test_vfs_scope.py
key_decisions:
  - Chain by-type narrowing uses SPARQL local name FILTER rather than pre-resolved IRI (D123)
  - Non-chain paths in _resolve_mount_path() preserved exactly — chain dispatch only activates when pipe detected
  - StrategyFolderCollection backward compat — when chain=None, all existing logic paths unchanged
patterns_established:
  - chain/chain_depth/chain_folder_values parameter triple for chain-aware collection construction
  - _build_cumulative_scope_filter() composes base scope + parent chain narrowing filters
  - _load_chain_subfolders() dispatches to next strategy's folder query with augmented scope
observability_surfaces:
  - DEBUG log "Chain dispatch" with mount path, chain list, and remaining segments in provider.py
  - DEBUG log "Chain narrowing at depth" with strategy, value, and SPARQL fragment in mount_collections.py
  - DEBUG log "Chain folder/file request" with depth and effective strategy in provider.py
  - WARNING log when chain depth exceeds chain length in provider.py
  - ValueError with chain length in message for chain depth > 3 in validation
  - strategy_chain key in to_dict() API response when mount has multi-level chain
duration: 30m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Strategy chains — data model + provider dispatch + collection nesting

**Added pipe-delimited chain strategy support with cumulative scope narrowing across up to 3 nesting levels, chain-aware WebDAV path dispatch for 5-6 segments, and 24 new unit tests.**

## What Happened

Step 1: Added `strategy_chain` property (splits on `|`), `is_chain` property, and `strategy_chain` key in `to_dict()` to `MountDefinition`. Created `_validate_strategy_chain()` as a replacement for the single-strategy validation in both `create_mount()` and `update_mount()`. Accepts pipe-delimited chains, enforces max 3 levels, validates each segment name.

Step 2: Added `build_chain_narrowing_filter()` to strategies.py. Returns SPARQL WHERE clause fragments for each strategy type: by-type uses FILTER on type local name extraction, by-tag/by-property use mount's group_by_property, by-date handles both year and month level narrowing. Added `_parse_month_folder()` helper for "MM-MonthName" format parsing.

Step 3: Rewrote `_resolve_mount_path()` in provider.py. Non-chain mounts branch immediately into the original dispatch logic (preserved exactly). Chain mounts use a new path: collect folder segments, determine file vs folder request, compute chain depth, and construct `StrategyFolderCollection` with chain params. Supports up to 6 segments (prefix + 3 folders + file).

Step 4: Extended `StrategyFolderCollection.__init__()` with `chain`, `chain_depth`, and `chain_folder_values` params. Added `_build_cumulative_scope_filter()` that composes base scope + all parent chain narrowing. Modified `get_member_names()` and `get_member()` to dispatch between chain and non-chain paths. Non-terminal chain depths use `_load_chain_subfolders()` to query the next strategy's folders with augmented scope. Terminal depths return files. Added `_load_chain_subfolders()` for all strategy types including flat-as-sublevel.

Step 5: `filename_template` is already threaded through from T01 — `_build_file_map()` passes `self._mount.filename_template` to `_build_file_map_from_bindings()`. Made query builder methods accept optional `scope_filter` parameter so chain file maps use the augmented scope.

Step 6: Added 24 new tests across 3 test classes: `TestChainStrategyParsing` (7 tests for property parsing, is_chain, to_dict), `TestChainValidation` (8 tests for max depth, invalid names, empty segments), `TestChainNarrowingFilter` (9 tests for each strategy type, escaping, edge cases).

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_vfs_scope.py tests/test_vfs_path_contract.py -v` — **83 passed** (45 scope + 38 path contract), 0 failures
- Manual code review: non-chain paths in `_resolve_mount_path()` unchanged — clean `if not is_chain:` branch preserves all 4 original segment handlers exactly
- No conflict markers in any modified files

Slice-level verification (partial — T02 is second of 4 tasks):
- ✅ `strategy_chain` and `is_chain` properties on `MountDefinition`
- ✅ Chain validation: max 3 levels, each valid strategy (tests pass)
- ✅ `build_chain_narrowing_filter()` returns correct SPARQL for each strategy type (tests pass)
- ✅ Provider dispatches 5-6 segment paths to correct chain depth
- ✅ `StrategyFolderCollection` at non-terminal depth returns sub-folders, at terminal returns files
- ✅ Each chain level narrows scope cumulatively
- ✅ Existing non-chain mounts work identically (all 59 pre-existing tests pass)
- ✅ Unit tests for chain parsing, validation, and narrowing (24 new)
- ✅ Diagnostic: chain depth > 3 raises `ValueError` with chain length in message
- ✅ Diagnostic: `{bogus}` passes through as literal text (from T01)
- ⏳ CRUD round-trip, browser verification, chain builder UI, explorer chain expansion — future tasks (T03, T04)

## Diagnostics

- **Chain dispatch logging:** Grep for `Chain dispatch` in provider.py logs to see chain resolution for each request.
- **Chain narrowing logging:** Grep for `Chain narrowing at depth` to see SPARQL narrowing applied at each level.
- **API inspection:** `GET /api/vfs/mounts` response includes `strategy_chain` key for chain mounts.
- **Validation failure shape:** `ValueError("Strategy chain too long (N levels). Maximum is 3 levels. Got: '...'")` — includes chain length and the full strategy string.

## Deviations

- Query builder methods (`_build_by_type_query`, etc.) now accept an optional `scope_filter` parameter — this wasn't in the plan but was needed so that chain file maps use the augmented scope (cumulative narrowing + current folder's narrowing) rather than just the base scope.
- `_build_file_map()` now adds the current folder's own narrowing to the scope before querying — plan mentioned this implicitly but implementation details differed.

## Known Issues

- `build_chain_narrowing_filter()` for by-type uses SPARQL FILTER on type local name rather than pre-resolved type IRI. This works but is slightly less efficient than an exact IRI match. Documented as D123 — revisable if performance matters.

## Files Created/Modified

- `backend/app/vfs/mount_service.py` — Added `strategy_chain`, `is_chain` properties, `_validate_strategy_chain()`, updated `to_dict()`, create/update validation
- `backend/app/vfs/mount_collections.py` — Chain-aware `StrategyFolderCollection` with `chain`/`chain_depth`/`chain_folder_values`, `_build_cumulative_scope_filter()`, `_load_chain_subfolders()`, imported `build_chain_narrowing_filter`
- `backend/app/vfs/provider.py` — Rewrote `_resolve_mount_path()` with chain dispatch for 5-6 segments while preserving non-chain behavior
- `backend/app/vfs/strategies.py` — Added `build_chain_narrowing_filter()` and `_parse_month_folder()`
- `backend/tests/test_vfs_scope.py` — Added `TestChainStrategyParsing`, `TestChainValidation`, `TestChainNarrowingFilter` (24 new tests)
