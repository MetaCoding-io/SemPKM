# S03: VFS-Driven Explorer Modes — Research

**Date:** 2026-03-12

## Summary

S03 bridges the VFS mount system (5 directory strategies, SPARQL query builders, async mount listing) with the S01 explorer mode infrastructure (EXPLORER_MODES registry, dropdown with htmx swap, `#explorer-tree-body` target). The core challenge is an **adapter layer** that reuses `strategies.py` SPARQL query builders (designed for WebDAV DAVCollection responses) to render htmx tree HTML instead. The SPARQL queries themselves don't change — only the output format.

Three integration surfaces need work: (1) dynamically injecting mount-based `<option>` entries into the explorer dropdown on page load, (2) dispatching `mode=mount&mount_id={id}` requests to the correct strategy handler, and (3) rendering strategy folders/objects as `.tree-node`/`.tree-leaf` elements with `handleTreeLeafClick` for full object click-through. All strategies produce the same two-tier pattern: folders at top level, objects as leaves — except `flat` (single tier of objects) and `by-date` (three tiers: year → month → objects).

The mount listing already has an async REST endpoint (`GET /api/vfs/mounts`) that returns JSON. The workspace template can fetch mounts via htmx or JS on page load and inject `<option value="mount:{id}">` entries into the dropdown. The explorer tree handler dispatches to strategy-specific rendering using the same `build_scope_filter()` + query builder pattern from `strategies.py`.

## Recommendation

**Approach:** Build a thin adapter layer in `workspace.py` that:
1. Adds an async helper to list user-visible mounts (reusing the SPARQL from `mount_router.list_mounts`)
2. Registers a single `_handle_mount` handler in EXPLORER_MODES that accepts `mount_id` via query param
3. Dispatches to strategy-specific sub-handlers that call the same `query_*` functions from `strategies.py`
4. Renders folder nodes via a new `mount_tree.html` template (`.tree-node` elements) and object leaves via a new `mount_tree_objects.html` template (`.tree-leaf` elements with `handleTreeLeafClick`)
5. Adds a `GET /browser/explorer/mount-children` endpoint for lazy folder expansion (analogous to `/browser/explorer/children` for hierarchy)

**Dynamic dropdown injection:** On workspace page load, fetch `/api/vfs/mounts` via JS, inject `<option value="mount:{id}">{name}</option>` entries into `#explorer-mode-select`. The `initExplorerMode()` function already validates persisted mode against available options, so dynamically-added mount options integrate cleanly with localStorage persistence.

**Why not refactor strategies.py:** The query builders are pure functions returning SPARQL strings — they don't know about WebDAV or htmx. No refactoring needed. The adaptation is in *how results are rendered*, not *how queries are built*.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| SPARQL query for strategy folders/objects | `strategies.py` query builders (14 functions) | Already tested via VFS WebDAV. Same SPARQL, different renderer. |
| Mount listing with visibility filtering | `mount_router.list_mounts` SPARQL pattern | Already handles shared/personal visibility filter per user. |
| Scope filtering | `strategies.build_scope_filter(mount)` | Handles `sparql_scope` → SPARQL sub-select conversion. |
| Object click-through | `handleTreeLeafClick(event, iri, label)` | Opens object tab in dockview. Used by by-type and hierarchy modes. |
| Label resolution for objects | `LabelService.resolve_batch()` | Consistent label precedence (dcterms:title > rdfs:label > ...). |
| IRI-safe DOM IDs | `safe_id` Jinja2 filter pattern (replace `:/_#.`) | Used in nav_tree.html, hierarchy_tree.html. Same for mount nodes. |
| Icon resolution by type | `IconService.get_type_icon(type_iri, context="tree")` | Already used by hierarchy mode handler. |
| Explorer mode persistence | `localStorage('sempkm_explorer_mode')` + `initExplorerMode()` | S01/T03 implemented restore with option validation. |

## Existing Code and Patterns

- `backend/app/vfs/strategies.py` — 14 SPARQL query builder functions. Pure functions: `query_fn(params, scope_filter) -> str`. Import and call directly from workspace handlers. Key: `build_scope_filter(mount)` turns `MountDefinition.sparql_scope` into SPARQL fragment.
- `backend/app/vfs/mount_service.py` — `MountDefinition` dataclass with `id`, `name`, `path`, `strategy`, `group_by_property`, `date_property`, `sparql_scope`. Import for type annotations. `GRAPH_MOUNTS`, `NS_MOUNT`, `NS_SEMPKM` constants for mount graph queries.
- `backend/app/vfs/mount_router.py` — `list_mounts` endpoint at `GET /api/vfs/mounts` with async SPARQL, returns JSON list of mount dicts. Reuse the SPARQL pattern (not the endpoint) for workspace handler since we need `MountDefinition` objects, not JSON.
- `backend/app/browser/workspace.py` — `EXPLORER_MODES` dict is the handler registry. Handler signature: `async fn(request, ..., **_kwargs) -> HTMLResponse`. Dispatcher passes `shapes_service`, `icon_svc`, `label_service` to all handlers. New mount handler needs `mount_id` — pass via query param (`request.query_params.get("mount_id")`).
- `backend/app/templates/browser/hierarchy_tree.html` — Reference for tree node rendering: `.tree-node` with `hx-get` for lazy children, `.tree-label` with `handleTreeLeafClick`, icon via Lucide `<i>`. Mount folder nodes follow same pattern.
- `backend/app/templates/browser/tree_children.html` — Reference for tree leaf rendering: `.tree-leaf` with `data-iri`, `draggable="true"`, `handleTreeLeafClick` onclick. Mount object leaves follow same pattern for EXP-05 (same click behavior).
- `frontend/static/js/workspace.js` — `initExplorerMode()` (line 2016) handles dropdown `change` listener and localStorage restore. Validates stored mode against dropdown options. Dynamically-added mount options will be validated correctly.
- `backend/app/vfs/mount_collections.py` — WebDAV adapter that dispatches to strategy queries and builds DAVCollection responses. This is the "other renderer" — our htmx adapter does the same dispatch but renders HTML instead of DAVCollection objects.

## Constraints

- **Handler receives kwargs only:** The `explorer_tree` dispatcher passes a fixed set of kwargs (`shapes_service`, `icon_svc`, `label_service`). To pass `mount_id`, the handler must read it from `request.query_params` — not as a dispatcher kwarg. This matches how `mode` is already passed via query string.
- **Dropdown `hx-include="this"` sends only `name="mode"` value:** The `<select>` sends `?mode=by-type` (etc). For mounts, we need both mode and mount_id. Solution: use `mode=mount` (static) and encode mount_id in a separate mechanism. Options: (a) `<option value="mount:{uuid}">` then parse the mode string server-side, or (b) add a hidden input. Option (a) is simpler — parse `mode` prefix to detect mount modes.
- **Sync vs async triplestore client:** `workspace.py` handlers use `request.app.state.triplestore_client` (async `TriplestoreClient`). The `strategies.py` query builders return SPARQL strings — call `await client.query(sparql)` in the handler. No sync client needed.
- **`strategies.py` queries use `FROM <urn:sempkm:current>`:** All queries scope to the current graph, which is correct for the explorer (showing objects the user has access to).
- **Five strategies with different folder depths:** `flat` has no folders (just objects), `by-type`/`by-tag`/`by-property` have 1 level of folders, `by-date` has 2 levels (year → month). The lazy children endpoint must handle all three depth patterns.
- **Rate limit constraint for E2E:** Auth magic-link rate limit is 5/minute per IP. E2E test file must stay ≤5 tests to avoid failures.
- **`build_scope_filter` expects `MountDefinition` object:** Must construct or fetch the full `MountDefinition` for the mount, not just the mount_id.

## Common Pitfalls

- **Mount options not present on initial page load** — The workspace template is server-rendered with a fixed `<select>`. Mounts must be injected client-side after page load (fetch + DOM insert). If a user's persisted mode is `mount:xxx` but the mount was deleted, `initExplorerMode()` will correctly fall back to "By Type" because the option won't exist in the dropdown. This is the right behavior.
- **Strategy-specific folder rendering differences** — `flat` strategy has no folders — the handler must render objects directly (like tree_children.html). `by-date` has 2-level nesting (year folders → month subfolders → objects). The lazy children endpoint must detect which level it's expanding: mount root → strategy folders; folder → objects (or month subfolders for by-date).
- **SPARQL injection via mount_id** — Mount IDs are UUIDs from the triplestore. Must validate `mount_id` format before using in queries. Use `_validate_iri` or UUID format check.
- **`by-type` strategy in VFS vs `by-type` explorer mode** — A VFS mount with `by-type` strategy should NOT conflict with the explorer's built-in `by-type` mode. They're different: the built-in mode uses ShapesService types; the VFS mount `by-type` uses the strategy query with scope filtering. Clear naming in the dropdown prevents confusion.
- **Missing `group_by_property`/`date_property`** — `by-tag` and `by-property` strategies need `group_by_property`; `by-date` needs `date_property`. If these are null (bad mount data), the query builders return empty results or queries that match nothing. Handle gracefully — return empty tree with a message.
- **Folder label → object query mapping** — `StrategyFolderCollection._resolve_type_iri_from_label()` resolves type labels back to IRIs for by-type. The explorer adapter needs the same resolution. Import and reuse the SPARQL pattern, or pass the type IRI through the query param instead of the label.

## Open Risks

- **Dynamic dropdown injection timing** — If the JS fetch for mounts completes after `initExplorerMode()` runs, and the user's stored mode is a mount mode, the stored mode won't be found in options and will fall back to by-type. Mitigation: fetch mounts *before* calling `initExplorerMode()`, or re-run mode restore after mount options are injected.
- **No existing E2E test coverage for VFS mounts** — There are no E2E tests that create mounts or verify VFS behavior. S03 E2E tests will need to create a mount via `POST /api/vfs/mounts` as setup, then verify it appears in the explorer dropdown. This depends on the E2E test stack having an active triplestore with writable mount graph.
- **Folder label roundtrip for by-type strategy** — The `by-type` VFS strategy uses type local names as folder labels (e.g., "Note"), but the children endpoint needs the full type IRI to query objects. Either pass the type IRI through the htmx request or re-resolve it server-side. The `StrategyFolderCollection._resolve_type_iri_from_label()` pattern exists but adds a query roundtrip.
- **by-property and by-tag uncategorized folders** — Both strategies can produce `_uncategorized` virtual folders for objects missing the grouping property. The children endpoint must handle this case with `query_uncategorized_objects()`.
- **Large mount lists** — A user with many mounts will expand the dropdown significantly. Not a near-term risk but worth noting. No pagination needed yet.

## Architecture: Mode Value Encoding

The cleanest approach for mount mode identification in the `<select>` dropdown:

```
<option value="mount:abc-123-uuid">My Notes (by-date)</option>
```

Server-side parsing in `explorer_tree`:
```python
if mode.startswith("mount:"):
    mount_id = mode[6:]  # strip "mount:" prefix
    return await _handle_mount(request, mount_id=mount_id, ...)
```

This avoids adding a second query param or hidden input. The `hx-include="this"` on the select sends `?mode=mount:abc-123-uuid`, which the dispatcher can parse.

**Dynamic modes in EXPLORER_MODES dict:** Rather than registering each mount as a separate key, keep a single `_handle_mount` handler and do prefix matching:

```python
handler = EXPLORER_MODES.get(mode)
if handler is None and mode.startswith("mount:"):
    handler = _handle_mount  # or EXPLORER_MODES.get("mount")
```

This is cleaner than polluting the registry with per-mount entries.

## Architecture: Lazy Children Endpoint

A single `GET /browser/explorer/mount-children` endpoint handles all folder expansion:

Query params:
- `mount_id` — UUID of the mount
- `folder` — folder label (for by-type, by-tag, by-property) or year string (for by-date)
- `subfolder` (optional) — month folder for by-date (2nd level expansion)

The endpoint fetches the mount, determines the strategy, and dispatches to the appropriate `query_objects_*` function. For `by-date`, it returns month folders if `subfolder` is absent, or objects if `subfolder` is present.

## Architecture: Dynamic Dropdown Population

On workspace page load:
1. `initExplorerMode()` runs but mount options aren't in the DOM yet
2. A `fetch('/api/vfs/mounts')` call returns the user's mounts
3. For each mount, inject `<option value="mount:{id}">{name} ({strategy})</option>` into `#explorer-mode-select`
4. After injection, re-check localStorage mode and trigger htmx if the stored mode matches a mount option

This can be wrapped in a new `initExplorerMountOptions()` function called from `init()` after `initExplorerMode()`, or combined into a single async init flow.

## Task Decomposition Sketch

1. **T01: Backend — mount listing + mount tree handler + folder children endpoint** — Add async mount listing helper, `_handle_mount` handler, mount folder/object templates, and `mount-children` endpoint. Register in EXPLORER_MODES with prefix matching. Unit tests for handler dispatch and SPARQL structure.
2. **T02: Frontend — dynamic mount dropdown injection + localStorage handling** — Fetch mounts on page load, inject options, handle mount mode persistence and restore. Test with browser verification.
3. **T03: E2E tests + integration verification** — Create mount via API in test setup, verify it appears in dropdown, verify folder expansion, verify object click-through opens tab.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| htmx | — | none found |
| FastAPI | — | none found |
| SPARQL / RDF4J | — | none found |

No relevant professional skills found for the core technologies. The codebase has well-established patterns for all three.

## Sources

- S01 task summaries (T01–T04) — explorer mode infrastructure, handler signatures, htmx wiring
- S02 task summaries (T01–T02) — hierarchy handler implementation pattern, children endpoint pattern
- `backend/app/vfs/strategies.py` — SPARQL query builders for all 5 strategies
- `backend/app/vfs/mount_service.py` — MountDefinition dataclass, mount graph constants
- `backend/app/vfs/mount_router.py` — async mount CRUD endpoints, SPARQL patterns
- `backend/app/vfs/mount_collections.py` — WebDAV adapter layer (reference for dispatch pattern)
- `backend/app/browser/workspace.py` — EXPLORER_MODES registry, explorer_tree dispatcher, handler signatures
- `backend/app/templates/browser/hierarchy_tree.html` — tree node rendering reference
- `backend/app/templates/browser/tree_children.html` — tree leaf rendering reference (click-through)
- `frontend/static/js/workspace.js` — initExplorerMode(), handleTreeLeafClick, refreshNavTree
- D030, D031, D032, D033, D034, D035, D036 — relevant architectural decisions
