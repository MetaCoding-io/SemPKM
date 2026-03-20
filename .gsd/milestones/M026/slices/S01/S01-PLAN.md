# S01: Homepage rewrite with outcome-focused messaging

**Goal:** Replace the technology-first homepage ("Semantics-Native PKM built on RDF/SHACL/SPARQL") with an outcome-focused homepage that leads with user value, persona-specific landing paths, competitive positioning, and CTAs linking to the M025 hosted demo.

**Demo:** Visitor opens `docs/index.html` and sees an outcome-focused hero ("Build knowledge that doesn't decay"), a 3-card persona selector ("Coming from Obsidian" / "Coming from Notion" / "Starting Fresh"), a competitive comparison table (SemPKM vs Obsidian/Notion/Tana/Capacities), Mental Models explained as "domain kits", condensed feature overview, and dual CTAs ("Try the Demo" → M025 instance, "Self-host" → Docker quickstart). All styling is in `docs/styles.css` (shared for S02 persona pages). No mentions of RDF/SHACL/SPARQL in hero or above-the-fold content.

## Must-Haves

- Hero section with outcome-focused messaging — no RDF/SHACL/SPARQL above the fold
- "Try the Demo" CTA linking to `https://demo.sempkm.app`
- "Self-host" CTA linking to Docker quickstart documentation
- 3-card persona selector linking to `/from-obsidian.html`, `/from-notion.html`, `/fresh-start.html`
- Competitive comparison section (SemPKM vs Obsidian/Notion/Tana/Capacities)
- Mental Models explained as "domain kits" (not ontologies)
- Shared CSS extracted to `docs/styles.css`
- Nav structure with persona dropdown links (for S02 to replicate)
- Mobile-responsive at 375px, 768px, 1200px+ viewports
- SEO meta tags and OG tags on the homepage
- CNAME file preserved (`sempkm.metacoding.io`)
- Dark theme consistent with existing design language

## Proof Level

- This slice proves: operational
- Real runtime required: yes (browser rendering verification)
- Human/UAT required: yes (messaging reads as outcome-focused, not technology-focused)

## Verification

- `python3 -c "import re; html=open('docs/index.html').read(); above=html[:html.find('class=\"persona')] if 'persona' in html else html[:3000]; bad=['RDF','SHACL','SPARQL']; hits=[w for w in bad if w in above]; assert not hits, f'Found tech jargon above fold: {hits}'"` — no RDF/SHACL/SPARQL above the fold
- `grep -c 'demo.sempkm.app' docs/index.html` returns ≥ 1 — demo CTA present
- `grep -c 'from-obsidian.html\|from-notion.html\|fresh-start.html' docs/index.html` returns ≥ 3 — persona links present
- `test -f docs/styles.css` — shared CSS extracted
- `grep -c 'styles.css' docs/index.html` returns ≥ 1 — CSS linked (not inline)
- `grep -c 'domain kit' docs/index.html` returns ≥ 1 — Mental Models framed as domain kits
- `test -f docs/CNAME` — CNAME preserved
- Browser verification at 375px, 768px, and 1200px widths — layout renders correctly at all breakpoints
- Competitive comparison table visible with at least 5 capability rows and 5 tool columns
- `python3 -c "from html.parser import HTMLParser; HTMLParser().feed(open('docs/index.html').read()); print('HTML parses OK')"` — HTML well-formedness check (diagnostic/failure-path)

## Integration Closure

- Upstream surfaces consumed: `.gsd/design/USER-CONVERSION-STRATEGY.md` (messaging strategy, persona definitions, competitive positioning table, what-not-to-lead-with rules)
- New wiring introduced in this slice: `docs/styles.css` (shared CSS for all site pages), nav HTML pattern (header/footer for persona pages to replicate)
- What remains before the milestone is truly usable end-to-end: S02 (persona path pages that the nav links point to), S03 (fresh screenshots, Lighthouse audit, comprehensive SEO verification)

## Observability / Diagnostics

- **Runtime signals:** `docs/index.html` is a static site — no server-side runtime. Observability is via browser DevTools: check the Network panel for missing assets (styles.css, screenshots), Console for JS errors from the canvas animation or IntersectionObserver, and Elements panel for correct CSS variable resolution.
- **Inspection surfaces:** Open `docs/index.html` in any browser. Inspect the `<link>` tag to confirm `styles.css` loads (200 status). Check that `document.querySelectorAll('.fade-in.visible').length` grows as you scroll — confirms the IntersectionObserver is running.
- **Failure visibility:** A missing `styles.css` causes unstyled content (visible immediately). A broken canvas animation shows a blank background behind the hero. A missing persona link shows a 404 on click. All failures are visually obvious.
- **Diagnostic command:** `python3 -c "from html.parser import HTMLParser; HTMLParser().feed(open('docs/index.html').read()); print('HTML parses OK')"` — confirms the HTML is well-formed.
- **Failure-path verification:** `grep -c 'onerror\|catch' docs/index.html` — confirms JS error handling exists in signup form and animation code.

## Tasks

- [x] **T01: Rewrite homepage with shared CSS extraction and outcome-focused content** `est:2h`
  - Why: This is the core deliverable — replacing the technology-first homepage with outcome-focused messaging. The CSS must be extracted to a shared file because S02 persona pages will consume it. All content sections (hero, persona selector, competitive comparison, domain kits, features, CTAs) must be written in a single cohesive pass because CSS classes and HTML structure are co-designed.
  - Files: `docs/styles.css` (new), `docs/index.html` (rewrite)
  - Do: Write `docs/styles.css` with the full design system (colors, typography, layout, responsive breakpoints, dark theme, animations, component styles for persona cards, comparison table, feature grid, CTAs). Rewrite `docs/index.html` to link to styles.css instead of inline styles, with new content sections grounded in USER-CONVERSION-STRATEGY.md. Keep the canvas animation and fade-in JS. Add SEO meta tags and OG tags. Nav must include persona dropdown links. All messaging passes the test: "Would an Obsidian user understand this without knowing what RDF is?"
  - Verify: `test -f docs/styles.css && grep 'styles.css' docs/index.html && python3 -c "html=open('docs/index.html').read(); assert 'demo.sempkm.app' in html; assert 'from-obsidian.html' in html; assert 'domain kit' in html; print('OK')"`
  - Done when: `docs/styles.css` exists with complete design system, `docs/index.html` renders with outcome-focused hero, persona selector, competitive comparison, domain kits section, condensed features, and dual CTAs — no RDF/SHACL/SPARQL above the fold

- [x] **T02: Browser verification at 3 responsive breakpoints and fix issues** `est:45m`
  - Why: T01 produces ~1500 lines of HTML/CSS that must render correctly at mobile (375px), tablet (768px), and desktop (1200px+) widths. Browser verification catches layout bugs, broken responsive breakpoints, truncated text, and invisible elements that static analysis cannot detect.
  - Files: `docs/styles.css` (fixes), `docs/index.html` (fixes)
  - Do: Open `docs/index.html` in browser. Verify at 1200px+ (desktop), 768px (tablet), and 375px (mobile). Check: hero text readable and centered, persona cards stack vertically on mobile, comparison table scrollable on narrow screens, nav hamburger menu works, all CTAs visible and tappable, no horizontal overflow, footer links present. Fix any issues found.
  - Verify: Browser screenshots at all 3 widths show correct rendering. `grep -rn "^<<<<<<< " docs/ --include="*.html" --include="*.css"` returns zero results (no conflict markers).
  - Done when: Homepage renders correctly at 375px, 768px, and 1200px+ with no layout issues, all CTAs visible, persona cards responsive, comparison table usable on mobile

## Files Likely Touched

- `docs/styles.css` (new — shared CSS extracted from inline styles + new component styles)
- `docs/index.html` (full rewrite — new content, linked CSS, updated nav, SEO tags)
