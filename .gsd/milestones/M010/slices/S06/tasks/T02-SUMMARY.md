---
id: T02
parent: S06
milestone: M010
provides:
  - "User guide Chapter 32 documenting the full RSS Reader app for end users (305 lines)"
  - "README TOC entry for Chapter 32"
  - "Navigation chain: ch.31 → ch.32 → Appendix A (Previous/Next footers updated in 3 files)"
  - "4 glossary entries: Article (RSS), Feed Subscription, OPML, Poll Interval"
key_files:
  - docs/guide/32-rss-reader.md
  - docs/guide/README.md
  - docs/guide/31-api-surface.md
  - docs/guide/appendix-a-environment-variables.md
  - docs/guide/appendix-d-glossary.md
key_decisions:
  - "Numbered as Chapter 32 (not 30 as plan assumed) — chapters 30 (Personas) and 31 (API Surface) already existed"
patterns_established:
  - "Chapter follows ch.29 App Platform style: tables for settings/status, blockquote tips, ASCII art for layout diagram, See Also section"
observability_surfaces:
  - none
duration: 8m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: User guide Chapter 32 and navigation chain updates

**Created 305-line Chapter 32 (RSS Reader) user guide covering install, subscribe, reader UI, star/read, OPML import, workspace integration, settings, and admin monitoring, with TOC entry, navigation chain through 3 files, and 4 glossary terms**

## What Happened

Created `docs/guide/32-rss-reader.md` (305 lines) covering all RSS Reader features in the established chapter style: prerequisites and install, three-pane reader interface with ASCII layout diagram, subscribing by URL and feed discovery, OPML import with category-as-tag preservation, reading/starring/keyboard nav, workspace integration (views, related articles, command palette, custom renderer), feed management, settings table, poll interval configuration, and admin monitoring with status/task-history/permissions tables.

Adapted chapter numbering from the plan's "Chapter 30" to "Chapter 32" since chapters 30 (Workspace Personas) and 31 (API Surface) already exist. Updated the navigation chain across three files: ch.31 footer Next → ch.32, ch.32 footer Previous → ch.31 and Next → Appendix A, Appendix A footer Previous → ch.32. Added Chapter 32 to the README TOC under Part VIII.

Inserted 4 glossary entries in alphabetical order: **Article (RSS)** between App SDK and Argument, **Feed Subscription** between Favorites and FleetingNote, **OPML** between OWL and Paper, **Poll Interval** between PKCE and Property Flip.

## Verification

All must-haves confirmed:

- `wc -l docs/guide/32-rss-reader.md` → 305 lines (≥150 ✅)
- Chapter covers all required features: subscribe, reader UI, star/read, OPML, settings, workspace integration, admin ✅
- README TOC includes "32. [RSS Reader](32-rss-reader.md)" ✅
- Navigation chain: ch.31 → ch.32 → Appendix A, all three footers correct ✅
- 4 glossary entries reference Chapter 32 (≥3 ✅)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `wc -l docs/guide/32-rss-reader.md` | 0 | ✅ 305 lines ≥ 150 | <1s |
| 2 | `grep "32-rss-reader" docs/guide/README.md` | 0 | ✅ present | <1s |
| 3 | `grep "32-rss-reader" docs/guide/31-api-surface.md` | 0 | ✅ present in footer | <1s |
| 4 | `grep "32-rss-reader" docs/guide/appendix-a-environment-variables.md` | 0 | ✅ present in footer | <1s |
| 5 | `grep -c "See \[Chapter 32" docs/guide/appendix-d-glossary.md` | 0 | ✅ 4 entries ≥ 3 | <1s |
| 6 | `grep -c "RSS\|OPML\|Feed Subscription\|Poll Interval" docs/guide/appendix-d-glossary.md` | 0 | ✅ 8 matches ≥ 3 | <1s |

## Diagnostics

Documentation-only task — no runtime signals. Correctness verifiable via:
- `wc -l docs/guide/32-rss-reader.md` for chapter existence
- `grep "32-rss-reader"` across README, ch.31, and Appendix A for navigation chain integrity
- Any Markdown link checker over `docs/guide/` detects broken cross-references

## Deviations

- **Chapter number changed from 30 to 32**: The plan assumed ch.29 was the last numbered chapter. Chapters 30 (Workspace Personas) and 31 (API Surface) already exist, so the RSS Reader was numbered 32. Navigation chain adjusted accordingly — ch.31→ch.32→Appendix A instead of ch.29→ch.30→Appendix A.
- **Updated ch.31 footer instead of ch.29**: Since ch.32 follows ch.31 (not ch.29), the Previous/Next footer update targeted `31-api-surface.md` instead of `29-app-platform.md`.
- **Appendix A Previous link**: Changed from the plan's "Chapter 26: IndieAuth" to "Chapter 32: RSS Reader" — the existing Previous link was already to ch.26, which was stale.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/32-rss-reader.md` — new 305-line Chapter 32 covering the complete RSS Reader user guide
- `docs/guide/README.md` — added Chapter 32 to Part VIII TOC listing
- `docs/guide/31-api-surface.md` — updated footer: Next → Chapter 32
- `docs/guide/appendix-a-environment-variables.md` — updated footer: Previous → Chapter 32
- `docs/guide/appendix-d-glossary.md` — added 4 entries: Article (RSS), Feed Subscription, OPML, Poll Interval
