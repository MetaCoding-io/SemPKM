---
id: T02
parent: S02
milestone: M040
provides:
  - All 9 orphan chapters (39–47) linked in README.md, index.html, and guide.html
  - Stale duplicate 29-mental-model-catalog entries removed from all 3 files
key_files:
  - docs/guide/README.md
  - docs/guide/index.html
  - backend/app/templates/guide.html
key_decisions:
  - Placed Mental Model Catalog (39) in Part III with other model chapters; all remaining orphans in Part VIII grouped by topic (import tools near onboarding, sync apps after existing syncs, RSS Reader near App Platform, AI Features near Context Overlay)
patterns_established:
  - none
observability_surfaces:
  - "grep -c 'mental-model-catalog\\|rss-reader\\|google-calendar\\|todoist\\|outlook-calendar\\|caldav\\|notion-import\\|ai-features\\|asana' docs/guide/README.md — should return 9"
  - "Same grep on index.html and guide.html — should each return 9"
duration: 8m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T02: Add orphan entries to all 3 navigation files

**Added 9 orphan guide chapters (39–47) to README.md, index.html, and guide.html with correct Part placement, and removed stale duplicate 29-mental-model-catalog entries.**

## What Happened

Added all 9 newly-numbered chapters from T01 to each of the three navigation files. Placement followed topical grouping:

- **Part III (Mental Models):** 39-mental-model-catalog after chapter 10
- **Part VIII (Discovery & Integration):**
  - 45-notion-import after 24-obsidian-onboarding (import tools together)
  - 40-rss-reader after 29-app-platform (app-related)
  - 46-ai-features after 33-context-overlay (AI-related)
  - 41–44 sync apps + 47-asana-sync after 37-monday-sync (all syncs together)

Also removed the stale `29-mental-model-catalog` entry (which pointed to the old pre-rename filename) from all three files.

For guide.html, chose appropriate Lucide icons: `library` (catalog), `rss` (reader), `file-input` (notion import), `sparkles` (AI), `calendar`/`check-square`/`mail`/`calendar-clock`/`list-checks` (sync apps).

## Verification

- Zero duplicate chapter numbers on disk
- 47 `.md` files match 47 numbered README entries
- All 9 orphan slugs found in README.md, index.html, and guide.html (9 matches each)
- Slice-level checks all pass

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `ls docs/guide/[0-9]*.md \| sed 's/.*\///' \| grep -oP '^\d+' \| sort -n \| uniq -d` | 0 (empty) | ✅ pass | <1s |
| 2 | `ls docs/guide/[0-9]*.md \| wc -l` → 47 vs README entries → 47 | 0 | ✅ pass | <1s |
| 3 | `grep -c "orphan slugs" README.md` → 9 | 0 | ✅ pass | <1s |
| 4 | `grep -c "orphan slugs" index.html` → 9 | 0 | ✅ pass | <1s |
| 5 | `grep -c "orphan slugs" guide.html` → 9 | 0 | ✅ pass | <1s |
| 6 | `grep -c 'data-file' index.html` → 53 (47 chapters + 6 appendices) | 0 | ✅ pass | <1s |

## Diagnostics

Static documentation files — no runtime diagnostics. Verify linkage state with:
- `grep -c "mental-model-catalog\|rss-reader\|google-calendar\|todoist\|outlook-calendar\|caldav\|notion-import\|ai-features\|asana" docs/guide/README.md docs/guide/index.html backend/app/templates/guide.html` — should show 9 for each file

## Deviations

None. All 9 entries placed in the planned Part sections.

## Known Issues

- Cross-references inside the orphan `.md` files still use old chapter numbers (e.g., prev/next links). This is explicitly deferred to T03.

## Files Created/Modified

- `docs/guide/README.md` — Added 9 chapter entries, removed stale 29-mental-model-catalog
- `docs/guide/index.html` — Added 9 sidebar entries, removed stale 29-mental-model-catalog
- `backend/app/templates/guide.html` — Added 9 button entries, removed stale 29-mental-model-catalog
