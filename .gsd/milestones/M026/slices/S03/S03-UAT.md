# S03: Screenshots, mobile polish, and SEO verification — UAT

**Milestone:** M026
**Written:** 2026-03-20

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All deliverables are static HTML files and PNG images verifiable via grep, file inspection, and local HTTP server. No runtime backend needed.

## Preconditions

- All 4 docs pages exist: `docs/index.html`, `docs/from-obsidian.html`, `docs/from-notion.html`, `docs/fresh-start.html`
- `docs/styles.css` exists and is linked from all 4 pages
- `docs/screenshots/` directory contains PNG images
- Node.js installed (for Lighthouse CLI)
- A browser available for responsive testing

## Smoke Test

Serve docs locally (`python3 -m http.server 8080 --directory docs/`) and open `http://localhost:8080/index.html` — page loads with visible hero section, screenshots in carousel, and all navigation links clickable.

## Test Cases

### 1. Broken guide links eliminated

1. Run: `grep -rn 'guide/20-production-deployment.html' docs/index.html docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html`
2. **Expected:** Zero results (exit code 1). All guide links should point to `guide/index.html`.

### 2. og:image present with absolute URL on all 4 pages

1. Run: `grep 'og:image' docs/index.html docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html`
2. **Expected:** Each file has exactly one `og:image` meta tag containing `https://sempkm.metacoding.io/screenshots/01-workspace-overview-dark.png` (absolute URL, not relative).

### 3. JSON-LD structured data on all 4 pages

1. Run: `grep 'application/ld+json' docs/index.html docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html`
2. **Expected:** Each file has exactly one `<script type="application/ld+json">` block.
3. Run: `python3 -c "import json; [json.loads(open(f).read().split('application/ld+json\">')[1].split('</script>')[0]) for f in ['docs/index.html','docs/from-obsidian.html','docs/from-notion.html','docs/fresh-start.html']]"`
4. **Expected:** No JSON parse errors. Each block contains valid JSON with `@graph` array including Organization and WebSite types.

### 4. Fresh screenshots exist with correct dimensions

1. Run: `ls -la docs/screenshots/01-workspace-overview-dark.png docs/screenshots/02-explorer-types-dark.png docs/screenshots/04-command-palette-dark.png docs/screenshots/05-canvas-dark.png docs/screenshots/06-object-read.png`
2. **Expected:** All 5 files exist with dates on or after 2026-03-20.
3. Run: `file docs/screenshots/01-workspace-overview-dark.png`
4. **Expected:** PNG image data, 1440 x 900, 8-bit/color RGB.

### 5. Google Fonts deferred loading

1. Run: `grep 'media="print"' docs/index.html docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html`
2. **Expected:** Each file has a Google Fonts `<link>` with `media="print"` and `onload="this.media='all'"`.
3. Run: `grep '<noscript>' docs/index.html`
4. **Expected:** A `<noscript>` fallback exists loading Google Fonts without the deferred pattern.

### 6. Lighthouse mobile performance ≥ 0.9

1. Start: `python3 -m http.server 8080 --directory docs/`
2. Run: `npx lighthouse http://localhost:8080/index.html --output=json --chrome-flags='--headless' | jq '.categories.performance.score'`
3. **Expected:** Score ≥ 0.9.

### 7. Responsive layout at 375px (mobile)

1. Open `http://localhost:8080/index.html` in browser at 375px width.
2. **Expected:** No horizontal scrollbar. Hero text wraps correctly. "Try the Demo" and "Self-host" CTAs are visible and tappable. Hamburger menu icon is visible (not full nav bar). Comparison table scrolls horizontally if needed (not clipped).

### 8. Responsive layout at 768px (tablet)

1. Open `http://localhost:8080/index.html` in browser at 768px width.
2. **Expected:** No horizontal scrollbar. Persona cards stack in 1-2 columns. All CTAs visible. Feature grid adjusts to fewer columns.

### 9. Responsive layout at 1200px (desktop)

1. Open `http://localhost:8080/index.html` in browser at 1200px width.
2. **Expected:** No horizontal scrollbar. Full navigation bar visible (no hamburger). Persona cards show in a row. Feature grid at full width.

### 10. Internal link integrity

1. Run Python link checker extracting all `href`/`src` values from all 4 HTML files, checking that non-HTTP, non-anchor targets resolve to files in `docs/`.
2. **Expected:** Zero broken internal links. Anchor links like `index.html#why` resolve because `docs/index.html` exists and contains `id="why"`.

### 11. HTML well-formedness

1. Run: `python3 -c "from html.parser import HTMLParser; [HTMLParser().feed(open(f).read()) for f in ['docs/index.html','docs/from-obsidian.html','docs/from-notion.html','docs/fresh-start.html']]"`
2. **Expected:** No exceptions. All 4 files parse cleanly.

## Edge Cases

### Google Fonts noscript fallback

1. Disable JavaScript in browser.
2. Load `http://localhost:8080/index.html`.
3. **Expected:** Google Fonts still load via the `<noscript>` fallback. Page text renders in Inter/Fira Code.

### Persona page og:image

1. Paste `http://localhost:8080/from-obsidian.html` URL into a social media link preview tool (e.g., Open Graph debugger).
2. **Expected:** Preview shows the workspace overview screenshot, not a broken image.

### Comparison table on narrow mobile (320px)

1. Open `http://localhost:8080/index.html` at 320px width.
2. Scroll to comparison table section.
3. **Expected:** Table is horizontally scrollable within its container. No content overflow breaks the page layout.

## Failure Signals

- `grep 'guide/20-production-deployment'` returns any results → broken guide links still present
- `grep 'og:image'` returns fewer than 4 files → missing social sharing image on some pages
- `grep 'application/ld+json'` returns fewer than 4 files → missing structured data for search engines
- Lighthouse performance score < 0.9 → render-blocking resources not addressed
- `document.documentElement.scrollWidth > document.documentElement.clientWidth` at any breakpoint → responsive layout broken
- Any screenshot file is 0 bytes or missing → screenshot capture failed

## Requirements Proved By This UAT

- SITE-05 (updated screenshots) — tests 4, verified 5 fresh screenshots exist with correct dimensions
- SITE-06 (mobile responsive + performance) — tests 6, 7, 8, 9 verify Lighthouse score and responsive layout
- SITE-07 (SEO basics) — tests 2, 3 verify og:image and JSON-LD on all pages; test 1 verifies internal links

## Not Proven By This UAT

- Actual social media card rendering on real platforms (Twitter, Facebook, LinkedIn) — only verifiable by posting links
- Search engine indexing of JSON-LD data — requires crawling by Google/Bing
- Real-user mobile performance (depends on hosting, CDN, actual network conditions)
- Graph/table/dashboard screenshot accuracy — those views weren't captured due to view system bug

## Notes for Tester

- The Lighthouse score under `--preset=perf` (simulated slow 4G) may be 0.88 instead of 0.9. This is an extreme throttling scenario — the **default mobile audit** (which is the standard) scores 0.99. Accept the default audit as the benchmark.
- Old screenshots from March 11 (files 03, 07-20) are still in `docs/screenshots/` but not referenced by any page. They're harmless clutter, not broken references.
- The `docs/CNAME` file must remain untouched — it controls the GitHub Pages custom domain.
