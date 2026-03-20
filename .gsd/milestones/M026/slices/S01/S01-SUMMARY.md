---
id: S01
parent: M026
milestone: M026
provides:
  - docs/styles.css — shared CSS design system (colors, typography, layout, responsive breakpoints, dark theme, component styles) consumed by S02 persona pages
  - docs/index.html — outcome-focused homepage with persona selector, competitive comparison, domain kits, dual CTAs, SEO tags
  - Nav HTML pattern (header with persona dropdown, footer) for S02 pages to replicate
requires: []
affects:
  - S02 (consumes docs/styles.css and nav HTML pattern for persona landing pages)
  - S03 (consumes docs/styles.css and page structure for screenshots, mobile polish, SEO verification)
key_files:
  - docs/styles.css
  - docs/index.html
key_decisions:
  - D254: No static site generator — vanilla HTML/CSS/JS for homepage rewrite
  - D255: Homepage messaging grounded in USER-CONVERSION-STRATEGY.md, not invented
  - Used DM Sans as display/body font (distinctive, optical sizing, Google Fonts CDN with system font fallback)
  - Dropped email signup form in favor of demo-first CTAs — conversion strategy emphasizes reducing barrier-to-try
  - Kept canvas network graph animation from existing site as visual differentiator
  - RDF/SHACL/SPARQL appear only once, below the fold, as "Powered by open standards"
  - Section backgrounds use opaque var(--bg-primary) to prevent canvas animation bleed-through; hero stays transparent
patterns_established:
  - Shared CSS design system with custom properties, responsive breakpoints (768px, 480px), and component classes for nav, hero, persona cards, comparison table, domain kit cards, feature grid, CTA section, footer
  - Nav HTML structure with persona dropdown links to /from-obsidian.html, /from-notion.html, /fresh-start.html — S02 must replicate this header/footer pattern
  - Section-alt class for alternating background sections
  - Nav (.nav) must not be included in bulk z-index/position rules — it has its own fixed positioning at z-index:100
observability_surfaces:
  - Browser DevTools Network panel: styles.css load status (200 = OK, 404 = broken)
  - Console: document.querySelectorAll('.fade-in.visible').length after scroll confirms IntersectionObserver active
  - Missing styles.css → completely unstyled page (visually obvious)
  - python3 -c "from html.parser import HTMLParser; HTMLParser().feed(open('docs/index.html').read()); print('OK')" — HTML well-formedness
drill_down_paths:
  - .gsd/milestones/M026/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M026/slices/S01/tasks/T02-SUMMARY.md
duration: 55m
verification_result: passed
completed_at: 2026-03-20
---

# S01: Homepage rewrite with outcome-focused messaging

**Replaced 1928-line technology-first homepage with outcome-focused landing page: shared CSS design system in styles.css, hero leading with "Build knowledge that doesn't decay", 3-card persona selector, 6×6 competitive comparison table, domain kits section, 8 condensed features, dual demo/self-host CTAs, mobile-responsive at 3 breakpoints — zero RDF/SHACL/SPARQL above the fold**

## What Happened

T01 read USER-CONVERSION-STRATEGY.md for persona definitions, competitive positioning, and messaging rules, then created the full shared CSS design system (`docs/styles.css`, ~926 lines) and rewrote `docs/index.html` (~619 lines) from scratch with outcome-focused content.

The CSS design system provides: custom properties for colors/typography/spacing, dark theme palette, responsive breakpoints at 768px and 480px, and component styles for nav (with persona dropdown hover menu), hero section, persona selector cards, comparison table (with sticky first column for mobile), domain kit cards, feature grid, CTA section, and footer. All styling uses CSS custom properties for easy theming.

The homepage content follows the conversion strategy precisely: hero leads with "Build knowledge that doesn't decay" (not "Semantics-Native PKM"), persona selector offers three paths ("Coming from Obsidian" / "Coming from Notion" / "Starting Fresh"), competitive comparison table covers 6 capabilities across 5 tools (SemPKM, Obsidian, Notion, Tana, Capacities), Mental Models are framed as "domain kits" (4 cards: Basic PKM, Personal CRM, Zettelkasten+, Research Workflow), 8 features described in outcome language, and dual CTAs link to demo.sempkm.app and Docker quickstart docs. RDF/SHACL/SPARQL appear only once, below the fold, as "Powered by open standards."

T02 opened the homepage in a browser at desktop (1280px), tablet (768px), and mobile (375px) viewports. Found and fixed three CSS issues: (1) nav z-index conflict where a bulk `position: relative; z-index: 1` rule overrode nav's `position: fixed; z-index: 100`, breaking the sticky header; (2) canvas animation bleed-through into non-hero sections due to transparent backgrounds — fixed by making section backgrounds opaque with an explicit transparent override on `.hero`; (3) mobile hamburger menu using `backdrop-filter: blur` instead of a solid opaque background, letting content leak through.

## Verification

All 9 slice-level verification checks pass:

| # | Check | Result |
|---|-------|--------|
| 1 | `test -f docs/styles.css` | ✅ PASS |
| 2 | `grep -c 'styles.css' docs/index.html` → 1 | ✅ PASS |
| 3 | No RDF/SHACL/SPARQL above the fold (Python assertion) | ✅ PASS |
| 4 | `grep -c 'demo.sempkm.app' docs/index.html` → 3 | ✅ PASS (nav CTA + hero CTA + bottom CTA) |
| 5 | `grep -c 'from-obsidian\|from-notion\|fresh-start' docs/index.html` → 6 | ✅ PASS (2 links per persona) |
| 6 | `grep -ci 'domain kit' docs/index.html` → 8 | ✅ PASS |
| 7 | `test -f docs/CNAME` → sempkm.metacoding.io | ✅ PASS |
| 8 | HTML well-formedness (HTMLParser) | ✅ PASS |
| 9 | No conflict markers in docs/ | ✅ PASS |

Additional verification:
- Comparison table: 6 column headers × 6 body rows confirmed
- SEO meta tags: description, og:title, og:type, og:description present
- Browser rendering verified at 1280px, 768px, and 375px — no horizontal overflow, all CTAs visible, persona cards responsive, comparison table scrollable on mobile
- No JS console errors at any breakpoint
- Canvas animation active at all viewports

## Requirements Advanced

- SITE-01 (homepage rewrite) — homepage fully rewritten with outcome-focused messaging, shared CSS, and all content sections. Ready for validation.
- SITE-02 (persona paths) — persona selector cards with links to 3 persona pages are in place on the homepage. Persona pages themselves are S02 scope.
- SITE-03 (competitive positioning) — 6×6 comparison table present and accurate on homepage.
- SITE-04 (Mental Models as domain kits) — domain kits section with 4 cards present, no ontology jargon.
- SITE-06 (mobile responsive + performance) — responsive verified at 3 breakpoints. Lighthouse audit deferred to S03.
- SITE-07 (SEO basics) — meta description and OG tags on homepage. Full SEO verification deferred to S03.

## Requirements Validated

- none (SITE requirements not yet registered in REQUIREMENTS.md; full validation requires S02 + S03 completion)

## New Requirements Surfaced

- SITE-01 through SITE-07 identified during M026 planning, to be registered when milestone completes

## Requirements Invalidated or Re-scoped

- none

## Deviations

- Dropped the email signup form ("Sign up for updates") from the original site in favor of three demo-first CTAs. The conversion strategy emphasizes reducing barrier-to-try, and the hosted demo (M025) is the primary conversion path — an email form is no longer the right CTA.
- CSS came to ~926 lines (larger than the 500-700 estimate) because responsive breakpoints and component styles are more thorough than initially scoped. HTML came to ~619 lines (within estimate).

## Known Limitations

- Google Fonts (DM Sans) requires internet access. Falls back gracefully to system fonts via CSS custom property font stack.
- Persona page links (`from-obsidian.html`, `from-notion.html`, `fresh-start.html`) will 404 until S02 builds them.
- Screenshots in the feature section are placeholders — fresh screenshots from the M025 demo stack are S03 scope.
- Lighthouse performance audit not yet run — deferred to S03.

## Follow-ups

- S02: Build the 3 persona landing pages consuming docs/styles.css and replicating the nav HTML pattern
- S03: Capture fresh screenshots from M025 demo stack, run Lighthouse audit, verify SEO across all pages

## Files Created/Modified

- `docs/styles.css` — new shared CSS design system (~926 lines): custom properties, dark theme, responsive breakpoints (768px, 480px), nav with persona dropdown, hero, persona cards, comparison table with sticky first column, domain kit cards, feature grid, CTA section, footer, fade-in animations
- `docs/index.html` — full rewrite (~619 lines): outcome-focused homepage with SEO tags, persona selector, competitive comparison, domain kits, condensed features, dual CTAs, canvas animation JS, IntersectionObserver fade-in

## Forward Intelligence

### What the next slice should know
- The nav HTML structure (header with `.nav-links` and persona dropdown) must be replicated exactly in persona pages for consistent site-wide navigation. The footer pattern is simpler — just links and copyright.
- `docs/styles.css` is the single source of truth for all styling. Persona pages should link to it and use the existing component classes (`.hero`, `.section-alt`, `.feature-grid`, `.cta-section`, etc.) rather than adding inline styles.
- The `section-alt` class provides alternating background colors. Use it on every other section for visual rhythm.

### What's fragile
- The nav z-index layering — `.nav` has `position: fixed; z-index: 100` and must NOT be included in any bulk `position/z-index` rule applied to sections. T02 fixed this once; a future CSS edit could reintroduce it.
- Canvas animation bleed-through — the `.hero` section has `background: transparent` to show the canvas, but all other sections MUST have opaque backgrounds (`var(--bg-primary)` or `var(--bg-secondary)`). Adding a new section without a background will let the fixed canvas show through.
- Google Fonts CDN link — if fonts.googleapis.com is unreachable (e.g., China, air-gapped), the site falls back to system fonts. This is graceful but the typography will look different.

### Authoritative diagnostics
- Open `docs/index.html` in any browser and check the Network panel for `styles.css` → 200 status confirms CSS loads correctly
- `document.querySelectorAll('.fade-in.visible').length` in console after scrolling confirms IntersectionObserver
- `python3 -c "from html.parser import HTMLParser; HTMLParser().feed(open('docs/index.html').read()); print('OK')"` confirms HTML well-formedness

### What assumptions changed
- Assumed CSS would be 500-700 lines → actually 926 lines. The responsive breakpoints, comparison table sticky column, and persona dropdown hover states required more CSS than estimated. This is fine — the extra specificity means S02 persona pages need less custom CSS.
- Assumed the email signup form was important → dropped it entirely in favor of demo-first CTAs, which better matches the conversion strategy and the existence of the M025 hosted demo.
