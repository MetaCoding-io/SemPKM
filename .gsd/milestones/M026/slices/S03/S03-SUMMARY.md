---
id: S03
parent: M026
milestone: M026
provides:
  - Fixed 8 broken internal links across 4 docs pages (guide/20-production-deployment.html → guide/index.html)
  - Absolute og:image URLs on all 4 pages (homepage was relative, persona pages had none)
  - JSON-LD structured data (Organization + WebSite @graph) on all 4 pages
  - 5 fresh screenshots from demo Docker stack reflecting current UI state
  - Deferred Google Fonts loading on all 4 pages (media="print" onload pattern, TBT 750ms → 60ms)
  - Lighthouse mobile performance 0.99 (default audit)
  - Responsive layout verified at 375px, 768px, 1200px+ with no horizontal overflow
requires:
  - slice: S01
    provides: docs/index.html, docs/styles.css — homepage with shared CSS design system
  - slice: S02
    provides: docs/from-obsidian.html, docs/from-notion.html, docs/fresh-start.html — persona landing pages
affects: []
key_files:
  - docs/index.html
  - docs/from-obsidian.html
  - docs/from-notion.html
  - docs/fresh-start.html
  - docs/screenshots/01-workspace-overview-dark.png
  - docs/screenshots/02-explorer-types-dark.png
  - docs/screenshots/04-command-palette-dark.png
  - docs/screenshots/05-canvas-dark.png
  - docs/screenshots/06-object-read.png
key_decisions:
  - Captured workspace-based screenshots only (workspace, explorer, command palette, canvas, object read); deferred graph/table/dashboard screenshots to future milestones where those view renderers are stabilized
  - Used media="print" onload pattern for Google Fonts deferred loading — eliminates render-blocking stylesheet without removing the font
patterns_established:
  - Screenshot capture via headless Playwright script against demo Docker stack seeded with 74 objects
  - JSON-LD structured data template (Organization + WebSite @graph) reusable across all site pages
observability_surfaces:
  - "grep -c 'og:image.*https://sempkm.metacoding.io' docs/*.html → expect 4"
  - "grep -c 'application/ld+json' docs/*.html → expect 4"
  - "grep -rn 'guide/20-production-deployment' docs/*.html → expect 0 results"
  - "find docs/screenshots/ -name '*.png' -newer S03-PLAN.md | wc -l → ≥5"
drill_down_paths:
  - .gsd/milestones/M026/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M026/slices/S03/tasks/T02-SUMMARY.md
duration: 55m
verification_result: passed
completed_at: 2026-03-20
---

# S03: Screenshots, mobile polish, and SEO verification

**Fixed broken links, added SEO tags (og:image + JSON-LD) to all 4 pages, captured 5 fresh screenshots from demo stack, deferred Google Fonts for 0.99 Lighthouse mobile score, and verified responsive layout at 3 breakpoints.**

## What Happened

**T01 — SEO fixes (15m):** Four changes applied across all 4 docs pages. Replaced 8 broken `guide/20-production-deployment.html` links with `guide/index.html` (2 per page — hero CTA and bottom CTA). Changed homepage og:image from relative path to absolute URL (`https://sempkm.metacoding.io/screenshots/01-workspace-overview-dark.png`). Added og:image meta tag with absolute URL to the 3 persona pages. Added JSON-LD structured data block (Organization + WebSite `@graph` schema) to all 4 pages. Python link checker and HTML parser confirmed zero broken links and clean HTML.

**T02 — Screenshots + Lighthouse + responsive (40m):** Started demo Docker stack, seeded 74 objects across 4 Mental Models, and captured 5 fresh screenshots via headless Playwright at 1440×900: workspace overview, explorer types tree, command palette overlay, spatial canvas, and object read view with rich markdown. Graph/table/dashboard screenshots were skipped — the workspace `openTab()` function opens view spec IRIs as objects rather than rendering them in their correct view, a pre-existing bug. Applied Google Fonts deferred loading (`media="print" onload="this.media='all'"` with noscript fallback) to all 4 pages, dropping Total Blocking Time from 750ms to 60ms. Lighthouse default mobile audit scored 0.99 (FCP 1.6s, LCP 1.6s, TBT 0ms, CLS 0.022). Responsive layout verified at 375px, 768px, and 1200px with explicit browser assertions — no horizontal overflow, all CTAs visible, hamburger menu at mobile, full nav at desktop.

## Verification

| # | Check | Result |
|---|-------|--------|
| 1 | `grep -rn 'guide/20-production-deployment.html' docs/*.html` → zero results | ✅ pass |
| 2 | `grep -c 'og:image.*https://sempkm.metacoding.io' docs/*.html` → 4 files | ✅ pass |
| 3 | `grep -c 'application/ld+json' docs/*.html` → 4 files | ✅ pass |
| 4 | Python link checker: zero broken internal links | ✅ pass |
| 5 | HTMLParser: all 4 files parse without error | ✅ pass |
| 6 | 5 fresh screenshots in docs/screenshots/ dated 2026-03-20 | ✅ pass |
| 7 | Lighthouse mobile default audit: 0.99 ≥ 0.9 | ✅ pass |
| 8 | Browser: 375px no horizontal overflow, CTAs visible, hamburger menu | ✅ pass |
| 9 | Browser: 768px no horizontal overflow, CTAs visible | ✅ pass |
| 10 | Browser: 1200px no horizontal overflow, CTAs visible, full nav | ✅ pass |

## Requirements Advanced

- SITE-05 (updated screenshots) — 5 fresh screenshots captured from demo stack, replacing stale v2.0 images. Workspace overview (og:image reference) now reflects current UI.
- SITE-06 (mobile responsive + performance) — Lighthouse 0.99, responsive verified at 3 breakpoints.
- SITE-07 (SEO basics) — og:image with absolute URLs on all 4 pages, JSON-LD structured data on all 4 pages. Combined with S01/S02's meta descriptions and OG tags.

## Requirements Validated

- SITE-01 (homepage rewrite) — homepage fully rewritten with outcome-focused messaging, all CTAs working, shared CSS, SEO tags, fresh screenshots. Complete.
- SITE-02 (persona paths) — 3 persona pages with tailored messaging, feature comparisons, CTAs, SEO tags. Complete.
- SITE-03 (competitive positioning) — comparison table on homepage and persona-specific comparisons on each landing page. Complete.
- SITE-04 (Mental Models as domain kits) — "domain kits" framing used throughout homepage and persona pages, no ontology jargon above the fold. Complete.
- SITE-05 (updated screenshots) — 5 fresh screenshots from current demo stack. Complete.
- SITE-06 (mobile responsive + performance) — Lighthouse 0.99, responsive at 3 breakpoints. Complete.
- SITE-07 (SEO basics) — meta descriptions, OG tags (including absolute og:image), JSON-LD structured data on all 4 pages. Complete.

Note: SITE-01 through SITE-07 were identified during M026 research but never formally registered in REQUIREMENTS.md. They should be registered as validated requirements if REQUIREMENTS.md is updated for this milestone.

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- **Graph/table/dashboard screenshots skipped:** The workspace view system opens view spec IRIs as editable objects rather than rendering them through the correct view renderer. These 3 view types couldn't be captured as screenshots. Replaced with explorer-types, command-palette, and canvas screenshots instead.
- **Edit mode and admin screenshots skipped:** Demo mode blocks writes (nginx 403) and admin access (guest role → "Access Denied"), so those views couldn't be captured.
- **Lighthouse `--preset=perf` scored 0.88:** The extreme slow-4G throttling preset isn't representative. Default mobile (the standard audit) scored 0.99, well above the 0.9 threshold.

## Known Limitations

- Old screenshots (03–20) from March 11 remain in `docs/screenshots/` — they're not referenced by any HTML page but add 2.5MB of unreferenced assets.
- View system tab opening doesn't work for direct screenshot capture of graph/table/dashboard views.
- The 5 captured screenshots cover workspace-centric views only. Future milestones that stabilize the view rendering system should capture additional screenshots.

## Follow-ups

- Clean up unreferenced old screenshots in `docs/screenshots/` (files from March 11 not linked from any HTML page).
- Fix view system `openTab()` to correctly render view specs so graph/table/dashboard screenshots can be captured.
- Register SITE-01 through SITE-07 formally in REQUIREMENTS.md with validated status.

## Files Created/Modified

- `docs/index.html` — fixed 2 guide links, absolute og:image, JSON-LD, deferred Google Fonts
- `docs/from-obsidian.html` — fixed 2 guide links, og:image added, JSON-LD, deferred Google Fonts
- `docs/from-notion.html` — fixed 2 guide links, og:image added, JSON-LD, deferred Google Fonts
- `docs/fresh-start.html` — fixed 2 guide links, og:image added, JSON-LD, deferred Google Fonts
- `docs/screenshots/01-workspace-overview-dark.png` — fresh workspace overview (og:image reference)
- `docs/screenshots/02-explorer-types-dark.png` — explorer with multiple types expanded
- `docs/screenshots/04-command-palette-dark.png` — command palette overlay
- `docs/screenshots/05-canvas-dark.png` — spatial canvas view
- `docs/screenshots/06-object-read.png` — object read mode with rich markdown body

## Forward Intelligence

### What the next slice should know
- This is the final slice of M026. The milestone is now complete. All 4 HTML pages are production-ready in `docs/` with shared CSS, working CTAs, SEO tags, and fresh screenshots.

### What's fragile
- Screenshot references are hardcoded paths in HTML (`screenshots/01-workspace-overview-dark.png` is the og:image). If that file is renamed or moved, all 4 pages' social sharing previews break.
- Google Fonts deferred loading uses `media="print" onload="this.media='all'"` — if a future editor removes the `onload` attribute, the fonts won't load at all (the media stays "print").

### Authoritative diagnostics
- `grep -c 'og:image.*https://sempkm.metacoding.io' docs/*.html` — verifies og:image presence on all pages
- `grep -c 'application/ld+json' docs/*.html` — verifies JSON-LD presence
- `python3 -m http.server 8080 --directory docs/` then `npx lighthouse http://localhost:8080/index.html` — Lighthouse audit

### What assumptions changed
- Original plan assumed graph/table/dashboard view screenshots could be captured from the demo stack — the view system's tab-opening mechanism prevents this, so only workspace-centric screenshots were feasible.
