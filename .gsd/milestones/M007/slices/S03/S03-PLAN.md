# S03: VFS Composable Chains & Filename Templates

**Goal:** VFS mounts support composable strategy chains (up to 3 levels of nested folders) and filename templates with variable expansion.
**Demo:** Create a mount with strategy `["by-tag", "by-date"]` → explorer shows tag folders → expand a tag → shows year/month folders → expand month → shows objects. Create a mount with `filename_template: "{date}-{title}"` → files named `2024-01-15-my-note.md`.

## Must-Haves

- `strategy` field accepts `str | list[str]` — backward compatible with existing single-strategy mounts
- Chain of up to 3 strategies produces nested folders via scope narrowing at each level
- Provider path dispatch extended from 4 to 6 segments for chain paths
- `filename_template` field with `{title}`, `{date}`, `{type}`, `{id}` variable expansion
- Template expansion in `_build_file_map_from_bindings()` before slugification; dedup suffix still applies
- Chain strategy stored as pipe-delimited string in RDF (e.g., `"by-tag|by-date"`)
- Mount form UI has chain-level builder (+ button, max 3, predefined combos)
- Mount form UI has filename template text input
- Explorer `mount_children` endpoint supports chain-aware multi-level expansion
- Preview endpoint produces nested tree for chain strategies
- Existing single-strategy mounts continue to work unchanged

## Proof Level

- This slice proves: contract + integration
- Real runtime required: yes (SPARQL queries, WebDAV path dispatch, htmx explorer)
- Human/UAT required: no (unit tests + browser verification sufficient)

## Verification

- `cd backend && python -m pytest tests/test_vfs_scope.py tests/test_vfs_path_contract.py -v` — all existing + new tests pass
- New filename template tests in `test_vfs_path_contract.py`: template expansion with all 4 variables, missing variables, no-template backward compat, dedup with templates
- New chain tests in `test_vfs_scope.py`: chain validation (max 3), pipe-delimited parse/format, chain depth narrowing
- Provider dispatch tests: paths with 5-6 segments resolve to correct `StrategyFolderCollection` chain depth
- CRUD round-trip: create mount with chain strategy via API → read back → strategy preserved as list
- Browser: mount form shows chain builder UI, create mount with 2-level chain, verify explorer tree shows nested folders
- Backward compat: existing single-strategy mounts work unchanged (no regressions in existing tests)
- Diagnostic: invalid `filename_template` variable (e.g., `{bogus}`) passes through as literal text in slug — verify with a test that `{bogus}` appears slugified in output rather than causing an error
- Diagnostic: chain depth > 3 raises `ValueError` — verify with a test that the error message includes the chain length

## Observability / Diagnostics

- Runtime signals: DEBUG log when chain strategy parsed from pipe-delimited string; DEBUG log at each chain depth during WebDAV dispatch; DEBUG log when filename template expanded
- Inspection surfaces: mount API response JSON shows `strategy` as string or list; preview endpoint returns nested tree structure
- Failure visibility: ValueError on chain depth > 3 in validation; clear error messages in preview for invalid chains
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `MountDefinition` fields, `build_scope_filter()` parts-list pattern, `_build_file_map_from_bindings()`, `StrategyFolderCollection` with `parent_folder_value`, `mount_children` endpoint, mount form `collectFormData()`/`mountPopulateForm()`
- New wiring introduced: chain dispatch in `_resolve_mount_path()` for 5-6 segment paths, chain-aware `StrategyFolderCollection` nesting, `filename_template` parameter threading from mount form → API → file map builder
- What remains before the milestone is truly usable end-to-end: nothing for VFS features (S04/S05 are independent)

## Tasks

- [x] **T01: Filename templates — backend + tests** `est:1h`
  - Why: Isolated feature that adds `filename_template` field and template expansion in file map builder. No dependency on chain work. Quick win.
  - Files: `backend/app/vfs/mount_service.py`, `backend/app/vfs/mount_collections.py`, `backend/app/vfs/mount_router.py`, `backend/tests/test_vfs_path_contract.py`
  - Do: Add `FILENAME_TEMPLATE` constant and `filename_template: str | None` to `MountDefinition`. Add to `to_dict()` and SPARQL read/write in both sync and async services. Add `filename_template` to Pydantic request models. Extend `_build_file_map_from_bindings()` with optional `filename_template` param — expand `{title}`, `{date}`, `{type}`, `{id}` before `_slugify()`. SPARQL queries need OPTIONAL for `dcterms:created` when template uses `{date}`. Write unit tests for template expansion.
  - Verify: `cd backend && python -m pytest tests/test_vfs_path_contract.py -v` — all existing + new tests pass
  - Done when: `_build_file_map_from_bindings()` with `filename_template="{date}-{title}"` produces `2024-01-15-my-note.md` style filenames; dedup still works; no template = existing behavior unchanged

- [x] **T02: Strategy chains — data model + provider dispatch + collection nesting** `est:2h`
  - Why: Core chain machinery. Changes `strategy` to `str | list[str]`, extends WebDAV path dispatch to 6 segments, generalizes `StrategyFolderCollection` for chain-aware nesting with scope narrowing at each depth level. Most complex task — all other chain work depends on this.
  - Files: `backend/app/vfs/mount_service.py`, `backend/app/vfs/mount_collections.py`, `backend/app/vfs/provider.py`, `backend/app/vfs/strategies.py`, `backend/tests/test_vfs_scope.py`
  - Do: (1) Change `strategy: str` to `strategy: str` on `MountDefinition` but add `strategy_chain` property that returns `list[str]` (split on `|`). Keep backward compat — single strategies stored as plain string, chains as `"by-tag|by-date"`. Add `is_chain` property (`|` in strategy). (2) Extend `_resolve_mount_path()` to handle 5-6 segment paths with chain-depth tracking. (3) Add `chain` and `chain_depth` params to `StrategyFolderCollection`. When at non-terminal chain depth, `get_member_names()` returns sub-folders from the next strategy in the chain (with scope narrowed by parent). When at terminal depth, returns files. (4) Each chain level adds a scope-narrowing WHERE clause based on the parent's grouping. (5) Write tests for chain parse/format, validation, depth narrowing.
  - Verify: `cd backend && python -m pytest tests/test_vfs_scope.py tests/test_vfs_path_contract.py -v`
  - Done when: `MountDefinition(strategy="by-tag|by-date")` produces a 2-level chain; provider routes 5-segment paths to the correct chain depth; `StrategyFolderCollection` at depth 0 returns sub-folders, at terminal depth returns files

- [x] **T03: Strategy chains — async API + explorer endpoint + preview** `est:1.5h`
  - Why: Wires chain support into the async API (Pydantic models, CRUD), explorer `mount_children` endpoint (chain-aware expansion), and preview (nested tree response). Depends on T02's data model.
  - Files: `backend/app/vfs/mount_router.py`, `backend/app/browser/workspace.py`
  - Do: (1) Update `MountCreateRequest`/`MountUpdateRequest`/`MountPreviewRequest` to accept `strategy: str | list[str]`. Add validation: if list, max 3 entries, each in `VALID_STRATEGIES`. Serialize chains as pipe-delimited on write. (2) Update async CRUD — create/update write pipe-delimited strategy string. Read parses back. (3) Update `mount_children` endpoint: add `depth` param (default 0). When mount has chain strategy, use `depth` to determine which strategy applies and what scope narrowing to add from parent folder values. Use pipe-delimited `parent_values` param for chain context. (4) Update preview endpoint to return nested tree structure for chains.
  - Verify: Create mount with `strategy: ["by-tag", "by-date"]` via API → read back → get list. Preview shows nested tree. Explorer expand shows chain-level folders.
  - Done when: Full CRUD round-trip preserves chain strategies; mount_children returns correct folders at each chain depth; preview shows nested tree for chains

- [x] **T04: UI — chain builder + filename template field** `est:1h`
  - Why: Mount form needs chain-level UI (strategy stacking with + button, max 3) and filename template text input. Both features need `collectFormData()` and `mountPopulateForm()` updates.
  - Files: `backend/app/templates/browser/_vfs_settings.html`, `frontend/static/js/workspace.js`, `frontend/static/css/workspace.css`
  - Do: (1) Add "Add level" button next to strategy select. Clicking adds another strategy dropdown row (max 3 total). Each row has a remove button (except first). Add predefined combo buttons (e.g., "Tag → Date", "Type → Tag") that pre-fill the chain. (2) Add filename template text input below strategy section with placeholder showing available variables. (3) Update `collectFormData()`: if multiple strategy rows, send `strategy` as array; collect `filename_template` value. (4) Update `mountPopulateForm()`: populate chain rows on edit; populate filename template. (5) Update `resetMountForm()`: clear chain rows back to single; clear template field. (6) Strategy-specific fields (group_by_property, date_property) should apply based on which strategies are in the chain.
  - Verify: Browser: create mount with 2-level chain from form → save → edit → chain levels preserved. Create mount with filename template → save → edit → template preserved.
  - Done when: Mount form supports creating/editing chain strategies and filename templates; predefined combos work; strategy-specific fields show correctly for chain levels

## Files Likely Touched

- `backend/app/vfs/mount_service.py` — `filename_template` field, chain strategy helpers
- `backend/app/vfs/mount_collections.py` — `_build_file_map_from_bindings()` template expansion, chain-aware `StrategyFolderCollection`
- `backend/app/vfs/provider.py` — `_resolve_mount_path()` extended to 6 segments
- `backend/app/vfs/mount_router.py` — Pydantic models, validation, CRUD, preview
- `backend/app/vfs/strategies.py` — chain scope narrowing helpers
- `backend/app/browser/workspace.py` — `mount_children` chain-aware expansion
- `backend/app/templates/browser/_vfs_settings.html` — chain builder UI, template field
- `frontend/static/js/workspace.js` — `collectFormData()`, `mountPopulateForm()`, chain UI JS
- `frontend/static/css/workspace.css` — chain builder styles
- `backend/tests/test_vfs_scope.py` — chain validation and scope tests
- `backend/tests/test_vfs_path_contract.py` — filename template tests
