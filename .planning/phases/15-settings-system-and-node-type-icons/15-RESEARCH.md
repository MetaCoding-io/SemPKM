# Phase 15: Settings System and Node Type Icons - Research

**Researched:** 2026-02-24
**Domain:** Settings infrastructure, icon system, manifest extension, server-side persistence
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Settings Page Layout:**
- Two-column layout: category sidebar on the left, settings detail panel on the right (VS Code / macOS System Preferences style)
- Settings are accessible via both `Ctrl+,` (global shortcut, works from anywhere) and the user menu
- Search filter works in-place: non-matching settings hide, categories collapse if all their settings are filtered out
- Apply is instant — no Save button; changes dispatch `sempkm:setting-changed` immediately on change

**Modified Indicators:**
- Both a badge ("Modified") and a per-setting reset button appear when a value differs from its default
- Per-setting reset plus a "Reset all to defaults" option per category and globally

**Setting Input Types:**
- All four input types required: toggle (boolean), dropdown/select, text input, color picker
- Initial settings scope: dark mode only — the system is wired up and ready to expand, but only dark mode is a real setting in this phase

**Persistence:**
- User overrides stored server-side in the database (not localStorage)
- Syncs across browsers/devices

**Icon Visual Treatment:**
- Each node type gets a distinct color (defined in the mental model manifest per type)
- Same icon and same color used consistently in explorer tree, graph view, and editor tab headers
- Icons appear on object tab headers: icon + object name
- Fallback for unmapped types: a generic neutral icon (e.g., circle/dot) in a neutral color
- Manifest supports icon, color, and size per context (tree vs. graph vs. tab) — granular per-context control

**Mental Model Contributions:**
- Model-contributed settings appear under a category named after the model in the sidebar (e.g., "Zettelkasten" section)
- When a model is removed, its contributed user overrides are also removed from the database (clean slate)
- Icon/color manifest entries can specify different values per view context: `{ type, icon, color, size }` per context

### Claude's Discretion

- Exact spacing, typography, and visual polish of the Settings page
- Progress indicator or loading state when settings are first fetched
- How color picker component is implemented (library choice or custom)
- Exact manifest JSON schema details beyond the per-context structure

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SETT-01 | A Settings page opens as a tab in the editor area (accessible via Ctrl+, or user menu) with categorized settings and a search filter | Settings tab opens via `openSettingsTab()` function in workspace.js, served from a new `/browser/settings` FastAPI endpoint as an htmx partial; search filter is DOM-only in-place filtering |
| SETT-02 | Settings use a layered resolution: system defaults < mental model defaults < user overrides | Three-layer merge: system defaults dict in Python, model manifest `settings` key parsed at load time, user overrides in a new `user_settings` SQL table keyed by `(user_id, setting_key)`; merged at request time in a `SettingsService` |
| SETT-03 | Settings changes dispatch a `sempkm:setting-changed` DOM event that consuming components listen to | `document.dispatchEvent(new CustomEvent('sempkm:setting-changed', { detail: { key, value, resolved } }))` dispatched by client-side `settings.js`; theme.js already has this pattern for `sempkm:theme-changed` |
| SETT-04 | Mental Models can contribute settings via a `settings` key in their manifest, which appear in the Settings page under the model's category | `ManifestSchema` extended with an optional `settings: list[ManifestSettingDef]` field; settings collected by `SettingsService.get_all_settings()` by iterating installed models |
| ICON-01 | Object explorer tree displays type-specific icons (from Lucide icon set) next to each object, with color coding | `nav_tree.html` and `tree_children.html` currently use emoji placeholders (📁 / 📄); backend passes `type_icons` dict to templates; Lucide icons rendered via `<i data-lucide="...">` with color inline style; `lucide.createIcons()` called after htmx swaps |
| ICON-02 | Graph view nodes display type-appropriate colors and optional shape differentiation | `graph.js` `buildSemanticStyle()` already applies per-type `background-color` from `typeColors`; extending to use `nodeIcon` requires Cytoscape `background-image` or `content` CSS (Cytoscape supports SVG data-URIs as node background images) |
| ICON-03 | Mental Models can declare icon and color mappings for their types in the model manifest | New optional `icons: list[ManifestIconDef]` field in `ManifestSchema`; parsed from manifest.yaml and stored/loaded via a new `IconService` or queried through SPARQL from a `sempkm:nodeIcon` property on ontology classes |
</phase_requirements>

---

## Summary

Phase 15 has two distinct workstreams that share one dependency: the manifest extension. The settings system is a new infrastructure layer (server-side storage, a JS module, a Settings page UI) with dark mode as its sole initial consumer. The icon system extends existing code paths (nav tree, graph view, editor tabs) with Lucide icon + color data derived from the mental model manifest.

The project already has substantial infrastructure that Phase 15 builds on. The `InstanceConfig` table exists as a key-value store but it is instance-wide — a new `user_settings` table with a `(user_id, setting_key)` primary key is needed for per-user overrides. The manifest system (`ManifestSchema`, `parse_manifest`) is Pydantic-based and easily extended. The graph view already has a `type_colors` pipeline (`sempkm:nodeColor` RDF property → `_get_model_node_colors()` → `buildSemanticStyle()`); adding `nodeIcon` follows the same pattern. The dark mode system currently reads from `localStorage` via `theme.js` — Phase 15 migrates persistence to server-side while keeping the anti-FOUC localStorage read in place as a fast-path.

The biggest design decision is the settings storage model: a dedicated `user_settings` SQL table (user_id, key, value, updated_at) is the right approach, NOT overloading `instance_config`. This keeps user preferences per-user and allows clean removal when a model is uninstalled.

**Primary recommendation:** Build settings as a service layer (`SettingsService`) with a SQL table, extend `ManifestSchema` with `settings` and `icons` fields, and wire icon lookups into the three existing render paths (nav tree, graph, tab bar) using the already-loaded Lucide CDN.

---

## Standard Stack

### Core (already in project — no new installs needed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | current | API routes for settings CRUD | Already the project web framework |
| SQLAlchemy async | current | `user_settings` table ORM model | Already used for `User`, `UserSession`, `InstanceConfig` |
| Alembic | current | Migration for `user_settings` table | Already the migration tool |
| Pydantic | current | `ManifestSettingDef`, `ManifestIconDef` | Already used in `ManifestSchema` |
| Lucide | 0.575.0 CDN | Type icons in tree, tabs | Already loaded in `base.html` via CDN |
| htmx | 2.0.4 CDN | Settings page as partial, PATCH for save | Already the project's AJAX mechanism |
| Jinja2 | current | Settings page template | Already the templating engine |

### Supporting (no install needed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| native `<input type="color">` | browser | Color picker for color settings | Claude's discretion: avoids a new CDN dependency; HTML5 color input works in all modern browsers with good dark mode support |
| `CustomEvent` DOM API | browser | `sempkm:setting-changed` dispatch | Matches existing `sempkm:theme-changed` pattern in theme.js |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| native `<input type="color">` | Pickr, Spectrum.js | Native is zero-dependency; third-party gives more control but adds a CDN script |
| SQL `user_settings` table | Triplestore SPARQL | SQL is already the persistence layer for user data; triplestore is for knowledge graph data |
| Pydantic-extended `ManifestSchema` | Separate YAML key outside manifest | Keeping settings and icons in manifest.yaml is consistent with existing `entrypoints` and `prefixes` |

**Installation:** No new packages needed. All tooling already in the project.

---

## Architecture Patterns

### Recommended Project Structure additions

```
backend/app/
├── services/
│   ├── settings.py        # NEW: SettingsService (layer merge, CRUD)
│   └── icons.py           # NEW: IconService (manifest icon lookup)
├── auth/
│   └── models.py          # EXTEND: add UserSetting ORM model
├── models/
│   └── manifest.py        # EXTEND: ManifestSettingDef, ManifestIconDef
├── browser/
│   └── router.py          # EXTEND: /browser/settings GET/POST/DELETE endpoints
├── templates/browser/
│   ├── settings_page.html # NEW: two-column settings page template
│   ├── nav_tree.html       # MODIFY: pass icon/color to tree nodes
│   └── tree_children.html  # MODIFY: pass icon/color to leaf nodes
└── migrations/versions/
    └── 002_user_settings.py  # NEW: user_settings table

frontend/static/js/
├── settings.js            # NEW: client-side settings module (fetch, merge, dispatch)
└── workspace.js           # MODIFY: add Ctrl+, shortcut + openSettingsTab()
```

### Pattern 1: Settings Tab as Special Tab

The `openViewTab()` function in workspace.js uses a `view:` prefix convention to distinguish view tabs from object tabs. The same pattern applies to the Settings tab:

```javascript
// In workspace.js (new function openSettingsTab)
function openSettingsTab() {
  var tabKey = 'special:settings';
  var layout = window._workspaceLayout;
  if (!layout) return;

  var activeGroup = layout.getGroup(layout.activeGroupId);
  if (activeGroup) {
    var existing = activeGroup.tabs.find(function (t) { return (t.id || t.iri) === tabKey; });
    if (existing) {
      switchTabInGroup(tabKey, layout.activeGroupId);
      return;
    }
  }
  layout.addTabToGroup(
    { id: tabKey, iri: tabKey, label: 'Settings', dirty: false, isView: false, isSpecial: true, specialType: 'settings' },
    layout.activeGroupId
  );
  window.loadTabInGroup(layout.activeGroupId, tabKey);
}
```

In `workspace-layout.js`'s `loadTabInGroup()`, a new branch handles `special:settings` tabs:

```javascript
// In loadTabInGroup() - add branch after view tab check
if (tabId === 'special:settings' || (tab.isSpecial && tab.specialType === 'settings')) {
  url = '/browser/settings';
}
```

The Ctrl+, shortcut adds one line to the keyboard handler in workspace.js:

```javascript
// In initKeyboardShortcuts() keydown handler
if (mod && e.key === ',') {
  e.preventDefault();
  openSettingsTab();
}
```

The user menu Settings link (currently `.disabled` in `_sidebar.html`) is activated:

```html
<!-- In components/_sidebar.html user popover -->
<a href="#" class="popover-item" onclick="openSettingsTab(); document.getElementById('user-popover').hidePopover();">
    <i data-lucide="settings" class="popover-icon"></i>
    <span>Settings</span>
</a>
```

### Pattern 2: Three-Layer Settings Resolution

```python
# backend/app/services/settings.py

@dataclass
class SettingDefinition:
    key: str           # e.g. "core.theme", "zettelkasten.defaultNoteType"
    label: str
    description: str
    input_type: str    # "toggle" | "select" | "text" | "color"
    options: list[str] | None   # for select type
    default: str       # system default value
    category: str      # sidebar category name
    model_id: str | None  # None for core settings

class SettingsService:
    # System defaults: hardcoded in Python
    SYSTEM_SETTINGS: dict[str, SettingDefinition] = {
        "core.theme": SettingDefinition(
            key="core.theme",
            label="Theme",
            input_type="select",
            options=["light", "dark", "system"],
            default="system",
            category="General",
            model_id=None,
        )
    }

    async def get_all_settings(self) -> list[SettingDefinition]:
        """Merge system + model-contributed settings."""
        settings = list(self.SYSTEM_SETTINGS.values())
        # Query installed models, parse manifest.yaml, collect manifest.settings
        ...

    async def get_user_overrides(self, user_id: UUID) -> dict[str, str]:
        """Load all user_settings rows for this user."""
        ...

    async def resolve(self, user_id: UUID) -> dict[str, str]:
        """Return fully merged settings: system defaults + model defaults + user overrides."""
        ...

    async def set_override(self, user_id: UUID, key: str, value: str) -> None:
        """Upsert a user_settings row."""
        ...

    async def reset_override(self, user_id: UUID, key: str) -> None:
        """Delete the user_settings row (restores to default)."""
        ...

    async def remove_model_overrides(self, user_id: UUID, model_id: str) -> None:
        """Delete all user_settings for keys contributed by a model."""
        ...
```

### Pattern 3: UserSetting ORM Model

Following the exact pattern of `InstanceConfig` in `backend/app/auth/models.py`:

```python
# In backend/app/auth/models.py (extend existing file)
import uuid

class UserSetting(Base):
    """Per-user setting overrides. Key is '{category}.{name}'."""

    __tablename__ = "user_settings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    key: Mapped[str] = mapped_column(String(255))
    value: Mapped[str] = mapped_column(String(4096))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_user_settings"),)
```

### Pattern 4: ManifestSchema Extensions

Extending `ManifestSchema` in `backend/app/models/manifest.py`:

```python
class ManifestSettingDef(BaseModel):
    key: str              # e.g. "defaultNoteType"  (prefixed by modelId at load time)
    label: str
    description: str = ""
    input_type: str       # "toggle" | "select" | "text" | "color"
    options: list[str] | None = None
    default: str

class ManifestIconContextDef(BaseModel):
    """Per-context icon/color/size override."""
    icon: str            # Lucide icon name, e.g. "file-text"
    color: str           # CSS hex color, e.g. "#4e79a7"
    size: int | None = None  # px, defaults to context default

class ManifestIconDef(BaseModel):
    type: str            # full type IRI or short local name (resolved against namespace)
    tree: ManifestIconContextDef | None = None
    graph: ManifestIconContextDef | None = None
    tab: ManifestIconContextDef | None = None
    # Convenience: top-level icon/color applied to all contexts unless overridden
    icon: str | None = None
    color: str | None = None

class ManifestSchema(BaseModel):
    # ... existing fields ...
    settings: list[ManifestSettingDef] = Field(default_factory=list)
    icons: list[ManifestIconDef] = Field(default_factory=list)
```

**Manifest YAML example** (in `models/basic-pkm/manifest.yaml`):

```yaml
icons:
  - type: "bpkm:Note"
    icon: "file-text"
    color: "#4e79a7"
    tab:
      icon: "file-text"
      color: "#4e79a7"
      size: 14
    tree:
      icon: "file-text"
      color: "#4e79a7"
      size: 16
    graph:
      icon: "file-text"
      color: "#4e79a7"

settings:
  - key: "defaultNoteType"
    label: "Default Note Type"
    input_type: "select"
    options: ["permanent", "fleeting", "literature"]
    default: "permanent"
```

### Pattern 5: Client-Side Settings Module (settings.js)

A new `settings.js` IIFE that owns the settings cache and dispatch:

```javascript
// frontend/static/js/settings.js
(function () {
  'use strict';

  var _cache = null;  // resolved settings from server

  function fetchSettings() {
    return fetch('/browser/settings/data')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        _cache = data;  // { key: resolvedValue, ... }
        return data;
      });
  }

  function get(key) {
    return _cache ? _cache[key] : null;
  }

  function set(key, value) {
    return fetch('/browser/settings/' + encodeURIComponent(key), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ value: value })
    }).then(function () {
      if (_cache) _cache[key] = value;
      document.dispatchEvent(new CustomEvent('sempkm:setting-changed', {
        detail: { key: key, value: value }
      }));
    });
  }

  function reset(key) {
    return fetch('/browser/settings/' + encodeURIComponent(key), {
      method: 'DELETE'
    }).then(fetchSettings).then(function (data) {
      document.dispatchEvent(new CustomEvent('sempkm:setting-changed', {
        detail: { key: key, value: data[key] }
      }));
    });
  }

  window.SemPKMSettings = { get: get, set: set, reset: reset, fetch: fetchSettings };
})();
```

The existing `theme.js` then becomes a consumer of `sempkm:setting-changed`:

```javascript
// In theme.js: replace localStorage theme read with settings API
// BUT: keep the anti-FOUC inline script reading localStorage as fast-path
// The settings system sets both localStorage AND server-side for theme
document.addEventListener('sempkm:setting-changed', function (e) {
  if (e.detail.key === 'core.theme') {
    window.setTheme(e.detail.value);
  }
});
```

### Pattern 6: Icon Rendering in Explorer Tree

Currently `nav_tree.html` uses an emoji fallback `&#128193;` (folder). The backend `workspace()` route passes `types` list. Extending to pass icon/color:

```python
# In browser/router.py workspace() route
# Load icon mappings from IconService
icon_map = await icon_service.get_icon_map(context='tree')
# icon_map: { type_iri: { icon: "file-text", color: "#4e79a7", size: 16 } }
context = {"request": request, "types": types, "type_icons": icon_map, "user": user}
```

In `nav_tree.html`:
```html
{% for type in types %}
{% set type_icon = type_icons.get(type.iri, {}) %}
<div class="tree-node" data-type-iri="{{ type.iri }}" ...>
    <span class="tree-toggle">&#9656;</span>
    {% if type_icon.icon %}
    <i data-lucide="{{ type_icon.icon }}"
       class="tree-node-icon"
       style="color: {{ type_icon.color }}; width: {{ type_icon.size or 16 }}px; height: {{ type_icon.size or 16 }}px;"></i>
    {% else %}
    <i data-lucide="circle" class="tree-node-icon" style="color: var(--color-text-faint);"></i>
    {% endif %}
    <span class="tree-label">{{ type.label }}</span>
</div>
{% endfor %}
```

`tree_children.html` similarly gets object-level icons (object icons use the same type icon):
```html
{% for obj in objects %}
{% set obj_icon = type_icons.get(obj.type_iri, {}) %}
<div class="tree-leaf" onclick="openTab('{{ obj.iri }}', '{{ obj.label }}')">
    {% if obj_icon.icon %}
    <i data-lucide="{{ obj_icon.icon }}"
       class="tree-leaf-icon"
       style="color: {{ obj_icon.color }};"></i>
    {% else %}
    <i data-lucide="circle" class="tree-leaf-icon" style="color: var(--color-text-faint); width:14px;height:14px;"></i>
    {% endif %}
    <span class="tree-leaf-label">{{ obj.label }}</span>
</div>
{% endfor %}
```

**Critical:** After htmx swaps nav_tree content, `lucide.createIcons()` must be called. This already happens in the workspace via `htmx:afterSwap` handlers. Verify the tree swap fires the icon init.

### Pattern 7: Icon Rendering in Tab Bar

`renderGroupTabBar()` in `workspace-layout.js` builds tab DOM with `createElement`. Tab objects stored in session state can include `typeIcon` and `typeColor`:

```javascript
// In renderGroupTabBar(), add icon before label for non-view, non-special tabs
if (!isView && tab.typeIcon) {
  var iconEl = document.createElement('i');
  iconEl.setAttribute('data-lucide', tab.typeIcon);
  iconEl.style.color = tab.typeColor || '';
  iconEl.style.width = '14px';
  iconEl.style.height = '14px';
  iconEl.style.flexShrink = '0';
  tabEl.insertBefore(iconEl, labelEl);
}
// After building the tab bar, reinitialize lucide icons
if (typeof lucide !== 'undefined') lucide.createIcons({ nodes: [tabBar] });
```

The tab object gets `typeIcon`/`typeColor` when `openTab()` is called. The backend `object/` endpoint must return icon metadata in a way JavaScript can access. Options:
1. Add `data-type-icon` and `data-type-color` attributes to the `object-tab` div in `object_tab.html` → JavaScript reads them after htmx load and updates the tab model.
2. Include a small inline script in `object_tab.html` that calls `window._workspaceLayout.updateTabIcon(objectIri, icon, color)`.

**Recommendation:** Option 2 — inline script in `object_tab.html` is consistent with how other post-load JS runs in that template.

### Pattern 8: Graph Node Icons via Cytoscape

Cytoscape supports node background images as SVG data-URIs. Lucide icons are SVG-based, so a type's icon can be converted to an inline SVG URI and set as `background-image` on the node style:

```javascript
// In graph.js buildSemanticStyle() — per-type icon style
if (typeIcons && typeIcons[typeIri]) {
  var iconInfo = typeIcons[typeIri];
  // SVG data-URI approach
  var svgContent = getLucideSvgString(iconInfo.icon);  // helper function
  if (svgContent) {
    styles.push({
      selector: 'node[type = "' + typeIri + '"]',
      style: {
        'background-image': 'data:image/svg+xml;utf8,' + encodeURIComponent(svgContent),
        'background-fit': 'contain',
        'background-clip': 'none',
        'background-position-x': '50%',
        'background-position-y': '50%',
        'background-width': '60%',
        'background-height': '60%',
        'background-opacity': 0.8
      }
    });
  }
}
```

**Complexity note:** Getting the SVG string from the Lucide CDN build requires calling `lucide.icons[iconName]` (an object with `toSvg()` or similar) — verify this API at implementation time. An alternative is to just extend the existing color coding with shape differentiation (`shape: 'rectangle'` for one type, `shape: 'diamond'` for another) which is simpler than SVG embedding. Since ICON-02 says "optional shape differentiation," shape differentiation may be sufficient for the graph view.

**Recommendation:** For the graph view, extend the existing `type_colors` pipeline to also serve `type_icons` from the manifest. At render time in graph.js, apply shapes per type (e.g., `rectangle` for Note, `diamond` for Concept, `ellipse` default) as a simpler alternative to SVG embedding. If SVG icons are needed, that becomes an enhancement.

### Anti-Patterns to Avoid

- **Overloading `instance_config`:** That table is instance-wide key-value; user settings MUST be per-user.
- **Storing icon/color in the triplestore only:** The manifest is YAML and should be the source; RDF `sempkm:nodeColor` already exists in the codebase as an optional RDF property. Phase 15 adds the manifest YAML path as the primary declaration method.
- **Calling `lucide.createIcons()` without scoping:** Always pass `{ nodes: [specificContainer] }` after partial swaps to avoid re-scanning the entire document.
- **Blocking the anti-FOUC inline script:** The theme quick-read from localStorage in `base.html` must stay; the settings API call happens after DOM ready and dispatches an event that updates if different.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Color picker | Custom color swatch UI | `<input type="color">` native | Browser-native, zero deps, dark mode adapts, returns hex strings directly |
| Settings persistence | localStorage or triplestore | SQL `user_settings` table (new Alembic migration) | Consistent with existing auth model, supports multi-device sync, easy to cascade-delete on model uninstall |
| Icon SVG extraction | DOM parsing of Lucide bundle | `lucide.icons[name]` object API | Lucide's UMD bundle exposes icon data; avoid parsing SVG files manually |
| Settings search filter | Server-side re-render | DOM-only show/hide with `display:none` | Settings are fully loaded on page open; filtering is UI-only, no round trips needed |

---

## Common Pitfalls

### Pitfall 1: Lucide Icons Not Rendering After htmx Swaps
**What goes wrong:** After the nav tree reloads children via htmx (`hx-swap="innerHTML"`), Lucide icons in the newly-inserted HTML are plain `<i data-lucide="...">` elements that Lucide hasn't processed.
**Why it happens:** `lucide.createIcons()` is called once on load; htmx swaps inject new DOM that Lucide has never seen.
**How to avoid:** Register an `htmx:afterSwap` listener that calls `lucide.createIcons()` after tree partial swaps. Also call it after `renderGroupTabBar()` in workspace-layout.js.
**Warning signs:** Icons appear as blank elements with no SVG content.

### Pitfall 2: theme.js and settings.js Race Condition
**What goes wrong:** On page load, `theme.js` reads `localStorage` synchronously (fast). `settings.js` fetches `/browser/settings/data` asynchronously (slow). If the server value differs from localStorage, a delayed flash occurs.
**Why it happens:** Two sources of truth momentarily disagree.
**How to avoid:** Keep localStorage as the fast-path FOUC prevention; settings.js fetch happens after DOM ready and only re-applies theme if server value differs from what was already applied. Write-through: when user changes theme via settings, update both localStorage AND the server simultaneously.
**Warning signs:** Visible theme flash after initial paint.

### Pitfall 3: UserSetting Key Collision Between Models
**What goes wrong:** Two models both contribute a setting with key `"defaultType"`. One model's override overwrites the other.
**Why it happens:** Keys not namespaced by model.
**How to avoid:** Prefix model-contributed setting keys with `{modelId}.` at load time: `"basic-pkm.defaultNoteType"`. Core settings use `"core."` prefix.
**Warning signs:** Settings from different models share a row in `user_settings`.

### Pitfall 4: `user_settings` Rows Orphaned When Model Removed
**What goes wrong:** User has overrides for `"basic-pkm.defaultNoteType"`. Model is uninstalled. The orphaned rows remain in `user_settings`.
**Why it happens:** No cascade cleanup in uninstall handler.
**How to avoid:** The model removal route (`DELETE /admin/models/{model_id}`) must call `SettingsService.remove_model_overrides(user_id, model_id)` for all users, or cascade via a model_id column on `user_settings`.
**Warning signs:** Settings page shows settings for an uninstalled model.

### Pitfall 5: Manifest Icon Type Resolution (Short Name vs Full IRI)
**What goes wrong:** Manifest declares `type: "bpkm:Note"` but the triplestore uses `urn:sempkm:model:basic-pkm:Note`. Lookup fails.
**Why it happens:** Prefixes in manifest YAML are not automatically expanded when parsing icon definitions.
**How to avoid:** `IconService` must expand type names using the model's namespace and `prefixes` from the manifest. `bpkm:Note` → `urn:sempkm:model:basic-pkm:Note` using `manifest.prefixes["bpkm"]` + `"Note"`.
**Warning signs:** Icon map never matches actual type IRIs from triplestore.

---

## Code Examples

### Settings API Routes (FastAPI)

```python
# In backend/app/browser/router.py

@router.get("/settings")
async def settings_page(
    request: Request,
    user: User = Depends(get_current_user),
    settings_service: SettingsService = Depends(get_settings_service),
):
    """Render the Settings page as an htmx partial."""
    templates = request.app.state.templates
    all_settings = await settings_service.get_all_settings()
    user_overrides = await settings_service.get_user_overrides(user.id)
    resolved = await settings_service.resolve(user.id)

    context = {
        "request": request,
        "all_settings": all_settings,
        "user_overrides": user_overrides,
        "resolved": resolved,
    }
    return templates.TemplateResponse(request, "browser/settings_page.html", context)


@router.get("/settings/data")
async def settings_data(
    user: User = Depends(get_current_user),
    settings_service: SettingsService = Depends(get_settings_service),
):
    """Return resolved settings as JSON for the client-side cache."""
    resolved = await settings_service.resolve(user.id)
    return JSONResponse(content=resolved)


@router.put("/settings/{key:path}")
async def update_setting(
    key: str,
    body: dict,
    user: User = Depends(get_current_user),
    settings_service: SettingsService = Depends(get_settings_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Upsert a user override for a setting key."""
    value = body.get("value", "")
    await settings_service.set_override(user.id, key, value, db)
    return {"key": key, "value": value}


@router.delete("/settings/{key:path}")
async def reset_setting(
    key: str,
    user: User = Depends(get_current_user),
    settings_service: SettingsService = Depends(get_settings_service),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a user override, reverting to default."""
    await settings_service.reset_override(user.id, key, db)
    resolved = await settings_service.resolve(user.id)
    return {"key": key, "default_value": resolved.get(key)}
```

### Alembic Migration for `user_settings`

```python
# backend/migrations/versions/002_user_settings.py
def upgrade() -> None:
    op.create_table(
        "user_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("value", sa.String(4096), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "key", name="uq_user_settings"),
    )
    op.create_index("ix_user_settings_user_id", "user_settings", ["user_id"])

def downgrade() -> None:
    op.drop_table("user_settings")
```

### Existing `_get_model_node_colors()` extension to also fetch icons

```python
# In backend/app/views/service.py (extend existing _get_model_node_colors pattern)
async def _get_model_node_icons(self, type_iris: set[str]) -> dict[str, str]:
    """Query ontology classes for sempkm:nodeIcon RDF property.

    Same pattern as _get_model_node_colors(). Returns type_iri -> icon_name dict.
    """
    # ... same structure as _get_model_node_colors but queries sempkm:nodeIcon
    icon_sparql = f"""SELECT ?type ?icon
{from_str}
WHERE {{
  VALUES (?type) {{ {values} }}
  ?type <{SEMPKM_VOCAB}nodeIcon> ?icon .
}}"""
```

### Settings Page Template Structure

```html
<!-- browser/settings_page.html -->
<div class="settings-page">
  <div class="settings-search-bar">
    <i data-lucide="search" style="width:16px;height:16px;"></i>
    <input type="text" id="settings-search" placeholder="Search settings..."
           oninput="filterSettings(this.value)">
  </div>
  <div class="settings-layout">
    <!-- Left: category sidebar -->
    <nav class="settings-sidebar" id="settings-sidebar">
      {% for category in categories %}
      <button class="settings-category-btn {% if loop.first %}active{% endif %}"
              data-category="{{ category.id }}"
              onclick="showSettingsCategory('{{ category.id }}')">
        {{ category.label }}
      </button>
      {% endfor %}
    </nav>
    <!-- Right: settings detail -->
    <div class="settings-detail" id="settings-detail">
      {% for category in categories %}
      <div class="settings-category-panel" id="category-{{ category.id }}"
           {% if not loop.first %}style="display:none"{% endif %}>
        <h2 class="settings-category-title">{{ category.label }}</h2>
        <button class="settings-reset-all-btn"
                onclick="resetCategoryDefaults('{{ category.id }}')">
          Reset category to defaults
        </button>
        {% for setting in category.settings %}
        <div class="settings-row" data-key="{{ setting.key }}" data-search="{{ setting.label | lower }}">
          <div class="settings-row-info">
            <span class="settings-label">{{ setting.label }}</span>
            {% if setting.description %}
            <span class="settings-description">{{ setting.description }}</span>
            {% endif %}
          </div>
          <div class="settings-row-control">
            {% if setting.key in user_overrides %}
            <span class="settings-modified-badge">Modified</span>
            <button class="settings-reset-btn" onclick="resetSetting('{{ setting.key }}')">Reset</button>
            {% endif %}
            <!-- Input rendered based on setting.input_type -->
            {% include "browser/_setting_input.html" %}
          </div>
        </div>
        {% endfor %}
      </div>
      {% endfor %}
    </div>
  </div>
</div>
```

---

## State of the Art

| Old Approach | Current Approach | Status in Codebase | Impact for Phase 15 |
|--------------|------------------|-------------------|---------------------|
| `sempkm:nodeColor` RDF property in ontology | Manifest YAML `icons` field | RDF approach already exists; manifest approach is new | Phase 15 adds manifest path; existing RDF approach is still supported as fallback |
| Emoji placeholders in nav tree (`&#128193;`, `&#128196;`) | Lucide SVG icons with per-type color | Currently emoji (nav_tree.html) | Replace with Lucide via icon_service lookup |
| Dark mode as localStorage-only | Dark mode as settings system consumer | Currently localStorage via theme.js | Phase 15 migrates to server-side with localStorage fast-path |
| Settings link disabled (`.disabled` class) | Settings opens as editor tab | Currently `.disabled` in `_sidebar.html` | Phase 15 enables the link |

---

## Open Questions

1. **How does `tree_children.html` know the type IRI?**
   - What we know: `/browser/tree/{type_iri}` receives `type_iri` in the URL; the template renders object leaves. The type IRI is available in the route handler.
   - What's unclear: The template context currently only has `objects: [{ iri, label }]`. It does not include `type_iri` or `type_icons`.
   - Recommendation: Pass `type_icon` (a single icon dict for this type) from the route handler into the tree_children template context. This is simple since all children share one type.

2. **Icon data accessibility for tab label updates**
   - What we know: Tab icon needs to appear when the tab is opened. `openTab()` in workspace.js creates the tab immediately before the htmx content loads.
   - What's unclear: When `openTab(objectIri, label)` is called from the explorer, the type IRI and icon are not yet known. Options: (a) fetch icon data eagerly when tree loads and cache it in a `window._typeIconMap`; (b) read `data-type-icon` from the object_tab DOM after htmx load.
   - Recommendation: Option (a) — load the icon map at workspace init via a small `/browser/icons` JSON endpoint and cache in `window._sempkmIcons`. Then `openTab()` can look up the type icon from the tree node's `data-type-iri` attribute before adding the tab.

3. **Color picker for color-type settings**
   - What we know: `<input type="color">` is browser-native and works. It opens a system color picker.
   - What's unclear: Dark mode styling of the native color picker varies by OS/browser. Custom pickers (Pickr.js) are more controllable but add CDN dependency.
   - Recommendation: Use native `<input type="color">` (Claude's discretion). The value is a hex string; no parsing needed. Flag this as a potential enhancement point.

4. **Dark mode migration: when does the server value take effect?**
   - What we know: The anti-FOUC script reads localStorage synchronously. Settings API is async.
   - What's unclear: Sequence of: localStorage read → DOM ready → settings.js fetch → possible theme change.
   - Recommendation: On settings save for `core.theme`, write through to both server AND localStorage simultaneously. On page load, settings.js reads server value and only dispatches if different from what's already applied. This means localStorage is always kept in sync, making it a reliable fast-path.

---

## Implementation Sequence for Plans

Based on the three-plan structure:

**Plan 15-01: Settings Infrastructure**
- SQL: `UserSetting` ORM model + Alembic migration `002_user_settings.py`
- Python: `SettingsService` (system defaults, merge logic, CRUD)
- Python: extend `ManifestSchema` with `settings` and `icons` fields
- FastAPI: `/browser/settings` GET, `/browser/settings/data` GET, `/browser/settings/{key}` PUT/DELETE
- JS: `settings.js` module (fetch, get, set, reset, dispatch)
- JS: Add `Ctrl+,` shortcut to workspace.js + `openSettingsTab()` + enable user menu link
- JS: wire workspace-layout.js `loadTabInGroup()` for `special:settings`

**Plan 15-02: Settings Page UI**
- Template: `settings_page.html` (two-column layout, search filter)
- Template: `_setting_input.html` (toggle/select/text/color input partials)
- CSS: settings page styles in `workspace.css` or new `settings.css`
- JS: in-page settings behavior (category switching, search filter, Modified badge logic)
- Wire: dark mode setting as first real consumer (settings.js + theme.js integration)
- Test: `Ctrl+,` opens tab, settings display, change fires event, dark mode responds

**Plan 15-03: Node Type Icons**
- Python: `IconService` (manifest icon parsing with prefix expansion)
- Python: extend `views/service.py` to serve `type_icons` alongside `type_colors`
- Python: extend browser routes to pass `type_icons` to nav tree templates
- Template: `nav_tree.html` and `tree_children.html` — replace emoji with Lucide icons
- Template: `object_tab.html` — add inline script to update tab with type icon
- JS: `workspace-layout.js` `renderGroupTabBar()` — render icon before label
- JS: `graph.js` — extend `buildSemanticStyle()` for icon shapes or SVG
- CSS: icon sizing styles for `.tree-node-icon`, `.tree-leaf-icon`, `.tab-type-icon`
- Model: update `basic-pkm/manifest.yaml` with icon/color definitions for 4 types
- Test: icons visible in tree, graph, tabs; fallback circle for unknown types

---

## Sources

### Primary (HIGH confidence)
- Codebase: `/home/james/Code/SemPKM/backend/app/auth/models.py` — existing ORM pattern for `InstanceConfig`
- Codebase: `/home/james/Code/SemPKM/backend/app/models/manifest.py` — Pydantic manifest schema
- Codebase: `/home/james/Code/SemPKM/backend/app/views/service.py` — `_get_model_node_colors()` + `SEMPKM_VOCAB`
- Codebase: `/home/james/Code/SemPKM/frontend/static/js/workspace-layout.js` — tab model, `renderGroupTabBar()`
- Codebase: `/home/james/Code/SemPKM/frontend/static/js/workspace.js` — keyboard shortcuts, `openViewTab()` pattern
- Codebase: `/home/james/Code/SemPKM/frontend/static/js/theme.js` — event dispatch, localStorage pattern
- Codebase: `/home/james/Code/SemPKM/frontend/static/js/graph.js` — `buildSemanticStyle()`, Cytoscape usage
- Codebase: `/home/james/Code/SemPKM/backend/app/templates/browser/nav_tree.html` — current emoji placeholders
- Codebase: `/home/james/Code/SemPKM/backend/app/templates/browser/tree_children.html` — leaf node rendering
- Codebase: `/home/james/Code/SemPKM/backend/app/templates/components/_sidebar.html` — disabled settings link
- Codebase: `/home/james/Code/SemPKM/backend/migrations/versions/001_initial_auth_tables.py` — Alembic pattern
- Codebase: `/home/james/Code/SemPKM/models/basic-pkm/manifest.yaml` — existing manifest structure

### Secondary (MEDIUM confidence)
- Lucide 0.575.0 CDN (already loaded in `base.html`) — Lucide exposes `lucide.icons` object in UMD build; `createIcons({ nodes: [...] })` for scoped re-init

### Tertiary (LOW confidence — verify at implementation)
- Cytoscape SVG background-image approach for node icons — needs testing that `background-image` with data-URI works correctly with the fCose/dagre layouts in the project's Cytoscape version (3.33.1)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project, patterns clearly identified from codebase
- Architecture: HIGH — all extension points found in existing code; no new dependencies required
- Settings persistence: HIGH — `InstanceConfig` pattern is a direct template for `UserSetting`
- Icon system: HIGH for tree/tab; MEDIUM for graph SVG icons (Cytoscape SVG API needs verification)
- Pitfalls: HIGH — all identified from direct code analysis

**Research date:** 2026-02-24
**Valid until:** 2026-03-25 (stable stack)
