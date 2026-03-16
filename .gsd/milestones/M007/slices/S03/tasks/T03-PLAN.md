---
estimated_steps: 5
estimated_files: 3
---

# T03: Strategy chains — async API + explorer endpoint + preview

**Slice:** S03 — VFS Composable Chains & Filename Templates
**Milestone:** M007

## Description

Wire chain support into the async API layer (Pydantic models, CRUD), the explorer `mount_children` endpoint (chain-aware multi-level expansion), and the preview endpoint (nested tree response for chains). This builds on T02's data model and collection nesting.

## Steps

1. **Update Pydantic models and validation** — In `backend/app/vfs/mount_router.py`:
   - Change `strategy` field in `MountCreateRequest` to `strategy: str | list[str]`. Add a Pydantic `field_validator` that normalizes list to pipe-delimited string: `if isinstance(v, list): return "|".join(v)`. Validate each segment is in `VALID_STRATEGIES` and max 3 entries.
   - Same for `MountUpdateRequest` and `MountPreviewRequest`.
   - In `_get_mount_by_id_async()`: strategy is already stored as pipe-delimited string — no parse change needed, it reads as-is into `MountDefinition.strategy`.
   - In `_get_mount_list_async()`: same — strategy read is already string.
   - Update `to_dict()` response for list_mounts: ensure `strategy_chain` key appears in API response when chain (this comes from `MountDefinition.to_dict()` which T02 updated).

2. **Update async CRUD for chains** — In `backend/app/vfs/mount_router.py`:
   - `create_mount()`: `body.strategy` is already normalized to pipe-delimited string by validator. The existing `DIRECTORY_STRATEGY` triple write (`"{strategy}"`) handles it — pipe-delimited string stored as-is. No change needed beyond the model validation.
   - `update_mount()`: if strategy is being updated, validate the new value (chain rules). The existing update logic writes `"{new_strategy}"` which works for pipe-delimited. Ensure the chain validation matches T02's sync validation.
   - The key insight: RDF stores `"by-tag|by-date"` as a plain string literal. No multi-triple or sequence predicates needed (research decision).

3. **Update mount_children endpoint for chains** — In `backend/app/browser/workspace.py`:
   - Add `depth: int = 0` and `parent_values: str | None = None` query params to `mount_children()`.
   - `parent_values` is a pipe-delimited string of folder values from parent chain levels (e.g., `"machine-learning"` for depth 1, `"machine-learning|2024"` for depth 2).
   - When mount `is_chain`:
     - Parse `chain = mount.strategy_chain`
     - Current strategy = `chain[depth]` (the strategy at this depth)
     - Build cumulative scope narrowing from parent_values using `build_chain_narrowing_filter()` from T02
     - Combine with base `build_scope_filter(mount, ...)` 
     - If depth < len(chain) - 1: this is a non-terminal level → return sub-folders using the current strategy's folder query (type_folders, tag_folders, etc.)
     - If depth = len(chain) - 1: this is terminal → return objects
     - Sub-folder template (`mount_tree_folders.html`) needs updated `hx-get` URLs that include `depth={depth+1}` and `parent_values={current_parent_values|folder_value}`
   - When not chain: existing behavior unchanged (depth=0, no parent_values).
   - Add a new template or modify `mount_tree_folders.html` to pass chain params in hx-get URLs. The cleanest approach: add optional `depth` and `parent_values` context variables. When present, include them in the URL. Template: `hx-get="/browser/explorer/mount-children?mount_id={{ mount_id }}&folder={{ folder.value | urlencode }}&depth={{ depth }}&parent_values={{ parent_values | urlencode }}"`.

4. **Update preview endpoint for chains** — In `backend/app/vfs/mount_router.py`:
   - In `preview_mount()`: when strategy is a chain (contains `|`):
     - Parse chain = strategy.split("|")
     - Level 0: query folders for chain[0] (type/tag/date/property folders)
     - For each level-0 folder (up to a cap, e.g., first 5): query level-1 folders with scope narrowed by level-0 value
     - Return nested tree: `{"name": "tag-value", "children": [{"name": "2024", "file_count": 12}, ...]}` format
   - Cap the preview depth to 2 levels to avoid expensive queries
   - For non-chain strategies: existing preview behavior unchanged

5. **Verify** — Run existing tests plus manual API testing:
   - `cd backend && python -m pytest tests/test_vfs_scope.py tests/test_vfs_path_contract.py -v`
   - Create mount via API with `strategy: ["by-tag", "by-date"]` → verify response has `strategy_chain`
   - Call preview with chain strategy → verify nested tree response

## Must-Haves

- [ ] Pydantic models accept `strategy: str | list[str]` with normalization to pipe-delimited
- [ ] Chain validation in create/update (max 3, each valid)
- [ ] `mount_children` handles `depth` and `parent_values` params for chain expansion
- [ ] Chain folder templates pass depth/parent_values in hx-get URLs
- [ ] Preview returns nested tree structure for chains
- [ ] Non-chain mounts: zero behavior change in API, explorer, and preview

## Verification

- `cd backend && python -m pytest tests/test_vfs_scope.py tests/test_vfs_path_contract.py -v` — no regressions
- API: `POST /api/vfs/mounts` with `strategy: ["by-tag", "by-date"]` returns 200 with `strategy_chain` in response
- API: `POST /api/vfs/mounts/preview` with chain strategy returns nested directory tree
- Browser (if running): expand mount tree → chain levels show nested folders

## Inputs

- T02's `MountDefinition.strategy_chain`, `is_chain`, `build_chain_narrowing_filter()` — the chain data model and narrowing functions
- `backend/app/vfs/mount_router.py` — existing Pydantic models with `type_filter`, async CRUD
- `backend/app/browser/workspace.py` — existing `mount_children` endpoint with `folder`/`subfolder` params
- `backend/app/templates/browser/mount_tree_folders.html` — existing sub-folder template with hx-get URLs

## Expected Output

- `backend/app/vfs/mount_router.py` — Pydantic models accept chains, preview returns nested tree
- `backend/app/browser/workspace.py` — `mount_children` handles chain depth expansion
- `backend/app/templates/browser/mount_tree_folders.html` — chain-aware hx-get URLs with depth/parent_values

## Observability Impact

- **API response shape:** `POST /api/vfs/mounts` with chain strategy returns `strategy_chain` key in response JSON. `GET /api/vfs/mounts` includes `strategy_chain` for chain mounts.
- **Preview response shape:** `POST /api/vfs/mounts/preview` with chain strategy returns `{"directories": [...nested...], "chain": ["by-tag", "by-date"]}` — nested tree structure. Non-chain preview unchanged.
- **Explorer chain logging:** `Chain dispatch in mount_children` and `Chain narrowing at depth N` DEBUG log lines trace chain folder expansion in workspace.py. Grep for these to follow multi-level expansion.
- **Validation errors:** Invalid chain in Pydantic model raises 422 with `_validate_strategy_chain` error message. Invalid chain in update raises 400 with same message format.
- **Failure shapes:** Chain depth out of bounds (depth >= len(chain)) silently returns flat objects. Missing `group_by_property`/`date_property` for chain sub-strategies returns empty folder list.
