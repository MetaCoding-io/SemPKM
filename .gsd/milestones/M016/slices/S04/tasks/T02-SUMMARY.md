---
id: T02
parent: S04
milestone: M016
provides:
  - User guide Chapter 34 documenting full Linear Sync workflow
  - README TOC entry for Chapter 34
  - Navigation chain Ch 33 → Ch 34 → Appendix A
  - Four glossary entries (Bidirectional Sync, Linear Sync, Pull Sync, Push Sync)
key_files:
  - docs/guide/34-linear-sync.md
  - docs/guide/README.md
  - docs/guide/33-context-overlay.md
  - docs/guide/appendix-d-glossary.md
key_decisions: []
patterns_established: []
observability_surfaces:
  - "test -f docs/guide/34-linear-sync.md && echo exists — confirms chapter presence"
  - "grep -c '34-linear-sync' docs/guide/README.md — verifies TOC entry"
  - "grep 'Chapter 34' docs/guide/33-context-overlay.md — verifies nav chain"
duration: 15m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: User guide Chapter 34 — Linear Sync

**Wrote complete Chapter 34 covering Linear Sync app installation, API key setup, team selection, sync configuration, field mapping, push sync, admin monitoring, and troubleshooting — plus README TOC, nav chain, and glossary updates**

## What Happened

Wrote `docs/guide/34-linear-sync.md` (~250 lines) with all 12 sections specified in the plan. Used the actual field mapper source code (`field_mapper.py`) as the source of truth for the mapping tables — the plan's mapping table had some inaccuracies (e.g., priority 1 maps to "critical" not "urgent", and additional fields like `completedDate`, `effort`, and `externalUuid` exist in the code). Documented all three mapping sub-tables (status, priority, effort) with the real values from the code.

Updated the README TOC with the Chapter 34 entry. Updated Chapter 33's navigation footer to point to Chapter 34. Added four glossary entries in correct alphabetical positions (Bidirectional Sync before Block, Linear Sync before Lint Dashboard, Pull Sync and Push Sync before RBox).

Also fixed the pre-flight observability gap by adding an `## Observability Impact` section to T02-PLAN.md.

## Verification

- `test -f docs/guide/34-linear-sync.md && echo "exists"` — exists ✅
- `grep "34-linear-sync" docs/guide/README.md` — match found ✅
- `grep "Chapter 34" docs/guide/33-context-overlay.md` — match in nav footer ✅
- `grep "Appendix A" docs/guide/34-linear-sync.md` — match in nav footer and See Also ✅
- `grep -c "Linear Sync\|Pull Sync\|Push Sync\|Bidirectional Sync" docs/guide/appendix-d-glossary.md` — returns 8 (≥ 4) ✅
- Chapter has 12 `##`-level sections covering all required topics ✅
- Field mapping table has 12 rows (main table) plus sub-tables for status (5), priority (5), effort (7) ✅

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f docs/guide/34-linear-sync.md && echo "exists"` | 0 | ✅ pass | <1s |
| 2 | `grep "34-linear-sync" docs/guide/README.md` | 0 | ✅ pass | <1s |
| 3 | `grep "Chapter 34" docs/guide/33-context-overlay.md` | 0 | ✅ pass | <1s |
| 4 | `grep "Appendix A" docs/guide/34-linear-sync.md` | 0 | ✅ pass | <1s |
| 5 | `grep -c "Linear Sync\|Pull Sync\|Push Sync\|Bidirectional Sync" docs/guide/appendix-d-glossary.md` | 0 | ✅ pass (8) | <1s |
| 6 | `grep '^## ' docs/guide/34-linear-sync.md \| wc -l` | 0 | ✅ pass (12 sections) | <1s |

Slice-level verification results (T02 is final task):
- ⏳ `npx playwright test e2e/tests/31-linear-sync/linear-sync.spec.ts` — requires Docker stack (T01 deliverable, not re-run here)
- ✅ `python3 -c "import ast; ast.parse(open('e2e/mock-linear-api/server.py').read())"` — syntax ok
- ✅ `grep "34-linear-sync" docs/guide/README.md` — hit
- ✅ `grep "Chapter 34" docs/guide/33-context-overlay.md` — hit in nav footer
- ✅ `grep "Linear Sync" docs/guide/appendix-d-glossary.md` — 4 glossary entries found

## Diagnostics

Documentation-only task. Verify link integrity by running the grep commands in the Verification Evidence table above.

## Deviations

- **Field mapping table expanded beyond plan spec.** The plan's mapping table had 9 rows with some inaccurate values (priority 1→"urgent" vs actual "critical"). Used the actual `field_mapper.py` source code to produce accurate tables with 12 rows in the main table plus separate sub-tables for status, priority, and effort mappings. This is more accurate and complete than the plan specified.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/34-linear-sync.md` — New: complete Chapter 34 with 12 sections (~250 lines)
- `docs/guide/README.md` — Added Chapter 34 TOC entry
- `docs/guide/33-context-overlay.md` — Updated nav footer to point to Chapter 34
- `docs/guide/appendix-d-glossary.md` — Added 4 glossary entries (Bidirectional Sync, Linear Sync, Pull Sync, Push Sync)
- `.gsd/milestones/M016/slices/S04/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
