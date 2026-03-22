# M032: Block-Based Custom UI Builder

**Vision:** SemPKM's dashboard system evolves from 5 fixed CSS Grid layouts with 6 block types into a free-form drag-drop-resize grid (GridStack.js) with a typed block registry, new data-driven widgets (stat cards, charts), and multi-object form groups that create linked objects in a single transaction.

## Success Criteria

- A user creates a new dashboard, drags blocks from a palette onto a GridStack canvas, resizes them, saves, and reopens the dashboard with layout preserved
- Existing dashboards created with the old fixed layouts render correctly without user intervention (auto-migration to GridStack positions)
- A stat-card block displays a live SPARQL-derived metric (e.g., object count) on a dashboard
- A chart block renders a Chart.js bar/line/pie chart from SPARQL query results
- A form-group block creates a Project plus 2 linked Tasks in a single atomic transaction, with cross-object edge linking
- The dashboard builder shows available block types from the BlockRegistry with icons, categories, and config panels
- Block content loads via htmx server-rendering inside GridStack widgets without sizing or interaction conflicts with dockview panels

## Key Risks / Unknowns

- **GridStack.js + htmx + dockview triple interaction** — GridStack uses drag-drop; dockview also uses drag-drop for panel management. Both systems need to coexist without intercepting each other's events. The canvas.js and kanban.js already solve this with `e.stopPropagation()`, but GridStack's event model hasn't been tested. This is the #1 risk.
- **GridStack widget sizing vs. htmx async content** — GridStack reserves space for widgets, but htmx block content loads asynchronously. Dynamic content height may mismatch the reserved cell height, causing overflow or empty space.
- **Slot-based IRI resolution in form-group transactions** — Creating object A, then object B with an edge to A requires knowing A's IRI before B's edge command. The existing `/api/commands/bulk` doesn't support cross-referencing between commands. Needs a server-side slot map.

## Proof Strategy

- **GridStack integration** → retire in S01 by building a real dashboard with drag-drop-resize blocks, all persisted in `blocks_json` with `{x, y, w, h}` position data, rendering through htmx inside a dockview panel.
- **New widget rendering** → retire in S02 by adding stat-card and chart blocks that display live SPARQL data on a real dashboard.
- **Multi-object form transaction** → retire in S03 by building a form-group block that creates linked objects atomically, verifiable through the object browser.

## Verification Classes

- **Contract verification:** pytest unit tests for BlockRegistry validation, config schema enforcement, slot-based IRI resolution logic, layout migration mapping — all run without Docker in <5s
- **Integration verification:** dashboard builder saves GridStack layout → dashboard page renders it → blocks load via htmx → stat-card/chart show live data — requires Docker stack with triplestore
- **Operational verification:** existing dashboards auto-migrate to GridStack positions on first load, form-group atomic creates roll back on partial failure
- **UAT / human verification:** dashboard builder UX for drag/drop/resize feels responsive, block palette is discoverable, chart renders correct data

## Milestone Definition of Done

This milestone is complete only when all are true:

- All 3 slice deliverables are complete (S01–S03)
- A dashboard with mixed block types (view-embed, stat-card, chart, markdown, form-group) renders correctly from a GridStack layout
- Existing dashboards created with old fixed layouts continue to work via auto-migration
- GridStack drag-drop-resize works inside dockview panels without event interference
- A form-group block creates multiple linked objects in one transaction
- Design document written as `M032-DESIGN.md` summarizing the architecture, block registry schema, widget inventory, and migration strategy
- Success criteria re-checked against live behavior in the Docker stack

## Requirement Coverage

No Active requirements in REQUIREMENTS.md directly target M032. The active requirements are scoped to APP-* (App Platform), RSS-* (RSS Reader), GCAL-* (Google Calendar), and EVENT-* (Calendar Events). M032 is self-contained new capability work.

The candidate requirements from research (BLOCK-01 through BLOCK-15) are tracked below:

| Candidate | Status | Slice |
|-----------|--------|-------|
| BLOCK-01 (GridStack replaces fixed CSS Grid) | ✅ Covered | S01 |
| BLOCK-02 (Auto-migrate 5 layouts to GridStack) | ✅ Covered | S01 |
| BLOCK-03 (Drag-from-palette block placement) | ✅ Covered | S01 |
| BLOCK-04 (Block resize via GridStack handles) | ✅ Covered | S01 |
| BLOCK-05 (Layout JSON round-trip) | ✅ Covered | S01 |
| BLOCK-06 (BlockRegistry pattern) | ✅ Covered | S01 |
| BLOCK-07 (stat-card widget) | ✅ Covered | S02 |
| BLOCK-08 (chart widget) | ✅ Covered | S02 |
| BLOCK-09 (form-group block) | ✅ Covered | S03 |
| BLOCK-10 (Batch commands with slot refs) | ✅ Covered | S03 |
| BLOCK-11 (Slash command insertion) | ⏭ Deferred | — |
| BLOCK-12 (Block templates) | ⏭ Deferred | — |
| BLOCK-13 (Dashboard/workflow unification) | ⏭ Deferred | — |
| BLOCK-14 (SQLite → RDF migration) | ⏭ Deferred | — |
| BLOCK-15 (Nested GridStack grids) | ⏭ Deferred | — |

**Deferred rationale:** BLOCK-11 through BLOCK-15 are enhancement-tier features that add polish but don't affect core capability. The dashboard/workflow unification (BLOCK-13) and RDF migration (BLOCK-14) are explicitly Phase 2/3 per the research migration strategy.

## Boundary Map

```
Frontend (browser)
├── GridStack.js (CDN) — layout engine, drag/drop/resize
├── dashboard_builder.html — builder UI with block palette + GridStack canvas
├── dashboard_page.html — viewer with static GridStack rendering
├── block config panels — per-type config forms in builder
└── chart.js init — Chart.js post-htmx-swap initialization

Backend (FastAPI)
├── dashboard/models.py — blocks_json gains {x, y, w, h} per block
├── dashboard/service.py — validation extended for position data + new types
├── dashboard/router.py — render_block() extended for new block types
├── dashboard/registry.py — NEW: BlockRegistry with typed widget declarations
├── dashboard/migration.py — NEW: layout→gridstack position auto-mapper
└── commands/router.py — /api/commands/bulk extended with slot_map resolution

Templates (Jinja2, server-rendered)
├── block_stat_card.html — stat card rendering
├── block_chart.html — chart data + Chart.js init script
├── block_heading.html — heading rendering
├── block_form_group.html — multi-object form composition
└── dashboard_builder.html — extended with GridStack + palette + new block types
```

## Slices

- [x] **S01: GridStack Layout Engine + Block Registry** `risk:high` `depends:[]`
  > After this: a user creates a dashboard in the builder by dragging blocks from a categorized palette onto a 12-column GridStack canvas, repositions and resizes them freely, saves the layout, and sees it render correctly on the dashboard page. Existing dashboards auto-migrate from fixed CSS Grid layouts to GridStack positions. The BlockRegistry declares all block types with config schemas, icons, and categories. All 6 existing block types work in the new GridStack layout.

- [ ] **S02: Data-Driven Widget Types (stat-card, chart, heading)** `risk:medium` `depends:[S01]`
  > After this: the block palette includes stat-card, chart, and heading widgets. A stat-card shows a live SPARQL-derived number (e.g., "42 Projects"). A chart block renders a Chart.js bar/line/pie chart from SPARQL query results. A heading block adds section labels to the dashboard. Each widget has a config panel in the builder. The design document (`M032-DESIGN.md`) is written.

- [ ] **S03: Multi-Object Form Groups** `risk:medium` `depends:[S01]`
  > After this: a form-group block in the dashboard builder lets users compose multiple SHACL forms (e.g., "Project + 2 Tasks"). Submitting creates all objects atomically via a slot-based transaction where later objects can reference earlier objects' IRIs for edge creation. SHACL validation runs per-sub-form. The form renders as collapsible sections using existing `_field.html` macros.
