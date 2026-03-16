# S03: VFS Composable Chains & Filename Templates — Research

**Date:** 2026-03-16

## Summary

This slice adds two features to VFS mounts: composable strategy chains (VFS-11) and filename templates (VFS-12). Both extend existing infrastructure in well-understood ways — no new technology, no ambiguous requirements.

**Strategy chains** generalize the existing `parent_folder_value` pattern already used by `by-date` (year→month nesting). The `strategy` field on `MountDefinition` changes from `str` to `str | list[str]`. Each level in the chain narrows objects via the previous level's grouping, producing nested folders. Max 3 levels (D100). The main work is: provider path dispatch extension from 4 to 6 segments, `StrategyFolderCollection` generalization to handle chain-aware nesting, and the explorer `mount_children` endpoint supporting multi-level expansion.

**Filename templates** add an optional `filename_template` field with `{title}`, `{date}`, `{type}`, `{id}` variables. Template expansion happens in `_build_file_map_from_bindings()` before slugification. Dedup suffix still applies. This is ~30 LOC of new logic.

The design doc mentions per-level property configuration (`[{"type": "by-property", "property": "..."}]`) for the repeat-strategy case. For this slice, I recommend `str | list[str]` with shared `group_by_property`/`date_property` — this covers the common combos (by-tag→by-date, by-type→by-tag, by-type→flat). Per-level objects are only needed when the same strategy repeats with different properties, which is a power-user edge case. The simple form is backward-compatible and avoids a schema migration complexity spike.

## Recommendation

Build in this order: filename templates first (isolated, low-risk, quick win), then strategy chains backend (provider dispatch + collection nesting), then chains UI + explorer. This unblocks filename template testing early while the chain work progresses.

For strategy chains, the `str | list[str]` approach with shared property fields covers all non-repeat combos. If the list has >1 entry, the mount uses the chain dispatch path. Single string = current behavior unchanged.

## Implementation Landscape

### Key Files

**Backend — strategy chains:**
- `backend/app/vfs/mount_service.py` — `MountDefinition.strategy` type annotation changes to `str | list[str]`. `VALID_STRATEGIES` validation needs chain-aware logic. `to_dict()` already returns whatever type `strategy` is. SPARQL read/write: strategy stored as multiple ordered triples (using `rdf:_1`, `rdf:_2`, `rdf:_3` sequence predicates) for chains, or single string literal for backward compat.
- `backend/app/vfs/mount_router.py` — Pydantic models: `strategy: str | list[str]`. Validation: max 3 entries, each must be in `VALID_STRATEGIES`. Async CRUD: multi-triple writes for chain strategies. Preview: nested tree response for chains.
- `backend/app/vfs/provider.py` — `_resolve_mount_path()`: extend from max 4 to max 6 `len(parts)` cases. Parts 5-6 create additional nested `StrategyFolderCollection` instances with chain-level tracking.
- `backend/app/vfs/mount_collections.py` — `MountRootCollection` and `StrategyFolderCollection` need chain awareness. When strategy is a list, the root collection uses `strategy[0]` for top-level folders. Each `StrategyFolderCollection` tracks its `chain_depth` (0-indexed). If `chain_depth < len(chain) - 1`, children are sub-folders using the next strategy. If at terminal depth, children are files.
- `backend/app/vfs/strategies.py` — `DirectoryStrategy` enum and `build_scope_filter()` unchanged. The chain logic lives in the collection classes, not the strategy query builders — each level just calls the appropriate query builder with an additional scope constraint from the parent.
- `backend/app/browser/workspace.py` — `_handle_mount()` and `mount_children()` need chain-aware dispatch. The `mount_children` endpoint gets a new `depth` param for chain level tracking. Each level uses the corresponding strategy from the chain list.

**Backend — filename templates:**
- `backend/app/vfs/mount_service.py` — Add `FILENAME_TEMPLATE` constant, `filename_template: str | None` field on `MountDefinition`, include in `to_dict()` and SPARQL read/write.
- `backend/app/vfs/mount_router.py` — Add `filename_template` to Pydantic request models. Pass through CRUD.
- `backend/app/vfs/mount_collections.py` — `_build_file_map_from_bindings()` gains optional `filename_template` and `type_labels` params. Template expansion happens before `_slugify()`. Variables: `{title}` = raw label, `{date}` = YYYY-MM-DD from created date, `{type}` = slugified type local name, `{id}` = IRI hash[:8].

**Frontend:**
- `backend/app/templates/browser/_vfs_settings.html` — Strategy field: either keep as single `<select>` with a "+" button to add chain levels (each level gets its own strategy dropdown + property config row), or predefined combos dropdown. Filename template: text input with placeholder showing variables.
- `frontend/static/js/workspace.js` — `collectFormData()`: collect chain strategy as array when multiple levels present. `mountStrategyChanged()`: handle chain-level UI. `mountPopulateForm()`: populate chain levels on edit. New `filename_template` field in collect/populate/reset.

**Tests:**
- `backend/tests/test_vfs_scope.py` — Add chain strategy tests (chain produces correct folder queries at each depth).
- `backend/tests/test_vfs_path_contract.py` — Add filename template tests (template expansion + slugify + dedup).

### Build Order

1. **T01: Filename templates (backend + tests)** — Add `filename_template` field to `MountDefinition`, expand templates in `_build_file_map_from_bindings()`, write unit tests. Isolated from chain work. ~30 LOC + tests.

2. **T02: Strategy chains — data model + provider dispatch** — Change `strategy` to `str | list[str]` on `MountDefinition`. Extend `provider.py` path dispatch to 6 segments. Add chain-aware nesting in `MountRootCollection` and `StrategyFolderCollection`. This is the riskiest piece — the WebDAV path dispatch is the critical path. Write unit tests for chain nesting logic.

3. **T03: Strategy chains — async API + explorer** — Update `mount_router.py` Pydantic models and CRUD for chain strategies. Update `workspace.py` `_handle_mount()` and `mount_children()` for chain-aware explorer tree. Update preview endpoint for nested tree response.

4. **T04: UI — chain builder + filename template field** — Mount form: add chain level UI (+ button, max 3 levels, predefined combos). Add filename template text input. Wire `collectFormData()`/`mountPopulateForm()` for both features.

### Verification Approach

- **Unit tests:** `cd backend && python -m pytest tests/test_vfs_scope.py tests/test_vfs_path_contract.py -v` — filename template expansion, chain scope filter generation, chain depth validation
- **Provider dispatch:** Test that paths with 5-6 segments correctly resolve to `StrategyFolderCollection` at the right chain depth
- **CRUD round-trip:** Create mount with chain strategy via API, read back, verify strategy is preserved as list
- **Browser:** Mount form shows chain builder UI, create mount with 2-level chain, verify explorer tree shows nested folders, verify WebDAV produces the correct path hierarchy
- **Backward compat:** Existing single-strategy mounts continue to work unchanged

## Constraints

- WebDAV runs in sync WSGI threads — all chain dispatch logic in `mount_collections.py` and `provider.py` uses `SyncTriplestoreClient` only. No `asyncio.run()`.
- RDF doesn't have native ordered lists without blank nodes (rdf:List) or sequence predicates (rdf:_1, rdf:_2). For simplicity, store chain strategies as pipe-delimited string literal (`"by-tag|by-date"`) rather than sequence predicates — same pattern as type_filter uses GROUP_CONCAT. Parse on read, join on write.
- Max 3 strategy levels enforced in validation. Combined with mount prefix, yields max 6 WebDAV path segments.
- `parent_folder_value` is currently only used by `by-date` (year→month). Chain generalization needs to ensure scope narrowing at each level — a by-tag folder at level 0 should only show by-date folders for objects with that tag.

## Common Pitfalls

- **Scope narrowing across chain levels** — Each chain level must filter to objects matching ALL parent-level groupings, not just the immediate parent. The scope_filter from `build_scope_filter()` handles mount-level scope (saved query, type filter). Chain-level narrowing adds per-level WHERE clauses. Must compose correctly — test with real SPARQL that level-2 queries don't return objects outside level-0's grouping.
- **Provider path ambiguity** — A path like `/prefix/tag-value/file.md` could be: (a) single-strategy by-tag file, or (b) chain level-0 folder → chain level-1 folder. The provider needs to know the mount's strategy to disambiguate. Currently `_resolve_mount_path` fetches the mount definition on every request — this already resolves the ambiguity since the mount knows its strategy type.
- **RDF strategy storage format** — Using pipe-delimited string for chain storage means the single-strategy case stores `"by-type"` (string) and the chain case stores `"by-tag|by-date"` (pipe-joined string). Parsing logic: `strategy_raw.split("|")` gives `["by-type"]` for single or `["by-tag", "by-date"]` for chain. `len > 1` triggers chain path. Backward compatible with existing mounts.
- **Template variable availability** — `{date}` requires a `dcterms:created` value in SPARQL bindings, which isn't currently fetched by all strategy query builders. The SPARQL queries in `strategies.py` that `_build_file_map_from_bindings` consumes need an OPTIONAL for the date variable when a template uses `{date}`.

## Open Risks

- **Performance at chain depth 3** — A 3-level chain generates multiple sequential SPARQL queries for folder enumeration. With 895 objects (Ideaverse test set), this should be fine. Monitor query count per WebDAV listing.
- **Explorer mount_children endpoint** — Currently uses `folder` + `subfolder` params (2 levels max for by-date). Chain support needs arbitrary depth. Options: add `depth` param + encode parent chain as pipe-delimited folder values, or use path-style encoding. The `depth` approach is cleaner.
