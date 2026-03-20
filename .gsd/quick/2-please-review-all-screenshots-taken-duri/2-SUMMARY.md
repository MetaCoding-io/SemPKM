# Quick Task: Place e2e screenshots into user guide

**Date:** 2026-03-20
**Branch:** gsd/quick/2-please-review-all-screenshots-taken-duri

## What Changed

### Pass 1: Place existing e2e screenshots (commit 3f09d883)
- Replaced 11 HTML placeholder comments with actual image references across 7 guide chapters
- Added workspace overview hero image to Ch 1 (What is SemPKM)
- Added table/cards/graph view screenshots to Ch 2 (Core Concepts)
- Added login page and workspace screenshots to Ch 3 (Installation)
- Added relations panel, edit form, and graph screenshots to Ch 6 (Edges)
- Added event log and lint panel screenshots to Ch 14 (System Health)
- Added event timeline screenshot to Ch 15 (Event Log)
- Added edit form and table view screenshots to Ch 19 (Creating Mental Models)
- Copied 3 missing dark-mode screenshots from `e2e/screenshots/` to `docs/screenshots/`
- Added README indexes for both `docs/guide/images/` and `docs/screenshots/`

### Pass 2: Audit docs for missing screenshots, capture new ones (commit b4ee2ba7)
- Audited all 36 guide chapters for screenshot needs
- Captured 7 new screenshots from running dev stack via headless Playwright:
  - SPARQL Console (Ch 21)
  - VFS File Browser (Ch 23)
  - Obsidian Import wizard (Ch 24)
  - Spatial Canvas (Ch 27)
  - Dashboard builder (Ch 28)
  - Workflow builder (Ch 28)
  - Command palette / Personas (Ch 30)
- Ran e2e guide-capture test suite, capturing 5 additional reference screenshots
- Replaced 2 more placeholder comments (Ch 14 SPARQL console, Ch 18)

### Final state
- **44 image references** across **23 chapters** (was 21 across 10)
- **28 unique images** in `docs/guide/images/`
- **25 dark-mode images** in `docs/screenshots/`
- **5 remaining placeholder comments** in Ch 14-15 (admin-only pages: health check, commands form, Swagger UI, filter dropdown, filter chips)

### Chapters that don't need screenshots (by design)
- Ch 16 (Data Model) — conceptual RDF explanation
- Ch 17 (Command API) — JSON API reference
- Ch 20 (Production Deployment) — server config docs
- Ch 22 (Keyword Search) — needs screenshot but search page 404'd on dev stack
- Ch 25 (WebID Profiles) — protocol documentation
- Ch 26 (IndieAuth) — auth protocol
- Ch 29 (App Platform, Mental Model Catalog) — SDK/developer docs
- Ch 31 (API Surface) — JSON endpoint reference
- Ch 32-36 (Browser Extension, Sync Apps) — need their respective apps running

## Files Modified
- `docs/guide/01-what-is-sempkm.md`
- `docs/guide/02-core-concepts.md`
- `docs/guide/03-installation-and-setup.md`
- `docs/guide/06-edges-and-relationships.md`
- `docs/guide/14-system-health-and-debugging.md`
- `docs/guide/15-event-log.md`
- `docs/guide/18-sparql-endpoint.md`
- `docs/guide/19-creating-mental-models.md`
- `docs/guide/21-sparql-console.md`
- `docs/guide/23-vfs.md`
- `docs/guide/24-obsidian-onboarding.md`
- `docs/guide/27-spatial-canvas.md`
- `docs/guide/28-dashboards-and-workflows.md`
- `docs/guide/30-personas.md`
- `docs/guide/images/README.md`
- `docs/screenshots/README.md`
- 7 new screenshots in `docs/guide/images/`
- 8 new screenshots in `docs/screenshots/`

## Verification
- All 44 image references resolve to existing files (verified via rg + file existence check)
- No broken image paths
- New screenshots visually verified via `Read` tool
- 5 remaining placeholder comments are for admin-only pages not accessible from dev stack member session
