---
estimated_steps: 5
estimated_files: 5
---

# T01: Backend mount handler, children endpoint, and templates

**Slice:** S03 — VFS-Driven Explorer Modes
**Milestone:** M003

## Description

Build the core backend that bridges VFS strategy SPARQL builders to htmx tree rendering. This includes: (1) parsing `mount:` prefix in the `explorer_tree` dispatcher to route to a mount handler, (2) an async `_handle_mount` handler that fetches the `MountDefinition`, builds scope filter, dispatches to the correct strategy query builder, and renders folder/object templates, (3) a `GET /browser/explorer/mount-children` endpoint for lazy folder expansion across all 5 strategies, and (4) three Jinja2 templates for mount tree rendering.

## Steps

1. **Add mount prefix matching to `explorer_tree` dispatcher.** Before the `EXPLORER_MODES.get(mode)` lookup, check if `mode.startswith("mount:")`. If so, extract the mount_id (everything after `mount:`), validate UUID format, and call `_handle_mount(request, mount_id, ...)` directly. This avoids polluting the EXPLORER_MODES registry with per-mount entries.

2. **Implement `_handle_mount` async handler.** Fetch `MountDefinition` by mount_id via async SPARQL query on `request.app.state.triplestore_client` (reuse the SPARQL pattern from `mount_router.list_mounts` / `mount_service.get_mount_by_id`, adapted for async client). Build scope filter via `strategies.build_scope_filter(mount)`. Dispatch to strategy-specific rendering:
   - `flat` → call `query_flat_objects(scope_filter)`, render objects directly via `mount_tree_objects.html`
   - `by-type` → call `query_type_folders(scope_filter)`, render folders via `mount_tree.html`
   - `by-date` → call `query_date_year_folders(mount.date_property, scope_filter)`, render year folders via `mount_tree.html`
   - `by-tag` → call `query_tag_folders(mount.group_by_property, scope_filter)`, render folders via `mount_tree.html`
   - `by-property` → call `query_property_folders(mount.group_by_property, scope_filter)`, render folders via `mount_tree.html`
   For by-tag/by-property, also check `query_has_uncategorized()` and add an `_uncategorized` folder if needed. Handle missing strategy config (null `date_property` for by-date, null `group_by_property` for by-tag/by-property) by returning empty tree with descriptive message. Return 400 for non-existent mount.

3. **Implement `mount_children` endpoint.** Add `GET /browser/explorer/mount-children` with query params `mount_id`, `folder`, and optional `subfolder`. Fetch mount, build scope filter, dispatch by strategy:
   - `by-type` → `query_objects_by_type(folder_as_type_iri, scope_filter)` → render `mount_tree_objects.html`. For by-type, `folder` will be the type IRI (passed through the htmx request).
   - `by-date` without `subfolder` → `query_date_month_folders(date_prop, folder_as_year, scope_filter)` → render `mount_tree_folders.html` (month sub-folders)
   - `by-date` with `subfolder` → `query_objects_by_date(date_prop, folder_as_year, subfolder_as_month, scope_filter)` → render `mount_tree_objects.html`
   - `by-tag` → `query_objects_by_tag(tag_prop, folder, scope_filter)` → render `mount_tree_objects.html`. Special case: `folder=_uncategorized` → `query_uncategorized_objects(tag_prop, scope_filter)`
   - `by-property` → `query_objects_by_property(group_prop, folder, is_iri, scope_filter)` → render `mount_tree_objects.html`. Special case: `folder=_uncategorized` → `query_uncategorized_objects(group_prop, scope_filter)`
   - `flat` → should not be called (flat has no folders), return empty
   Resolve labels via `label_service.resolve_batch()` and icons via `icon_svc.get_type_icon()`.

4. **Create templates.** Three Jinja2 templates:
   - `mount_tree.html` — Renders folder nodes as `.tree-node` with `hx-get="/browser/explorer/mount-children?mount_id={mount_id}&folder={folder_value}"`, `hx-trigger="click once"`, `hx-target` pointing to a `#mount-children-{safe_id}` div. Uses folder icon (folder lucide icon). Context: `folders` list, `mount_id`, `mount_name`. Empty state: "No folders found" message.
   - `mount_tree_objects.html` — Renders object leaves as `.tree-leaf` with `data-iri`, `draggable="true"`, `handleTreeLeafClick(event, iri, label)`. Matches `tree_children.html` pattern exactly for click-through (EXP-05). Context: `objects` list with `iri`, `label`, `icon`. Empty state: "No objects" message.
   - `mount_tree_folders.html` — Renders sub-folder nodes (by-date months) as `.tree-node` with `hx-get` including `subfolder` param. Context: `folders` list, `mount_id`, `parent_folder`. Same structure as `mount_tree.html` but with `subfolder` query param added.

5. **Wire helper for async mount fetch.** Add `_get_mount_definition(client, mount_id)` async helper in workspace.py that queries the mount graph and returns `MountDefinition | None`. Reuse the SPARQL pattern from `mount_service.get_mount_by_id()` but call `await client.query()` instead of sync. Import `MountDefinition`, `GRAPH_MOUNTS`, `NS_MOUNT`, namespace constants from `mount_service.py`.

## Must-Haves

- [ ] `explorer_tree` parses `mount:` prefix and routes to mount handler
- [ ] `_handle_mount` dispatches to all 5 strategy query builders correctly
- [ ] `mount_children` endpoint handles folder expansion for all strategies including by-date 3-tier
- [ ] Object leaves have `handleTreeLeafClick` for full click-through (EXP-05)
- [ ] Missing/invalid mount returns HTTP 400 with descriptive error
- [ ] Missing strategy config (null date_property, null group_by_property) returns empty tree with message
- [ ] Existing explorer modes (by-type, hierarchy, by-tag placeholder) still work unchanged

## Verification

- `GET /browser/explorer/tree?mode=mount:{valid-uuid}` → 200 with folder/object HTML
- `GET /browser/explorer/tree?mode=mount:nonexistent-uuid` → 400
- `GET /browser/explorer/tree?mode=mount:not-a-uuid` → 400
- `GET /browser/explorer/mount-children?mount_id=xxx&folder=yyy` → 200
- `GET /browser/explorer/tree?mode=by-type` → 200 (no regression)
- `GET /browser/explorer/tree?mode=hierarchy` → 200 (no regression)

## Observability Impact

- Signals added/changed: DEBUG log `"Mount explorer tree requested: mount_id=%s, strategy=%s"` on mount handler entry; DEBUG log `"Mount children requested: mount_id=%s, folder=%s, strategy=%s"` on children expansion
- How a future agent inspects this: `curl` the endpoints directly with a known mount_id; inspect server logs with DEBUG level
- Failure state exposed: HTTP 400 with `{"detail":"Unknown mount: {id}"}` for missing mount; HTTP 400 with `{"detail":"Invalid mount_id format"}` for bad UUID; empty tree with descriptive message for missing strategy config

## Inputs

- `backend/app/browser/workspace.py` — `EXPLORER_MODES`, `explorer_tree` dispatcher, handler pattern from S01/S02
- `backend/app/vfs/strategies.py` — 14 SPARQL query builder functions, `build_scope_filter()`
- `backend/app/vfs/mount_service.py` — `MountDefinition` dataclass, `GRAPH_MOUNTS`, `NS_MOUNT`, namespace constants
- `backend/app/templates/browser/hierarchy_tree.html` — reference for `.tree-node` rendering
- `backend/app/templates/browser/tree_children.html` — reference for `.tree-leaf` object rendering with `handleTreeLeafClick`
- S03-RESEARCH.md — architecture decisions for mode encoding, children endpoint, and adapter layer

## Expected Output

- `backend/app/browser/workspace.py` — `_handle_mount` handler, `mount_children` endpoint, `_get_mount_definition` helper, prefix dispatch in `explorer_tree`
- `backend/app/templates/browser/mount_tree.html` — root folder template
- `backend/app/templates/browser/mount_tree_objects.html` — object leaf template with click-through
- `backend/app/templates/browser/mount_tree_folders.html` — sub-folder template (by-date months)
