---
id: S03
parent: M007
milestone: M007
provides:
  - filename_template field on MountDefinition with {title}, {date}, {type}, {id} variable expansion
  - strategy_chain property supporting pipe-delimited multi-level folder nesting (max 3 levels)
  - Chain-aware WebDAV path dispatch for 5-6 segment paths
  - Cumulative scope narrowing — each chain depth inherits all parent grouping constraints
  - Pydantic models accept strategy as str or list[str] with normalization to pipe-delimited string
  - mount_children endpoint with depth/parent_values for chain folder expansion
  - Preview endpoint returns nested tree structure for chain strategies
  - Chain builder UI with add/remove/preset controls and filename template text input
requires:
  - slice: S02
    provides: MountDefinition fields, build_scope_filter() parts-list pattern, strategies.py query builders
affects:
  - S04
  - S05
key_files:
  - backend/app/vfs/mount_service.py
  - backend/app/vfs/mount_collections.py
  - backend/app/vfs/provider.py
  - backend/app/vfs/strategies.py
  - backend/app/vfs/mount_router.py
  - backend/app/browser/workspace.py
  - backend/app/templates/browser/_vfs_settings.html
  - backend/app/templates/browser/mount_tree_folders.html
  - frontend/static/js/workspace.js
  - frontend/static/css/workspace.css
  - backend/tests/test_vfs_scope.py
  - backend/tests/test_vfs_path_contract.py
key_decisions:
  - D120: Chain strategies stored as pipe-delimited string literal (no RDF ordered lists)
  - D121: Chain scope narrowing is cumulative across all parent levels
  - D122: Filename template expansion before slugification
  - D123: Chain by-type narrowing uses SPARQL local name FILTER, not pre-resolved IRI
  - Pydantic field_validator normalizes list to pipe-delimited string — single validation path
  - Chain preview capped at 2 levels depth and 5 top-level folders to bound query cost
  - Unknown template variables ({bogus}) pass through as literal text, not errors
patterns_established:
  - chain/chain_depth/chain_folder_values parameter triple for chain-aware collection construction
  - _build_cumulative_scope_filter() composes base scope + parent chain narrowing filters
  - _normalize_strategy() shared Pydantic validator across create/update/preview models
  - _get_strategy_folders() async helper for reusable folder querying across chain levels
  - filename_template parameter threading from mount definition → collection classes → file map builder
observability_surfaces:
  - DEBUG "filename_template expanded" with template, IRI, and resulting slug
  - DEBUG "Chain dispatch" with mount path, chain list, remaining segments
  - DEBUG "Chain narrowing at depth" with strategy, value, SPARQL fragment
  - DEBUG "Chain mount initial render" on first tree expansion
  - DEBUG "Chain dispatch in mount_children" with depth, parent_values, chain
  - ValueError with chain length for depth > 3 in validation
  - strategy_chain key in mount API response for chain mounts
  - Preview response includes "chain" key for chain strategies
drill_down_paths:
  - .gsd/milestones/M007/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M007/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M007/slices/S03/tasks/T03-SUMMARY.md
  - .gsd/milestones/M007/slices/S03/tasks/T04-SUMMARY.md
duration: 2h5m
verification_result: passed
completed_at: 2026-03-16
---

# S03: VFS Composable Chains & Filename Templates

**VFS mounts support composable strategy chains (up to 3 levels of nested folders with cumulative scope narrowing) and filename templates with `{title}`, `{date}`, `{type}`, `{id}` variable expansion, with 51 new unit tests and full browser-verified UI.**

## What Happened

Four tasks built this feature bottom-up:

**T01 (Filename templates)** added `filename_template` field to `MountDefinition` with SPARQL persistence in both sync and async paths. Extended `_build_file_map_from_bindings()` with template variable expansion — `{title}` from label, `{date}` from `dcterms:created` (or "undated"), `{type}` from type label or IRI local name, `{id}` from 8-char SHA-256 prefix. Expansion happens before slugification so filesystem names are always safe. Added `OPTIONAL { ?iri <dcterms:created> ?created }` to all 6 object-listing query builders in strategies.py. 12 new unit tests.

**T02 (Chain data model + dispatch)** added `strategy_chain` and `is_chain` properties to `MountDefinition`, parsing pipe-delimited strings into ordered lists. Created `_validate_strategy_chain()` enforcing max 3 levels with valid strategy names. Added `build_chain_narrowing_filter()` returning SPARQL WHERE clause fragments per strategy type (by-type uses local name FILTER, by-tag/by-property use group_by_property, by-date handles year and month levels). Rewrote `_resolve_mount_path()` in provider.py — non-chain mounts branch into the original dispatch logic (preserved exactly), chain mounts use a new path supporting up to 6 segments. Extended `StrategyFolderCollection` with chain/chain_depth/chain_folder_values params; non-terminal depths query sub-folders from the next strategy, terminal depths return files. Scope narrowing is cumulative — each depth inherits ALL parent grouping constraints. 24 new unit tests.

**T03 (Async API + explorer + preview)** wired chains into the API layer. Pydantic models (`MountCreateRequest`/`MountUpdateRequest`/`MountPreviewRequest`) accept `strategy: str | list[str]` with a shared `_normalize_strategy()` validator that converts lists to pipe-delimited strings. Explorer `mount_children` endpoint gained `depth` and `parent_values` params for chain folder expansion. `_handle_mount` dispatches chain mounts to the first strategy level. Preview endpoint returns nested tree structure for chains (capped at 2 levels, 5 top-level folders). Updated `mount_tree_folders.html` with conditional chain-aware hx-get URLs. 15 new unit tests.

**T04 (UI)** added the chain builder to the mount form: strategy select + "+ Add level" button, `#strategy-chain-container` for dynamically-added levels (max 3 total), preset buttons ("Tag → Date", "Type → Tag", "Type → Date"), and filename template text input with variable hint. Updated `collectFormData()` to send `strategy` as array for chains or string for single (backward compat). Updated `populateEditForm()` to restore chain levels and filename template on edit. `mountStrategyChanged()` scans ALL chain levels for strategy-specific field visibility.

## Verification

- **Unit tests:** `pytest tests/test_vfs_scope.py tests/test_vfs_path_contract.py` — **98 passed** in 0.55s (47 existing + 51 new)
  - 12 filename template tests: all 4 variables, missing date/type fallback, no-template backward compat, dedup, bogus variable passthrough, hash fragment/colon type IRIs
  - 24 chain tests: parsing (7), validation (8), narrowing filters (9) — covering each strategy type, escaping, edge cases
  - 15 API tests: Pydantic normalization (12) + MountDefinition chain dict (3)
- **Browser verification (T04):** 14 assertions all PASS — chain builder visible, add/remove levels, max 3 enforcement, preset application, strategy-specific field toggling, collectFormData shape (string vs array), filename_template collection, CRUD round-trip with chain strategy preserved on edit
- **Backward compatibility:** All 47 pre-existing tests pass unchanged. Single-strategy mounts send string, not array. Non-chain paths in `_resolve_mount_path()` preserved exactly.
- **Conflict markers:** Zero across backend/ and frontend/
- **Observability:** DEBUG logs confirmed present for template expansion, chain dispatch, chain narrowing, chain initial render

## Requirements Advanced

- VFS-11 — Composable strategy chains fully implemented: pipe-delimited storage, max 3 levels, cumulative scope narrowing, chain-aware WebDAV dispatch (5-6 segments), explorer mount_children chain expansion, preview nested tree, chain builder UI with presets. 39 new tests + 14 browser assertions.
- VFS-12 — Filename templates fully implemented: `{title}`, `{date}`, `{type}`, `{id}` variables, expansion before slugification, dedup suffix preserved, SPARQL persistence in sync + async paths, mount form text input with variable hint. 12 new tests.

## Requirements Validated

- VFS-11 — 39 unit tests (chain parsing, validation, narrowing, Pydantic normalization, dict output) + browser verification of chain builder UI creation/edit round-trip + chain-aware explorer expansion + preview nested tree structure
- VFS-12 — 12 unit tests (all 4 variables, missing variable fallbacks, backward compat, dedup, bogus variable passthrough) + browser verification of filename template input in mount form with CRUD round-trip

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- T02 added optional `scope_filter` parameter to query builder methods — needed for chain file maps to use augmented (cumulative narrowing) scope instead of just base scope. Not in original plan.
- T03 added `_get_strategy_folders()` and `_query_strategy_folders()` helpers — not specified in plan but needed to avoid duplicating strategy-specific SPARQL across chain traversal.
- T03 added chain dispatch in `_handle_mount` for initial tree render — plan focused on `mount_children` but initial render also needs chain awareness.

## Known Limitations

- Chain by-type narrowing uses SPARQL FILTER on type local name rather than pre-resolved IRI (D123). Works but slightly less efficient than exact IRI match. Revisable if performance matters.
- Chain preview capped at 2 levels depth and 5 top-level folders (each with 10 children) to bound query cost. Adequate for preview purposes but won't show full tree.
- Scope dropdown shows "Custom SPARQL..." with "all" in textarea when editing mounts that have `sparql_scope: "all"` — pre-existing issue, not introduced by S03.

## Follow-ups

- none — S04 (UI Polish) and S05 (Docs) are independent slices that don't depend on S03 outputs.

## Files Created/Modified

- `backend/app/vfs/mount_service.py` — `strategy_chain`, `is_chain` properties, `_validate_strategy_chain()`, `filename_template` field, `to_dict()` updates
- `backend/app/vfs/mount_collections.py` — Chain-aware `StrategyFolderCollection` with cumulative scope narrowing, `_build_file_map_from_bindings()` template expansion, chain subfolder loading
- `backend/app/vfs/provider.py` — `_resolve_mount_path()` extended for 5-6 segment chain paths
- `backend/app/vfs/strategies.py` — `build_chain_narrowing_filter()`, `_parse_month_folder()`, `dcterms:created` OPTIONAL in all 6 query builders
- `backend/app/vfs/mount_router.py` — Pydantic models accept `str | list[str]` strategy, chain validation, preview nested tree, async CRUD filename_template
- `backend/app/browser/workspace.py` — `mount_children` chain dispatch with depth/parent_values, `_get_strategy_folders()`, `_handle_mount` chain awareness
- `backend/app/templates/browser/_vfs_settings.html` — Chain builder UI (add/remove/presets), filename template input
- `backend/app/templates/browser/mount_tree_folders.html` — Chain-aware hx-get URLs with conditional depth/parent_values
- `frontend/static/js/workspace.js` — Chain management functions, updated collectFormData/populateEditForm/resetMountForm/mountStrategyChanged
- `frontend/static/css/workspace.css` — Chain builder styles (strategy-chain-row, chain-level-row, chain-presets, mount-form-hint)
- `backend/tests/test_vfs_scope.py` — 39 new tests (chain parsing, validation, narrowing, Pydantic normalization, chain dict)
- `backend/tests/test_vfs_path_contract.py` — 12 new tests (filename template expansion)

## Forward Intelligence

### What the next slice should know
- S04 (UI Polish) and S05 (Docs) are both independent — neither consumes S03 outputs. VFS features are complete after S03.
- The VFS mount form has grown significantly — `_vfs_settings.html` now has strategy chain builder, filename template, type filter multi-select, scope dropdown. Any UI polish touching the mount form should review the full template.

### What's fragile
- `mountStrategyChanged()` in workspace.js scans ALL chain levels to determine strategy-specific field visibility — adding a new strategy type requires updating both the chain level select options and the field-visibility logic.
- Chain-aware hx-get URLs in `mount_tree_folders.html` use conditional Jinja2 (`if chain_depth is defined`) — non-chain mounts must not pass chain_depth context or the template will render wrong URLs.

### Authoritative diagnostics
- `pytest tests/test_vfs_scope.py tests/test_vfs_path_contract.py -v` — 98 tests, <1s, covers all chain and template logic. Trust these over manual inspection.
- DEBUG logs (`Chain dispatch`, `Chain narrowing at depth`, `filename_template expanded`) trace the full request lifecycle through provider → collection → file map.

### What assumptions changed
- Original plan assumed `_build_file_map_from_bindings()` would be the only place needing scope_filter changes — in practice, all query builder methods (`_build_by_type_query`, etc.) needed an optional `scope_filter` parameter for chain file maps to use cumulative narrowing.
