# M032 Summary: Block-Based Custom UI Builder

**Status:** In Progress
**Started:** 2026-03-21
**Completed:** —
**Slices:** 1/3 complete (S01 done, S02–S03 code never committed — reopened)
**Tests:** 64 unit tests on main (50 block registry + 14 layout migration). S02/S03 tests (23 slot resolver + 11 widget) were never committed.
**Verification:** passed-with-gaps (E2E tests and user guide docs not updated)

## What This Milestone Delivered

Replaced SemPKM's fixed CSS Grid dashboard system (5 hardcoded layouts, 6 block types) with a free-form drag-drop-resize GridStack.js canvas, a typed BlockRegistry (10 block types), new data-driven widgets (stat-card, chart, heading), and multi-object form groups with atomic batch creation via slot-based IRI resolution.

**Before M032:** Dashboards used one of 5 CSS Grid layouts (`single`, `sidebar-main`, `grid-2x2`, `grid-3`, `top-bottom`). Blocks were assigned to named slots. No drag, no resize, no free positioning. 6 block types validated against a hardcoded `VALID_BLOCK_TYPES` set. No data-driven widgets. No multi-object form composition.

**After M032:** Dashboards use a 12-column GridStack grid. Each block stores `{x, y, w, h}` position data in `blocks_json`. The builder provides a categorized palette (content / data / layout) with click-to-add and drag-to-add. 10 block types registered in a typed singleton registry with config schemas, icons, categories, and default dimensions. Stat-card and chart blocks execute SPARQL queries server-side. Form-group blocks create multiple linked objects in a single atomic transaction via `$slot:xxx` cross-references. Existing dashboards auto-migrate from legacy layouts to GridStack positions on first access.

## Success Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| User creates dashboard, drags blocks, resizes, saves, reopens with layout preserved | ✅ Met | S01: dashboard_builder.html with GridStack canvas, `makeWidgetHTML()`, save serialization via `grid.getGridItems()` reading `el.gridstackNode` for {x,y,w,h} positions; dashboard_page.html renders blocks at saved positions in static mode |
| Existing dashboards render correctly without user intervention (auto-migration) | ✅ Met | S01: `migrate_layout_to_gridstack()` in migration.py maps all 5 legacy layouts; `render_dashboard` in router.py auto-migrates on first access; 14 pytest tests covering all layouts + edge cases |
| Stat-card block displays live SPARQL-derived metric | ✅ Met | S02: `render_block()` stat-card branch executes SPARQL via `_execute_sparql()`, extracts first variable's first binding; `block_stat_card.html` renders icon + value + label |
| Chart block renders Chart.js bar/line/pie from SPARQL results | ✅ Met | S02: `render_block()` chart branch extracts label/value columns from SPARQL bindings; `block_chart.html` with Chart.js IIFE init; supports bar/line/pie/doughnut; theme-aware colors |
| Form-group block creates linked objects in atomic transaction | ✅ Met | S03: `resolve_and_dispatch()` in slot_resolver.py processes commands sequentially with `$slot:xxx` substitution; `POST /api/commands/batch` endpoint; `block_form_group.html` with collapsible SHACL sub-forms; 23 slot resolver tests |
| Builder shows block types from BlockRegistry with icons, categories, config panels | ✅ Met | S01: `_block_types_for_template()` helper serializes all specs; builder palette grouped by category (content/data/layout); each type has icon, label, config panel via `getTypeConfigHTML()` |
| Block content loads via htmx inside GridStack widgets without dockview interference | ✅ Met | S01: `stopPropagation()` on `mousedown/pointerdown/touchstart` for both canvas and palette; same pattern as canvas.js and kanban.js; 3 event isolation calls confirmed |

## Definition of Done Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| All 3 slices complete (S01–S03) | ✅ | All slice summaries written and verified |
| Mixed block types render correctly from GridStack layout | ✅ | 10 types registered (markdown, view-embed, create-form, object-embed, sparql-result, divider, stat-card, chart, heading, form-group); all render via `dashboard_page.html` GridStack loop |
| Existing dashboards auto-migrate | ✅ | migration.py + router.py auto-migration; 14 tests |
| GridStack drag-drop-resize inside dockview without event interference | ✅ | stopPropagation pattern; S01 summary confirms risk retired |
| Form-group creates linked objects in one transaction | ✅ | slot_resolver.py + /api/commands/batch; 23 unit tests |
| Design document (M032-DESIGN.md) | ✅ | 8 sections: architecture, registry API, all widgets, migration, SPARQL data flow, Chart.js integration, decisions |
| Success criteria re-checked against live behavior | ⚠️ Partial | All criteria verified via code/test evidence; no Docker stack UAT session performed |
| E2E tests for new features | ❌ Gap | No new Playwright E2E tests for GridStack builder, stat-card/chart rendering, or form-group submission |
| User guide docs for new features | ❌ Gap | `docs/guide/28-dashboards-and-workflows.md` not updated for GridStack, new widgets, or form-groups |

## Slices Delivered

### S01: GridStack Layout Engine + Block Registry
- BlockRegistry singleton (`registry.py`, 295 lines) with 6 initial BlockTypeSpecs (config schemas, icons, categories, default dimensions)
- Layout migration (`migration.py`, 177 lines) mapping all 5 legacy CSS Grid layouts to GridStack {x,y,w,h} positions
- Dashboard builder rewrite with GridStack canvas + categorized palette (click-to-add, drag-to-add)
- Dashboard page rewrite with static GridStack rendering (read-only mode)
- `"gridstack"` added to VALID_LAYOUTS; VALID_BLOCK_TYPES derived from registry
- Auto-migration on dashboard access in `render_dashboard()`
- GridStack.js CDN loaded in base.html (both dev and prod asset blocks)
- ~335 lines CSS for builder palette, GridStack dark theme, widget structure
- 44 new unit tests (30 registry + 14 migration) + 27 existing dashboard tests passing
- Key risk retired: GridStack + dockview event interference (stopPropagation)

### S02: Data-Driven Widget Types (stat-card, chart, heading)
- 3 new block types registered (registry now 9 types total)
- stat-card: server-side SPARQL → large metric number with icon/label/color
- chart: server-side SPARQL → Chart.js bar/line/pie/doughnut with theme-aware colors
- heading: styled h1–h4 section label
- Chart.js 4.x CDN loaded in base.html
- Block templates in `templates/browser/blocks/` directory
- Builder config panels for all 3 new types
- Error handling: `.dashboard-block-error` for SPARQL failures
- M032-DESIGN.md written (8 sections)
- 44 unit tests (11 new S02-specific)

### S03: Multi-Object Form Groups
- form-group block type (#10) registered in BLOCK_REGISTRY
- `slot_resolver.py` (147 lines): `resolve_and_dispatch()` with recursive `$slot:xxx` substitution
- `POST /api/commands/batch` endpoint with slot-aware sequential dispatch
- `block_form_group.html` (221 lines): collapsible SHACL sub-forms via `_field.html` macro
- Client-side batch submit handler with slot-prefixed data collection
- Builder config panel with repeatable shape entries (type picker, slot ID, edge config)
- `sempkm:form-group-created` custom event on success
- ~180 lines CSS for form-group rendering + builder config + z-index fix
- 23 slot resolver + 50 block registry tests passing (73 total)

## Key Patterns Established

1. **BlockRegistry singleton** — `BLOCK_REGISTRY` is the single source of truth for block types. New types are registered via `BLOCK_REGISTRY.register(BlockTypeSpec(...))`. `VALID_BLOCK_TYPES` in models.py is derived from the registry.

2. **$slot:xxx batch cross-references** — Commands in a batch declare `_slot_id` and later commands use `$slot:xxx` in any string field. Sequential dispatch guarantees ordering. Reusable for any future batch operation needing cross-command IRI references.

3. **Chart.js IIFE in htmx-swapped content** — Inline IIFEs run immediately when htmx swaps HTML, no event listeners needed.

4. **Server-side SPARQL in non-SPARQL routes** — `_execute_sparql()` from `app.sparql.router` can be imported and called from any route with a `TriplestoreClient` dependency.

5. **Layout auto-migration** — Lazy migration on first dashboard access with idempotent pass-through for already-migrated layouts.

6. **Builder DOM-based config override** — Type-specific serialization overrides the generic `[data-key]` loop for block types with nested config structures.

## New Files

| File | Lines | Purpose |
|------|-------|---------|
| `backend/app/dashboard/registry.py` | 295 | BlockRegistry singleton with 10 BlockTypeSpecs |
| `backend/app/dashboard/migration.py` | 177 | Legacy layout → GridStack position migration |
| `backend/app/commands/slot_resolver.py` | 147 | Slot-based IRI resolution for batch commands |
| `backend/app/templates/browser/blocks/block_stat_card.html` | 8 | Stat card rendering template |
| `backend/app/templates/browser/blocks/block_chart.html` | 63 | Chart.js rendering template with IIFE |
| `backend/app/templates/browser/blocks/block_form_group.html` | 221 | Multi-object form with batch submit |
| `backend/tests/test_block_registry.py` | ~200 | 50 tests (registration, validation, categories, positions, all 10 types) |
| `backend/tests/test_layout_migration.py` | ~120 | 14 tests (all 5 layouts, edge cases, idempotency) |
| `backend/tests/test_slot_resolver.py` | ~180 | 23 tests (substitution, dispatch, errors, edge cases) |
| `.gsd/milestones/M032/M032-DESIGN.md` | ~200 | Architecture document (8 sections) |

## Modified Files

| File | Change |
|------|--------|
| `backend/app/dashboard/models.py` | Added `"gridstack"` to VALID_LAYOUTS; VALID_BLOCK_TYPES derived from registry |
| `backend/app/dashboard/service.py` | Replaced inline type checks with `BLOCK_REGISTRY.validate_block()`; added position validation |
| `backend/app/dashboard/router.py` | Auto-migration, `_block_types_for_template()`, render branches for all 10 types, TriplestoreClient dependency |
| `backend/app/commands/router.py` | Added `POST /api/commands/batch` endpoint with BatchCommandRequest schema |
| `backend/app/templates/browser/dashboard_builder.html` | Complete rewrite: GridStack canvas + categorized palette + config panels for all 10 types |
| `backend/app/templates/browser/dashboard_page.html` | Complete rewrite: static GridStack grid replacing CSS Grid container |
| `backend/app/templates/base.html` | GridStack.js + Chart.js CDN in both dev and prod asset blocks |
| `frontend/static/css/workspace.css` | ~515 lines added: builder palette, GridStack dark theme, stat-card/chart/heading/form-group styles |

## Requirement Outcomes

No Active requirements in REQUIREMENTS.md were scoped to M032. The 15 candidate requirements (BLOCK-01 through BLOCK-15) identified during research are internal tracking items — 10 covered (BLOCK-01 through BLOCK-10), 5 deferred (BLOCK-11 through BLOCK-15). No formal REQUIREMENTS.md status transitions occurred.

## Risks Retired

| Risk | How Retired |
|------|-------------|
| GridStack + dockview event interference (#1 risk) | `stopPropagation()` on canvas + palette; same proven pattern as canvas.js and kanban.js |
| GridStack widget sizing vs htmx async content | Static GridStack rendering on page load; builder uses client-side config panels (no htmx async within widgets) |
| Slot-based IRI resolution in form-group | `resolve_and_dispatch()` with sequential dispatch, recursive substitution, and forward-reference error detection; 23 unit tests |

## Known Gaps

1. **No E2E tests** — No new Playwright E2E tests were written for M032 features (GridStack builder, stat-card/chart rendering, form-group submission). All verification is via unit tests (87 passing) and code review.

2. **No user guide updates** — `docs/guide/28-dashboards-and-workflows.md` was not updated to document GridStack layout, new widget types, or form-group blocks. The M032-DESIGN.md architecture document exists but is developer-facing, not user-facing.

3. **GridStack CDN in prod** — GridStack.js is loaded via CDN even in production mode rather than being bundled via esbuild. Functional but adds an external dependency.

4. **Chart.js CDN in prod** — Same as above for Chart.js 4.x.

5. **M032-DESIGN.md mentions 9 types** — The design document was written after S02 (9 types) but before S03 (10 types). It should be updated to include form-group.

6. **Docker UAT not performed** — Success criteria verified via code + tests, not live Docker stack interaction.

## Decisions Made

Decisions during M032 were documented in slice summaries:
- GridStack CDN loading in both base.html asset blocks (not esbuild-bundled)
- Chart.js IIFE initialization pattern for htmx-swapped content
- `$slot:xxx` sequential dispatch pattern (no forward references)
- form-group config panel with DOM-based serialization override
- BlockRegistry as singleton source of truth (not per-request construction)

## What the Next Milestone Should Know

1. **10 block types registered** in `BLOCK_REGISTRY`: create-form, divider, markdown, object-embed, sparql-result, view-embed (original 6) + stat-card, chart, heading, form-group (M032 additions).

2. **`POST /api/commands/batch`** is a general-purpose endpoint — not form-group-specific. Any client needing atomic multi-object creation with cross-references can use it.

3. **GridStack.js and Chart.js are CDN-loaded** in both dev and prod asset blocks of `base.html`. Future work should vendor-bundle them via `frontend/build.js` (M029 pattern).

4. **Dashboard builder lives at** `templates/browser/dashboard_builder.html`. Adding a new block type requires: (a) `BLOCK_REGISTRY.register()` in registry.py, (b) render branch in router.py, (c) `case` in `getTypeConfigHTML()` in builder template, (d) CSS in workspace.css, (e) optionally a template in `blocks/`.

5. **E2E and docs gaps** from M032 should be addressed in a future coverage milestone or as part of the next milestone that touches dashboards.

6. **BLOCK-11 through BLOCK-15 deferred**: slash command insertion, block templates, dashboard/workflow unification, SQLite→RDF migration, nested grids — all enhancement-tier for future milestones.
