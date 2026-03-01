# Architecture Research: SemPKM v2.3 Shell, Navigation & Views

**Domain:** Integration architecture for dockview Phase A, carousel views, named layouts, FTS fuzzy
**Researched:** 2026-03-01
**Confidence:** HIGH (based on direct codebase analysis, prior phase-23 research doc, and existing DECISIONS.md)

---

## System Overview

The four v2.3 features integrate into an existing three-layer architecture:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Browser (htmx + vanilla JS)                       │
│                                                                           │
│  workspace.html          workspace.js         workspace-layout.js         │
│  ┌───────────────┐       ┌─────────────┐     ┌──────────────────────┐   │
│  │  nav-pane     │       │ openTab()   │────▶│ WorkspaceLayout       │   │
│  │  editor-pane  │       │ openViewTab │     │  .groups[]            │   │
│  │  right-pane   │       │ togglePane()│     │  addGroup()           │   │
│  └───────────────┘       └─────────────┘     │  recreateGroupSplit() │   │
│                                              │  loadTabInGroup()     │   │
│  Split.js (outer panes)  ◀── kept v2.3 ──▶  │  ← Phase A replaces   │   │
│  dockview-core (inner)   ◀── NEW Phase A ──  │  recreateGroupSplit() │   │
│                                              └──────────────────────┘   │
│                                                                           │
│  carousel-view.js (NEW)  view_switcher template (modified)                │
│  named-layouts.js (NEW)  command palette entries (modified)               │
└───────────────────────────────────────────────────────────────────────────┘
                                    │ htmx.ajax / fetch
┌───────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                                     │
│                                                                           │
│  browser/router.py   views/router.py   sparql/router.py                  │
│  ┌──────────────┐   ┌──────────────┐  ┌─────────────────────┐           │
│  │ /browser/    │   │ /browser/    │  │ /api/search          │           │
│  │  object/{iri}│   │  views/      │  │  SearchService       │           │
│  │  settings    │   │  table/card/ │  │  (FTS fuzzy changes) │           │
│  └──────────────┘   │  graph/      │  └─────────────────────┘           │
│                     │  carousel/   │                                      │
│                     │  (NEW)       │  /api/layouts (NEW)                 │
│                     └──────────────┘   LayoutService (NEW)               │
│                                                                           │
│  views/service.py (ViewSpecService)   models/manifest.py (schema mod)    │
└───────────────────────────────────────────────────────────────────────────┘
                                    │ SPARQL / LuceneSail
┌───────────────────────────────────────────────────────────────────────────┐
│                        RDF4J Triplestore                                  │
│  urn:sempkm:current  urn:sempkm:model:{id}:views  urn:sempkm:events      │
│  LuceneSail index (FTS, fuzzy query syntax support)                      │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Feature 1: Dockview Phase A — Editor-Pane Migration

### What Changes

Phase A replaces the Split.js editor-groups split managed by `workspace-layout.js` with a `dockview-core` DockviewComponent instance. The outer three-column split (nav-pane / editor-pane / right-pane) run by `workspace.js` via Split.js is **not** touched in Phase A.

### Integration Points

**workspace-layout.js** is the primary target. The function `recreateGroupSplit()` (lines 301-408) builds the DOM and creates/destroys the Split.js instance between groups. This function is replaced wholesale by a dockview initialization call.

Current `recreateGroupSplit()` responsibilities, mapped to dockview equivalents:

| Current (Split.js) | Dockview Phase A Replacement |
|--------------------|------------------------------|
| Creates `#editor-groups-container` div | Becomes the dockview root element (existing `#editor-groups-container`) |
| Creates `.editor-group` divs with `.group-tab-bar` and `.group-editor-area` | Dockview owns tab bars and group containers natively |
| Creates horizontal Split.js instance between groups | Dockview handles group splits with its own sash/resize |
| Calls `renderGroupTabBar(group)` per group | Dockview renders tab bars natively via its `tabComponent` |
| Calls `loadTabInGroup(groupId, tabId)` per group | `createComponent` callback calls `htmx.ajax()` on `params.containerElement` |
| `onDragEnd` saves split sizes to sessionStorage | `onDidLayoutChange` serializes to sessionStorage via `dockview.toJSON()` |

**workspace.js** changes are smaller: `openTab()`, `openViewTab()`, `splitRight()` currently call `layout.addTabToGroup()` which triggers `recreateGroupSplit()`. With dockview, these functions instead call `dockview.api.addPanel()` with appropriate panel options. The window export names (`window.openTab`, `window.splitRight`) remain unchanged — callers in HTML templates are unaffected.

**workspace.html** changes: The static initial HTML inside `#editor-groups-container` (the `#group-1` div with `#tab-bar-group-1` and `#editor-area-group-1`) is replaced with an empty container div. Dockview creates all internal DOM. The `bottom-panel` and `panel-resize-handle` elements outside the groups container are unaffected.

**dockview-sempkm-bridge.css** is activated: load order in `workspace.html` becomes:
```
theme.css → dockview-sempkm-bridge.css → dockview-core CDN CSS
```
This bridge file already exists at `frontend/static/css/dockview-sempkm-bridge.css` as a pattern-only file from v2.2. It maps all `--dv-*` variables to SemPKM `--color-*` / `--tab-*` / `--panel-*` tokens.

### dockview Component Registration

Two panel content components must be registered at init time:

```javascript
const dockview = new DockviewComponent(
  document.getElementById('editor-groups-container'),
  {
    createComponent: (options) => {
      if (options.name === 'object-editor') {
        return {
          init: (params) => {
            htmx.ajax('GET', '/browser/object/' + encodeURIComponent(params.params.iri), {
              target: params.containerElement, swap: 'innerHTML'
            });
          }
        };
      }
      if (options.name === 'view-panel') {
        return {
          init: (params) => {
            const url = '/browser/views/' + params.params.viewType + '/' + encodeURIComponent(params.params.viewId);
            htmx.ajax('GET', url, { target: params.containerElement, swap: 'innerHTML' });
          }
        };
      }
      if (options.name === 'special-panel') {
        return {
          init: (params) => {
            htmx.ajax('GET', '/browser/' + params.params.specialType, {
              target: params.containerElement, swap: 'innerHTML'
            });
          }
        };
      }
    },
    createTabComponent: (options) => { /* optional custom tab renderer */ }
  }
);
```

The `params.containerElement` is a plain DOM element. This matches the existing `htmx.ajax()` call in `loadTabInGroup()` exactly — the only change is the target element reference.

### WorkspaceLayout Data Model Changes

`WorkspaceLayout` currently stores:
```json
{
  "groups": [{ "id": "group-1", "tabs": [...], "activeTabId": "...", "size": 50 }],
  "activeGroupId": "group-1"
}
```

With dockview, the canonical layout state is owned by dockview's `toJSON()`. The `WorkspaceLayout` class either:
1. **Thin wrapper**: Delegates all state reads to `dockview.toJSON()` and writes to `dockview.api.addPanel()`. The class persists `dockview.toJSON()` to sessionStorage instead of its own format.
2. **Retained for tab metadata**: `WorkspaceLayout` keeps the tab metadata structure (label, dirty, typeIcon) as a sidecar dict keyed by panel ID. Dockview stores only the panel IDs and IRIs in its serialization.

Option 2 is the cleaner migration path. Keep `WorkspaceLayout` as a tab metadata registry; dockview owns the layout geometry. Persist both as `sempkm_workspace_layout_v2` (new key) to avoid collisions with the existing sessionStorage key.

### htmx Re-wiring Required

1. **`sempkm:tab-activated` event**: Currently dispatched from `switchTabInGroup()` and `openTab()` in `workspace-layout.js`. With dockview, wire to `dockview.onDidActivePanelChange` event instead. Same event shape: `{ tabId, groupId, isObjectTab }`.

2. **`sempkm:tabs-empty` event**: Currently dispatched from `removeTabFromGroup()` when no object tabs remain. Wire to `dockview.onDidRemovePanel` callback that checks remaining panels.

3. **`htmx.process()` after panel moves**: The `dockview.onDidLayoutChange` handler should call `htmx.process(changedPanel.view.contentContainer)` to re-establish htmx attribute bindings after drag-to-reorder events (not required for tab switches within same group).

4. **`loadRightPaneSection()`**: Called from `setActiveGroup()` and `switchTabInGroup()` to update the Relations and Lint panels in the right pane. Wire to `dockview.onDidActivePanelChange` instead.

### New vs Modified Files (Phase A)

| File | Status | Change |
|------|--------|--------|
| `frontend/static/js/workspace-layout.js` | MODIFIED | Replace `recreateGroupSplit()`, `groupSplitInstance`, HTML5 drag-drop logic with dockview API calls. Keep `WorkspaceLayout` class as metadata registry. |
| `frontend/static/js/workspace.js` | MODIFIED | `openTab()`, `openViewTab()`, `splitRight()` call `dockview.api.addPanel()` instead of `layout.addTabToGroup()`. Wire events to dockview callbacks. |
| `backend/app/templates/browser/workspace.html` | MODIFIED | Remove static `#group-1` inner HTML. Add dockview CDN `<link>` and `<script>`. Load `dockview-sempkm-bridge.css`. |
| `frontend/static/css/dockview-sempkm-bridge.css` | MODIFIED (activated) | Remove "STATUS: Pattern file — NOT loaded" comment. This file is now loaded. |
| `frontend/static/css/workspace.css` | MODIFIED | Remove `.editor-group`, `.group-tab-bar`, `.group-editor-area`, `gutter-editor-groups` styles. Dockview owns tab bar and group styling. Adjust `.editor-groups-container` to be a full-height dockview host. |

---

## Feature 2: Carousel Views

### What Carousel Means

When a user opens an object of type `bpkm:Note`, a carousel bar appears showing all `sempkm:ViewSpec` instances with `sempkm:targetClass: bpkm:Note`. The user clicks (or keyboard-navigates) through them — each switch loads a different view (table, card, graph) for that type. This is "view rotation" per type: instead of navigating away to pick a view from the sidebar, the user cycles views in-place at the top of the editor area.

### Manifest Schema Changes

The current `basic-pkm/views/basic-pkm.jsonld` already declares `sempkm:targetClass` on each `sempkm:ViewSpec`. The data needed for carousel is already present. No schema changes to the JSON-LD view specs are required.

The manifest `manifest.yaml` does not declare views inline — it uses the `entrypoints.views` path to a JSON-LD file. No changes to `ManifestSchema` in `backend/app/models/manifest.py` are needed for carousel.

What IS needed: a **per-type default view order** mechanism. The manifest could declare:

```yaml
# manifest.yaml addition (new optional key)
viewOrder:
  - type: "bpkm:Note"
    defaultView: "bpkm:view-note-table"
    order: ["bpkm:view-note-table", "bpkm:view-note-card", "bpkm:view-note-graph"]
```

However, this adds manifest complexity. The simpler approach: use `sempkm:viewOrder` as an integer property directly on ViewSpec entries in the JSON-LD file:

```json
{
  "@id": "bpkm:view-note-table",
  "@type": "sempkm:ViewSpec",
  "sempkm:targetClass": { "@id": "bpkm:Note" },
  "sempkm:viewOrder": 1,
  "sempkm:isDefaultView": true,
  ...
}
```

This is the recommended approach. It keeps ordering co-located with the view spec itself, survives model install/uninstall correctly, and requires only two new `sempkm:` vocabulary properties.

### Backend Changes

`ViewSpec` dataclass in `backend/app/views/service.py` gains two new optional fields:

```python
@dataclass
class ViewSpec:
    ...
    view_order: int = 99          # NEW: sort order within type, lower = first
    is_default_view: bool = False  # NEW: which view opens by default for this type
```

`ViewSpecService.get_all_view_specs()` SPARQL query gains two `OPTIONAL` clauses:

```sparql
OPTIONAL { ?spec <urn:sempkm:vocab:viewOrder> ?order }
OPTIONAL { ?spec <urn:sempkm:vocab:isDefaultView> ?isDefault }
```

A new endpoint is added to `backend/app/views/router.py`:

```
GET /browser/views/carousel/{type_iri:path}
```

Returns an HTML partial (not JSON) containing the carousel bar for a given type. The partial lists all view specs for the type sorted by `view_order`, with the current view highlighted. This endpoint is called by htmx when an object is opened (or when a type-contextual tab is activated).

The existing `get_view_specs_for_type()` method already does the right query — the new endpoint just adds sorting and renders the carousel template.

### Frontend Changes

A new template `backend/app/templates/browser/carousel_bar.html` renders the view switcher row. It is an htmx partial that loads into a `#carousel-bar` div inside the editor area, above the view content.

The view templates (`table_view.html`, `cards_view.html`, `graph_view.html`) currently include `all_specs` in context and render a simple view-type switcher (the "broken buttons" mentioned in BUG-03). These switcher buttons are replaced by (or rendered from) the carousel bar partial.

`workspace.js` gains a `loadCarouselBar(typeIri, currentSpecIri)` function that calls:

```javascript
htmx.ajax('GET', '/browser/views/carousel/' + encodeURIComponent(typeIri) + '?current=' + encodeURIComponent(currentSpecIri), {
  target: '#carousel-bar-' + activeGroupId,
  swap: 'innerHTML'
});
```

The carousel bar is wired into `loadTabInGroup()` — after loading a view tab, the carousel bar is also refreshed. For object tabs (not view tabs), no carousel bar is shown (or it shows the object-level view options if VIEW-01 "object view redesign" implements per-object carousel).

### New vs Modified Files (Carousel)

| File | Status | Change |
|------|--------|--------|
| `backend/app/views/service.py` | MODIFIED | Add `view_order` and `is_default_view` to `ViewSpec`. Update SPARQL query. Add `get_view_specs_for_type()` sort by `view_order`. |
| `backend/app/views/router.py` | MODIFIED | Add `GET /browser/views/carousel/{type_iri:path}` endpoint. |
| `backend/app/templates/browser/carousel_bar.html` | NEW | Carousel bar partial: view spec pills per type, clickable to switch. |
| `backend/app/templates/browser/table_view.html` | MODIFIED | Remove broken view switcher buttons (BUG-03). Add `#carousel-bar-{groupId}` div. |
| `backend/app/templates/browser/cards_view.html` | MODIFIED | Same as table_view. |
| `backend/app/templates/browser/graph_view.html` | MODIFIED | Same as table_view. |
| `frontend/static/js/workspace.js` | MODIFIED | Add `loadCarouselBar()`. Call it from view tab activation path. |
| `models/basic-pkm/views/basic-pkm.jsonld` | MODIFIED | Add `sempkm:viewOrder` and `sempkm:isDefaultView` to each ViewSpec. |

---

## Feature 3: Named Workspace Layouts

### Persistence Decision: localStorage + Backend API

Two options:

1. **localStorage only**: Fast, no server round-trip, no auth concerns. But layouts are lost when localStorage is cleared, not portable across devices, and Mental Model-provided layouts cannot be pre-populated.

2. **Backend API (triplestore)**: Durable, cross-device, allows model-provided defaults. Adds a server call on save/load.

**Recommendation: localStorage fast-path with backend API for named saves.** Session layout (the live working state) lives in localStorage as `sempkm_workspace_layout_v2`. Named layouts (user-saved "Research Mode", "Writing Mode") are stored via backend API in the triplestore as user preferences. Mental Model-provided layouts are stored in the model's views graph as `sempkm:WorkspaceLayout` instances and read at load time.

This matches the pattern already established by the phase-23 research (Section 3 of RESEARCH.md).

### Backend (Named Layouts API)

New module: `backend/app/layouts/` (router.py + service.py)

```
GET  /api/layouts          — list user's named layouts + model-provided layouts
POST /api/layouts          — save current layout as named layout
GET  /api/layouts/{name}   — load a specific named layout (returns dockview JSON)
DELETE /api/layouts/{name} — delete a user-saved layout
```

`LayoutService` stores user layouts as RDF in the triplestore under a user-specific named graph `urn:sempkm:user:{user_id}:layouts`. Each layout is a `sempkm:WorkspaceLayout` resource with:
- `sempkm:layoutName` (string)
- `sempkm:layoutConfig` (JSON string — dockview `toJSON()` output)
- `sempkm:isDefault` (boolean)
- `sempkm:dockviewVersion` (string, for future migration guards)
- `dcterms:modified` (datetime)

Model-provided layouts are stored in the model's views graph as `sempkm:WorkspaceLayout` instances alongside ViewSpec instances. `ViewSpecService.get_model_layouts()` already has a partial implementation of this query (it currently returns layout algorithm configs for graph views). This method is extended (or a new `get_model_workspace_layouts()` is added) to return full named workspace layout definitions.

### Frontend (Named Layouts)

A new `frontend/static/js/named-layouts.js` module handles:

```javascript
// Auto-save on layout change (debounced 2s)
dockview.onDidLayoutChange(debounce(() => {
  localStorage.setItem('sempkm_workspace_layout_v2', JSON.stringify(dockview.toJSON()));
}, 2000));

// Save as named layout
function saveNamedLayout(name) {
  return fetch('/api/layouts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, config: dockview.toJSON() })
  });
}

// Load named layout
function loadNamedLayout(name) {
  return fetch('/api/layouts/' + encodeURIComponent(name))
    .then(r => r.json())
    .then(data => {
      dockview.fromJSON(data.config);
      // Re-process htmx on all newly created panels
      document.querySelectorAll('.dv-content-container').forEach(el => htmx.process(el));
    });
}
```

The command palette (`ninja-keys` in `workspace.js`) gains entries for "Save Layout as..." and "Load Layout: {name}" loaded dynamically from `GET /api/layouts`.

### New vs Modified Files (Named Layouts)

| File | Status | Change |
|------|--------|--------|
| `backend/app/layouts/` | NEW directory | `router.py` + `service.py` for CRUD on named layouts |
| `backend/app/main.py` | MODIFIED | Mount layouts router |
| `frontend/static/js/named-layouts.js` | NEW | `saveNamedLayout()`, `loadNamedLayout()`, auto-save debounce, localStorage persistence |
| `frontend/static/js/workspace.js` | MODIFIED | Load named-layouts.js, add command palette entries for layout save/load |
| `backend/app/templates/browser/workspace.html` | MODIFIED | Load `named-layouts.js` |

Note: named layouts depend on Phase A (dockview must be initialized before `dockview.toJSON()` is available). Named layouts ship in the same phase or immediately after Phase A.

---

## Feature 4: FTS Fuzzy Search

### Current State

`SearchService` in `backend/app/services/search.py` runs this query pattern:

```sparql
?iri search:matches [
  search:query "knowledge base" ;
  search:score ?score ;
  search:snippet ?snippet
]
```

LuceneSail interprets the `search:query` value as a standard Lucene query string. The current implementation passes the raw user query string directly into `search:query`. This means the user must already know Lucene syntax to use wildcards (`knowl*`) or fuzzy matching (`knowlege~`).

### FTS-04 Change: Query Normalization

The `SearchService.search()` method adds a query normalization step before passing to SPARQL. The normalization appends a `~` (Lucene fuzzy edit-distance operator) to each term unless the user has already used query syntax:

```python
def _normalize_query(self, raw: str) -> str:
    """Append fuzzy operator to bare terms for approximate matching.

    Rules:
    - If query contains Lucene operators (AND, OR, NOT, *, ?, ~, ", :, +, -)
      treat as a power-user query and pass through unchanged.
    - Otherwise, split on whitespace and append ~ to each term.
      "knowledge base" → "knowledge~ base~"
    """
    LUCENE_OPERATORS = set('*?~":()+')
    LUCENE_KEYWORDS = {'AND', 'OR', 'NOT'}
    terms = raw.strip().split()
    if any(c in raw for c in LUCENE_OPERATORS) or any(t.upper() in LUCENE_KEYWORDS for t in terms):
        return raw  # pass through unchanged
    return ' '.join(t + '~' for t in terms)
```

The `~` operator in Lucene uses edit-distance 2 by default (configurable: `~1` for edit-distance 1). For PKM search, `~` (edit-distance 2) is appropriate. This handles common typos like "knowlege~" matching "knowledge".

Additionally, for multi-word queries, wrap in a phrase-with-slop or use OR logic. The recommended normalization for a two-word query "knowledge base":
- Raw passthrough for power users: `knowledge AND base` or `"knowledge base"`
- Fuzzy normalization for bare terms: `knowledge~ base~` (both terms must appear with fuzzy matching)

### Backend Changes

`backend/app/services/search.py`:
1. Add `_normalize_query()` method to `SearchService`
2. Call it in `search()` before building the SPARQL string: `normalized = self._normalize_query(query.strip())`
3. Optionally add a `fuzzy: bool = True` parameter to allow callers to disable fuzzy for exact searches (command palette might want exact prefix matching)

The `FTS_QUERY` template and SPARQL structure are unchanged. Only the value passed to `search:query` changes.

The `/api/search` endpoint (in `browser/router.py` or a dedicated `search/router.py`) gains an optional `fuzzy=false` query parameter for callers that need exact matching.

### Confidence on Lucene Fuzzy Syntax

The `~` fuzzy operator is standard Lucene syntax supported by LuceneSail — LuceneSail uses Apache Lucene's QueryParser internally, which supports the full Lucene query syntax including `~`. This is HIGH confidence from the LuceneSail documentation and Lucene query syntax reference.

Edit-distance defaults: Lucene 9.x (used by RDF4J 5.x) uses `~` for edit-distance 2. This can be tuned per-term: `knowledge~1` for edit-distance 1 (less permissive), `knowledge~2` for edit-distance 2.

### New vs Modified Files (FTS Fuzzy)

| File | Status | Change |
|------|--------|--------|
| `backend/app/services/search.py` | MODIFIED | Add `_normalize_query()`. Call in `search()`. Optional `fuzzy` parameter. |
| Backend search endpoint | MODIFIED | Add `fuzzy=true` query param. |

This is the smallest change of the four features — two files, one new method.

---

## Data Flow Changes

### Dockview Phase A: Tab Open Flow

```
User clicks tree node
    ↓
onclick="openTab(iri, label)"         [workspace.js — unchanged call site]
    ↓
openTab() in workspace.js
    ↓
dockview.api.addPanel({              [NEW — replaces layout.addTabToGroup()]
  id: iri,
  component: 'object-editor',
  params: { iri: iri },
  title: label
})
    ↓
dockview createComponent callback
    ↓
htmx.ajax('GET', '/browser/object/'+iri, {  [same as current loadTabInGroup()]
  target: params.containerElement,
  swap: 'innerHTML'
})
    ↓
Backend: browser/router.py → object.html partial
    ↓
DOM updated in dockview container element
    ↓
dockview.onDidActivePanelChange fires
    ↓
document.dispatchEvent('sempkm:tab-activated', {isObjectTab: true})  [same event]
    ↓
workspace.js panel indicator updates (unchanged listener)
```

### Carousel Views: View Switch Flow

```
User opens view tab (table view for bpkm:Note)
    ↓
loadTabInGroup() / dockview createComponent (view-panel)
    ↓
htmx.ajax('/browser/views/table/'+specIri) → table_view.html partial
    ↓
table_view.html renders with #carousel-bar-{groupId} div
    ↓
loadCarouselBar(typeIri, currentSpecIri) in workspace.js
    ↓
htmx.ajax('/browser/views/carousel/'+typeIri+'?current='+specIri)
    ↓
carousel_bar.html partial: pills for [Table][Card][Graph] with active state
    ↓
User clicks "Card" pill
    ↓
onclick="openViewTab(cardSpecIri, 'People Cards', 'card')"
    ↓
Existing openViewTab() flow — loads new view tab or switches to existing
```

### Named Layout: Save Flow

```
User clicks "Save Layout" in command palette
    ↓
saveNamedLayout(name) in named-layouts.js
    ↓
dockview.toJSON() → layout JSON object
    ↓
POST /api/layouts { name, config: JSON.stringify(layoutJson) }
    ↓
LayoutService.save_layout(user_id, name, config_str)
    ↓
SPARQL UPDATE: insert sempkm:WorkspaceLayout into urn:sempkm:user:{id}:layouts
```

### FTS Fuzzy: Search Flow

```
User types "knowlege" in Ctrl+K palette
    ↓
_initFtsSearch() debounce 300ms fires in workspace.js (unchanged)
    ↓
GET /api/search?q=knowlege&limit=10
    ↓
SearchService.search("knowlege")
    ↓
_normalize_query("knowlege") → "knowlege~"       [NEW]
    ↓
FTS_QUERY with search:query "knowlege~"
    ↓
LuceneSail fuzzy match: "knowlege~" matches "knowledge" (edit-distance 1)
    ↓
SearchResult list returned, rendered as command palette entries (unchanged)
```

---

## Component Boundary Summary

| Component | Owns | Does NOT Own |
|-----------|------|-------------|
| `workspace.js` | Outer pane sizes (Split.js), command palette, keyboard shortcuts, event routing | Tab bars, group splits, panel content loading |
| `workspace-layout.js` (modified) | Tab metadata (label, dirty, typeIcon) per panel ID, dockview init, sessionStorage persistence | Layout geometry (now owned by dockview), DOM structure |
| `dockview-core` (new) | Tab bars, group creation/destruction, drag-to-reorder, sash resize, panel serialization | Content loaded into panels (htmx does this) |
| `named-layouts.js` (new) | Named layout CRUD, auto-save debounce | Layout display UI (command palette does this) |
| `ViewSpecService` | Loading ViewSpec from triplestore, executing SPARQL queries, `view_order` / `is_default_view` | Carousel rendering (router + template does this) |
| `SearchService` | Query normalization, LuceneSail FTS execution | Search UI (command palette does this) |
| `LayoutService` (new) | Persisting named layouts to triplestore | Layout serialization format (dockview + named-layouts.js do this) |

---

## Build Order (Dependency Graph)

```
FTS Fuzzy (FTS-04)                      ← INDEPENDENT, ship first
    ↓ no blockers

Dockview Phase A (DOCK-01)             ← requires CSS bridge already in place (done v2.2)
    ↓
    ├── Carousel Views (VIEW-02)        ← requires view router; can proceed in parallel
    │       depends on: ViewSpecService changes (small), new endpoint, new template
    │
    └── Named Layouts (DOCK-02)         ← requires dockview.toJSON() available (needs DOCK-01)
            depends on: new LayoutService, new API routes, dockview Phase A complete
```

Recommended phase sequence:

1. **FTS-04** (2 files, lowest risk — ship independently, immediate user value)
2. **DOCK-01** (Phase A — largest change, but well-scoped to workspace-layout.js)
3. **VIEW-02** (Carousel — can start in parallel with DOCK-01 since backend is independent; frontend carousel bar wires into dockview panels after DOCK-01 stabilizes)
4. **DOCK-02** (Named layouts — depends on DOCK-01 dockview.toJSON() being live)

BUG-01/02/03 can be fixed anytime independently (no cross-feature dependencies).

---

## Architectural Patterns to Follow

### Pattern: htmx Target is Always a Named Container

All `htmx.ajax()` calls use explicit container IDs, never relative selectors like `closest`. This ensures calls survive dockview panel reparenting.

```javascript
// Good: explicit container element reference
htmx.ajax('GET', url, { target: params.containerElement, swap: 'innerHTML' });

// Bad: ancestor-scoped selector (breaks after dockview reparent)
htmx.ajax('GET', url, { target: 'closest .group-editor-area', swap: 'innerHTML' });
```

### Pattern: Dockview Events Drive SemPKM Events

SemPKM custom events (`sempkm:tab-activated`, `sempkm:tabs-empty`) are dispatched from dockview event callbacks, not from SemPKM data model mutations. This keeps the event contract stable for all consumers (panel indicator, lint panel, relations panel) while the internals migrate.

### Pattern: ViewSpec is Renderer-Agnostic

The `ViewSpec` dataclass does not know about carousel, dockview, or any UI concept. It is pure data (IRI, label, SPARQL query, renderer type). The carousel bar is a rendering layer on top of `ViewSpec` data — `ViewSpecService` methods return data, templates decide how to present it.

### Pattern: Layout JSON is Versioned

All stored layout JSON (localStorage and triplestore) includes a `dockviewVersion` field. When loading, check this field and skip loading (fall back to default) if the major version does not match the loaded dockview-core version. This prevents silently broken layouts after a dockview major upgrade.

---

## Anti-Patterns to Avoid

### Anti-Pattern: Modifying dockview Internal DOM

**What:** Using querySelector on dockview-generated elements (class names like `dv-content-container`, `dv-tabs-and-actions-container`) to inject custom behavior.

**Why bad:** dockview class names are not part of the public API and change between versions. CSS customization must go through `--dv-*` CSS variables in the bridge file only.

**Instead:** Use dockview's public API (`dockview.api`, `panel.api`, `onDidActivePanelChange`) for all behavioral integration.

### Anti-Pattern: Storing Tab Content in dockview Panel Params

**What:** Putting the full object IRI and all metadata in the dockview panel params that are serialized by `toJSON()`.

**Why bad:** IRIs are fine in params (that is intentional). But putting display metadata (label, dirty state, typeIcon) in dockview params means they live in two places (WorkspaceLayout metadata map + dockview params), creating sync bugs.

**Instead:** Store only the minimal routing parameters in dockview panel params (`iri`, `viewType`, `viewId`). Keep all display metadata in `WorkspaceLayout`'s tab metadata map, keyed by panel ID.

### Anti-Pattern: Carousel Bar Inside Panel HTML

**What:** Embedding the carousel bar HTML directly inside `table_view.html` / `cards_view.html` by including a template fragment there.

**Why bad:** When the user switches view type (e.g., table → card), the entire panel content swaps, which would destroy the carousel bar and require it to be re-rendered as part of every view response — coupling view responses to carousel state.

**Instead:** The carousel bar lives in a separate `#carousel-bar-{groupId}` div outside the view content area. It is loaded once when a view tab activates and persists across in-place view switches. The view content area (`#view-content-{groupId}`) swaps independently.

---

## Scaling Considerations

These features are single-user local deployments. Scaling is not a concern for v2.3. The architecture choices that matter for correctness at SemPKM scale:

| Concern | Approach |
|---------|----------|
| Named layouts in triplestore | Use dedicated user layout graph (`urn:sempkm:user:{id}:layouts`) — keep separate from domain data |
| Carousel ViewSpec query | Already cached in ViewSpecService 300s TTL — carousel bar is fast |
| dockview bundle size | CDN-loaded, scoped to workspace page only — no impact on admin/setup pages |
| LuceneSail fuzzy overhead | Edit-distance 2 is O(n * edit_distance^2) — acceptable for PKM-scale datasets (<10K objects) |

---

## Sources

- `frontend/static/js/workspace-layout.js` — direct codebase analysis (1073 lines)
- `frontend/static/js/workspace.js` — direct codebase analysis (openTab, openViewTab, switchTabInGroup)
- `backend/app/views/service.py` — ViewSpecService, ViewSpec dataclass
- `backend/app/views/router.py` — view endpoints, all_specs context
- `backend/app/models/manifest.py` — ManifestSchema, no views: key
- `models/basic-pkm/views/basic-pkm.jsonld` — existing ViewSpec structure
- `backend/app/services/search.py` — SearchService FTS_QUERY, current normalization
- `frontend/static/css/dockview-sempkm-bridge.css` — --dv-* token mapping
- `.planning/research/phase-23-ui-shell/RESEARCH.md` — dockview htmx integration patterns, toJSON format, layout storage design
- `.planning/DECISIONS.md` — DEC-04 dockview rationale, Phase A/B/C migration plan
- `backend/app/templates/browser/workspace.html` — current HTML structure

---

*Architecture research for: SemPKM v2.3 Shell, Navigation & Views*
*Researched: 2026-03-01*
