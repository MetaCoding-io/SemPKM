---
id: T01
parent: S02
milestone: M032
provides:
  - stat-card, chart, heading block types registered in BLOCK_REGISTRY (9 total)
  - builder config panels for all 3 new types in dashboard_builder.html
  - 44 unit tests covering all 9 block types with validation
key_files:
  - backend/app/dashboard/registry.py
  - backend/app/templates/browser/dashboard_builder.html
  - backend/tests/test_block_registry.py
key_decisions:
  - stat-card default 3×2 grid cells; chart 6×4; heading 12×1
  - chart_type stored as string with select options bar/line/pie/doughnut
  - heading level defaults to h2 when no selection
patterns_established:
  - data-category blocks include query textarea with SPARQL placeholder
  - select elements for enum config values (chart_type, heading level) use data-key attribute like other inputs
observability_surfaces:
  - validate_block() raises descriptive ValueError for wrong config types on new blocks
  - all_types() returns 9 sorted type names — inspectable via Python one-liner
duration: 12m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T01: Register stat-card, chart, heading block types with builder config panels and tests

**Registered 3 new block types (stat-card, chart, heading) in BLOCK_REGISTRY with builder config panels and 44 passing unit tests**

## What Happened

Added three `BlockTypeSpec` registrations to `_build_default_registry()` in `registry.py`: stat-card (data, 3×2), chart (data, 6×4), and heading (layout, 12×1). Each has a typed config_schema for validation.

Added three `case` branches to `getTypeConfigHTML()` in `dashboard_builder.html`: stat-card gets a SPARQL query textarea plus label/icon/color text inputs; chart gets a SPARQL query textarea, chart_type select (bar/line/pie/doughnut), and label_var/value_var inputs; heading gets a text input and level select (h1–h4, default h2). All inputs use `escapeAttr()`/`escapeHtml()` and follow existing patterns.

Updated `test_block_registry.py` with EXPECTED_TYPES expanded to 9, renamed the count test, and added `TestS02BlockTypes` class with 11 new tests: category/icon/dimension checks, parameterized valid config acceptance, and negative validation cases for non-string config values.

## Verification

- `cd backend && uv run --extra dev python -m pytest tests/test_block_registry.py -v` — 44 passed in 0.07s
- Python one-liner confirmed 9 types with stat-card/chart/heading present
- `data-key` count in builder template increased from 11 to 21 (expected +10)
- Diagnostic check: `validate_block({'type':'stat-card','config':{'query':42}})` raises `ValueError: must be str, got int`

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && uv run --extra dev python -m pytest tests/test_block_registry.py -v` | 0 | ✅ pass | 0.07s |
| 2 | `python3 -c "...assert len(types) == 9; assert 'stat-card' in types..."` | 0 | ✅ pass | <1s |
| 3 | `grep -c "data-key" backend/app/templates/browser/dashboard_builder.html` → 21 | 0 | ✅ pass | <1s |
| 4 | `grep -q "chart.js" backend/app/templates/base.html` | 1 | ❌ fail (T02) | <1s |
| 5 | `test -f backend/app/templates/browser/blocks/block_stat_card.html` | 1 | ❌ fail (T02) | <1s |
| 6 | `test -f backend/app/templates/browser/blocks/block_chart.html` | 1 | ❌ fail (T02) | <1s |
| 7 | `test -f .gsd/milestones/M032/M032-DESIGN.md` | 1 | ❌ fail (T03) | <1s |

Slice checks 4–7 are expected to fail at this intermediate task; they belong to T02 and T03.

## Diagnostics

- Inspect registered types: `cd backend && python3 -c "from app.dashboard.registry import BLOCK_REGISTRY; print(BLOCK_REGISTRY.all_types())"`
- Inspect a specific type: `cd backend && python3 -c "from app.dashboard.registry import BLOCK_REGISTRY; print(BLOCK_REGISTRY.get('stat-card'))"`
- Test failure-path validation: `cd backend && python3 -c "from app.dashboard.registry import BLOCK_REGISTRY; BLOCK_REGISTRY.validate_block({'type':'stat-card','config':{'query':42}})"`

## Deviations

- Added `## Observability Impact` section to T01-PLAN.md per pre-flight requirement.
- Added diagnostic failure-path verification step to S02-PLAN.md per pre-flight requirement.
- Used `uv run --extra dev` instead of `python -m pytest` since no Docker stack was running and pytest needed installing via dev extras.

## Known Issues

None.

## Files Created/Modified

- `backend/app/dashboard/registry.py` — Added 3 new BlockTypeSpec registrations (stat-card, chart, heading); updated docstring to "9 built-in block types"
- `backend/app/templates/browser/dashboard_builder.html` — Added 3 case branches in getTypeConfigHTML() with config inputs for new block types
- `backend/tests/test_block_registry.py` — Expanded EXPECTED_TYPES to 9, added TestS02BlockTypes class with 11 new tests
- `.gsd/milestones/M032/slices/S02/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
- `.gsd/milestones/M032/slices/S02/S02-PLAN.md` — Added diagnostic failure-path verification step (pre-flight fix)
