---
id: T01
parent: S02
milestone: M040
provides:
  - 9 orphan guide files renamed to unique chapter numbers (39–47)
  - Internal chapter headings updated to match new filenames
key_files:
  - docs/guide/39-mental-model-catalog.md
  - docs/guide/40-rss-reader.md
  - docs/guide/41-google-calendar-sync.md
  - docs/guide/42-todoist-sync.md
  - docs/guide/43-outlook-calendar-sync.md
  - docs/guide/44-caldav-calendar-sync.md
  - docs/guide/45-notion-import.md
  - docs/guide/46-ai-features.md
  - docs/guide/47-asana-sync.md
key_decisions:
  - Renumber orphans starting at 39 (after highest linked chapter 38-hosted-demo) to avoid gaps
patterns_established:
  - none
observability_surfaces:
  - "ls docs/guide/[0-9]*.md | sed 's/.*\\///' | grep -oP '^\\d+' | sort -n | uniq -d — detects duplicate chapter numbers"
duration: 8m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T01: Rename orphan files and assign unique chapter numbers

**Renamed 9 duplicate-numbered guide files to chapters 39–47 and updated internal headings to match.**

## What Happened

Verified all 9 orphan files existed at their original paths with duplicate chapter numbers (7 collisions across numbers 29, 32, 36, 37, 38, 39, 40). Renamed each file to a unique sequential number starting at 39, immediately after the highest linked chapter (38-hosted-demo). Updated the `# Chapter NN:` heading inside each file to match its new number.

Renaming mapping:
- `29-mental-model-catalog.md` → `39-mental-model-catalog.md`
- `32-rss-reader.md` → `40-rss-reader.md`
- `36-google-calendar-sync.md` → `41-google-calendar-sync.md`
- `37-todoist-sync.md` → `42-todoist-sync.md`
- `38-outlook-calendar-sync.md` → `43-outlook-calendar-sync.md`
- `39-caldav-calendar-sync.md` → `44-caldav-calendar-sync.md`
- `39-notion-import.md` → `45-notion-import.md`
- `40-ai-features.md` → `46-ai-features.md`
- `40-asana-sync.md` → `47-asana-sync.md`

## Verification

- Duplicate check (`uniq -d`) returns empty — zero duplicate chapter numbers on disk.
- All 9 renamed files confirmed at new paths.
- All 9 internal `# Chapter NN:` headings verified to match their filename numbers.
- Total numbered guide files: 47 (chapters 01–47, all unique).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `ls docs/guide/[0-9]*.md \| sed 's/.*\///' \| grep -oP '^\d+' \| sort -n \| uniq -d` | 0 (empty output) | ✅ pass | <1s |
| 2 | `ls docs/guide/[0-9]*.md \| wc -l` → 47 | 0 | ✅ pass | <1s |
| 3 | Existence check for all 9 renamed files | 0 | ✅ pass | <1s |
| 4 | Heading-filename consistency check for all 9 files | 0 | ✅ pass | <1s |

## Diagnostics

Static file renames — no runtime diagnostics. Future agents can verify state with:
- `ls docs/guide/[0-9]*.md | sed 's/.*\///' | grep -oP '^\d+' | sort -n | uniq -d` — should return empty
- `head -1 docs/guide/{39..47}-*.md` — shows chapter headings for quick consistency check

## Deviations

Used `mv` instead of `git mv` since the system handles commits. Same end result — git tracks renames from content similarity.

## Known Issues

Cross-references inside renamed files still point to old chapter numbers (e.g., `40-rss-reader.md` references `37-todoist-sync.md` in its prev/next nav). This is explicitly deferred to T03 (cross-reference audit and fix).

## Files Created/Modified

- `docs/guide/39-mental-model-catalog.md` — renamed from 29-*, heading updated to Chapter 39
- `docs/guide/40-rss-reader.md` — renamed from 32-*, heading updated to Chapter 40
- `docs/guide/41-google-calendar-sync.md` — renamed from 36-*, heading updated to Chapter 41
- `docs/guide/42-todoist-sync.md` — renamed from 37-*, heading updated to Chapter 42
- `docs/guide/43-outlook-calendar-sync.md` — renamed from 38-*, heading updated to Chapter 43
- `docs/guide/44-caldav-calendar-sync.md` — renamed from 39-caldav-*, heading updated to Chapter 44
- `docs/guide/45-notion-import.md` — renamed from 39-notion-*, heading updated to Chapter 45
- `docs/guide/46-ai-features.md` — renamed from 40-ai-*, heading updated to Chapter 46
- `docs/guide/47-asana-sync.md` — renamed from 40-asana-*, heading updated to Chapter 47
- `.gsd/milestones/M040/slices/S02/S02-PLAN.md` — added Observability / Diagnostics section
