# M054 Research: Explorer Composable Filter/Group/Sort

## Current Explorer Architecture

### Backend

**workspace.py** (1341 lines) — the main explorer router with:
- `EXPLORER_MODES` dict: `by-type`, `hierarchy`, `by-tag` — three built-in mode handlers
- VFS mount dispatch via `mount:<uuid>` prefix in the mode parameter
- `GET /browser/explorer/tree?mode=<mode>` — returns htmx partial for the tree body
- `GET /browser/tree/{type_iri}` — lazy-loads objects under a type node
- `GET /browser/explorer/children?parent=<iri>` — hierarchy child expansion
- `GET /browser/explorer/tag-children?tag=<val>&prefix=<prefix>` — tag tree expansion
- `GET /browser/explorer/mount-children?mount_id=<uuid>&folder=<val>&depth=<n>` — VFS mount folder drill-down

All tree rendering uses htmx partials: `nav_tree.html`, `tree_children.html`, `hierarchy_tree.html`, `tag_tree.html`, `mount_tree.html`, `mount_tree_folders.html`, `mount_tree_objects.html`.

### Frontend

**workspace.js** — explorer state management:
- `EXPLORER_MODE_KEY = 'sempkm_explorer_mode'` stored in localStorage
- `initExplorerMode()` — restores mode from localStorage on page load
- `initExplorerMountOptions()` — fetches VFS mounts, injects as `<optgroup>` in the dropdown
- `refreshNavTree()` — re-fetches the current mode's tree via htmx
- Mode dropdown is `<select id="explorer-mode-select">` with htmx `hx-get="/browser/explorer/tree"` on `change`

**workspace.html** — sidebar structure:
- `#section-objects` is a static `div.explorer-section` inside the `#nav-pane` sidebar
- Contains the mode dropdown and `#explorer-tree-body` target
- Sidebar is outside dockview — it's a fixed HTML structure, not a panel

### VFS Strategies (Pattern Reference)

**strategies.py** (486 lines) — composable SPARQL query builders:
- 5 strategies: `flat`, `by-type`, `by-date`, `by-tag`, `by-property`
- Each strategy has folder-listing queries and object-listing queries
- `_LABEL_OPTIONALS` / `_LABEL_COALESCE` — shared label resolution SPARQL fragments
- `build_scope_filter(mount, ...)` — generates WHERE clause fragments from MountDefinition
- `build_chain_narrowing_filter(strategy, folder_value, mount)` — generates cumulative scope narrowing for chain traversal

**mount_service.py** — `MountDefinition` dataclass:
- `strategy: str` — single strategy or pipe-delimited chain (`"by-type|by-tag"`)
- `strategy_chain` property — splits into ordered list
- `is_chain` property — detects multi-level
- `type_filter: list[str] | None` — constrains to specific types via VALUES clause
- `group_by_property: str | None` — IRI of property to group by
- `date_property: str | None` — IRI of date property for by-date strategy
- `scope_query: str | None` — saved query IRI for scope filtering
- Maximum 3 chain levels enforced by `_validate_strategy_chain()`

### SHACL Property Discovery

**ShapesService** provides:
- `get_types(exclude_iris)` → list of `{iri, label}` — already strips " Shape" suffix
- `get_node_shapes()` → list of `NodeShapeForm` with full property metadata
- `get_form_for_type(type_iri)` → single `NodeShapeForm` with `PropertyShape` list
- Each `PropertyShape` has: `path`, `name`, `datatype`, `in_values` (for enum/status fields), `order`, `group`

**ViewSpecService** provides field detection heuristics:
- `_detect_status_field(type_iri)` — finds sh:in property for kanban grouping
- `_detect_date_fields(type_iri)` — finds date/dateTime properties for calendar/timeline
- `_detect_geo_fields(type_iri)` — finds lat/lng properties for map view
- `_detect_enrichment_fields(type_iri)` — finds priority + date for kanban card enrichment

**No JSON API for types/properties exists.** Frontend currently gets types via template context, not fetch. M054 needs a JSON endpoint for the config builder.

## Key Design Decisions

### 1. Explorer Configurations — Where to Store

**Options:**
- **localStorage** — current pattern for mode, panel positions. Lost on browser clear, not portable.
- **SQL table** — like DashboardSpec. Persistent, per-user, supports sharing. Requires migration.
- **RDF named graph** — like saved queries. Semantic but overkill for UI config.

**Recommendation: SQL table.** Follows the DashboardSpec pattern. A new `explorer_configs` table with:
- `id`, `user_id`, `name`, `config_json` (filter/group/sort layers), `created_at`, `updated_at`

The active config for the OBJECTS section stays in localStorage (just stores the config UUID). Persona system captures it like explorer_mode today.

### 2. Multiple OBJECTS Panels — Implementation Path

The OBJECTS section is a sidebar `div.explorer-section`, not a dockview panel. Two approaches:

**Option A: Multiple sidebar sections.** Add a "Duplicate" button to the OBJECTS header. Each duplicate gets its own config, tree body, and ID. Sidebar already supports section reordering.
- Pro: Stays within existing sidebar pattern
- Con: Sidebar space is limited, multiple tree sections get cramped

**Option B: Explorer as dockview panel.** Open explorer configs as dockview tabs in the main area, like view panels.
- Pro: Full-size panel, consistent with how views work
- Con: Explorer tree in main area feels wrong for navigation — it's a sidebar concept

**Recommendation: Option A** (multiple sidebar sections) with a config selector. Defers Option B to a follow-up if sidebar space proves too limited.

### 3. Filter/Group/Sort Layers — SPARQL Strategy

The VFS chain strategy pattern already solves multi-level grouping via pipe-delimited strategies and cumulative `build_chain_narrowing_filter()`. The new explorer configs should:

1. **Filter layer** → `build_scope_filter()` equivalent (type_filter VALUES clause + optional saved query scope)
2. **Group layer** → reuse `by-type`, `by-tag`, `by-property`, `by-date` strategies from strategies.py
3. **Sort layer** → extend SPARQL query builders with `ORDER BY ?{sortProperty}` instead of hardcoded `ORDER BY ?label`

Multi-level grouping = chain strategies with depth tracking, already implemented in `mount_children()`.

### 4. Config Builder UI

The config builder needs:
1. Type picker (multi-select from available types)
2. Group-by picker (properties available for selected type(s), from SHACL shapes)
3. Sort-by picker (label, created date, or any SHACL property)
4. Name field for saving

**Requires new JSON API endpoint:** `GET /api/explorer/types-and-properties` → returns types with their groupable/sortable properties for the config builder UI.

## Existing Code to Reuse

| Component | Reuse | Notes |
|-----------|-------|-------|
| `strategies.py` query builders | Direct reuse | All 5 strategies + chain narrowing |
| `build_scope_filter()` | Direct reuse | Handles type_filter + scope_query |
| `_LABEL_OPTIONALS` / `_LABEL_COALESCE` | Direct reuse | Label resolution pattern |
| `MountDefinition` pattern | Structural reference | ExplorerConfig follows same shape |
| `workspace.html` section pattern | Template reference | New section duplicates section-objects structure |
| `tree_children.html` / `nav_tree.html` | Direct reuse | Object leaf rendering unchanged |
| `DashboardSpec` model pattern | SQL model reference | explorer_configs follows same UUID+user_id+JSON pattern |
| `ShapesService.get_types()` | Direct reuse | Type picker data |
| `ShapesService.get_form_for_type()` | Direct reuse | Property picker data |

## Risks and Mitigations

### Risk 1: SPARQL Performance with Multi-Level Grouping
**Assessment:** Medium. The existing VFS chain queries work at moderate scale. RDF4J handles GROUP BY efficiently for type/property grouping. The risk is with sorting by arbitrary properties — each OPTIONAL for a sort property adds join overhead.
**Mitigation:** Limit sort properties to those present in SHACL shapes (known set, not arbitrary). Consider LIMIT on initial tree load.

### Risk 2: Config Builder Complexity
**Assessment:** Low-Medium. The builder needs to dynamically show available properties based on selected types. This requires a new JSON API endpoint and dynamic form UI.
**Mitigation:** Use htmx for property loading — when type selection changes, fetch properties via htmx. No need for a SPA-style reactive form.

### Risk 3: Multiple Sidebar Sections — Space and UX
**Assessment:** Low. Most users will have 1-2 configs. The sidebar already scrolls. Each config section collapses when not in use.
**Mitigation:** Start with max 3 config sections. Add a UI affordance (collapse all others when expanding one).

### Risk 4: VFS Mount Dropdown Removal
**Assessment:** Low but has migration concern. The context says "Remove VFS Mounts from mode dropdown." VFS mounts have their own management UI at `/admin/vfs`. Removing from dropdown doesn't remove the feature.
**Mitigation:** Keep VFS mount tree rendering intact but remove from the explorer mode dropdown. VFS browsing still accessible via admin.

## Natural Slice Boundaries

### Slice 1: Explorer Configuration Backend + API (Risk: Medium)
- SQL model for `explorer_configs` (migration, CRUD service)
- JSON API: `GET/POST/PUT/DELETE /api/explorer/configs`
- JSON API: `GET /api/explorer/types-and-properties` (type picker + property picker data)
- Reuse ShapesService for type/property discovery

### Slice 2: Composable SPARQL Query Builder (Risk: Highest)
- New `build_explorer_query()` that composes filter→group→sort layers
- Reuses existing strategy query builders from strategies.py
- Adds sort-by-property capability to SPARQL builders
- New `GET /browser/explorer/config-tree?config_id=<uuid>` endpoint for tree rendering
- Unit tests proving correct SPARQL generation for multi-level configs

### Slice 3: Config Builder UI (Risk: Medium)
- htmx-powered config builder partial with type/property pickers
- Integrated into explorer section header (replace mode dropdown)
- Save/name/manage configurations
- Config selector dropdown (replaces current mode dropdown with config picker)

### Slice 4: Multiple Panels + Cleanup (Risk: Low)
- "Duplicate" button on OBJECTS section header
- Each duplicate section has its own config and tree body
- Remove VFS Mounts from explorer dropdown
- Clean up old mode code
- E2E tests for full flow

## Candidate Requirements

The following should be tracked as requirements if the planner agrees:

1. **Explorer config CRUD** — users can create, name, update, and delete explorer configurations
2. **Composable filter/group/sort** — configurations support independent filter (type/tag/query), group-by (property/type/tag), and sort (label/date/property) layers
3. **Config persistence** — saved configs survive browser restart (server-side storage)
4. **Multiple explorer panels** — at least 2 OBJECTS sections with different configs open simultaneously
5. **Clean type labels** — no raw model IDs, no " Shape" suffixes in explorer tree (already handled by `get_types()` but verify in tree rendering)
6. **VFS mount dropdown removal** — VFS mounts no longer appear in explorer mode dropdown
7. **Backward compatibility** — existing by-type/hierarchy/by-tag modes remain accessible as built-in configs or presets

## Open Questions (Resolved by Research)

**Q: How many grouping levels?** → 3, matching VFS chain limit. Already enforced by `_validate_strategy_chain()`.

**Q: Server-side or localStorage?** → Server-side SQL, following DashboardSpec pattern. localStorage stores only the active config ID. Persona system captures it.

**Q: What about the existing by-type/hierarchy/by-tag modes?** → These become "preset" configs that ship as system defaults. Users can still select them but can also create custom configs. The mode dropdown evolves into a config picker.
