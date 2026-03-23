---
id: S02
milestone: M040
title: "Orphan Chapter Integration & Renumbering"
status: done
completed_at: 2026-03-22
tasks_completed: 3
tasks_total: 3
---

# S02: Orphan Chapter Integration & Renumbering

**Integrated 9 orphaned guide chapters into the user guide navigation with unique chapter numbers and zero broken cross-references.**

## What Was Delivered

Nine guide `.md` files that had duplicate chapter numbers (collisions at numbers 29, 32, 36, 37, 38, 39, and 40) were renumbered to chapters 39–47 and linked into all three navigation surfaces (README.md, index.html, guide.html). All 27 internal cross-references broken by the renumbering were fixed.

### T01: File Renaming (8m)

Renamed 9 orphan files to unique sequential chapter numbers starting at 39 (immediately after the highest existing linked chapter, 38-hosted-demo):

| Old File | New File |
|----------|----------|
| 29-mental-model-catalog.md | 39-mental-model-catalog.md |
| 32-rss-reader.md | 40-rss-reader.md |
| 36-google-calendar-sync.md | 41-google-calendar-sync.md |
| 37-todoist-sync.md | 42-todoist-sync.md |
| 38-outlook-calendar-sync.md | 43-outlook-calendar-sync.md |
| 39-caldav-calendar-sync.md | 44-caldav-calendar-sync.md |
| 39-notion-import.md | 45-notion-import.md |
| 40-ai-features.md | 46-ai-features.md |
| 40-asana-sync.md | 47-asana-sync.md |

Updated each file's internal `# Chapter NN:` heading to match its new number.

### T02: Navigation File Updates (8m)

Added all 9 chapters to README.md, index.html, and guide.html with topical grouping:
- **Part III:** 39-mental-model-catalog (with other model chapters)
- **Part VIII:** 45-notion-import (with import tools), 40-rss-reader (with app platform), 46-ai-features (with context overlay), 41–44 sync apps + 47-asana-sync (with other sync apps)

Removed stale `29-mental-model-catalog` entries from all three files. guide.html entries use appropriate Lucide icons.

### T03: Cross-Reference Audit & Fix (6m)

Fixed 27 broken markdown cross-references across 9 files:
- 16 references to old `29-mental-model-catalog.md` updated (in glossary and personas chapter)
- 11 prev/next navigation links in sync app chapters updated to new chapter numbers

## Final State

- **47 numbered guide chapters** on disk, all with unique chapter numbers
- **47 matching entries** in README.md
- **57 data-file entries** in index.html (47 chapters + appendices + scripts)
- **53 hx-get entries** in guide.html (47 chapters + appendices)
- **Zero broken cross-references** between guide chapters
- **Zero duplicate chapter numbers**

## Verification Results

| Check | Result |
|-------|--------|
| `uniq -d` duplicate chapter numbers | ✅ empty (zero duplicates) |
| Disk file count vs README entry count | ✅ 47 = 47 |
| Orphan slugs in README.md | ✅ 9 matches |
| Orphan slugs in index.html | ✅ 9 matches |
| Orphan slugs in guide.html | ✅ 9 matches |
| Broken markdown cross-references | ✅ zero |

## What the Next Slice Should Know

- The guide now has 47 numbered chapters (01–47) plus 6 appendices (A–F). The next available chapter number is **48**.
- All three navigation files (README.md, index.html, guide.html) must be updated together per the existing Knowledge entry about "User guide has THREE files that must stay in sync."
- The cross-reference audit script from the slice plan had a bug (only extracted the first link per line). The corrected version uses `grep -rnoP '\]\(\K[^)]+\.md[^)]*'` for per-match extraction — use this for future audits.

## Files Modified

- `docs/guide/39-mental-model-catalog.md` through `docs/guide/47-asana-sync.md` — renamed + headings + cross-refs
- `docs/guide/README.md` — 9 entries added, 1 stale removed
- `docs/guide/index.html` — 9 entries added, 1 stale removed
- `backend/app/templates/guide.html` — 9 entries added, 1 stale removed
- `docs/guide/appendix-d-glossary.md` — 15 cross-references updated
- `docs/guide/30-personas.md` — 1 cross-reference updated
