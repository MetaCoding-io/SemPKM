# S03: VFS-Driven Explorer Modes

**Goal:** Each user-created VFS mount appears as a selectable mode in the explorer dropdown. Objects are organized by the mount's directory strategy and clicking opens the full object tab.
**Demo:** User creates a VFS mount (e.g. by-date), sees it in the explorer dropdown, selects it, sees date-organized folders, expands a folder, clicks an object → the object opens in a workspace tab just like clicking in "By Type" view.

## Must-Haves

- Dynamic mount options injected into `#explorer-mode-select` dropdown on page load
- `mount:` prefix mode values parsed by `explorer_tree` dispatcher, routing to mount handler
- Mount handler fetches `MountDefinition`, builds scope filter, dispatches to correct strategy SPARQL query builder
- `GET /browser/explorer/mount-children` endpoint for lazy folder/object expansion (all 5 strategies)
- Mount tree templates rendering `.tree-node` folders and `.tree-leaf` objects with `handleTreeLeafClick`
- By-date strategy renders 3-tier: year → month → objects
- Flat strategy renders objects directly (no folder level)
- Mount mode persistence works with `initExplorerMode()` and validates against dynamically-added options
- Object click-through opens full object tab (EXP-05)
- Backend unit tests for mount handler dispatch, SPARQL structure, children endpoint
- E2E tests verify mount appears in dropdown, folder expansion works, object click-through works

## Proof Level

- This slice proves: integration
- Real runtime required: yes (Docker Compose stack with triplestore)
- Human/UAT required: no

## Verification

- `cd backend && python -m pytest tests/test_mount_explorer.py -v` — all pass (handler dispatch, SPARQL structure, strategy routing, children endpoint validation)
- `cd e2e && npx playwright test tests/20-vfs-explorer/ --reporter=list --project=chromium` — all pass (mount in dropdown, folder expansion, object click-through)
- Manual: `curl .../explorer/tree?mode=mount:some-uuid` → 200, returns mount-organized tree HTML
- Manual: `curl .../explorer/mount-children?mount_id=xxx&folder=yyy` → 200, returns folder contents

## Observability / Diagnostics

- Runtime signals: DEBUG log `"Mount explorer tree requested: mount_id=%s, strategy=%s"` in `app.browser.workspace`; DEBUG log `"Mount children requested: mount_id=%s, folder=%s, strategy=%s"` for expansion
- Inspection surfaces: `GET /browser/explorer/tree?mode=mount:{id}` directly testable; `GET /api/vfs/mounts` shows available mounts
- Failure visibility: HTTP 400 `{"detail":"Unknown mount: {id}"}` for invalid mount_id; HTTP 400 `{"detail":"Invalid mount_id format"}` for non-UUID; empty tree with message for mounts with missing strategy config (e.g. null date_property on by-date)
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed:
  - `EXPLORER_MODES` registry + `explorer_tree` dispatcher from S01 (workspace.py)
  - `initExplorerMode()` + `handleTreeLeafClick` from S01 (workspace.js)
  - `strategies.py` SPARQL query builders from VFS system (14 functions)
  - `MountDefinition` dataclass from `mount_service.py`
  - `build_scope_filter()` from `strategies.py`
  - `GET /api/vfs/mounts` REST endpoint from `mount_router.py`
  - `hierarchy_tree.html` / `tree_children.html` template patterns from S01/S02
  - `IconService.get_type_icon()`, `LabelService.resolve_batch()` from core services
- New wiring introduced in this slice:
  - `mount:` prefix parsing in `explorer_tree` dispatcher (workspace.py)
  - `_handle_mount` handler bridging VFS strategies to htmx tree rendering
  - `GET /browser/explorer/mount-children` endpoint for lazy folder expansion
  - `mount_tree.html` + `mount_tree_objects.html` + `mount_tree_folders.html` templates
  - JS `initExplorerMountOptions()` function fetching mounts and injecting dropdown options
- What remains before the milestone is truly usable end-to-end:
  - S04 (tag explorer mode), S05 (favorites), S06 (comments), S07 (ontology), S08 (class creation), S09 (admin stats)

## Tasks

- [x] **T01: Backend mount handler, children endpoint, and templates** `est:2h`
  - Why: Core backend that bridges VFS strategy SPARQL builders to htmx tree rendering — the mount handler, children endpoint, and all templates
  - Files: `backend/app/browser/workspace.py`, `backend/app/templates/browser/mount_tree.html`, `backend/app/templates/browser/mount_tree_objects.html`, `backend/app/templates/browser/mount_tree_folders.html`
  - Do: Add `_handle_mount` async handler that parses `mount:` prefix from mode, fetches `MountDefinition` via async SPARQL, calls strategy-specific query builder with `build_scope_filter()`, renders folder nodes or flat object list. Add `GET /browser/explorer/mount-children` endpoint handling folder expansion for all 5 strategies (flat returns objects, by-type/by-tag/by-property returns objects, by-date returns month folders or objects depending on depth). Wire `mount:` prefix matching into `explorer_tree` dispatcher. Create 3 templates: `mount_tree.html` (root folders for a strategy), `mount_tree_objects.html` (object leaves with `handleTreeLeafClick`), `mount_tree_folders.html` (sub-folders for by-date month level). Handle edge cases: missing mount → 400, missing strategy config → empty tree with message, by-date year→month→objects depth.
  - Verify: `curl .../explorer/tree?mode=mount:valid-uuid` returns HTML with `.tree-node` or `.tree-leaf` elements; `curl .../explorer/tree?mode=mount:nonexistent` returns 400; `curl .../explorer/mount-children?mount_id=xxx&folder=yyy` returns folder contents
  - Done when: Mount handler dispatches to all 5 strategies, children endpoint expands folders, templates render with correct click-through handlers, and existing explorer modes still work

- [x] **T02: Backend unit tests for mount handler and children endpoint** `est:1h`
  - Why: Proves mount handler dispatch logic, SPARQL query structure, strategy routing, and children endpoint validation without requiring live triplestore
  - Files: `backend/tests/test_mount_explorer.py`
  - Do: Create test file with: (1) TestMountHandlerDispatch — verify `mount:` prefix parsing routes to `_handle_mount`, verify invalid mount_id returns 400, verify non-existent mount returns 400; (2) TestMountStrategySPARQL — for each of the 5 strategies, mock the triplestore and verify the correct `strategies.py` query builder is called with proper scope_filter; (3) TestMountChildrenEndpoint — verify folder param dispatches to correct object query, verify by-date year→month vs year+month→objects routing, verify invalid mount_id returns 400; (4) TestMountEdgeCases — null date_property on by-date mount returns empty, uncategorized folder handling for by-tag/by-property
  - Verify: `cd backend && python -m pytest tests/test_mount_explorer.py -v` — all pass; `cd backend && python -m pytest tests/ -v --tb=short` — no regressions
  - Done when: ≥15 unit tests pass covering handler dispatch, all 5 strategies, children endpoint, and edge cases

- [x] **T03: Frontend dynamic mount dropdown injection and mode persistence** `est:1h`
  - Why: Mounts must appear in the explorer dropdown dynamically (they don't exist at server-render time) and mode persistence must work with dynamically-added mount options
  - Files: `frontend/static/js/workspace.js`, `backend/app/templates/browser/workspace.html`
  - Do: Add `initExplorerMountOptions()` async function that fetches `GET /api/vfs/mounts`, creates `<option value="mount:{id}">{name} ({strategy})</option>` for each, injects into `#explorer-mode-select` (after static options, before close), then re-runs mode restore logic if stored mode starts with `mount:`. Ensure this runs from `init()` after `initExplorerMode()`. Add an `<optgroup label="VFS Mounts">` wrapper if mounts exist, to visually separate them from built-in modes. Handle timing: if fetch fails or returns empty, no options added (graceful degradation).
  - Verify: Browser shows mount options in dropdown after page load; selecting a mount mode loads mount tree; refreshing page with mount mode persisted restores correctly; if mount is deleted, fallback to by-type on next load
  - Done when: Mount options appear in dropdown, persist/restore works, no regressions to existing mode switching

- [x] **T04: E2E tests for VFS explorer modes** `est:1h`
  - Why: End-to-end verification that mounts appear in dropdown, folders expand, and object click-through works in a real browser against the full stack
  - Files: `e2e/tests/20-vfs-explorer/vfs-explorer.spec.ts`, `e2e/helpers/selectors.ts`
  - Do: Create E2E test file (≤5 tests for rate limit). Test setup: create a mount via `POST /api/vfs/mounts` with by-type strategy. Tests: (1) mount option appears in explorer dropdown after page load, (2) selecting mount mode loads mount-organized tree with folder nodes, (3) expanding a folder shows object leaves, (4) clicking an object leaf opens object tab (EXP-05 verification), (5) switching back to by-type restores normal tree. Add mount-specific selectors to `selectors.ts`. Test teardown: delete the created mount.
  - Verify: `cd e2e && npx playwright test tests/20-vfs-explorer/ --reporter=list --project=chromium` — all 5 pass
  - Done when: E2E tests pass, EXP-04 and EXP-05 requirements verified end-to-end

## Files Likely Touched

- `backend/app/browser/workspace.py` — mount handler, children endpoint, prefix dispatch
- `backend/app/templates/browser/mount_tree.html` — root folder template
- `backend/app/templates/browser/mount_tree_objects.html` — object leaf template
- `backend/app/templates/browser/mount_tree_folders.html` — sub-folder template (by-date months)
- `backend/tests/test_mount_explorer.py` — unit tests
- `frontend/static/js/workspace.js` — dynamic mount option injection
- `backend/app/templates/browser/workspace.html` — minor if optgroup needed
- `e2e/tests/20-vfs-explorer/vfs-explorer.spec.ts` — E2E tests
- `e2e/helpers/selectors.ts` — mount explorer selectors
