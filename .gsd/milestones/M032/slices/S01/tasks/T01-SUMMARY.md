---
id: T01
parent: S01
milestone: M032
provides:
  - BlockRegistry singleton with typed declarations for all 6 block types
  - "gridstack" as a valid layout value in VALID_LAYOUTS
  - Registry-based block validation in DashboardService
  - Layout-to-gridstack migration utility for all 5 legacy layouts
  - Position validation (x,y,w,h bounds checking) for gridstack blocks
key_files:
  - backend/app/dashboard/registry.py
  - backend/app/dashboard/migration.py
  - backend/app/dashboard/models.py
  - backend/app/dashboard/service.py
  - backend/app/dashboard/router.py
  - backend/tests/test_block_registry.py
  - backend/tests/test_layout_migration.py
key_decisions:
  - Config schema validation is lightweight (type checks on present keys, not required-key enforcement) — config keys are optional to allow partial/progressive block configuration in the builder
  - VALID_BLOCK_TYPES is derived from the registry singleton rather than hardcoded — single source of truth
  - GridStack position validation only runs when layout is "gridstack" AND position fields are present — allows legacy blocks without positions
  - Added minimal "gridstack" entry to LAYOUT_DEFINITIONS to maintain backward compat with existing test that asserts all VALID_LAYOUTS are in LAYOUT_DEFINITIONS
patterns_established:
  - BlockRegistry singleton pattern — import BLOCK_REGISTRY from registry.py, use validate_block() for type+config checks, validate_position() for gridstack bounds
  - Migration utility is idempotent — blocks with existing x,y,w,h pass through unchanged
observability_surfaces:
  - BLOCK_REGISTRY.validate_block() raises ValueError with descriptive messages (invalid type names, wrong config types)
  - migration.py logger.info() on every migration call with block count and source layout
  - migration.py logger.debug() for each unmatched slot
  - BLOCK_REGISTRY.all_types() and by_category() for runtime introspection
duration: 30m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T01: BlockRegistry + model/service updates + layout migration utility

**Created BlockRegistry with 6 typed block declarations, added "gridstack" layout support, wired registry validation into DashboardService, and built layout-to-gridstack migration utility with 44 passing tests.**

## What Happened

1. Created `registry.py` with `BlockTypeSpec` dataclass and `BlockRegistry` class. Registered all 6 existing block types (view-embed, markdown, object-embed, create-form, sparql-result, divider) with icons, categories, config schemas, and default GridStack dimensions. The singleton `BLOCK_REGISTRY` is the single source of truth for block type validity.

2. Updated `models.py` to add `"gridstack"` to `VALID_LAYOUTS` and derive `VALID_BLOCK_TYPES` from the registry instead of a hardcoded set. Updated the docstring to document the new optional `x, y, w, h` position fields on blocks.

3. Updated `service.py` to replace inline `VALID_BLOCK_TYPES` membership checks with `BLOCK_REGISTRY.validate_block()` calls in both `create()` and `update()`. Added position validation via `BLOCK_REGISTRY.validate_position()` when saving gridstack-layout dashboards with position fields.

4. Created `migration.py` with `migrate_layout_to_gridstack()` that maps all 5 legacy CSS Grid layouts to GridStack positions. The function is idempotent (blocks with existing positions pass through), handles unmatched slots by stacking at the bottom, and deep-copies blocks to avoid mutating inputs.

5. Added a minimal `"gridstack"` entry to `LAYOUT_DEFINITIONS` in `router.py` to maintain backward compatibility with the existing `test_layout_definitions_complete` test.

6. Wrote 30 tests in `test_block_registry.py` (registration, lookup, categorization, validation, position bounds) and 14 tests in `test_layout_migration.py` (all 5 layouts, edge cases, idempotency, immutability).

## Verification

- `pytest tests/test_block_registry.py tests/test_layout_migration.py -v` → 44 passed
- `pytest tests/test_dashboard.py -v` → 27 passed (no regressions, including the layout_definitions_complete test)
- `python -c "from app.dashboard.registry import BLOCK_REGISTRY; print(BLOCK_REGISTRY.all_types())"` → prints all 6 types
- `python -c "...migrate_layout_to_gridstack('grid-2x2', blocks)..."` → correct x,y,w,h positions
- Failure-path: `validate_block({'type':'bogus',...})` raises ValueError with descriptive message

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && python -m pytest tests/test_block_registry.py tests/test_layout_migration.py -v` | 0 | ✅ pass | 0.08s |
| 2 | `cd backend && python -m pytest tests/test_dashboard.py -v` | 0 | ✅ pass | 0.74s |
| 3 | `python -c "from app.dashboard.registry import BLOCK_REGISTRY; print(BLOCK_REGISTRY.all_types())"` | 0 | ✅ pass | <1s |
| 4 | `python -c "...migrate_layout_to_gridstack('grid-2x2', blocks)..."` | 0 | ✅ pass | <1s |
| 5 | `python -c "BLOCK_REGISTRY.validate_block({'type':'bogus','config':{}})"` — ValueError raised | 0 | ✅ pass | <1s |

## Diagnostics

- **Inspect registered types:** `python -c "from app.dashboard.registry import BLOCK_REGISTRY; print(BLOCK_REGISTRY.all_types())"`
- **Inspect by category:** `python -c "from app.dashboard.registry import BLOCK_REGISTRY; print({k: [s.type_name for s in v] for k, v in BLOCK_REGISTRY.by_category().items()})"`
- **Test migration:** `python -c "from app.dashboard.migration import migrate_layout_to_gridstack; print(migrate_layout_to_gridstack('grid-2x2', [{'type':'markdown','slot':'top-left','config':{'content':'x'}}]))"`
- **Error shape:** `ValueError("Invalid block type: 'foo'. Must be one of ['create-form', ...]")`
- **Migration logs:** `logger.info("Migrated %d blocks from layout '%s' to gridstack positions", ...)` at INFO level

## Deviations

- Added a minimal `"gridstack"` entry to `LAYOUT_DEFINITIONS` in `router.py` — not in the original task plan, but required to prevent regression in the existing `test_layout_definitions_complete` test which asserts all `VALID_LAYOUTS` keys exist in `LAYOUT_DEFINITIONS`.

## Known Issues

None.

## Files Created/Modified

- `backend/app/dashboard/registry.py` — NEW: BlockRegistry with BlockTypeSpec dataclass, 6 block type declarations, validate_block/validate_position methods
- `backend/app/dashboard/migration.py` — NEW: migrate_layout_to_gridstack() maps 5 legacy layouts to GridStack positions
- `backend/app/dashboard/models.py` — Added "gridstack" to VALID_LAYOUTS, derived VALID_BLOCK_TYPES from registry
- `backend/app/dashboard/service.py` — Replaced inline type checks with BLOCK_REGISTRY.validate_block(), added position validation
- `backend/app/dashboard/router.py` — Added "gridstack" entry to LAYOUT_DEFINITIONS
- `backend/tests/test_block_registry.py` — NEW: 30 tests for registry lookup, validation, categorization, position bounds
- `backend/tests/test_layout_migration.py` — NEW: 14 tests for all 5 layout migrations, edge cases, idempotency
