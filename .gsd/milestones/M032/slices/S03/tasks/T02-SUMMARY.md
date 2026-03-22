---
id: T02
parent: S03
milestone: M032
provides:
  - Updated user guide chapter 28 documenting all 10 dashboard block types, GridStack builder, data widgets, and form groups
key_files:
  - docs/guide/28-dashboards-and-workflows.md
key_decisions:
  - Kept legacy CSS Grid layout note as a compatibility callout rather than removing all mention of it
patterns_established: []
observability_surfaces:
  - "none — docs-only change; staleness detectable by comparing BLOCK_REGISTRY types against guide block table"
duration: 12m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T02: Update user guide chapter 28 with new block types and GridStack builder

**Rewrote chapter 28 with all 10 block types (added stat-card, chart, heading, form-group), GridStack drag-drop layout, Data Widgets subsection with SPARQL examples, and Form Groups subsection with slot/edge concepts.**

## What Happened

Rewrote `docs/guide/28-dashboards-and-workflows.md` with the following changes:

1. **Block Types table:** Expanded from 6 to 10 types. Added stat-card, chart, heading, and form-group with descriptions matching BLOCK_REGISTRY. Updated markdown (now mentions marked.js/DOMPurify) and sparql-result (now describes live query execution).

2. **GridStack Layout section:** Replaced the Layout Templates section (5 CSS Grid templates) with GridStack drag-and-drop description covering 12-column grid, drag-to-reposition, resize by dragging, and default dimensions per block type. Added a backwards-compatibility note for legacy CSS Grid dashboards.

3. **Data Widgets subsection:** New section after Block Types documenting stat-card (COUNT query + label/icon/color config), chart (label/value query + chart type selection), and sparql-result (any SELECT query). Each includes a complete SPARQL example query.

4. **Form Groups subsection:** New section explaining slots (SHACL sub-forms per target class), edges (source→target + predicate), batch creation via Command API, and slot-based IRI resolution. Includes a concrete Note+Task example.

5. **Dashboard vs. Workflow table:** Updated from "6 block types" to "10 block types" with expanded content list.

6. **Creating a Dashboard:** Rewritten for GridStack workflow (palette-based block selection, drag to position) instead of slot-based assignment.

All three guide index files (README.md, index.html, guide.html) already had chapter 28 — no index changes needed.

## Verification

All task-level and slice-level checks pass:

- File exists at `docs/guide/28-dashboards-and-workflows.md`
- All 4 new block type names present: stat-card, chart, heading, form-group
- GridStack mentioned in layout section
- 25 table rows (pipe-lines) — well above ≥12 threshold
- 19 occurrences of new block type names — well above ≥4 threshold
- Navigation links to chapters 27 and 29 preserved

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f docs/guide/28-dashboards-and-workflows.md` | 0 | ✅ pass | <1s |
| 2 | `grep -q 'stat-card' docs/guide/28-dashboards-and-workflows.md` | 0 | ✅ pass | <1s |
| 3 | `grep -q 'form-group' docs/guide/28-dashboards-and-workflows.md` | 0 | ✅ pass | <1s |
| 4 | `grep -q 'chart' docs/guide/28-dashboards-and-workflows.md` | 0 | ✅ pass | <1s |
| 5 | `grep -q 'heading' docs/guide/28-dashboards-and-workflows.md` | 0 | ✅ pass | <1s |
| 6 | `grep -q 'GridStack' docs/guide/28-dashboards-and-workflows.md` | 0 | ✅ pass | <1s |
| 7 | `grep -c '^|' docs/guide/28-dashboards-and-workflows.md` → 25 | 0 | ✅ pass (≥12) | <1s |
| 8 | `grep -c 'stat-card\|chart\|heading\|form-group' docs/guide/28-dashboards-and-workflows.md` → 19 | 0 | ✅ pass (≥4) | <1s |

## Diagnostics

- **Staleness check:** Compare `BLOCK_REGISTRY` types in `backend/app/dashboard/registry.py` against the Block Types table in the guide. If a new type is registered but not in the table, the docs are stale.
- **No runtime signals** — this is a documentation-only change.

## Deviations

- Added backwards-compatibility note about legacy CSS Grid layouts (not in plan, but necessary for existing users whose dashboards use the old layout system).
- Expanded cross-view context example to reference stat-cards (plan didn't specify, but it demonstrates the new block type in context).

## Known Issues

None.

## Files Created/Modified

- `docs/guide/28-dashboards-and-workflows.md` — Rewrote chapter with 10 block types, GridStack layout, Data Widgets, and Form Groups
- `.gsd/milestones/M032/slices/S03/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
