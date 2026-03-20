---
id: M026
provides:
  - docs/index.html — outcome-focused homepage replacing technology-first messaging
  - docs/styles.css — shared CSS design system (1109 lines) with responsive breakpoints, dark theme, component styles
  - docs/from-obsidian.html — persona landing page for Obsidian users (536 lines)
  - docs/from-notion.html — persona landing page for Notion users (536 lines)
  - docs/fresh-start.html — persona landing page for newcomers (510 lines)
  - 5 fresh screenshots from M025 demo stack reflecting current UI state
  - Complete SEO suite: meta descriptions, OG tags with absolute URLs, JSON-LD structured data on all 4 pages
  - Deferred Google Fonts loading pattern (media="print" onload) achieving 0.99 Lighthouse mobile score
key_decisions:
  - D254: No static site generator — vanilla HTML/CSS/JS in-place rewrite
  - D255: All messaging grounded in USER-CONVERSION-STRATEGY.md, not invented
  - D256: SITE-01 through SITE-07 requirement IDs for homepage scope
  - D257: Screenshots captured from M025 demo stack, not fresh Docker build
patterns_established:
  - Shared CSS design system with custom properties, responsive breakpoints (768px, 480px), and reusable component classes
  - Persona page template pattern: nav with index.html# prefixed anchors, canvas animation, hero, pain-grid, features, comparison, steps, CTA, footer
  - Section backgrounds use opaque var(--bg-primary) to prevent canvas animation bleed-through; hero stays transparent
  - Deferred Google Fonts via media="print" onload="this.media='all'" with noscript fallback
  - JSON-LD structured data template (Organization + WebSite @graph) reusable across site pages
observability_surfaces:
  - Browser DevTools Network: styles.css load status (200 = OK, 404 = broken)
  - Console: document.querySelectorAll('.fade-in.visible').length after scroll confirms IntersectionObserver
  - grep -c 'og:image.*https://sempkm.metacoding.io' docs/*.html → expect 4
  - grep -c 'application/ld+json' docs/*.html → expect 4
  - python3 -m http.server 8080 --directory docs/ then npx lighthouse for audit
requirement_outcomes:
  - id: SITE-01
    from_status: active
    to_status: validated
    proof: docs/index.html fully rewritten with outcome-focused messaging, all CTAs working, shared CSS, SEO tags, fresh screenshots
  - id: SITE-02
    from_status: active
    to_status: validated
    proof: 3 persona pages (from-obsidian, from-notion, fresh-start) with tailored messaging, feature comparisons, persona-specific CTAs
  - id: SITE-03
    from_status: active
    to_status: validated
    proof: 6-capability × 5-tool comparison table on homepage, persona-specific mini-comparisons on each landing page
  - id: SITE-04
    from_status: active
    to_status: validated
    proof: "Domain kits" framing used throughout (8 mentions on homepage), no ontology jargon above the fold
  - id: SITE-05
    from_status: active
    to_status: validated
    proof: 5 fresh screenshots from demo stack dated 2026-03-20 (workspace overview, explorer types, command palette, canvas, object read)
  - id: SITE-06
    from_status: active
    to_status: validated
    proof: Lighthouse default mobile audit 0.99 (FCP 1.6s, LCP 1.6s, TBT 0ms). Responsive verified at 375px, 768px, 1200px+
  - id: SITE-07
    from_status: active
    to_status: validated
    proof: meta descriptions on all 4 pages, og:image with absolute URLs on all 4, JSON-LD (Organization + WebSite) on all 4
duration: 110m
verification_result: passed
completed_at: 2026-03-20
---

# M026: Homepage & Messaging Rewrite

**Replaced the technology-first homepage with an outcome-focused marketing site: shared CSS design system, hero leading with "Build knowledge that doesn't decay", 3 persona landing pages (Obsidian/Notion/Fresh Start), competitive comparison table, "domain kits" framing for Mental Models, dual demo/self-host CTAs, 5 fresh screenshots, Lighthouse 0.99 mobile score, complete SEO tags — zero RDF/SHACL/SPARQL above the fold on any page.**

## What Happened

**S01 (55m)** rewrote the homepage from scratch. The old 1928-line `docs/index.html` led with "Semantics-Native PKM built on RDF/SHACL/SPARQL" — exactly the wrong message for the target audience. The new 619-line page leads with "Build knowledge that doesn't decay" and organizes content around user outcomes. A shared CSS design system (`docs/styles.css`, 1109 lines) was extracted with custom properties, responsive breakpoints at 768px and 480px, dark theme palette, and component styles for the nav (with persona dropdown hover menu), hero, persona selector cards, comparison table (with sticky first column for mobile), domain kit cards, feature grid, CTA section, and footer. The competitive comparison table covers 6 capabilities across 5 tools (SemPKM, Obsidian, Notion, Tana, Capacities). Mental Models are framed as "domain kits" — 4 cards (Basic PKM, Personal CRM, Zettelkasten+, Research Workflow) with no ontology jargon. RDF/SHACL/SPARQL appear only once on the entire homepage, below the fold, as "Powered by open standards." Browser verification at 3 viewports caught and fixed 3 CSS issues: nav z-index conflict from a bulk position/z-index rule, canvas animation bleed-through into non-hero sections, and mobile hamburger menu backdrop-filter transparency.

**S02 (50m)** built the 3 persona landing pages consuming the shared CSS and replicating the nav pattern from S01. `from-obsidian.html` targets power users frustrated with Dataview fragility, informal YAML, and untyped links — messaging frames SemPKM as "Everything you built in Dataview — but reliable." `from-notion.html` targets users hitting Notion's vendor lock-in and flat relations — messaging frames SemPKM as "Everything you love about Notion databases — but yours to keep." `fresh-start.html` targets newcomers with no migration baggage — messaging leads with "Pick a workflow, start building" and showcases the 4 domain kits with expanded descriptions and "Best for" audience targeting. Each page follows the established template: persona-specific hero, pain points with red-accent cards, SemPKM feature answers, mini comparison table, numbered migration/onboarding steps, and dual CTAs. All pages link to `styles.css`, have persona-specific SEO meta tags, and replicate the nav/footer pattern. ~130 lines of new CSS added for pain-grid, step-card, and before-after components. The S02 slice summary was a doctor-created placeholder, but task summaries (T01, T02) are authoritative and confirm full delivery with browser verification at desktop and mobile viewports.

**S03 (55m)** polished SEO, captured screenshots, and ran final verification. Fixed 8 broken internal links across all 4 pages (guide/20-production-deployment.html → guide/index.html). Added absolute og:image URLs to all 4 pages (homepage had relative, persona pages had none). Added JSON-LD structured data (Organization + WebSite `@graph`) to all 4 pages. Captured 5 fresh screenshots from the M025 demo Docker stack (seeded with 74 objects): workspace overview, explorer types tree, command palette overlay, spatial canvas, and object read view. Applied deferred Google Fonts loading (`media="print" onload="this.media='all'"` with noscript fallback) to all 4 pages, dropping Total Blocking Time from 750ms to 60ms. Lighthouse default mobile audit scored 0.99 (FCP 1.6s, LCP 1.6s, TBT 0ms, CLS 0.022). Responsive layout verified at 375px, 768px, and 1200px with browser assertions confirming no horizontal overflow, all CTAs visible, hamburger menu at mobile, full nav at desktop.

## Cross-Slice Verification

| # | Success Criterion | Evidence | Result |
|---|-------------------|----------|--------|
| 1 | Outcome-focused hero messaging (not "RDF-native PKM") | Hero says "Build knowledge that doesn't decay"; Python regex confirms zero RDF/SHACL/SPARQL in hero | ✅ pass |
| 2 | Persona selector with 3 paths | 6 persona links in index.html (2 per persona: nav dropdown + selector cards) | ✅ pass |
| 3 | Dedicated persona pages with tailored messaging | from-obsidian.html (536 lines), from-notion.html (536 lines), fresh-start.html (510 lines) exist with persona-specific content | ✅ pass |
| 4 | "Try the Demo" CTA links to M025 demo | 3 demo.sempkm.app links per page (nav + hero + bottom CTA) across all 4 pages | ✅ pass |
| 5 | "Self-host" CTA links to Docker quickstart | guide/index.html links present on all pages | ✅ pass |
| 6 | Competitive comparison section | 6 capabilities × 5 tools (SemPKM, Obsidian, Notion, Tana, Capacities) on homepage | ✅ pass |
| 7 | Mental Models as "domain kits" | 8 "domain kit" mentions on homepage, no ontology jargon above fold | ✅ pass |
| 8 | No RDF/SHACL/SPARQL above the fold | Python regex check on all 4 HTML files returns zero above-fold matches | ✅ pass |
| 9 | Homepage loads < 2s on mobile | Lighthouse 0.99: FCP 1.6s, LCP 1.6s, TBT 0ms | ✅ pass |
| 10 | Mobile responsive at 375px, 768px, 1200px+ | Browser assertions at all 3 breakpoints — no overflow, CTAs visible, hamburger at mobile | ✅ pass |
| 11 | SEO: meta description, OG tags, structured data | meta description × 4, og:image (absolute URL) × 4, JSON-LD × 4 | ✅ pass |
| 12 | Screenshots reflect current UI | 5 fresh screenshots from demo stack dated 2026-03-20 | ✅ pass |
| 13 | CNAME preserved | docs/CNAME = sempkm.metacoding.io | ✅ pass |
| 14 | Shared CSS linked from all pages | styles.css (1109 lines) linked from all 4 HTML files | ✅ pass |

All 14 definition-of-done items verified with on-disk evidence and browser assertions.

## Requirement Changes

- SITE-01: active → validated — homepage fully rewritten with outcome-focused messaging, shared CSS, all content sections, SEO tags, fresh screenshots
- SITE-02: active → validated — 3 persona landing pages built with tailored messaging, feature comparisons, persona-specific CTAs linked from homepage selector
- SITE-03: active → validated — 6×5 competitive comparison table on homepage, persona-specific mini-comparisons on each landing page
- SITE-04: active → validated — "domain kits" framing throughout (8 mentions on homepage), no ontology jargon above the fold on any page
- SITE-05: active → validated — 5 fresh screenshots captured from M025 demo stack (workspace overview, explorer types, command palette, canvas, object read)
- SITE-06: active → validated — Lighthouse default mobile audit 0.99 (≥0.90 threshold), responsive verified at 375px, 768px, 1200px+
- SITE-07: active → validated — meta descriptions, OG tags with absolute og:image URLs, JSON-LD structured data (Organization + WebSite) on all 4 pages

## Forward Intelligence

### What the next milestone should know
- The docs/ directory is a static site served by GitHub Pages with no build step. 4 HTML files + 1 CSS file + screenshots. All styling via `docs/styles.css` custom properties — easy to update colors/typography without touching HTML.
- The persona page template is established: hero, pain points, features, comparison, steps, CTA. Adding a 4th persona page (e.g., "Coming from Tana") would take ~30 minutes following the pattern.
- Screenshot paths are hardcoded in HTML. The og:image on all 4 pages references `screenshots/01-workspace-overview-dark.png`. If that file changes name, all 4 pages break their social previews.
- The demo link (demo.sempkm.app) appears 12+ times across all pages. If the demo domain changes, a bulk find-replace is needed.

### What's fragile
- **Nav z-index layering** — `.nav` has `position: fixed; z-index: 100` and must NOT be included in any bulk position/z-index rule. S01/T02 fixed this once; a future CSS edit could reintroduce it.
- **Canvas animation bleed-through** — `.hero` has `background: transparent` to show the canvas; all other sections MUST have opaque backgrounds. A new section without a background will let the canvas show through.
- **Google Fonts deferred loading** — uses `media="print" onload="this.media='all'"`. If a future editor removes the `onload` attribute, fonts won't load (media stays "print").
- **S02 slice summary is a doctor-created placeholder** — task summaries (T01, T02) are the authoritative records for S02 work.

### Authoritative diagnostics
- `python3 -m http.server 8080 --directory docs/` → open in browser to visually inspect all 4 pages
- `grep -c 'og:image.*https://sempkm.metacoding.io' docs/*.html` → should return 4
- `grep -c 'application/ld+json' docs/*.html` → should return 4
- `npx lighthouse http://localhost:8080/index.html --output=json` → check categories.performance.score ≥ 0.90

### What assumptions changed
- **CSS size**: estimated 500–700 lines → actual 1109 lines. Responsive breakpoints, comparison table sticky column, persona dropdown, and the 3 new persona page components (pain-grid, step-card, before-after) required more CSS than scoped. This is fine — the extra specificity means new pages need less custom CSS.
- **Email signup form dropped**: the existing site had an email signup CTA. Replaced entirely with demo-first CTAs matching the M025 conversion strategy.
- **Graph/table/dashboard screenshots not feasible**: the workspace view system opens view spec IRIs as editable objects rather than rendering them. Only workspace-centric screenshots were captured. Not an M026 issue — it's a pre-existing view system limitation.

## Files Created/Modified

- `docs/index.html` — full rewrite (~619 lines → final with SEO fixes): outcome-focused homepage with hero, persona selector, comparison table, domain kits, features, dual CTAs, canvas animation, deferred fonts, og:image, JSON-LD
- `docs/styles.css` — new shared CSS design system (1109 lines): custom properties, dark theme, responsive breakpoints, nav with persona dropdown, hero, persona cards, comparison table, domain kit cards, feature grid, CTA section, pain-grid, step-card, before-after components
- `docs/from-obsidian.html` — new persona page (536 lines): Obsidian user messaging, pain points, feature comparison, migration steps
- `docs/from-notion.html` — new persona page (536 lines): Notion user messaging, pain points, feature comparison, getting started steps
- `docs/fresh-start.html` — new persona page (510 lines): newcomer messaging, domain kit showcase, onboarding path
- `docs/screenshots/01-workspace-overview-dark.png` — fresh screenshot (og:image reference)
- `docs/screenshots/02-explorer-types-dark.png` — fresh screenshot
- `docs/screenshots/04-command-palette-dark.png` — fresh screenshot
- `docs/screenshots/05-canvas-dark.png` — fresh screenshot
- `docs/screenshots/06-object-read.png` — fresh screenshot
