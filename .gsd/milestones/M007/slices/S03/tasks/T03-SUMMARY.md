---
id: T03
parent: S03
milestone: M007
provides:
  - Pydantic models accept strategy as str or list[str] with normalization to pipe-delimited string
  - Chain validation (max 3, each valid) in async create/update/preview endpoints
  - mount_children endpoint handles depth and parent_values params for chain folder expansion
  - Chain-aware mount_tree_folders.html template passes depth/parent_values in hx-get URLs
  - Preview endpoint returns nested tree structure for chain strategies
  - _get_strategy_folders helper for reusable folder querying across chain levels
  - _query_strategy_folders helper for preview endpoint chain tree generation
key_files:
  - backend/app/vfs/mount_router.py
  - backend/app/browser/workspace.py
  - backend/app/templates/browser/mount_tree_folders.html
  - backend/tests/test_vfs_scope.py
key_decisions:
  - Pydantic field_validator normalizes list to pipe-delimited string before storage — single validation path for both input forms
  - Chain preview capped at 2 levels depth and 5 top-level folders (each with up to 10 children) to bound query cost
  - mount_tree_folders.html uses conditional hx-get URL (chain params vs legacy subfolder params) via Jinja2 if/else
patterns_established:
  - _normalize_strategy() shared validator used by all three Pydantic models (create/update/preview)
  - _get_strategy_folders() async helper encapsulates per-strategy folder querying for chain traversal
  - chain_depth/chain_parent_values template context variables for progressive chain expansion
observability_surfaces:
  - "Chain dispatch in mount_children" DEBUG log with depth, parent_values, chain
  - "Chain narrowing at depth N" DEBUG log per narrowing level
  - "Chain mount initial render" DEBUG log when chain mount first expanded
  - Preview response includes "chain" key in JSON for chain strategies
  - Pydantic validation errors surface as 422 with _validate_strategy_chain message
duration: 30min
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T03: Strategy chains — async API + explorer endpoint + preview

**Wired chain strategy support into async API (Pydantic models, CRUD), explorer mount_children endpoint (chain-aware multi-level expansion), and preview endpoint (nested tree response for chains).**

## What Happened

1. **Pydantic model updates**: Changed `strategy` field in `MountCreateRequest`, `MountUpdateRequest`, and `MountPreviewRequest` from `str` to `str | list[str]`. Added `field_validator` that normalizes lists to pipe-delimited strings and validates via `_validate_strategy_chain()` (max 3 levels, each valid). Shared `_normalize_strategy()` helper avoids duplication across models.

2. **Async CRUD chain support**: Removed the old single-strategy validation checks in `create_mount()` and `update_mount()` — the Pydantic validator now handles validation at the model layer. Strategy is stored as pipe-delimited string in RDF (e.g., `"by-tag|by-date"`) — no multi-triple storage needed.

3. **Explorer mount_children chain dispatch**: Added `depth` and `parent_values` query params. When `mount.is_chain`, builds cumulative scope narrowing from parent_values using `build_chain_narrowing_filter()` at each level, then either returns sub-folders (non-terminal depth) or objects (terminal depth). Added `_get_strategy_folders()` helper that encapsulates per-strategy folder querying for reuse in chain traversal.

4. **Explorer _handle_mount chain support**: When mount is a chain, renders first strategy level's folders using `_get_strategy_folders()` instead of dispatching to individual strategy handlers.

5. **Template updates**: Updated `mount_tree_folders.html` with conditional hx-get URL — when `chain_depth` context is present, includes depth and parent_values params; otherwise uses legacy subfolder params. Backward compatible with non-chain by-date month expansion.

6. **Preview chain support**: When strategy contains `|`, parses chain, queries level-0 folders, then for each (up to 5) queries level-1 folders with scope narrowed by level-0 value. Returns `{"directories": [...nested...], "chain": ["by-tag", "by-date"]}`. Capped at 2 levels to bound query cost.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_vfs_scope.py tests/test_vfs_path_contract.py -v` — **98 tests passed** (83 existing + 15 new)
- New tests: `TestPydanticStrategyNormalization` (12 tests covering string/list/chain/rejection for all 3 models) + `TestMountDefinitionChainDict` (3 tests for to_dict chain key)
- Python syntax verified: `ast.parse()` passes for both mount_router.py and workspace.py

## Diagnostics

- **Chain dispatch logging:** Grep for `Chain dispatch in mount_children` in workspace.py logs to see depth/parent_values/chain during expansion
- **Chain narrowing logging:** Grep for `Chain narrowing at depth` to trace cumulative scope narrowing
- **Chain initial render:** Grep for `Chain mount initial render` when mount tree first loads
- **Preview response:** Chain preview JSON includes `"chain"` key — presence indicates chain processing was used
- **Validation error shape:** Invalid chain strategy returns 422 from Pydantic with `_validate_strategy_chain` error text. Invalid strategy on update returns 400 with same message.

## Deviations

- Added `_query_strategy_folders` helper in mount_router.py for preview chain tree generation (plan didn't specify this helper but it was needed to avoid duplicating existing strategy-specific SPARQL queries)
- Added `_get_strategy_folders` helper in workspace.py for chain folder querying in explorer (plan mentioned using strategy folder queries but didn't specify a shared helper)
- Added chain dispatch in `_handle_mount` for initial tree render (plan focused on `mount_children` but initial render also needs chain awareness)

## Known Issues

- Pyright reports false-positive type errors for `str | list[str]` strategy fields because it can't trace Pydantic's runtime field_validator normalization. Runtime behavior is correct per 98 passing tests.

## Files Created/Modified

- `backend/app/vfs/mount_router.py` — Pydantic models accept str|list[str] strategy with chain validation; preview returns nested tree for chains; _query_strategy_folders helper
- `backend/app/browser/workspace.py` — mount_children handles depth/parent_values for chain expansion; _get_strategy_folders helper; _handle_mount dispatches chain mounts to first strategy level
- `backend/app/templates/browser/mount_tree_folders.html` — Chain-aware hx-get URLs with conditional depth/parent_values params
- `backend/tests/test_vfs_scope.py` — 15 new tests for Pydantic model chain normalization and MountDefinition chain dict
- `.gsd/milestones/M007/slices/S03/tasks/T03-PLAN.md` — Added Observability Impact section
