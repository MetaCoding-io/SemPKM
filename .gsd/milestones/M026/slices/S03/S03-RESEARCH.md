# S03: Screenshots, Mobile Polish, and SEO Verification — Research

**Date:** 2026-03-20
**Status:** Complete

## Summary

S03 is a polish and verification slice. The homepage (S01) and three persona pages (S02) are complete with full content, responsive CSS, and partial SEO tags. The remaining work falls into four categories: (1) fix broken links, (2) add missing SEO tags, (3) capture fresh screenshots from the demo Docker stack, and (4) run Lighthouse audit and browser-verify responsiveness at 3 breakpoints.

The work is straightforward — no architectural decisions, no unfamiliar technology. The main complexity is screenshot capture, which requires starting the demo Docker stack (`docker-compose.demo.yml`), seeding demo data, and using a browser to capture screenshots at 1440×900.

## Recommendation

Split into two tasks: T01 handles all HTML fixes (broken links, missing SEO tags, JSON-LD structured data, og:image on persona pages) — this is purely file editing. T02 handles screenshot capture from the demo stack and Lighthouse/responsive verification in a browser — this requires Docker and Playwright/browser automation.

## Implementation Landscape

### Key Files

- `docs/index.html` (619 lines) — Homepage. Has partial SEO tags (description, og:title/description/type/url, og:image as relative URL). Missing: JSON-LD structured data, og:image should be absolute URL.
- `docs/from-obsidian.html` (536 lines) — Obsidian persona page. Has description + og:title/description/type/url. Missing: og:image, JSON-LD.
- `docs/from-notion.html` (536 lines) — Notion persona page. Same gaps as from-obsidian.
- `docs/fresh-start.html` (510 lines) — Fresh start persona page. Same gaps.
- `docs/styles.css` (1109 lines) — Shared CSS with responsive breakpoints at 768px and 480px. Already covers persona page components. Unlikely to need changes unless Lighthouse flags specific issues.
- `docs/screenshots/` — 17 existing screenshots at 1440×900 PNG. All are v2.0-era, pre-dating dashboards, canvas embeds, persona selector, and other recent features. Only `01-workspace-overview-dark.png` is referenced (as og:image on homepage).
- `docs/CNAME` — Contains `sempkm.metacoding.io`. All canonical/og:url tags use this domain correctly.
- `docker-compose.demo.yml` — Demo stack config. Ports 3902 (frontend) / 8902 (API). Includes DEMO_MODE=true for anonymous access.
- `scripts/seed-demo-data.py` — Seeds 74 objects across 4 Mental Models with cross-model edges.

### Issues Found

**1. Broken link: `guide/20-production-deployment.html` (8 occurrences across 4 files)**

All four pages link to `guide/20-production-deployment.html` for the "Self-Host with Docker" CTA. This file doesn't exist — the guide is an SPA (`guide/index.html`) that loads `.md` files via JS fetch. The guide has no hash-based deep linking, so the only valid link target is `guide/index.html`.

Fix: Change all `guide/20-production-deployment.html` links to `guide/index.html`. The user can then navigate to the deployment chapter from the sidebar.

**2. Missing `og:image` on persona pages**

`index.html` has `<meta property="og:image" content="screenshots/01-workspace-overview-dark.png">` (relative URL). The three persona pages have no `og:image` at all. For proper social sharing previews, all pages need `og:image` with an absolute URL.

Fix: Add `og:image` with absolute URL (`https://sempkm.metacoding.io/screenshots/01-workspace-overview-dark.png`) to all four pages. The homepage og:image also needs to become absolute.

**3. No JSON-LD structured data on any page**

The roadmap and success criteria call for "structured data present on all pages." None of the four pages have `<script type="application/ld+json">`. A basic Organization + WebSite schema is the minimum useful structured data for a software product homepage.

Fix: Add a JSON-LD block to each page with Organization schema (name, url, logo, sameAs for GitHub) and WebSite schema (name, url).

**4. Screenshot staleness**

17 existing screenshots in `docs/screenshots/` are all from v2.0 era. Features like dashboards, canvas embeds with iframes, persona selector, lint panel improvements, and the new explorer modes are not shown. However, the new homepage and persona pages don't actually reference any screenshots in `<img>` tags — the only screenshot reference is `og:image` on the homepage.

The roadmap says "all pages have fresh screenshots from current UI" but the S01/S02 pages were designed without screenshot sections or carousel. The screenshots are used only for og:image (social sharing preview) and exist in the `docs/screenshots/` directory for potential future use.

Approach: Capture 5-8 fresh screenshots from the demo stack showing the best views (workspace overview, dashboard, canvas, graph view, table view, object read view, lint panel). Replace stale files in `docs/screenshots/`. The og:image reference to `01-workspace-overview-dark.png` should point to a fresh workspace screenshot.

**5. Responsive verification needed at 3 breakpoints**

S01 summary confirms verification at 1280px, 768px, and 375px for the homepage. The persona pages (S02) need the same verification. The CSS already has responsive rules for persona-specific components (pain-grid, steps-grid, before-after at 768px and 480px).

**6. Lighthouse mobile audit**

Success criteria: ≥90 performance score on mobile. The pages are static HTML with one external dependency (Google Fonts CDN). Should score well. Need to serve the pages via a local HTTP server (Lighthouse requires HTTP, not file://).

### Build Order

**T01: SEO fixes and link repair (pure HTML editing)**
1. Fix `guide/20-production-deployment.html` → `guide/index.html` in all 4 files (8 replacements)
2. Make og:image absolute URL on homepage
3. Add og:image to 3 persona pages
4. Add JSON-LD structured data (Organization + WebSite) to all 4 pages
5. Verify: grep for broken links, validate HTML, check meta tags

**T02: Screenshots, Lighthouse audit, and responsive verification (requires Docker + browser)**
1. Start demo Docker stack, seed data, wait for healthy
2. Open demo instance at localhost:3902, capture 5-8 fresh screenshots at 1440×900
3. Replace stale screenshots in `docs/screenshots/`
4. Serve `docs/` via `python3 -m http.server` on a local port
5. Run `npx lighthouse` on all 4 pages (mobile preset), verify ≥90 performance
6. Open each page in browser at 375px, 768px, 1200px+ — verify layout, no overflow, all CTAs visible
7. Stop demo stack

T01 and T02 are independent — T01 is pure file editing, T02 is Docker + browser work. T01 should go first since it's faster and fixes broken links that Lighthouse would flag.

### Verification Approach

**Link verification:**
```bash
# No broken internal links
python3 -c "
from html.parser import HTMLParser
import os
class C(HTMLParser):
    def __init__(s): super().__init__(); s.b=[]
    def handle_starttag(s,t,a):
        if t=='a':
            for k,v in a:
                if k=='href' and v and not v.startswith(('#','http','mailto')):
                    base=v.split('#')[0]
                    if base and not os.path.exists(f'docs/{base}'): s.b.append(base)
for f in ['docs/index.html','docs/from-obsidian.html','docs/from-notion.html','docs/fresh-start.html']:
    c=C(); c.feed(open(f).read())
    for b in c.b: print(f'BROKEN: {f} -> {b}')
print('Done') if not any(C().b for f in []) else None
"
```

**SEO tag verification:**
```bash
# All pages have og:image with absolute URL
grep -l 'og:image.*https://sempkm.metacoding.io' docs/index.html docs/from-*.html docs/fresh-start.html | wc -l
# Expected: 4

# All pages have JSON-LD
grep -l 'application/ld+json' docs/index.html docs/from-*.html docs/fresh-start.html | wc -l
# Expected: 4
```

**Lighthouse:**
```bash
cd docs && python3 -m http.server 8080 &
npx lighthouse http://localhost:8080/index.html --preset=perf --output=json --chrome-flags="--headless" | jq '.categories.performance.score'
# Expected: >= 0.9
```

**Responsive (browser):**
Open each page at 375px, 768px, 1200px and visually verify:
- No horizontal scrollbar / overflow
- All CTAs visible and tappable
- Comparison table scrollable on mobile
- Nav hamburger menu functional
- Persona cards stack vertically on mobile

## Constraints

- No build step — all changes are direct HTML edits to files in `docs/`
- Screenshots must come from the demo Docker stack (per D257) to match what the "Try the Demo" CTA links to
- Lighthouse requires pages served over HTTP (not file://)
- og:image URLs must be absolute for social sharing to work correctly

## Common Pitfalls

- **Relative og:image URLs** — Social media crawlers resolve og:image relative to the page URL, but many (Twitter, LinkedIn) require absolute URLs for reliable preview images. Always use `https://sempkm.metacoding.io/screenshots/...`.
- **Lighthouse on file:// protocol** — Lighthouse refuses to audit file:// URLs. Must use a local HTTP server (`python3 -m http.server`).
- **Demo stack port conflict** — The dev stack runs on ports 3000/8001. The demo stack uses 3902/8902. Both can run simultaneously, but if the dev stack is using shared Docker volumes, ensure no conflicts.
- **Screenshot capture timing** — The demo workspace uses htmx lazy-loading and SSE. Screenshots must wait for all content to render before capture. Use Playwright `waitForLoadState('networkidle')` or manual wait.

## Sources

- S01 summary (forward intelligence): nav z-index fragility, canvas bleed-through, section-alt pattern
- S02 summary: doctor-created placeholder — task summaries in S02/tasks/ are the authoritative source
- docs/guide/index.html: guide SPA structure — no deep linking, `data-file` attribute loading
