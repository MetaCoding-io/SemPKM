---
estimated_steps: 5
estimated_files: 6
skills_used:
  - test
  - review
---

# T01: BlockRegistry + model/service updates + layout migration utility

**Slice:** S01 — GridStack Layout Engine + Block Registry
**Milestone:** M032

## Description

Create the backend foundation for the GridStack-based dashboard system. This includes:

1. A **BlockRegistry** that declares all 6 existing block types with typed config schemas, icons, categories, and default sizes
2. Model updates to accept `"gridstack"` as a valid layout and `{x, y, w, h}` position fields per block
3. Service validation updates to use the registry for block type and config validation
4. A **layout migration utility** that maps each of the 5 old CSS Grid layouts to GridStack `{x, y, w, h}` positions
5. Comprehensive pytest unit tests for both the registry and migration logic

## Steps

1. **Create `backend/app/dashboard/registry.py`** — Define a `BlockTypeSpec` dataclass with fields: `type_name`, `label`, `icon` (Lucide icon name), `category` (e.g. "content", "data", "layout"), `config_schema` (dict describing expected config keys and types), `default_w`, `default_h` (default GridStack cell dimensions). Create a `BlockRegistry` class with a dict of `BlockTypeSpec` entries for all 6 types: `view-embed`, `markdown`, `object-embed`, `create-form`, `sparql-result`, `divider`. Add methods: `get(type_name)`, `validate_block(block_dict)` (validates type exists and config matches schema), `all_types()`, `by_category()`. The existing `VALID_BLOCK_TYPES` set in models.py should be derived from the registry going forward.

2. **Update `backend/app/dashboard/models.py`** — Add `"gridstack"` to `VALID_LAYOUTS`. The block JSON schema now accepts optional position fields: `x` (int, 0-11), `y` (int, ≥0), `w` (int, 1-12), `h` (int, ≥1). The `slot` field becomes optional (only used by legacy layouts). Import and expose the `BLOCK_REGISTRY` singleton from registry.py. Keep `VALID_BLOCK_TYPES` as a derived set from the registry for backward compat.

3. **Update `backend/app/dashboard/service.py`** — Replace the inline `VALID_BLOCK_TYPES` check in `create()` and `update()` with `BLOCK_REGISTRY.validate_block(block)`. The registry raises `ValueError` with descriptive messages. When saving blocks with `layout="gridstack"`, validate that position fields are present and within bounds.

4. **Create `backend/app/dashboard/migration.py`** — Implement `migrate_layout_to_gridstack(layout: str, blocks: list[dict]) -> list[dict]` that maps each of the 5 old layouts to GridStack positions:
   - `single`: all blocks stack vertically at x=0, w=12, h=4, incrementing y
   - `sidebar-main`: sidebar blocks at x=0, w=3; main blocks at x=3, w=9
   - `grid-2x2`: top-left (0,0,6,4), top-right (6,0,6,4), bottom-left (0,4,6,4), bottom-right (6,4,6,4)
   - `grid-3`: left (0,0,4,6), center (4,0,4,6), right (8,0,4,6)
   - `top-bottom`: top (0,0,12,4), bottom (0,4,12,4)
   Each block gets its `x,y,w,h` set based on its `slot` value matching the layout's slot definitions. Blocks without a matching slot get stacked at the end.

5. **Write tests** — Create `backend/tests/test_block_registry.py` testing: all 6 types registered, `get()` returns correct spec, `validate_block()` accepts valid blocks, `validate_block()` rejects unknown types, `by_category()` groups correctly. Create `backend/tests/test_layout_migration.py` testing: each of the 5 layouts produces correct `{x,y,w,h}` positions, blocks without slots get default positions, already-gridstack blocks pass through unchanged.

## Must-Haves

- [ ] BlockRegistry declares all 6 existing block types with icon, category, config_schema, default_w, default_h
- [ ] `validate_block()` rejects unknown types and produces clear error messages
- [ ] `"gridstack"` is a valid layout value
- [ ] Block dicts accept optional `x, y, w, h` integer position fields
- [ ] Service uses registry for validation instead of raw `VALID_BLOCK_TYPES` set check
- [ ] Migration maps all 5 old layouts to correct GridStack positions
- [ ] All tests pass: `python -m pytest tests/test_block_registry.py tests/test_layout_migration.py -v`

## Verification

- `cd backend && python -m pytest tests/test_block_registry.py tests/test_layout_migration.py -v` — all tests pass
- `python -c "from app.dashboard.registry import BLOCK_REGISTRY; print(BLOCK_REGISTRY.all_types())"` — prints all 6 type names
- `python -c "from app.dashboard.migration import migrate_layout_to_gridstack; blocks = [{'type':'markdown','slot':'top-left','config':{'content':'hi'}},{'type':'divider','slot':'bottom-right','config':{}}]; result = migrate_layout_to_gridstack('grid-2x2', blocks); print(result)"` — prints blocks with correct x,y,w,h

## Inputs

- `backend/app/dashboard/models.py` — current model with VALID_LAYOUTS and VALID_BLOCK_TYPES
- `backend/app/dashboard/service.py` — current service with inline validation
- `backend/app/dashboard/router.py` — LAYOUT_DEFINITIONS dict showing the 5 old layouts and their slots

## Expected Output

- `backend/app/dashboard/registry.py` — NEW: BlockRegistry with all 6 block type declarations
- `backend/app/dashboard/migration.py` — NEW: layout-to-gridstack migration utility
- `backend/app/dashboard/models.py` — updated with "gridstack" in VALID_LAYOUTS
- `backend/app/dashboard/service.py` — updated to use BlockRegistry for validation
- `backend/tests/test_block_registry.py` — NEW: unit tests for registry
- `backend/tests/test_layout_migration.py` — NEW: unit tests for layout migration

## Observability Impact

- **New failure signals:** `BLOCK_REGISTRY.validate_block()` raises `ValueError` with descriptive messages naming the invalid type or config key — these propagate to the HTTP 400 response via the service layer.
- **New runtime logging:** `migration.py` emits `logger.info(...)` with block count and source layout name on every migration call, plus `logger.debug(...)` for each unmatched slot.
- **Inspection:** `BLOCK_REGISTRY.all_types()` and `BLOCK_REGISTRY.by_category()` are available from a Python shell for runtime introspection of registered types.
- **Failure path:** Passing an unknown layout to `migrate_layout_to_gridstack()` raises `ValueError` listing known layouts.

