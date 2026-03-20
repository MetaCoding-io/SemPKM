# S01: Homepage rewrite with outcome-focused messaging — UAT

**Milestone:** M026
**Written:** 2026-03-20

## UAT Type

- UAT mode: mixed (artifact-driven verification + live-runtime browser rendering)
- Why this mode is sufficient: The homepage is a static site (HTML/CSS/JS) — no server-side runtime. Artifact checks confirm file structure and content correctness; browser rendering confirms visual layout and interactivity. No backend services needed.

## Preconditions

- `docs/index.html` and `docs/styles.css` exist in the repository
- A browser is available to open local files (or a local HTTP server to serve them)
- For comparison table and responsive checks, browser DevTools viewport emulation is sufficient

## Smoke Test

Open `docs/index.html` in a browser. The page should show a dark-themed homepage with a hero section reading "Build knowledge that doesn't decay" — not "Semantics-Native PKM" or any mention of RDF/SHACL/SPARQL in the first visible screen.

## Test Cases

### 1. Hero messaging is outcome-focused, no tech jargon above the fold

1. Open `docs/index.html` in a browser
2. Read the hero section without scrolling
3. **Expected:** Hero headline says "Build knowledge that doesn't decay" (or similar outcome-focused copy). No mentions of RDF, SHACL, or SPARQL visible above the fold. The subheadline describes user value, not technology.
4. Scroll down past the hero
5. **Expected:** RDF/SHACL/SPARQL appear only once, below the features section, as "Powered by open standards (RDF, SHACL, SPARQL)" or similar subordinate mention.

### 2. Persona selector has 3 cards with correct links

1. Scroll to the persona selector section (below hero)
2. **Expected:** 3 cards visible: "Coming from Obsidian", "Coming from Notion", "Starting Fresh"
3. Hover over each card
4. **Expected:** Each card has a brief description of what that persona will find
5. Click "Coming from Obsidian" card
6. **Expected:** Browser navigates to `from-obsidian.html` (will 404 until S02 — verify the link target is correct in the href)
7. Repeat for "Coming from Notion" → `from-notion.html` and "Starting Fresh" → `fresh-start.html`

### 3. Competitive comparison table is present and complete

1. Scroll to the comparison section
2. **Expected:** A table with column headers for SemPKM, Obsidian, Notion, Tana, and Capacities (5 tools)
3. Count the capability rows
4. **Expected:** At least 6 rows covering capabilities like knowledge structure, validation, views, querying, etc.
5. On desktop (≥1200px), verify all columns are visible simultaneously
6. On mobile (375px), swipe the table horizontally
7. **Expected:** First column (capability names) stays fixed/sticky while tool columns scroll

### 4. Mental Models section uses "domain kits" framing

1. Scroll to the Mental Models / Domain Kits section
2. **Expected:** Section heading uses "domain kits" language, not "ontologies" or "mental models" exclusively
3. **Expected:** 4 cards visible: Basic PKM, Personal CRM, Zettelkasten+, Research Workflow
4. **Expected:** Each card describes what the domain kit helps with in user-benefit language, not technical terms

### 5. CTAs link to correct destinations

1. Find the hero "Try the Demo" CTA button
2. **Expected:** Links to `https://demo.sempkm.app` (or similar demo URL)
3. Find the "Self-host" CTA button
4. **Expected:** Links to Docker quickstart documentation (a docs/guide/ page or similar)
5. Scroll to the bottom CTA section
6. **Expected:** Bottom section also has "Try the Demo" and "Self-host" buttons with same link targets
7. Check the nav bar
8. **Expected:** Nav has a "Try Demo" button/link also pointing to demo.sempkm.app

### 6. CSS is external, not inline

1. View page source of `docs/index.html`
2. **Expected:** A `<link rel="stylesheet" href="styles.css">` tag in the `<head>` — no large `<style>` blocks with layout/component CSS
3. Open `docs/styles.css` separately
4. **Expected:** File exists and contains CSS custom properties (`:root { --color-... }`), responsive media queries, and component classes

### 7. SEO meta tags and OG tags present

1. View page source of `docs/index.html`
2. **Expected:** `<meta name="description" content="...">` tag present with meaningful content
3. **Expected:** `<meta property="og:title" content="...">` tag present
4. **Expected:** `<meta property="og:type" content="...">` tag present
5. **Expected:** `<meta property="og:description" content="...">` tag present

### 8. Desktop rendering (1280px+)

1. Open `docs/index.html` at 1280px viewport width
2. **Expected:** Hero text centered, readable
3. **Expected:** Persona cards in 3-column layout
4. **Expected:** Comparison table fully visible without horizontal scroll
5. **Expected:** Domain kits in multi-column grid
6. **Expected:** Features in multi-column grid
7. **Expected:** Nav shows all links (no hamburger menu)
8. **Expected:** No horizontal overflow (`document.documentElement.scrollWidth <= document.documentElement.clientWidth` returns true)

### 9. Tablet rendering (768px)

1. Resize viewport to 768px width
2. **Expected:** Hamburger menu icon appears in nav (links hidden)
3. Click hamburger menu
4. **Expected:** Nav menu opens with opaque background, showing all links
5. **Expected:** Persona cards stack to single column
6. **Expected:** No horizontal overflow

### 10. Mobile rendering (375px)

1. Resize viewport to 375px width
2. **Expected:** Hero text readable, not clipped
3. **Expected:** CTA buttons are full-width and at least 44px height (tappable)
4. **Expected:** Comparison table scrolls horizontally with sticky first column
5. **Expected:** All font sizes ≥14px (no tiny text)
6. **Expected:** Footer content stacks vertically and is centered
7. **Expected:** No horizontal overflow

### 11. Canvas animation renders

1. Open `docs/index.html` and observe the hero section
2. **Expected:** Animated network graph (dots and connecting lines) visible behind the hero text
3. Scroll past the hero section
4. **Expected:** Canvas animation is NOT visible behind other sections (comparison table, features, etc.) — sections have opaque backgrounds

### 12. CNAME file preserved

1. Check that `docs/CNAME` exists
2. **Expected:** File contains `sempkm.metacoding.io`

## Edge Cases

### Empty viewport / extreme narrow width (320px)

1. Resize to 320px width
2. **Expected:** Page still renders without broken layout. Content may wrap more aggressively but no horizontal overflow or clipped text.

### JavaScript disabled

1. Open `docs/index.html` with JavaScript disabled
2. **Expected:** All content is still visible and readable. Canvas animation won't run (blank background behind hero). Fade-in animations won't trigger (elements may be invisible if they start with opacity: 0 — this is a known limitation). Nav hamburger menu won't toggle.

### Slow/offline network (Google Fonts)

1. Open `docs/index.html` with network throttled or fonts.googleapis.com blocked
2. **Expected:** Page renders with system fonts. Typography looks different but all content is readable. No layout breakage.

## Failure Signals

- Hero section shows "Semantics-Native PKM" or "RDF/SHACL/SPARQL" — messaging rewrite failed
- `styles.css` returns 404 — shared CSS extraction broken, page will be unstyled
- Persona cards link to wrong pages or have no links — navigation contract broken for S02
- Comparison table missing or incomplete — competitive positioning section not built
- "Domain kits" not mentioned — Mental Models framing not applied
- demo.sempkm.app not in any CTA link — demo integration broken
- Horizontal overflow at any viewport width — responsive CSS broken
- Canvas animation visible behind non-hero sections — section background opacity fix missing
- Hamburger menu has translucent background — mobile nav fix missing

## Requirements Proved By This UAT

- SITE-01 (homepage rewrite) — tests 1, 5, 6, 8-12 prove the homepage is rewritten with outcome-focused messaging, external CSS, responsive layout, and preserved CNAME
- SITE-03 (competitive positioning) — test 3 proves comparison table is present and complete
- SITE-04 (Mental Models as domain kits) — test 4 proves domain kits framing
- SITE-07 (SEO basics) — test 7 proves meta/OG tags on homepage

## Not Proven By This UAT

- SITE-02 (persona paths) — persona pages don't exist yet (S02 scope). Test 2 only verifies the links are present on the homepage.
- SITE-05 (updated screenshots) — S03 scope
- SITE-06 (Lighthouse audit) — performance score not measured in this UAT (S03 scope). Responsive layout verified visually.
- Full SEO verification (structured data, all pages) — S03 scope

## Notes for Tester

- Persona page links will 404 — this is expected until S02 builds them. Verify the href values are correct, not the destinations.
- The Google Fonts 404 error in browser console when serving from a local Python HTTP server is a false positive — the dev server can't proxy the Google Fonts CSS request. This won't happen on GitHub Pages.
- The canvas animation uses `requestAnimationFrame` and may not render in some automated testing tools — visual inspection in a real browser is the authoritative check.
- The comparison table sticky first column may not work in all browsers' DevTools viewport emulation — test on a real mobile device if the emulator shows unexpected behavior.
