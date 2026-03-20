---
id: T03
parent: S04
milestone: M024
provides:
  - Chapter 37 user guide (Monday.com Sync) with column mapping walkthrough, label mapping, LoopGuard docs
  - Three-file navigation sync (README.md TOC, index.html sidebar, guide.html in-app)
  - Appendix A MONDAY_API_URL entry
  - Glossary entries for Column Mapping, LoopGuard, Monday.com Sync
key_files:
  - docs/guide/37-monday-sync.md
  - docs/guide/README.md
  - docs/guide/index.html
  - backend/app/templates/guide.html
  - docs/guide/appendix-a-environment-variables.md
  - docs/guide/appendix-d-glossary.md
  - docs/guide/36-jira-sync.md
key_decisions:
  - Used columns-3 Lucide icon for Monday.com guide.html button (represents board/column nature)
patterns_established:
  - Glossary entries for sync apps follow pattern: bold term, one-sentence summary, feature highlights, "See Chapter N" link
observability_surfaces:
  - none (documentation-only task)
duration: 15m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T03: User guide Chapter 37 + docs file updates

**Created 393-line Monday.com Sync user guide (Chapter 37) with column mapping walkthrough, label mapping, LoopGuard docs, and updated all navigation files, appendix, and glossary.**

## What Happened

Wrote the complete Monday.com Sync user guide at `docs/guide/37-monday-sync.md` (393 lines), cloning Chapter 36's structure but replacing Jira-specific content with Monday.com's unique features:

- **Column Mapping** — full walkthrough with worked example showing how type-filtered dropdowns map board columns to bpkm properties, plus column type compatibility table
- **Status/Priority Label Mapping** — explains how custom Monday.com labels (e.g., "Working on it") map to bpkm enum values, with example tables
- **LoopGuard Echo Prevention** — documents the in-memory TTL cache mechanism that prevents infinite push→pull loops in bidirectional mode
- **Groups/Subitems/Dependencies** — three dedicated sections for Monday.com structural features (taskGroup, parentTask, dependsOn edges)
- **Field Mapping Table** — all 13 column types with SemPKM property, transform, and direction
- **Simplified auth** — single API token (no email/site URL like Jira)

Updated 6 additional files:
1. `docs/guide/README.md` — added Chapter 37 to TOC
2. `docs/guide/index.html` — added Chapter 37 to sidebar
3. `backend/app/templates/guide.html` — added Chapter 37 button with `columns-3` icon
4. `docs/guide/appendix-a-environment-variables.md` — added `MONDAY_API_URL` row
5. `docs/guide/appendix-d-glossary.md` — added 3 entries (Column Mapping, LoopGuard, Monday.com Sync) in alphabetical order
6. `docs/guide/36-jira-sync.md` — updated navigation footer: Ch 36 → Ch 37 (was Ch 36 → Appendix A)

## Verification

All task-level and slice-level checks passed:

- Chapter 37 file exists at 393 lines (within 300–400 target)
- All 3 navigation files reference `37-monday-sync` (README.md, index.html, guide.html)
- Appendix A contains `MONDAY_API_URL` entry
- Glossary contains all 3 new bold heading entries
- Ch 36 navigation footer updated to point to Ch 37
- Mock selftest passes 12/12 checks (slice regression)
- Docker compose test config validates cleanly

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f docs/guide/37-monday-sync.md` | 0 | ✅ pass | <1s |
| 2 | `wc -l docs/guide/37-monday-sync.md` (393 lines) | 0 | ✅ pass | <1s |
| 3 | `grep -c "37-monday-sync" docs/guide/README.md docs/guide/index.html backend/app/templates/guide.html` (all ≥1) | 0 | ✅ pass | <1s |
| 4 | `grep -c "MONDAY_API_URL" docs/guide/appendix-a-environment-variables.md` (1) | 0 | ✅ pass | <1s |
| 5 | `grep -c "^\*\*Column Mapping\*\*\|^\*\*LoopGuard\*\*\|^\*\*Monday.com Sync\*\*" docs/guide/appendix-d-glossary.md` (3) | 0 | ✅ pass | <1s |
| 6 | `grep -c "37-monday-sync" docs/guide/36-jira-sync.md` (1) | 0 | ✅ pass | <1s |
| 7 | `python3 e2e/mock-monday-api/server.py --selftest` (12 passed, 0 failed) | 0 | ✅ pass | 1s |
| 8 | `docker compose -f docker-compose.test.yml config --quiet` | 0 | ✅ pass | <1s |

## Diagnostics

This is a documentation-only task. No runtime artifacts to inspect. Verify content by:
- Reading `docs/guide/37-monday-sync.md` directly
- Checking navigation consistency: `grep -c "37-monday-sync" docs/guide/README.md docs/guide/index.html backend/app/templates/guide.html`
- Glossary alphabetical order: `grep -n "^\*\*" docs/guide/appendix-d-glossary.md` — Column Mapping, LoopGuard, and Monday.com Sync entries should appear in correct alphabetical positions

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/37-monday-sync.md` — New: complete Monday.com Sync user guide (393 lines)
- `docs/guide/README.md` — Added Chapter 37 to TOC
- `docs/guide/index.html` — Added Chapter 37 to sidebar navigation
- `backend/app/templates/guide.html` — Added Chapter 37 button with columns-3 Lucide icon
- `docs/guide/appendix-a-environment-variables.md` — Added MONDAY_API_URL row to App-Specific Variables table
- `docs/guide/appendix-d-glossary.md` — Added 3 entries: Column Mapping, LoopGuard, Monday.com Sync
- `docs/guide/36-jira-sync.md` — Updated navigation footer to point to Ch 37 instead of Appendix A
- `.gsd/milestones/M024/slices/S04/tasks/T03-PLAN.md` — Added Observability Impact section (pre-flight fix)
