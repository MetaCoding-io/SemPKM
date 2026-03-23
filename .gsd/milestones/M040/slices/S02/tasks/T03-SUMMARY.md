---
id: T03
parent: S02
milestone: M040
provides:
  - All markdown cross-references between guide chapters resolve to existing files
  - Orphan files' prev/next navigation and "See Also" links updated to new chapter numbers
  - Glossary references to old 29-mental-model-catalog updated to 39-mental-model-catalog
key_files:
  - docs/guide/appendix-d-glossary.md
  - docs/guide/30-personas.md
  - docs/guide/41-google-calendar-sync.md
  - docs/guide/42-todoist-sync.md
  - docs/guide/43-outlook-calendar-sync.md
  - docs/guide/44-caldav-calendar-sync.md
  - docs/guide/45-notion-import.md
  - docs/guide/46-ai-features.md
  - docs/guide/47-asana-sync.md
key_decisions:
  - none
patterns_established:
  - none
observability_surfaces:
  - "grep -rnoP '\\]\\(\\K[^)]+\\.md[^)]*' docs/guide/*.md | while IFS=: read -r s l t; do b=\"${t%%#*}\"; [ -f \"docs/guide/$b\" ] || echo \"BROKEN: $s:$l -> $b\"; done — returns empty when all cross-references resolve"
duration: 6m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T03: Audit and fix cross-references

**Fixed 27 broken markdown cross-references across 9 guide files caused by T01 renumbering.**

## What Happened

Ran a cross-reference audit extracting all markdown links to `.md` files from every guide chapter and checking each target exists on disk. Found 27 broken links in 9 files, falling into two categories:

1. **Glossary and personas referencing old `29-mental-model-catalog.md`** (16 occurrences in `appendix-d-glossary.md` and `30-personas.md`) — updated all to `39-mental-model-catalog.md` with correct "Chapter 39" text.

2. **Orphan files' prev/next navigation using pre-renumber filenames** (11 occurrences across `41-google-calendar-sync.md` through `47-asana-sync.md`) — updated each link to point to the correct new chapter number (e.g., `37-todoist-sync.md` → `42-todoist-sync.md`).

Also verified that all 9 renamed files' `# Chapter NN:` headings match their filename numbers (confirmed by T01, re-verified here).

## Verification

- Cross-reference audit returns zero broken links
- No duplicate chapter numbers on disk (47 unique)
- 47 files match 47 README entries
- index.html data-file count is 57 (47 chapters + 6 appendices + 4 script refs)
- All "Chapter NN" text references in orphan files point to files that exist

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | Cross-reference link audit (grep + file existence check) | 0 (empty) | ✅ pass | <1s |
| 2 | `ls docs/guide/[0-9]*.md \| sed ... \| uniq -d` (duplicate check) | 0 (empty) | ✅ pass | <1s |
| 3 | File count (47) vs README entries (47) | 0 | ✅ pass | <1s |
| 4 | `grep -c "data-file" docs/guide/index.html` → 57 | 0 | ✅ pass | <1s |
| 5 | Heading-filename consistency for chapters 39–47 | 0 | ✅ pass | <1s |

## Diagnostics

Static documentation files — no runtime diagnostics. Verify cross-reference integrity with:
- `grep -rnoP '\]\(\K[^)]+\.md[^)]*' docs/guide/*.md | while IFS=: read -r s l t; do b="${t%%#*}"; [ -f "docs/guide/$b" ] || echo "BROKEN: $s:$l -> $b"; done` — should return empty

## Deviations

None. The initial broken-link detection script from the slice plan (using `while read line; do ... grep -oP '\]\(\K[^)]+' ... done`) had a bug: it only extracted the first link per line when lines contained multiple links, producing false positives. Rewrote the check to use `grep -rnoP` for per-match extraction, which correctly identifies only genuinely broken links.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/appendix-d-glossary.md` — Updated 15 references from `29-mental-model-catalog.md` to `39-mental-model-catalog.md`
- `docs/guide/30-personas.md` — Updated 1 prev/next reference from `29-mental-model-catalog.md` to `39-mental-model-catalog.md`
- `docs/guide/41-google-calendar-sync.md` — Fixed prev/next nav: `37-todoist-sync.md` → `42-todoist-sync.md`
- `docs/guide/42-todoist-sync.md` — Fixed prev/next nav: `36-google-calendar-sync.md` → `41-google-calendar-sync.md`, `38-outlook-calendar-sync.md` → `43-outlook-calendar-sync.md`
- `docs/guide/43-outlook-calendar-sync.md` — Fixed prev/next nav: `37-todoist-sync.md` → `42-todoist-sync.md`, `39-caldav-calendar-sync.md` → `44-caldav-calendar-sync.md`
- `docs/guide/44-caldav-calendar-sync.md` — Fixed prev/next nav: `38-outlook-calendar-sync.md` → `43-outlook-calendar-sync.md`, `40-asana-sync.md` → `47-asana-sync.md`
- `docs/guide/45-notion-import.md` — Fixed next nav: `40-ai-features.md` → `46-ai-features.md`
- `docs/guide/46-ai-features.md` — Fixed prev nav: `39-notion-import.md` → `45-notion-import.md`
- `docs/guide/47-asana-sync.md` — Fixed "See Also" reference: `37-todoist-sync.md` → `42-todoist-sync.md`; Fixed prev nav: `39-caldav-calendar-sync.md` → `44-caldav-calendar-sync.md`
