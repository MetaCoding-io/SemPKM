# M026: Homepage & Messaging Rewrite

**Vision:** Replace the technology-first homepage ("Semantics-Native PKM built on RDF/SHACL/SPARQL") with an outcome-focused site that leads with user value, persona-specific landing paths, competitive positioning, and CTAs linking to the M025 hosted demo — removing messaging as a conversion barrier.

## Success Criteria

- Visitor lands on homepage and reads outcome-focused hero messaging (not "RDF-native PKM")
- Visitor sees a persona selector with 3 paths: "Coming from Obsidian" / "Coming from Notion" / "Starting Fresh"
- Clicking a persona path opens a dedicated page with tailored messaging for that audience
- "Try the Demo" CTA links to the M025 demo instance and is reachable
- "Self-host" CTA links to Docker quickstart instructions
- Competitive comparison section shows SemPKM vs Obsidian/Notion/Tana/Capacities
- Mental Models explained as "domain kits" without requiring ontology knowledge
- No mentions of RDF/SHACL/SPARQL in hero or above-the-fold content on any page
- Homepage loads in under 2 seconds on mobile (Lighthouse audit)
- All pages are mobile-responsive and render correctly at 375px, 768px, and 1200px+ widths
- SEO basics: meta description, OG tags, structured data present on all pages

## Key Risks / Unknowns

- **Messaging effectiveness** — The copy is based on USER-CONVERSION-STRATEGY.md but hasn't been tested with real users. May need iteration post-launch. Low technical risk but high uncertainty on conversion impact.
- **Screenshot staleness** — Existing screenshots show v2.0-era UI. Many features shipped since then. Fresh screenshots require a running Docker stack with populated demo data.

## Proof Strategy

- Messaging effectiveness → not retirable by code — mitigated by grounding all copy in USER-CONVERSION-STRATEGY.md competitive analysis. Plan for easy content updates (no build step).
- Screenshot staleness → retire in S03 by capturing fresh screenshots from the M025 demo Docker stack.

## Verification Classes

- Contract verification: HTML validation, link checking (all CTAs resolve), Lighthouse audit for performance and SEO
- Integration verification: Demo link works (M025 instance reachable), self-host link resolves to Docker quickstart docs, user guide link resolves
- Operational verification: Page loads under 2s on mobile, no broken images, responsive at 3 breakpoints
- UAT / human verification: Messaging reads as outcome-focused, not technology-focused. No RDF/SHACL/SPARQL in hero or above-the-fold content.

## Milestone Definition of Done

This milestone is complete only when all are true:

- All 3 slice deliverables complete (homepage rewrite, persona pages, polish/screenshots)
- Homepage deployed to `docs/` directory with CNAME preserved
- All 4 HTML pages (index, from-obsidian, from-notion, fresh-start) render correctly
- Shared CSS extracted and linked from all pages
- "Try the Demo" CTA links to live M025 demo instance
- "Self-host" CTA links to Docker quickstart documentation
- Competitive comparison table present and accurate
- Mental Models section uses "domain kits" framing
- No RDF/SHACL/SPARQL in hero or above-the-fold content on any page
- Mobile responsive verified at 375px, 768px, 1200px+
- Lighthouse mobile score ≥ 90 for performance
- SEO meta tags and OG tags on all pages
- Screenshots reflect current UI state
- Success criteria re-checked against live pages in browser

## Requirement Coverage

- Covers: SITE-01 (homepage rewrite), SITE-02 (persona paths), SITE-03 (competitive positioning), SITE-04 (Mental Models as domain kits), SITE-05 (updated screenshots), SITE-06 (mobile responsive + performance), SITE-07 (SEO basics)
- Partially covers: none
- Leaves for later: none
- Orphan risks: none — SITE-04 through SITE-07 are quality attributes naturally embedded in the homepage and persona page work

**Note:** SITE-01 through SITE-07 are new requirements identified during M026 research. They do not exist in REQUIREMENTS.md yet and should be registered during execution.

## Slices

- [x] **S01: Homepage rewrite with outcome-focused messaging** `risk:medium` `depends:[]`
  > After this: Visitor opens docs/index.html and sees outcome-focused hero, persona selector cards, competitive comparison table, condensed feature overview, "Try the Demo" and "Self-host" CTAs — all with shared CSS extracted to docs/styles.css

- [ ] **S02: Persona landing path pages** `risk:low` `depends:[S01]`
  > After this: Visitor clicks "Coming from Obsidian" / "Coming from Notion" / "Starting Fresh" on homepage and lands on dedicated pages with tailored messaging, feature comparisons, and CTAs specific to their background

- [ ] **S03: Screenshots, mobile polish, and SEO verification** `risk:low` `depends:[S01,S02]`
  > After this: All pages have fresh screenshots from current UI, pass Lighthouse mobile audit (≥90 performance), have complete SEO meta tags and OG images, all links verified working, responsive layout confirmed at 3 breakpoints

## Boundary Map

### S01 → S02

Produces:
- `docs/styles.css` — shared CSS extracted from inline styles, providing the complete design system (colors, typography, layout, responsive breakpoints, dark theme, animations) for all site pages
- `docs/index.html` — rewritten homepage with nav structure including persona dropdown links pointing to `/from-obsidian.html`, `/from-notion.html`, `/fresh-start.html`
- Nav HTML pattern — header/footer structure that persona pages will replicate for consistent site-wide navigation

Consumes:
- nothing (first slice)

### S01 → S03

Produces:
- `docs/styles.css` — shared CSS (same as above)
- `docs/index.html` — homepage with screenshot carousel placeholder sections ready for updated images
- Site structure and navigation pattern established

Consumes:
- nothing (first slice)

### S02 → S03

Produces:
- `docs/from-obsidian.html`, `docs/from-notion.html`, `docs/fresh-start.html` — 3 persona pages with screenshot placeholders and content sections needing SEO tags
- Complete set of pages requiring mobile/SEO verification

Consumes:
- `docs/styles.css` and nav pattern from S01
