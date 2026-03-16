---
estimated_steps: 7
estimated_files: 5
---

# T02: Strategy chains — data model + provider dispatch + collection nesting

**Slice:** S03 — VFS Composable Chains & Filename Templates
**Milestone:** M007

## Description

The core chain machinery. Changes the `strategy` field to support pipe-delimited chains (e.g., `"by-tag|by-date"`), extends WebDAV provider path dispatch from 4 to 6 segments, and generalizes `StrategyFolderCollection` to handle chain-aware nesting where each depth level narrows scope based on the parent's grouping. This is the riskiest and most complex task — all subsequent chain work (API, explorer, UI) builds on top.

## Steps

1. **Extend MountDefinition for chains** — In `backend/app/vfs/mount_service.py`:
   - Keep `strategy: str` (stores `"by-tag"` or `"by-tag|by-date"` — pipe-delimited)
   - Add helper properties to `MountDefinition`:
     ```python
     @property
     def strategy_chain(self) -> list[str]:
         """Parse strategy into ordered list. Single = ['by-tag'], chain = ['by-tag', 'by-date']."""
         return self.strategy.split("|")

     @property
     def is_chain(self) -> bool:
         """True if strategy is a multi-level chain."""
         return "|" in self.strategy
     ```
   - Update `SyncMountService.create()` validation: each segment of `strategy.split("|")` must be in `VALID_STRATEGIES`, and `len(chain) <= 3`
   - Update `SyncMountService.update()` validation: same chain validation for strategy field
   - `to_dict()` — strategy is already stored as-is (string), no change needed. But add a `strategy_chain` key for API convenience:
     ```python
     result = {... existing fields ...}
     chain = self.strategy.split("|")
     if len(chain) > 1:
         result["strategy_chain"] = chain
     return result
     ```

2. **Add chain scope narrowing helpers** — In `backend/app/vfs/strategies.py`:
   - Add a function `build_chain_narrowing_filter(strategy: str, folder_value: str, mount: MountDefinition) -> str` that returns a SPARQL WHERE clause fragment narrowing objects to those matching a specific folder grouping:
     - `by-type`: `?iri a <{type_iri}> .` — need to resolve type label back to IRI (or pass IRI directly)
     - `by-tag`: `?iri <{tag_property}> "{escaped_tag_value}" .` where tag_property is `mount.group_by_property`
     - `by-property`: `?iri <{group_by_property}> ?_pval . FILTER(STR(?_pval) = "{folder_value}")` (handles both IRI and literal)
     - `by-date` at year level: `FILTER(STRSTARTS(STR(?_date), "{year}"))` with `?iri <{date_property}> ?_date .`
     - `by-date` at month level: `FILTER(STRSTARTS(STR(?_date), "{year}-{month:02d}"))` with the same pattern
     - `flat`: no narrowing (shouldn't appear mid-chain, but return empty string)
   - This function is the critical piece — each chain level calls it to build cumulative scope narrowing from all parent levels.

3. **Extend provider path dispatch** — In `backend/app/vfs/provider.py`, `_resolve_mount_path()`:
   - Current max: 4 segments (`/prefix/year/month/file.md`). Need 6 for 3-level chain.
   - The key insight: when a mount has a chain, intermediate segments are folders at successive chain depths, and the terminal `.md` segment is a file at the terminal depth.
   - Refactor the current if/elif cascade to be chain-aware:
     ```python
     chain = mount.strategy_chain
     is_chain = mount.is_chain
     remaining = parts[1:]  # strip mount prefix

     if len(remaining) == 0:
         return MountRootCollection(...)

     # For non-chain mounts, preserve existing behavior exactly
     if not is_chain:
         # ... existing 2/3/4 segment handling unchanged ...

     # Chain dispatch
     # Each segment (except terminal .md) is a folder at a chain depth
     # Terminal .md is a file inside the deepest folder
     ```
   - For chain mounts: collect `folder_values` from path segments. If terminal segment is `.md`, it's a file at the parent depth. Otherwise it's a folder at that depth.
   - Pass `chain=chain`, `chain_depth=depth`, and `chain_folder_values=folder_values[:depth]` to `StrategyFolderCollection`.

4. **Generalize StrategyFolderCollection for chains** — In `backend/app/vfs/mount_collections.py`:
   - Add optional params to `__init__()`: `chain: list[str] | None = None`, `chain_depth: int = 0`, `chain_folder_values: list[str] | None = None`
   - Compute `_effective_strategy`: if chain provided, use `chain[chain_depth]`; otherwise use `mount.strategy` (backward compat)
   - Compute `_is_terminal`: if chain, true when `chain_depth >= len(chain) - 1`; if not chain, true unless it's `by-date` at year level (existing behavior)
   - Build cumulative scope narrowing: combine `build_scope_filter(mount)` with `build_chain_narrowing_filter()` for each chain level above current depth
   - Modify `get_member_names()`:
     - If non-terminal chain depth: return sub-folder names using the _next_ strategy's folder query builder (type folders, tag folders, etc.)
     - If terminal: return file names from file map (existing behavior)
   - Modify `get_member()`:
     - If non-terminal: return a new `StrategyFolderCollection` at `chain_depth + 1` with updated `chain_folder_values`
     - If terminal: return a `MountedResourceFile` (existing behavior)
   - **Critical: existing non-chain behavior must be preserved.** When `chain` is None, all existing logic paths remain unchanged. The `by-date` year→month nesting via `parent_folder_value` continues to work.

5. **Thread filename_template through** — When building file maps, pass `self._mount.filename_template` from T01's work. This is a simple passthrough — just ensure the existing `_build_file_map` call sites use the new parameter. (If T01 hasn't been applied yet, add the parameter threading and it will connect when T01's expansion code lands.)

6. **Write unit tests** — In `backend/tests/test_vfs_scope.py`, add:
   - `TestChainStrategyParsing`: test `strategy_chain` property for single and multi-level, `is_chain` property
   - `TestChainValidation`: test max 3 levels, invalid strategy in chain, empty segments
   - `TestChainNarrowingFilter`: test `build_chain_narrowing_filter()` for each strategy type
   - In `backend/tests/test_vfs_path_contract.py`: optionally test that `_build_file_map_from_bindings()` still works unchanged when no chain params are involved (backward compat sanity)

7. **Run full test suite** — `cd backend && python -m pytest tests/test_vfs_scope.py tests/test_vfs_path_contract.py -v`

## Must-Haves

- [ ] `strategy_chain` and `is_chain` properties on `MountDefinition`
- [ ] Chain validation: max 3 levels, each valid strategy
- [ ] `build_chain_narrowing_filter()` returns correct SPARQL for each strategy type
- [ ] Provider dispatches 5-6 segment paths to correct chain depth
- [ ] `StrategyFolderCollection` at non-terminal depth returns sub-folders, at terminal returns files
- [ ] Each chain level narrows scope cumulatively (objects must match ALL parent groupings)
- [ ] Existing non-chain mounts work identically (zero behavior change)
- [ ] Unit tests for chain parsing, validation, and narrowing

## Verification

- `cd backend && python -m pytest tests/test_vfs_scope.py tests/test_vfs_path_contract.py -v` — all pass
- Manual code review: non-chain paths in `_resolve_mount_path()` unchanged or equivalent

## Observability Impact

- Signals added/changed: DEBUG log when chain strategy detected in `_resolve_mount_path()`; DEBUG log at each chain depth with effective strategy and narrowing filter
- How a future agent inspects this: grep `chain` in provider.py/mount_collections.py logs; check `strategy_chain` in mount API response
- Failure state exposed: ValueError with clear message on chain depth > 3; chain depth mismatch logs at WARNING

## Inputs

- `backend/app/vfs/mount_service.py` — `MountDefinition` with `strategy: str` and T01's `filename_template`
- `backend/app/vfs/mount_collections.py` — `StrategyFolderCollection` with `parent_folder_value` pattern (by-date year→month)
- `backend/app/vfs/provider.py` — `_resolve_mount_path()` handling up to 4 segments
- `backend/app/vfs/strategies.py` — `build_scope_filter()` parts-list pattern, individual strategy query builders
- S02 summary: `build_scope_filter()` returns concatenated filter parts joined by newline+indent — follow same pattern

## Expected Output

- `backend/app/vfs/mount_service.py` — `strategy_chain`, `is_chain` properties; chain validation in create/update
- `backend/app/vfs/mount_collections.py` — chain-aware `StrategyFolderCollection` with `chain`/`chain_depth`/`chain_folder_values` params
- `backend/app/vfs/provider.py` — `_resolve_mount_path()` extended to 6 segments for chains
- `backend/app/vfs/strategies.py` — `build_chain_narrowing_filter()` function
- `backend/tests/test_vfs_scope.py` — new chain-related test classes
