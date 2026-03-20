# S03: Screenshots, mobile polish, and SEO verification

**Goal:** All 4 pages (index, from-obsidian, from-notion, fresh-start) have complete SEO tags (including JSON-LD structured data and absolute og:image), all internal links resolve, fresh screenshots captured from the demo Docker stack, Lighthouse mobile score ≥90, and responsive layout confirmed at 375px, 768px, 1200px+.
**Demo:** Open any page on sempkm.metacoding.io — social sharing preview shows og:image, JSON-LD is present, all CTAs link to working targets, screenshots reflect current UI, and Lighthouse mobile audit passes ≥90 performance.

## Must-Haves

- All `guide/20-production-deployment.html` links replaced with `guide/index.html` (8 occurrences across 4 files)
- `og:image` with absolute URL (`https://sempkm.metacoding.io/screenshots/...`) on all 4 pages
- JSON-LD structured data (Organization + WebSite schema) on all 4 pages
- Fresh screenshots from demo Docker stack replacing stale v2.0 images in `docs/screenshots/`
- Lighthouse mobile performance score ≥90 on all 4 pages
- Responsive layout verified at 375px, 768px, 1200px+ — no horizontal overflow, all CTAs visible

## Proof Level

- This slice proves: operational
- Real runtime required: yes (Docker demo stack for screenshots, HTTP server for Lighthouse)
- Human/UAT required: no (automated Lighthouse + browser assertions sufficient)

## Verification

- `grep -rn 'guide/20-production-deployment.html' docs/index.html docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html` → zero results
- `grep -c 'og:image.*https://sempkm.metacoding.io' docs/index.html docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html` → 4 files match
- `grep -c 'application/ld+json' docs/index.html docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html` → 4 files match
- Python link checker: zero broken internal links across all 4 pages
- HTML well-formedness: all 4 pages parse without error via `html.parser.HTMLParser`
- Fresh screenshots exist in `docs/screenshots/` with recent modification timestamps
- Lighthouse mobile performance score ≥ 0.9 on `docs/index.html`
- Browser rendering at 375px, 768px, 1200px — no horizontal overflow, all CTAs visible

## Integration Closure

- Upstream surfaces consumed: `docs/index.html`, `docs/from-obsidian.html`, `docs/from-notion.html`, `docs/fresh-start.html`, `docs/styles.css` (all from S01/S02)
- New wiring introduced in this slice: none — pure polish and verification
- What remains before the milestone is truly usable end-to-end: nothing — S03 is the final slice

## Tasks

- [x] **T01: Fix broken links and add missing SEO tags** `est:30m`
  - Why: 8 broken guide links, missing og:image on persona pages, homepage og:image is relative not absolute, and no JSON-LD structured data on any page — all required by milestone success criteria
  - Files: `docs/index.html`, `docs/from-obsidian.html`, `docs/from-notion.html`, `docs/fresh-start.html`
  - Do: (1) Replace `guide/20-production-deployment.html` with `guide/index.html` in all 4 files. (2) Change homepage og:image from relative to absolute URL. (3) Add og:image meta tag with absolute URL to 3 persona pages. (4) Add JSON-LD script block (Organization + WebSite schema) to all 4 pages. (5) Run link checker and HTML parser to verify.
  - Verify: `grep -rn 'guide/20-production-deployment' docs/*.html` returns nothing; `grep -l 'og:image.*https://sempkm' docs/*.html | wc -l` returns 4; `grep -l 'application/ld+json' docs/*.html | wc -l` returns 4; Python link checker finds zero broken links
  - Done when: All 4 pages have working internal links, absolute og:image URLs, and JSON-LD structured data; HTML parses cleanly
- [ ] **T02: Capture fresh screenshots, run Lighthouse audit, verify responsive layout** `est:1h`
  - Why: Screenshots are stale v2.0 images, Lighthouse mobile audit not yet run, and persona pages need responsive verification at 3 breakpoints — all required by milestone definition of done
  - Files: `docs/screenshots/*.png`
  - Do: (1) Start demo Docker stack (`docker-compose.demo.yml`), seed data, wait for healthy. (2) Open demo instance (localhost:3902) in browser, capture 5-8 fresh screenshots at 1440×900 showing workspace overview, dashboard, graph view, table view, object read view, canvas, lint panel. (3) Save screenshots to `docs/screenshots/`, ensuring `01-workspace-overview-dark.png` is replaced (referenced by og:image). (4) Serve docs/ via `python3 -m http.server` on port 8080. (5) Run Lighthouse mobile audit on index.html, verify ≥90 performance. (6) Open each of the 4 pages in browser at 375px, 768px, 1200px — verify no horizontal overflow, all CTAs visible, comparison tables scrollable on mobile, nav functional. (7) Stop demo stack.
  - Verify: Fresh screenshots in `docs/screenshots/` with today's date; Lighthouse mobile performance ≥ 0.9; browser assertions pass at all 3 breakpoints for all 4 pages
  - Done when: Screenshots reflect current UI, Lighthouse ≥90, all pages render correctly at 3 breakpoints

## Observability / Diagnostics

- **SEO tag presence:** `grep -c 'og:image.*https://sempkm.metacoding.io' docs/*.html` and `grep -c 'application/ld+json' docs/*.html` — both should return 4 matches.
- **Broken internal links:** Python link checker (see T01 plan step 5) reports zero broken links. If a new page is added without updating cross-references, the checker will surface the broken path.
- **HTML well-formedness:** `python3 -c "from html.parser import HTMLParser; HTMLParser().feed(open('docs/FILE.html').read())"` — raises on malformed HTML.
- **Lighthouse score:** `npx lighthouse --output=json --output-path=... --chrome-flags='--headless'` — machine-readable performance score at `categories.performance.score`.
- **Failure visibility:** All checks are grep/Python one-liners that can be run from any CI or agent without Docker.
- **No secrets or credentials in these files.**

## Files Likely Touched

- `docs/index.html`
- `docs/from-obsidian.html`
- `docs/from-notion.html`
- `docs/fresh-start.html`
- `docs/screenshots/*.png`
