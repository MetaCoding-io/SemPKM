# Quick Task: Place E2E screenshots into user guide

**Date:** 2026-03-20
**Branch:** gsd/quick/2-please-review-all-screenshots-taken-duri

## What Changed

- Replaced 11 HTML placeholder comments (`<!-- Screenshot: ... -->`) with actual image references across 7 guide chapters
- Added workspace overview hero image to Ch 1 (What is SemPKM)
- Added table/cards/graph view screenshots to Ch 2 (Core Concepts)
- Added login page and workspace screenshots to Ch 3 (Installation)
- Added relations panel, edit form, and graph screenshots to Ch 6 (Edges)
- Added event log and lint panel screenshots to Ch 14 (System Health)
- Added event timeline screenshot to Ch 15 (Event Log)
- Added edit form and table view screenshots to Ch 19 (Creating Mental Models)
- Copied 3 missing dark-mode screenshots from `e2e/screenshots/` to `docs/screenshots/`
- Added README indexes for both `docs/guide/images/` and `docs/screenshots/` with descriptions and chapter cross-references

## Inventory

The e2e test suite produces 20 light-mode + 20 dark-mode screenshots. Before this task:
- All 20 light-mode images were in `docs/guide/images/` but only 21 references existed in guide markdown
- 17 of 20 dark-mode images were in `docs/screenshots/`, 3 were missing
- 18 placeholder comments existed in guide pages waiting for screenshots

After this task:
- 32 image references across 15 guide chapters (was 21 across 10)
- All 20 dark-mode images in `docs/screenshots/`
- 7 remaining placeholder comments are for screenshots not captured by the e2e suite (health page, commands page, SPARQL console, Swagger UI, filter dropdowns)

## Files Modified

- `docs/guide/01-what-is-sempkm.md` — added workspace overview image
- `docs/guide/02-core-concepts.md` — replaced 3 placeholders with view screenshots
- `docs/guide/03-installation-and-setup.md` — replaced 2 placeholders
- `docs/guide/06-edges-and-relationships.md` — replaced 3 placeholders
- `docs/guide/14-system-health-and-debugging.md` — replaced 2 placeholders
- `docs/guide/15-event-log.md` — replaced 1 placeholder
- `docs/guide/19-creating-mental-models.md` — replaced 2 placeholders
- `docs/guide/images/README.md` — new, light-mode screenshot index
- `docs/screenshots/README.md` — new, dark-mode screenshot index
- `docs/screenshots/05-create-note-form-dark.png` — copied from e2e
- `docs/screenshots/11-dark-mode.png` — copied from e2e
- `docs/screenshots/18-object-read-concept-dark.png` — copied from e2e

## Verification

- All 32 image references resolve to existing files (verified via rg + file existence check)
- No broken image paths
- Remaining 7 placeholder comments are for screenshots that don't exist in the e2e set
