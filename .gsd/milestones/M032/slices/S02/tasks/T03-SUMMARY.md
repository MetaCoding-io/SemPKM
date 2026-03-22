---
id: T03
parent: S02
milestone: M032
provides:
  - M032 architecture design document covering registry, widgets, migration, SPARQL data flow, and key decisions
key_files:
  - .gsd/milestones/M032/M032-DESIGN.md
key_decisions:
  - none (documentation task — records decisions made in T01/T02, does not introduce new ones)
patterns_established:
  - none
observability_surfaces:
  - none (documentation-only task; no runtime behavior changes)
duration: 8m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T03: Write M032 architecture design document

**Wrote M032-DESIGN.md with 8 sections covering the BlockRegistry, all 9 widget types, layout migration, SPARQL data flow, Chart.js integration, and key architectural decisions**

## What Happened

Read the registry implementation (9 BlockTypeSpecs), router.py (render_block with all 9 branches), migration.py (5 legacy layouts), S01 summary, T01/T02 summaries, viewer/builder templates, and block templates to gather accurate details.

Wrote `.gsd/milestones/M032/M032-DESIGN.md` with 8 top-level sections:
1. **Overview** — M032 purpose, what it replaced (CSS Grid → GridStack), two-slice structure
2. **Architecture** — GridStack.js + BlockRegistry + htmx pipeline, dockview event isolation, CDN loading strategy, key files table
3. **Block Registry** — BlockTypeSpec fields table, BLOCK_REGISTRY API table, config validation approach, VALID_BLOCK_TYPES derivation
4. **Widget Inventory** — All 9 block types with type name, category, config keys, rendering approach, default dimensions
5. **Layout Migration** — 5 slot mappings table, lazy migration trigger, idempotency guarantee, unmatched slot handling
6. **Data Flow for SPARQL Widgets** — Execution path (htmx → render_block → _execute_sparql → Jinja2 → HTMLResponse), result extraction logic, Chart.js IIFE init, error handling at logging and UI levels
7. **Key Decisions** — Event isolation, server-side SPARQL, CDN loading strategy, theme integration, lightweight validation, default dimensions rationale
8. **Observability and Diagnostics** — Inspection commands for registry, validation failure paths, DOM error class, backend log format, Chart.js verification

All file paths referenced in the document were verified to exist in the worktree.

## Verification

- `test -f .gsd/milestones/M032/M032-DESIGN.md` → exists
- `grep -c "^## " M032-DESIGN.md` → 8 (≥ 4 required)
- `! grep -qi "TBD\|TODO" M032-DESIGN.md` → no placeholders
- All 9 block type names present in document
- File paths for registry.py, router.py, migration.py, templates, CSS all confirmed present
- All 7 slice-level verification checks pass (44 tests, CDN grep, template files, design doc, 9 types, failure-path validation)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f .gsd/milestones/M032/M032-DESIGN.md` | 0 | ✅ pass | <1s |
| 2 | `grep -c "^## " .gsd/milestones/M032/M032-DESIGN.md` → 8 | 0 | ✅ pass | <1s |
| 3 | `! grep -qi "TBD\|TODO" .gsd/milestones/M032/M032-DESIGN.md` | 0 | ✅ pass | <1s |
| 4 | `cd backend && uv run --extra dev python -m pytest tests/test_block_registry.py -v` — 44 passed | 0 | ✅ pass | 0.05s |
| 5 | `grep -q "chart.js" backend/app/templates/base.html` | 0 | ✅ pass | <1s |
| 6 | `test -f backend/app/templates/browser/blocks/block_stat_card.html` | 0 | ✅ pass | <1s |
| 7 | `test -f backend/app/templates/browser/blocks/block_chart.html` | 0 | ✅ pass | <1s |
| 8 | `python3 -c "...assert len(BLOCK_REGISTRY.all_types()) == 9"` | 0 | ✅ pass | <1s |
| 9 | `python3 -c "...validate_block({'type':'stat-card','config':{'query':42}})"` — ValueError raised | 0 | ✅ pass | <1s |

## Diagnostics

This is a documentation-only task. The design document itself is the inspection surface — read `.gsd/milestones/M032/M032-DESIGN.md` for architecture details, widget inventory, and file locations.

## Deviations

- Added `## Observability Impact` section to T03-PLAN.md per pre-flight requirement.

## Known Issues

None.

## Files Created/Modified

- `.gsd/milestones/M032/M032-DESIGN.md` — Architecture design document: 8 sections, ~480 lines, covering registry API, all 9 block types, layout migration, SPARQL data flow, Chart.js integration, and key decisions
- `.gsd/milestones/M032/slices/S02/tasks/T03-PLAN.md` — Added Observability Impact section (pre-flight fix)
