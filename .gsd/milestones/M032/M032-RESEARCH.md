# M032 — Block-Based Custom UI Builder: Research

## 1. Executive Summary

M032 designs a Notion-inspired block composition system for SemPKM that lets users build custom dashboards, views, and multi-object creation forms from reusable blocks. The research finds that the existing dashboard and workflow systems are well-isolated in SQLite (noted as tech debt) with JSON block serialization — providing a clear migration target. The primary technical challenge is replacing the 5 fixed CSS Grid layout templates with a free-form drag-drop grid while maintaining htmx server-rendered block content.

**Recommendation:** Use **GridStack.js** as the layout engine (vanilla JS, CDN-loadable, JSON-serializable, matches all stack constraints), extend the existing `blocks_json` format with position metadata (x, y, w, h), and introduce a `BlockRegistry` pattern for typed widget declarations. Multi-object forms should use `commit_bulk()` with temporary IRI placeholders resolved server-side.

---

## 2. Codebase Exploration — What Exists

### 2.1 Dashboard System (SQLite + JSON)

**Location:** `backend/app/dashboard/` (models.py, service.py, router.py, seed.py)

The existing dashboard system stores everything in SQLite:

| Component | Implementation | Lines |
|-----------|---------------|-------|
| `DashboardSpec` model | SQLAlchemy: id, user_id, name, description, layout, blocks_json | ~65 |
| `DashboardService` | Async CRUD with block validation | ~160 |
| Dashboard router | 8 endpoints (browser + API) | ~310 |
| Dashboard builder | Jinja2 + vanilla JS builder UI | ~320 |
| Dashboard page | CSS Grid rendering + htmx block lazy-loading | ~75 |
| Dashboard seed | Idempotent "Getting Started" sample | ~90 |

**Key observations:**
- **Tech debt note in models.py:** *"These are model-layer concepts that belong in RDF named graphs. SQLite JSON is used for faster iteration. Migration to RDF is planned for a follow-up milestone."*
- **5 fixed layout templates:** `single`, `sidebar-main`, `grid-2x2`, `grid-3`, `top-bottom` — each maps to CSS Grid `grid-template-areas` + `grid-template-columns`
- **6 block types:** `view-embed`, `markdown`, `object-embed`, `create-form`, `sparql-result`, `divider`
- **Block format:** `{"type": str, "slot": str, "config": dict}` — slot is a named CSS Grid area
- **Cross-view context filtering** already works: `dashboardContextChanged` custom event passes IRIs between blocks that set `data-emits-context="1"` and `data-listens-to-context="varName"`
- **Autocomplete** for class and object IRI references exists in the builder

### 2.2 Workflow System (SQLite + JSON)

**Location:** `backend/app/workflow/` (models.py, service.py, router.py)

Nearly identical architecture to dashboards:
- `WorkflowSpec` model: id, user_id, name, description, steps_json
- 3 step types: `view`, `dashboard`, `form`
- Stepper runner UI with prev/next navigation, htmx step loading
- **Same tech debt note** about RDF migration

### 2.3 SHACL Form System

**Location:** `backend/app/templates/forms/_field.html`, `backend/app/services/shapes.py`

The form system is mature and SHACL-driven:
- `PropertyShape` dataclass: path, name, datatype, target_class, order, group, min_count, max_count, in_values, default_value, description, helptext
- `NodeShapeForm`: shape_iri, target_class, label, groups, properties, helptext
- `_field.html` macro dispatches to **10+ widget types**: text, date, datetime, boolean, integer, decimal, URL, select (sh:in), object reference (search-as-you-type), tag autocomplete
- Multi-value support with add/remove buttons
- Property groups for sectioning

### 2.4 View System

**Location:** `backend/app/views/service.py`, `backend/app/views/router.py`

- `ViewSpec` dataclass: spec_iri, label, target_class, renderer_type, sparql_query, columns
- 4 renderers: table, card, graph, kanban
- Generic views with type filter pills
- Saved query scope binding (`scope_query` parameter)
- View toolbar with "Save View" button → PromotedView persistence

### 2.5 Canvas System (Comparison Point)

**Location:** `frontend/static/js/canvas.js` (~940 lines)

The spatial canvas has a fully custom layout engine:
- Free-form drag positioning (not grid-based)
- Resizable nodes with corner/edge/bottom handles
- **Embed nodes** with iframes (views, dashboards, queries, objects)
- JSON serialization of node positions, sizes, and embed configs
- Max 8 embeds enforced
- Dual-layer rendering: embed iframes in persistent DOM layer

**Relevance:** Canvas proves that iframe-based content embedding works well in the codebase. The block system can reuse this pattern.

### 2.6 Frontend Stack Constraints

| Constraint | Detail |
|-----------|--------|
| No build step | All JS loaded via CDN or inline `<script>` |
| htmx server-rendering | Block content rendered server-side, swapped via htmx |
| Vanilla JS only | No React/Vue/Angular |
| dockview-core | Workspace panel management (tabs, split groups) |
| CDN pattern | Libraries loaded from unpkg/jsdelivr/esm.sh |
| CSS custom properties | 35+ design tokens in theme.css |

### 2.7 Data Mutation Pattern

All writes go through `POST /api/commands`:
- 6 command types: object.create, object.patch, body.set, body.diff, edge.create, edge.patch
- Each returns an `Operation` (data_triples + materialize_inserts/deletes)
- `EventStore.commit()` atomic transaction
- `EventStore.commit_bulk()` for batch operations (summary metadata instead of per-op)

---

## 3. Technology Research

### 3.1 Layout Engine: GridStack.js

GridStack.js is the strongest candidate for replacing the fixed CSS Grid templates:

| Criterion | GridStack.js | Muuri | Custom CSS Grid |
|-----------|-------------|-------|-----------------|
| Vanilla JS (no framework) | ✅ v5+ is pure JS | ✅ | ✅ |
| CDN-loadable | ✅ jsdelivr/unpkg | ✅ | N/A |
| Drag-and-drop | ✅ Built-in | ✅ | ❌ Manual |
| Resize handles | ✅ Built-in | ❌ | ❌ Manual |
| Grid snapping | ✅ 12-column | ❌ Masonry | ✅ CSS Grid |
| JSON serialize/load | ✅ `grid.save()` / `grid.load()` | ❌ Manual | ❌ Manual |
| Nested grids | ✅ subGridOpts | ❌ | ✅ |
| Mobile responsive | ✅ breakpoints | ❌ | ✅ media queries |
| Bundle size | ~45KB min | ~25KB min | 0 |
| htmx compat | ✅ content via innerHTML | ✅ | ✅ |

**GridStack.js is the recommended choice** because:
1. It provides drag-drop + resize + grid snapping + JSON serialization out of the box — the exact feature set needed
2. It works with vanilla JS and CDN loading — matching the codebase pattern
3. Layout serialization (`grid.save()` → JSON array of `{x, y, w, h, id, content}`) maps directly to the `blocks_json` field
4. The 12-column grid is the industry standard (Bootstrap, Tailwind, Grafana)
5. No jQuery dependency since v5; v12 is the current release

**CDN URL:** `https://cdn.jsdelivr.net/npm/gridstack@12/dist/gridstack-all.js` + `gridstack.min.css`

**Integration approach:** Replace the `grid-template-areas` CSS rendering with GridStack initialization on the dashboard container. Each block becomes a GridStack widget with `{x, y, w, h}` position data. Block content still loads via htmx `hx-get`.

### 3.2 Block Editor Approaches (Notion vs. Zabbix)

**Notion model:**
- Linear block list with nested blocks and column dividers
- Rich inline editing (text directly editable)
- Slash command (`/`) to insert blocks
- Block types: text, heading, list, toggle, callout, divider, table, image, embed, database view
- Layout: columns created by dragging blocks side-by-side

**Zabbix model:**
- 2D grid with absolute positioning
- Widgets placed in cells with explicit (x, y, w, h)
- Configuration panels for each widget
- Widget types: graph, gauge, pie chart, stat card, clock, map, URL
- Fixed grid resolution

**Recommended hybrid for SemPKM:**
- **Grid-based positioning** (Zabbix/GridStack model) — more appropriate for dashboards and forms where blocks have distinct data scopes
- **Slash command block insertion** (Notion-inspired) — for quick block addition within the builder
- **Block configuration panels** (Zabbix-inspired) — since blocks load server-rendered content, inline editing doesn't apply

### 3.3 RDF Storage for Block Layouts

Two viable approaches:

**Option A: JSON-LD Literal (Pragmatic)**
```turtle
<urn:sempkm:dashboard:uuid> a sempkm:DashboardSpec ;
    dcterms:title "My Dashboard" ;
    sempkm:layout "gridstack" ;
    sempkm:blocksData '''[
        {"id":"b1","type":"view-embed","x":0,"y":0,"w":6,"h":4,"config":{"spec_iri":"..."}},
        {"id":"b2","type":"markdown","x":6,"y":0,"w":6,"h":2,"config":{"content":"..."}}
    ]'''^^xsd:string .
```

**Option B: Full RDF Graph**
```turtle
<urn:sempkm:dashboard:uuid> a sempkm:DashboardSpec ;
    dcterms:title "My Dashboard" ;
    sempkm:hasBlock <urn:sempkm:block:b1>, <urn:sempkm:block:b2> .

<urn:sempkm:block:b1> a sempkm:ViewEmbedBlock ;
    sempkm:gridX 0 ; sempkm:gridY 0 ;
    sempkm:gridW 6 ; sempkm:gridH 4 ;
    sempkm:viewSpec <urn:sempkm:model:basic-pkm:views:note-table> .
```

**Recommendation: Option A (JSON-LD Literal).** Rationale:
1. The current system already uses `blocks_json` as a JSON text column — this is a direct 1:1 migration
2. Block layouts are an internal concern, not something external clients query via SPARQL
3. Full RDF (Option B) would require ~5 triples per block × N blocks per dashboard — SPARQL queries to reconstruct a dashboard layout would be expensive and fragile
4. GridStack's `grid.save()` already produces a JSON array — storing it as-is eliminates serialization overhead
5. The M032 context note explicitly says "RDF storage preferred but pragmatic JSON-in-literal is acceptable if the alternative is over-engineering" — Option B is over-engineering

The outer DashboardSpec metadata (name, description, creator, timestamps) should be in RDF for discoverability and federation. The inner block layout data stays as a JSON literal.

---

## 4. Widget Inventory

### 4.1 Existing Block Types (Keep)

| Widget | Current Config | Notes |
|--------|---------------|-------|
| `view-embed` | spec_iri, renderer_type, height, emits_context, listens_to_context | Core data display block |
| `markdown` | content | Static content block |
| `object-embed` | object_iri, mode (read/edit) | Single object display |
| `create-form` | target_class, defaults | SHACL-driven form |
| `sparql-result` | query, label | Single-value metric display |
| `divider` | (none) | Visual separator |

### 4.2 Proposed New Block Types

| Widget | Config Schema | Data Dependencies | Notes |
|--------|--------------|-------------------|-------|
| `stat-card` | query (SPARQL SELECT returning 1 value), label, icon, color, format | SPARQL endpoint | Styled metric card (count, percentage, etc.) |
| `chart` | query (SPARQL), chart_type (bar/line/pie/doughnut), options | SPARQL + Chart.js | Already CDN-loaded (Chart.js 4.4) |
| `heading` | text, level (h1-h4) | None | Section header within dashboard |
| `saved-query-result` | query_id | Saved query service | Table output from a saved query |
| `image` | url, alt, width | None | Static image embed |
| `kanban-embed` | type_iri, status_property | SHACL + SPARQL | Inline kanban board |
| `graph-embed` | query, layout (fcose/dagre) | Cytoscape.js | Graph visualization block |
| `form-group` | shapes (array of {type_iri, label, edge_to_parent?}) | ShapesService | **Multi-object creation** — the key new capability |

### 4.3 Widget Config Panel Pattern

Each widget type needs:
1. **Config schema** — declares required/optional fields
2. **Config panel** — builder UI for configuring the widget (reuse existing autocomplete pattern)
3. **Render endpoint** — `GET /browser/dashboard/{id}/block/{index}` already handles this
4. **Client-side init** — some widgets (chart, graph) need JS initialization after htmx swap

**Pattern:** Register widgets in a `BLOCK_REGISTRY` dict keyed by type string, with each entry declaring:
```python
BLOCK_REGISTRY = {
    "stat-card": {
        "label": "Stat Card",
        "icon": "hash",
        "config_fields": [
            {"key": "query", "type": "sparql", "required": True},
            {"key": "label", "type": "text", "required": True},
            {"key": "icon", "type": "icon-picker"},
            {"key": "color", "type": "color"},
        ],
        "renderer": "block_stat_card.html",
    },
    ...
}
```

---

## 5. Multi-Object Custom Forms

### 5.1 The Problem

Current `create-form` blocks create one object at a time. Users want:
- "Create a Project with 3 linked Tasks in one form"
- "Create a Contact, a Company, and link them together"
- "Create a Research Question with pre-linked Papers and Claims"

### 5.2 Proposed `form-group` Block

A `form-group` block contains an ordered array of SHACL form references:

```json
{
    "type": "form-group",
    "config": {
        "shapes": [
            {
                "type_iri": "urn:sempkm:data:Project",
                "label": "New Project",
                "slot_id": "project",
                "defaults": {"bpkm:status": "active"}
            },
            {
                "type_iri": "urn:sempkm:data:Task",
                "label": "Task 1",
                "slot_id": "task1",
                "edge_to": {"slot_id": "project", "predicate": "bpkm:assignedTo"}
            },
            {
                "type_iri": "urn:sempkm:data:Task",
                "label": "Task 2", 
                "slot_id": "task2",
                "edge_to": {"slot_id": "project", "predicate": "bpkm:assignedTo"}
            }
        ],
        "submit_mode": "bulk"
    }
}
```

### 5.3 Transaction Semantics

**Server-side resolution pattern:**

1. Client submits all forms as a single POST with slot IDs
2. Server processes in order: creates `project` first (gets real IRI), then `task1` and `task2` (with `edge_to` referencing the project's real IRI)
3. Uses `EventStore.commit_bulk()` for the batch — all-or-nothing

**Endpoint:** `POST /api/commands/batch` — new endpoint that accepts an array of commands with `_slot_id` metadata for cross-referencing:

```json
{
    "commands": [
        {"command": "object.create", "_slot_id": "project", "params": {...}},
        {"command": "object.create", "_slot_id": "task1", "params": {...}},
        {"command": "edge.create", "params": {"from_slot": "task1", "to_slot": "project", "predicate": "bpkm:assignedTo"}}
    ]
}
```

### 5.4 Form Rendering

Each shape within a `form-group` renders as a collapsible section using the existing `_field.html` macro:

```
┌─ New Project ─────────────────┐
│  Title: [_______________]     │
│  Status: [Active ▾]          │
│  Due Date: [____]            │
└───────────────────────────────┘
┌─ Task 1 → links to Project ──┐
│  Title: [_______________]     │
│  Priority: [High ▾]          │
└───────────────────────────────┘
┌─ Task 2 → links to Project ──┐
│  Title: [_______________]     │
│  Priority: [Medium ▾]        │
└───────────────────────────────┘
         [ Create All ]
```

### 5.5 SHACL Validation

- Each sub-form validates independently against its SHACL shape before submission
- Cross-form validation (e.g., "at least one Task required") is a stretch goal — not in MVP
- The existing `_field.html` macro handles required fields, type constraints, and in_values — reused as-is

---

## 6. Migration Strategy

### 6.1 Dashboard Migration (SQLite → GridStack + RDF)

**Phase 1 (MVP):** Replace fixed CSS Grid rendering with GridStack.js
- Map existing 5 layouts to GridStack positions:
  - `single` → `[{x:0, y:0, w:12, h:6}]`
  - `sidebar-main` → `[{x:0, y:0, w:3, h:6}, {x:3, y:0, w:9, h:6}]`
  - `grid-2x2` → `[{x:0, y:0, w:6, h:3}, {x:6, y:0, w:6, h:3}, {x:0, y:3, w:6, h:3}, {x:6, y:3, w:6, h:3}]`
  - etc.
- Keep `blocks_json` in SQLite for now, add `x, y, w, h` to each block object
- Old blocks without position data get auto-positioned using the mapping above

**Phase 2:** Migrate DashboardSpec to RDF
- Create `sempkm:DashboardSpec` class in vocab
- Store as RDF triples in `urn:sempkm:user-dashboards` named graph
- `blocksData` as JSON-LD literal
- Write migration script (read SQLite → write RDF)

**Phase 3:** Unify dashboards and workflows into "compositions"
- Both are ordered collections of blocks — dashboards show them simultaneously, workflows show them sequentially
- A "composition" with `display_mode: "grid"` is a dashboard; with `display_mode: "stepper"` is a workflow

### 6.2 Backward Compatibility

- Existing `DashboardSpec` records continue to work — the router checks for position data and falls back to layout-based positioning
- Existing `WorkflowSpec` records unaffected — workflow runner is separate
- No breaking changes to the API

---

## 7. Architecture Sketch

### 7.1 Component Diagram

```
┌──────────────────────────────────────────────────┐
│  Dashboard Builder (Jinja2 + JS)                 │
│  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Block Palette │  │ GridStack Canvas          │  │
│  │ (drag source) │  │ (drop target, resize)    │  │
│  │               │  │                          │  │
│  │ stat-card     │→→│  ┌────┐ ┌──────────┐   │  │
│  │ view-embed    │  │  │ B1 │ │   B2     │   │  │
│  │ chart         │  │  └────┘ └──────────┘   │  │
│  │ form-group    │  │  ┌─────────────────┐   │  │
│  │ markdown      │  │  │       B3        │   │  │
│  │ ...           │  │  └─────────────────┘   │  │
│  └──────────────┘  └──────────────────────────┘  │
│                                                  │
│  Block Config Panel (collapsible, per-block)     │
└──────────────────────────────────────────────────┘
         │ save → JSON
         ▼
┌──────────────────────┐     ┌──────────────────────┐
│ DashboardService     │     │ BlockRegistry         │
│ (CRUD + validation)  │     │ (type → schema +      │
│                      │     │  renderer template)   │
│ blocks_json: [       │     │                       │
│  {type, x,y,w,h,    │     │ validate_config()     │
│   config}            │     │ render_block()        │
│ ]                    │     └──────────────────────┘
└──────────────────────┘
         │
         ▼ render
┌──────────────────────────────────────────────────┐
│  Dashboard Page                                  │
│  GridStack.init() → load(blocks) → htmx blocks   │
│                                                  │
│  Each block: hx-get="/browser/dashboard/{id}/    │
│              block/{idx}" hx-trigger="load"       │
└──────────────────────────────────────────────────┘
```

### 7.2 BlockRegistry Design

```python
@dataclass
class BlockType:
    type_id: str           # "stat-card"
    label: str             # "Stat Card"
    icon: str              # Lucide icon name
    category: str          # "data", "content", "form", "embed"
    config_fields: list[ConfigField]
    renderer_template: str # "block_stat_card.html"
    min_width: int = 3     # GridStack min width
    min_height: int = 2    # GridStack min height

@dataclass
class ConfigField:
    key: str
    type: str  # "text", "sparql", "iri", "select", "icon-picker", "color"
    label: str
    required: bool = False
    options: list[str] | None = None  # for "select" type

BLOCK_REGISTRY: dict[str, BlockType] = {}

def register_block(block_type: BlockType):
    BLOCK_REGISTRY[block_type.type_id] = block_type
```

---

## 8. Risk Analysis

### 8.1 High Risk: GridStack + htmx Block Loading

**Problem:** GridStack renders the grid layout synchronously, but block content loads asynchronously via htmx. This creates a potential sizing mismatch — GridStack reserves space for a block, but the htmx-loaded content may be taller/shorter.

**Mitigation:** Set `GridStackOptions.cellHeight = 'auto'` or a fixed cell height (e.g., 80px). Blocks that need dynamic sizing (markdown, tables) should specify explicit `h` values in their grid config. Use htmx `afterSwap` event to call `grid.resizeToContent(el)` if available.

### 8.2 High Risk: Multi-Object Form Transaction

**Problem:** Creating objects A, B, C with edges between them requires knowing the IRI of A before creating the edge from B→A. But IRIs are minted server-side at creation time.

**Mitigation:** The `POST /api/commands/batch` endpoint processes commands sequentially, resolving slot references to real IRIs. The server maintains a `slot_map: dict[str, str]` during the batch. This is a new endpoint — it needs careful testing.

### 8.3 Medium Risk: dockview + GridStack Interaction

**Problem:** Both dockview and GridStack use drag-and-drop. GridStack drag events must be isolated within the dashboard panel to prevent dockview from intercepting them.

**Mitigation:** Use `e.stopPropagation()` in GridStack drag handlers — the exact same pattern already proven in `kanban.js` and `canvas.js` (both successfully prevent dockview interference). GridStack's `handleClass` option restricts drag initiation to header handles.

### 8.4 Low Risk: Migration of Existing Dashboards

**Problem:** Existing dashboards use slot-based layouts that must map to GridStack positions.

**Mitigation:** The 5 layout types have deterministic mappings to (x, y, w, h) coordinates. A migration function converts `layout + slot` to position data. Old dashboards render correctly without user intervention.

---

## 9. Slice Boundary Recommendations

Based on the research, the natural slices are:

### S01: GridStack Layout Engine + Block Registry
- Replace CSS Grid rendering with GridStack.js
- Implement `BlockRegistry` pattern
- Migrate existing 5 layouts to GridStack positions
- Dashboard builder gains drag-drop block placement
- **Risk:** GridStack + htmx interaction
- **Proves:** The layout engine works, blocks render correctly

### S02: New Widget Types
- `stat-card`, `chart`, `heading`, `image`, `saved-query-result`
- Config panels for each type
- Extend `render_block()` with new type handlers
- **Depends on:** S01 (registry, rendering)

### S03: Multi-Object Form Groups
- `form-group` block type
- `POST /api/commands/batch` endpoint
- Slot-based cross-referencing
- SHACL form composition
- **Risk:** Transaction semantics, IRI resolution
- **Depends on:** S01 (rendering in grid)

### S04: Polish, Migration & Documentation
- SQLite → RDF migration for DashboardSpec (optional, can defer)
- Dashboard/workflow unification design
- User guide documentation
- E2E tests

---

## 10. Strategic Questions Answered

### What should be proven first?
**GridStack.js integration** — this is the highest-risk technical bet. If GridStack doesn't play well with htmx server-rendered content inside dockview panels, the entire approach needs rethinking. S01 proves this.

### What existing patterns should be reused?
1. **Dashboard builder UI** — extend, don't rewrite. The existing builder has autocomplete, type pickers, block add/remove. Add GridStack as the layout canvas.
2. **`_field.html` macro** — the SHACL form rendering is mature and complete. Multi-object forms should compose existing form macros.
3. **`render_block()` pattern** — the per-type block rendering in the dashboard router works well. New widget types are new `elif` branches.
4. **`commit_bulk()` for batched operations** — already proven in the RSS app for bulk article ingestion.
5. **`e.stopPropagation()` for drag isolation** — proven in kanban.js and canvas.js.

### What boundary contracts matter?
1. **Block config schema** — each widget type must declare its config fields so the builder can auto-generate config panels
2. **GridStack ↔ blocks_json serialization** — `grid.save()` output must round-trip through `blocks_json` storage
3. **Batch command slot resolution** — the `_slot_id` → real IRI mapping must be deterministic and documented
4. **htmx `hx-trigger="load"` on blocks** — must fire after GridStack positions the element in the DOM

### What constraints does the existing codebase impose?
1. **No npm build step** — GridStack must be CDN-loaded
2. **htmx server-rendering** — block content is HTML from Jinja2, not client-rendered
3. **Single `POST /api/commands`** — batch needs a new endpoint, not modifications to the existing one
4. **SHACL shapes are source of truth** — form blocks compose shapes, they don't define new fields
5. **Dockview panels** — dashboards render inside dockview panels, GridStack must work within them

### Are there known failure modes?
1. **GridStack widget content overflowing** — fixed-height cells may clip dynamic content. Need `overflow:auto` on block containers.
2. **htmx swapping inside GridStack widgets** — htmx may not find target elements if GridStack wraps them in additional divs. Need to verify selector targeting.
3. **Cross-view context with GridStack** — the existing `dashboardContextChanged` event system must work with GridStack's event model.

---

## 11. Candidate Requirements

The following are surfaced as candidates for the roadmap planner to evaluate:

### Table Stakes (likely required)
- **BLOCK-01:** GridStack.js replaces fixed CSS Grid layouts for dashboards
- **BLOCK-02:** Existing 5 layout templates auto-migrate to GridStack positions
- **BLOCK-03:** Dashboard builder has drag-from-palette block placement
- **BLOCK-04:** Block resize via GridStack handles
- **BLOCK-05:** Layout JSON serialization round-trips through storage

### High Value (recommended)
- **BLOCK-06:** `BlockRegistry` pattern for typed widget declarations
- **BLOCK-07:** `stat-card` widget with SPARQL-driven metric display
- **BLOCK-08:** `chart` widget using existing Chart.js CDN
- **BLOCK-09:** `form-group` block for multi-object creation
- **BLOCK-10:** `POST /api/commands/batch` for transactional multi-object creates

### Nice to Have (optional for MVP)
- **BLOCK-11:** Slash command (`/`) block insertion in builder
- **BLOCK-12:** Block templates (pre-configured common layouts)
- **BLOCK-13:** Dashboard/workflow unification into "compositions"
- **BLOCK-14:** SQLite → RDF migration for DashboardSpec storage
- **BLOCK-15:** Nested GridStack grids (dashboard within dashboard)

### Explicitly Out of Scope
- Inline rich text editing (Notion-style contenteditable) — too much complexity, not aligned with htmx architecture
- Real-time collaborative editing of dashboards — event-sourced but single-writer
- Mobile-specific layout breakpoints — defer to later
- Custom widget JS plugin API — internal widget types only for MVP

---

## 12. Technology Skills Assessment

### Available skills (already installed):
- `frontend-design` — for UI polish of the builder
- `make-interfaces-feel-better` — for drag-drop micro-interactions
- `accessibility` — for keyboard navigation in the grid builder
- `best-practices` — for security audit of the batch command endpoint

### Potentially useful skills (not installed):
- `mindrally/skills@htmx` (234 installs) — htmx best practices. Install: `npx skills add mindrally/skills@htmx`

No GridStack.js-specific skill exists in the marketplace, which is expected for a focused UI library.

---

## 13. Open Questions for Design Phase

1. **Should the block registry be Python-only or also exposed as JSON to the frontend?** The builder needs to know available block types, their icons, categories, and config schemas. A JSON endpoint (`GET /api/blocks/types`) would allow the builder to be data-driven rather than hardcoded.

2. **Should GridStack be initialized in edit mode (builder) vs. static mode (viewer)?** The dashboard page could use `GridStack.init({staticGrid: true})` for viewing, and `GridStack.init({float: false})` for editing. This avoids the drag handles appearing on read-only dashboards.

3. **How deep should the form-group nesting go?** "Create a Project with 3 Tasks" is clear. "Create a Project with 3 Tasks, each with 2 Sub-tasks" is 3 levels. Recommend capping at 2 levels for MVP.

4. **Should chart widgets use inline SPARQL or reference saved queries?** Saved queries are more reusable but add indirection. Recommend supporting both.
