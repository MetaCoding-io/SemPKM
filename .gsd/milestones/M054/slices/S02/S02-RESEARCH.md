# S02 Research: Config Persistence, Multi-Panel & Presets

## Summary

Straightforward CRUD + UI slice. All patterns are established in the codebase — `DashboardSpec` model/service/migration for SQL persistence, `explorer-config.js` for frontend config state, sidebar `explorer-section` for multi-panel. No unfamiliar technology, no ambiguous scope.

## Requirements Owned

- **R011** — Explorer configs persist server-side, CRUD API, survive browser restart
- **R012** — Multiple OBJECTS sections open simultaneously with independent configs  
- **R013** — Existing modes (by-type, hierarchy, by-tag) accessible as built-in presets

## Recommendation

Four tasks: (1) SQL model + migration + service, (2) REST API router + presets, (3) frontend config persistence + preset selector, (4) multi-panel duplicate support. T1→T2→T3→T4 linear dependency.

## Implementation Landscape

### 1. SQL Model + Migration (follows DashboardSpec exactly)

**New model:** `backend/app/browser/explorer_models.py`

```python
class ExplorerConfigSpec(Base):
    __tablename__ = "explorer_configs"
    id: Mapped[uuid.UUID]           # PK, default uuid4
    user_id: Mapped[uuid.UUID]      # FK users.id
    name: Mapped[str]               # String(255)
    config_json: Mapped[str]        # Text — JSON of {type_filter, group_by, sort_by, sort_order}
    is_preset: Mapped[bool]         # False for user configs, True for system presets
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

**Migration:** `backend/migrations/versions/026_add_explorer_configs.py` (revision "026", down_revision "025").

**Service:** `backend/app/browser/explorer_config_service.py` — async CRUD class taking `session_factory`, methods: `create()`, `list_for_user()`, `get()`, `update()`, `delete()`, `get_or_create_presets()`.

**Pattern source:** `backend/app/dashboard/models.py` (DashboardSpec), `backend/app/dashboard/service.py` (DashboardService). Copy structure exactly.

### 2. REST API + Presets

**New routes on `workspace_router`** (or a new `explorer_api_router`):

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/explorer/configs` | List user's saved configs + presets |
| POST | `/api/explorer/configs` | Create new config |
| PATCH | `/api/explorer/configs/{id}` | Update config name/settings |
| DELETE | `/api/explorer/configs/{id}` | Delete user config (not presets) |

**Presets:** Three built-in presets created on first access via `get_or_create_presets()`:

| Preset Name | Config |
|-------------|--------|
| By Type | `{group_by: "type", sort_by: "label", sort_order: "asc"}` |
| By Tag | `{group_by: "tag", sort_by: "label", sort_order: "asc"}` |
| Hierarchy | Special flag — delegates to existing `_handle_hierarchy()` |

**Hierarchy note:** The hierarchy mode uses `dcterms:isPartOf` traversal — a fundamentally different query pattern than the composable config engine. The preset can't express this as an ExplorerConfig. Options: (a) add a `mode` field to ExplorerConfig that says "use legacy handler", or (b) treat hierarchy as a separate option in the dropdown rather than a preset config. Option (b) is simpler — keep the hierarchy as a built-in option alongside saved configs in the selector UI.

**Service wiring:** `app.state.explorer_config_service = ExplorerConfigService(async_session_factory)` in main.py lifespan.

### 3. Frontend Config Persistence + Preset Selector

**Changes to `explorer-config.js`:**

- Add a config selector dropdown above the config builder panel (replaces "OBJECTS" header area)
- "Save" button in config panel → POST to `/api/explorer/configs` with name + current settings
- "Load" a saved config → populates dropdowns from config_json + applies
- Active config ID stored in localStorage (lightweight — just the UUID reference, data is server-side)
- On page load: fetch configs list, restore active config from localStorage if present

**Changes to `explorer_config_panel.html`:**

- Add name input field for saving
- Add "Save" / "Save As" button
- Add config selector (dropdown or list) above the config builder

### 4. Multi-Panel Support

**The OBJECTS section** in `workspace.html` is a single `<div id="section-objects">`. For multi-panel:

- "Duplicate" button in OBJECTS header → JS clones the section structure with unique IDs
- Each cloned section gets its own `explorer-tree-body-{n}`, config panel, and config state
- Config panel controls are scoped to the parent section (use `closest('.explorer-section')` instead of global IDs)

**Key refactor needed:** Currently all DOM IDs in explorer-config.js are global (`explorer-config-type`, `explorer-tree-body`, etc.). For multi-panel, these need to become section-scoped. Options:
- (a) Suffix all IDs with a panel index: `explorer-config-type-0`, `explorer-config-type-1`
- (b) Use `closest('.explorer-section').querySelector('.explorer-config-type')` — class-based instead of ID-based
- (c) Keep primary section with IDs, duplicate section uses different prefix

**Recommendation:** Option (b) — class-based selectors scoped to the parent section. This requires refactoring `_el(id)` calls in `explorer-config.js` to accept a section root element parameter. The refactor is contained within one file.

**Sidebar ordering:** Duplicated sections use existing `data-panel-name` + `draggable` drag-reorder. Panel positions already use localStorage (`sempkm_panel_positions`).

### 5. Persona Integration

The persona model has `explorer_mode: str` column. S02 should:
- Store the active config UUID instead of mode string (e.g., `config:<uuid>`)
- On persona switch: load the stored config and apply it
- Backward compat: existing `by-type`/`by-tag` values map to presets

This is a minor extension of the persona save/load flow in `persona/router.py`.

## Files to Create

| File | Purpose |
|------|---------|
| `backend/app/browser/explorer_models.py` | ExplorerConfigSpec SQLAlchemy model |
| `backend/app/browser/explorer_config_service.py` | Async CRUD service |
| `backend/migrations/versions/026_add_explorer_configs.py` | Alembic migration |
| `backend/tests/test_explorer_config_service.py` | Service unit tests |

## Files to Modify

| File | Change |
|------|--------|
| `backend/app/browser/workspace.py` | Add 4 API endpoints for config CRUD |
| `backend/app/main.py` | Wire ExplorerConfigService on app.state |
| `frontend/static/js/explorer-config.js` | Add save/load/selector logic, section-scoped DOM access |
| `backend/app/templates/browser/explorer_config_panel.html` | Add name field, save button, config selector |
| `backend/app/templates/browser/workspace.html` | Add duplicate button in OBJECTS header |
| `frontend/static/css/explorer-config.css` | Config selector and multi-panel styles |
| `e2e/helpers/selectors.ts` | Add persistence/multi-panel selectors |

## Constraints & Gotchas

1. **In-memory SQLite FK constraint** (Pattern #8): Test fixtures must import `User` model for FK resolution.
2. **Hierarchy preset** can't be expressed as ExplorerConfig — keep it as a separate option in the selector rather than a saved config row.
3. **Multi-panel DOM refactor:** All ID-based element access in `explorer-config.js` must become section-scoped class-based access for multi-panel to work. This is the riskiest part of the slice.
4. **No VFS mount dropdown removal** in this slice — the dropdown was already removed in S01. VFS mount tree rendering remains intact via legacy `/browser/explorer/tree?mode=mount:<uuid>` endpoint.
5. **Migration revision "026":** down_revision must be "025" (latest existing migration).

## Verification Strategy

- Unit tests: CRUD operations on ExplorerConfigSpec — create, list, get, update, delete, presets auto-creation
- API tests: HTTP endpoints return correct responses, auth required, user isolation
- Browser verification: save config → reload page → config appears in selector → click to apply → tree renders correctly. Duplicate → second section with independent config.
- Preset verification: By Type and By Tag presets produce same trees as S01's built-in group options.

## Skills

No external skills needed. All patterns are established in-codebase. No unfamiliar libraries.
