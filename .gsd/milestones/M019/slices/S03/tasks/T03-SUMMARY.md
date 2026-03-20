---
id: T03
parent: S03
milestone: M019
provides:
  - Chapter 37 user guide for Todoist Sync with field mapping tables, priority inversion, close/reopen pattern, troubleshooting
  - README TOC entry for Chapter 37
  - Glossary entry for Todoist Sync
  - Appendix A entry for TODOIST_API_URL env var
  - Navigation chain Ch 36 → Ch 37 → Appendix A
key_files:
  - docs/guide/37-todoist-sync.md
  - docs/guide/README.md
  - docs/guide/appendix-d-glossary.md
  - docs/guide/appendix-a-environment-variables.md
  - docs/guide/36-google-calendar-sync.md
key_decisions: []
patterns_established: []
observability_surfaces:
  - none (documentation only — no runtime changes)
duration: 12m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T03: Write Chapter 37 user guide and update documentation chain

**Added Chapter 37 (Todoist Sync) user guide with priority inversion table, close/reopen endpoint documentation, status mapping, field mapping tables, and troubleshooting — updated README TOC, glossary, appendix A, and Ch 36 navigation footer**

## What Happened

Created `docs/guide/37-todoist-sync.md` (~290 lines, 37 `##` sections) following Ch. 35 (GitHub Sync) as the structural reference. Key documentation sections:

- **Priority Mapping** table with all 4 levels mapped bidirectionally, including explanation of Todoist's inverted API scale (API `priority: 4` = UI "Priority 1" = SemPKM `critical`).
- **Status Mapping** with separate pull (is_completed → todo/done) and push (taskStatus → close/reopen endpoint) tables.
- **Close/Reopen Pattern** section explaining Todoist's dedicated `POST /tasks/{id}/close` and `POST /tasks/{id}/reopen` endpoints — distinct from PATCH-based status in GitHub/Linear sync.
- **Due Dates** table covering date-only, datetime, and missing due date cases.
- **Labels**, **External Link**, **Sync Metadata**, **Loop Prevention** sections.
- **Push Sync** section with supported push fields table (status, title, priority, labels, due date).
- **Troubleshooting** with 5 subsections covering common failure modes.

Updated 4 cross-reference files: README TOC (line 37 added), glossary (Todoist Sync entry under T), appendix A (TODOIST_API_URL row after GOOGLE_TOKEN_URL), Ch 36 navigation footer (Next → Ch 37 instead of Appendix A).

## Verification

All task-level and slice-level verification checks pass:

- `rg "37-todoist" docs/guide/` — hits in README.md, appendix-d-glossary.md, 36-google-calendar-sync.md
- `rg "Todoist Sync" docs/guide/appendix-d-glossary.md` — glossary entry present
- `rg "TODOIST_API_URL" docs/guide/appendix-a-environment-variables.md` — env var documented
- `grep -c "^##" docs/guide/37-todoist-sync.md` — 37 sections (well above minimum 12)
- Navigation chain verified: Ch 36 → Ch 37 → Appendix A

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg "37-todoist" docs/guide/` | 0 | ✅ pass — 3 files (README, glossary, Ch 36) | <1s |
| 2 | `rg "Todoist Sync" docs/guide/appendix-d-glossary.md` | 0 | ✅ pass — entry present | <1s |
| 3 | `rg "TODOIST_API_URL" docs/guide/appendix-a-environment-variables.md` | 0 | ✅ pass — row present | <1s |
| 4 | `grep -c "^##" docs/guide/37-todoist-sync.md` | 0 | ✅ pass — 37 (≥12) | <1s |
| 5 | `rg "os.environ" apps/todoist-sync/services/todoist_client.py apps/todoist-sync/services/auth.py` | 0 | ✅ pass — both files use env var override | <1s |
| 6 | `rg "hx-(post\|get)=" apps/todoist-sync/frontend/templates/ \| grep -v "/app/todoist-sync/"` | 1 | ✅ pass — empty (all htmx URLs prefixed) | <1s |

## Diagnostics

Documentation-only task — no runtime diagnostics. Verify cross-references with `rg "37-todoist" docs/guide/`. Verify section completeness with `grep -c "^##" docs/guide/37-todoist-sync.md`.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/37-todoist-sync.md` — New Chapter 37 user guide (~290 lines) with field mapping tables, priority inversion, close/reopen pattern, troubleshooting
- `docs/guide/README.md` — Added line 37 to TOC
- `docs/guide/appendix-d-glossary.md` — Added "Todoist Sync" entry (alphabetical under T)
- `docs/guide/appendix-a-environment-variables.md` — Added `TODOIST_API_URL` row after `GOOGLE_TOKEN_URL`
- `docs/guide/36-google-calendar-sync.md` — Updated navigation footer (Next → Ch 37)
- `.gsd/milestones/M019/slices/S03/tasks/T03-PLAN.md` — Added Observability Impact section (pre-flight fix)
