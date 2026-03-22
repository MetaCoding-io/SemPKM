# S01 Summary: GridStack Layout Engine + Block Registry

**Status:** Complete  
**Duration:** ~90 minutes across 3 tasks  
**Verification:** 71 unit tests pass (44 new registry/migration + 27 existing dashboard), all file presence checks pass, failure-path check confirms descriptive ValueError on invalid block type.

## What This Slice Delivered

Replaced the fixed CSS Grid dashboard layout system (5 hardcoded layouts with slot-based block placement) with a free-form GridStack.js 12-column canvas backed by a typed BlockRegistry. Existing dashboards auto-migrate to GridStack positions on first access.

**Before:** Dashboards used one of 5 CSS Grid layouts (`single`, `sidebar-main`, `grid-2x2`, `grid-3`, `top-bottom`). Blocks were assigned to named slots (`top-left`, `main`, etc.). No drag, no resize, no free positioning. Block types were validated against a hardcoded `VALID_BLOCK_TYPES` set.

**After:** Dashboards use a 12-column GridStack grid. Each block stores `{x, y, w, h}` position data in `blocks_json`. The builder provides a categorized palette (content / data / layout) with click-to-add and drag-to-add. The viewer renders blocks at exact GridStack positions in static (read-only) mode. The `BLOCK_REGISTRY` singleton is the single source of truth for block type validation, config schemas, icons, categories, and default dimensions.

## Key Files Created/Modified

| File | Change |
|------|--------|
| `backend/app/dashboard/registry.py` | **NEW** — BlockRegistry with BlockTypeSpec dataclass, 6 block type declarations |
| `backend/app/dashboard/migration.py` | **NEW** — `migrate_layout_to_gridstack()` maps 5 legacy layouts to GridStack positions |
| `backend/app/dashboard/models.py` | Added `"gridstack"` to VALID_LAYOUTS, derived VALID_BLOCK_TYPES from registry |
| `backend/app/dashboard/service.py` | Replaced inline type checks with `BLOCK_REGISTRY.validate_block()`, added position validation |
| `backend/app/dashboard/router.py` | Auto-migration in `render_dashboard`, `_block_types_for_template()` helper, flat blocks context |
| `backend/app/templates/browser/dashboard_builder.html` | Complete rewrite: GridStack canvas + categorized block palette |
| `backend/app/templates/browser/dashboard_page.html` | Complete rewrite: static GridStack grid replacing CSS Grid container |
| `backend/app/templates/base.html` | GridStack.js CDN added to both dev and prod asset blocks |
| `frontend/static/css/workspace.css` | ~335 lines added: builder palette, GridStack dark theme, widget structure, read-only dashboard |
| `backend/tests/test_block_registry.py` | **NEW** — 30 tests (registration, lookup, categorization, validation, position bounds) |
| `backend/tests/test_layout_migration.py` | **NEW** — 14 tests (all 5 layouts, edge cases, idempotency, immutability) |

## Patterns Established

### BlockRegistry Singleton
```python
from app.dashboard.registry import BLOCK_REGISTRY

# Validate a block dict (type + config)
BLOCK_REGISTRY.validate_block({"type": "markdown", "config": {"content": "# Hi"}})

# Validate GridStack position fields
BLOCK_REGISTRY.validate_position({"x": 0, "y": 0, "w": 6, "h": 4})

# Get all registered types
BLOCK_REGISTRY.all_types()  # ['create-form', 'divider', 'markdown', ...]

# Get types grouped by category
BLOCK_REGISTRY.by_category()  # {'content': [...], 'data': [...], 'layout': [...]}

# Look up a single spec
spec = BLOCK_REGISTRY.get("markdown")  # BlockTypeSpec with icon, default_w/h, etc.
```

S02 should use `BLOCK_REGISTRY.register()` to add new block types (stat-card, chart, heading). The registry auto-updates `VALID_BLOCK_TYPES` via the models.py derivation.

### Layout Migration
```python
from app.dashboard.migration import migrate_layout_to_gridstack

# Converts legacy slot-based blocks to GridStack positions
migrated_blocks = migrate_layout_to_gridstack("grid-2x2", blocks)
# Each block now has x, y, w, h fields
```

Migration is idempotent — blocks with existing positions pass through unchanged. The function deep-copies blocks to avoid mutating inputs.

### Auto-Migration on Dashboard Access
`render_dashboard` in `router.py` checks `dashboard.layout != "gridstack"` before rendering. If true, it calls `migrate_layout_to_gridstack()`, persists the migrated result via `service.update()`, then renders the GridStack page. This is lazy — migration only runs when a user opens a legacy dashboard.

### GridStack Widget Pattern (Builder)
Builder widgets use `makeWidgetHTML()` → `.gs-widget-inner` div with `.widget-header` (type label + remove button) and `.block-config-container` (config form with `[data-key]` elements). Save serializes by iterating `grid.getGridItems()` and reading `el.gridstackNode` for positions + `el.dataset.blockType` for type + `[data-key]` elements for config.

### Event Isolation
Both builder canvas and palette use `stopPropagation()` on `mousedown/pointerdown/touchstart` to prevent dockview panel drag interference — same pattern as canvas.js and kanban.js.

## Risks Retired

- **GridStack.js + dockview event interference** (Key Risk #1 from roadmap) — retired via `stopPropagation()` on the GridStack canvas wrapper and palette. Matches proven pattern from canvas.js.
- **Layout migration correctness** — retired via 14 pytest tests covering all 5 layouts, edge cases (unmatched slots, missing positions), idempotency, and immutability.

## What S02/S03 Need to Know

1. **Registering new block types:** Call `BLOCK_REGISTRY.register(BlockTypeSpec(...))` in `registry.py`. The `_block_types_for_template()` helper in `router.py` auto-serializes all specs to the builder template context.

2. **Adding new block rendering:** The dashboard page template (`dashboard_page.html`) uses `{% if block.type == 'markdown' %}...{% elif block.type == 'stat-card' %}...` pattern inside the GridStack widget loop. Add new block type branches there.

3. **GridStack CDN is loaded globally:** Both `base.html` dev and prod blocks include GridStack CSS + JS. No additional loading needed.

4. **GridStack is NOT yet in the vendor bundle:** It's loaded from CDN in both dev and prod modes. A future build step should bundle it. Not blocking for S02/S03.

5. **Position validation:** `BLOCK_REGISTRY.validate_position()` checks x/y/w/h bounds (0 ≤ x < 12, y ≥ 0, 1 ≤ w ≤ 12, h ≥ 1, x+w ≤ 12). Runs only when layout is "gridstack" AND position fields are present.

6. **Config schema validation is lightweight:** Registry validates config value types against the schema but doesn't enforce required keys — config keys are optional to allow partial/progressive block configuration in the builder. S02 block types should follow the same convention.

## Known Issues

- GridStack CDN in prod asset block is a pragmatic fix. Should be bundled via esbuild (M029 pattern) when this is stabilized.
- Drag-from-palette type tracking uses a module-level `_draggingType` variable. Click-to-add is the reliable fallback.
- Migration log messages may not appear in Docker logs depending on logging level configuration — the migration itself works correctly.
