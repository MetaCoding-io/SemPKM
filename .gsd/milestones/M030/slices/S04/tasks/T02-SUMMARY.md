---
id: T02
parent: S04
milestone: M030
provides:
  - User guide documentation for data quality rules, lint filter system (suppress/dismiss/presets/settings)
  - Glossary entries for Data Quality Rules, Lint Dismissal, Lint Preset, Lint Suppression
key_files:
  - docs/guide/14-system-health-and-debugging.md
  - docs/guide/appendix-d-glossary.md
key_decisions: []
patterns_established: []
observability_surfaces:
  - none (documentation only)
duration: 15m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T02: Extend user guide with data quality rules and lint filter documentation

**Added 5 new sections to Chapter 14 (Data Quality Rules table, Suppressing Rule Types, Dismissing Individual Results, Filter Presets, Lint Settings) and 4 glossary entries to Appendix D**

## What Happened

Extended Chapter 14 ("System Health and Debugging") with 5 new sections inserted between the existing "Using the Dashboard for Data Cleanup" section and the Troubleshooting section. The new sections document:

1. **Data Quality Rules** — severity level explanation (Violation/Warning/Info) and a table of all 11 built-in rules across 4 models (Basic PKM, Zettelkasten+, PPV, Research) with name, severity, model, what it detects, and how to fix.
2. **Suppressing Rule Types** — eye-off button workflow, what happens (badge, still validates internally), how to un-suppress via Lint Settings.
3. **Dismissing Individual Results** — × button workflow, violations cannot be dismissed, per-object scope, persistence across validation runs.
4. **Filter Presets** — save/apply/switch workflow, preset dropdown, "No preset" to clear.
5. **Lint Settings** — management hub with three sections (Suppressions, Dismissals, Presets) and their CRUD operations.

Added 4 new glossary entries to Appendix D in alphabetical order: Data Quality Rules, Lint Dismissal, Lint Preset, Lint Suppression. Updated the existing Lint Dashboard entry to mention filtering capabilities.

## Verification

- `wc -l docs/guide/14-system-health-and-debugging.md` → 568 lines (target: >550, was 429) ✓
- `grep -c` for glossary terms → 4 matches (target: ≥4) ✓
- All 5 section headings present at correct line numbers (396, 430, 454, 478, 501) ✓
- Glossary entries verified in correct alphabetical order ✓

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `wc -l docs/guide/14-system-health-and-debugging.md` | 0 | ✅ pass (568 lines > 550) | <1s |
| 2 | `grep -c "Lint Suppression\|Lint Dismissal\|Lint Preset\|Data Quality" docs/guide/appendix-d-glossary.md` | 0 | ✅ pass (4 ≥ 4) | <1s |
| 3 | `grep -n "### Data Quality\|### Suppressing\|### Dismissing\|### Filter Presets\|### Lint Settings" docs/guide/14-system-health-and-debugging.md` | 0 | ✅ pass (5 headings found) | <1s |

## Diagnostics

None — documentation-only task with no runtime artifacts.

## Deviations

The task plan listed 10 rules but the table has 11 rows because EmptyBodyValidation appears in both Basic PKM and Zettelkasten+ models (separate implementations for different object types). This matches the S02 implementation.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/14-system-health-and-debugging.md` — Added 5 new sections (139 lines) documenting data quality rules and lint filter system
- `docs/guide/appendix-d-glossary.md` — Added 4 new entries (Data Quality Rules, Lint Dismissal, Lint Preset, Lint Suppression) and updated Lint Dashboard entry
