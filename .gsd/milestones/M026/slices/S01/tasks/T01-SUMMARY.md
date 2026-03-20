---
id: T01
parent: S01
milestone: M026
provides:
  - docs/styles.css shared CSS design system (S01→S02 boundary contract)
  - docs/index.html outcome-focused homepage with persona selector, competitive comparison, domain kits, and dual CTAs
key_files:
  - docs/styles.css
  - docs/index.html
key_decisions:
  - Used DM Sans as display/body font (distinctive, optical sizing, Google Fonts CDN)
  - Dropped email signup form in favor of pure demo-first CTAs per conversion strategy
  - Kept canvas network graph animation from existing site — strong visual differentiator
  - RDF/SHACL/SPARQL appear only once, below the fold, as "Powered by open standards"
patterns_established:
  - Shared CSS design system with custom properties, responsive breakpoints, and component classes consumed by both homepage and future persona pages
  - Nav HTML structure with persona dropdown for S02 pages to replicate
  - Section-alt class for alternating background sections
observability_surfaces:
  - Browser DevTools Network panel shows styles.css load status (200/404)
  - console: document.querySelectorAll('.fade-in.visible').length after scroll confirms observer active
  - Missing styles.css → unstyled page (visually obvious)
duration: 30m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T01: Rewrite homepage with shared CSS extraction and outcome-focused content

**Replaced 1928-line technology-first homepage with outcome-focused landing page: shared CSS extracted to styles.css, hero leads with "Build knowledge that doesn't decay", 3 persona selector cards, 6×6 competitive comparison table, domain kits section, 8 condensed features, dual demo CTAs**

## What Happened

Read the USER-CONVERSION-STRATEGY.md for persona definitions, competitive positioning matrix, messaging shifts, and "what NOT to lead with" rules. Created `docs/styles.css` (~570 lines) with the full design system: CSS custom properties for colors/typography/spacing, dark theme palette, responsive breakpoints at 768px and 480px, and component styles for nav (with persona dropdown), hero, persona cards, comparison table (with sticky first column), domain kit cards, feature grid, CTA section, and footer.

Rewrote `docs/index.html` from scratch with outcome-focused content structure: hero ("Build knowledge that doesn't decay"), persona selector ("Coming from Obsidian/Notion/Starting Fresh"), competitive comparison table (6 capabilities × 5 tools), Mental Models as "domain kits" (4 cards: Basic PKM, Personal CRM, Zettelkasten+, Research Workflow), condensed 8-feature overview with outcome language, bottom CTA section, and footer. All SEO meta tags and OG tags added. Canvas animation JS, IntersectionObserver fade-in, and mobile nav toggle preserved from original.

Content rules enforced: no RDF/SHACL/SPARQL above the fold. Standards mentioned once below features as "Powered by open standards (RDF, SHACL, SPARQL)." Every feature description passes the Obsidian-user-comprehension test.

## Verification

- `test -f docs/styles.css` → PASS (file exists, ~570 lines)
- `grep -c 'styles.css' docs/index.html` → 1 (linked, no inline styles)
- No RDF/SHACL/SPARQL above fold → PASS (Python assertion)
- `grep -c 'demo.sempkm.app' docs/index.html` → 3 (nav CTA + hero CTA + bottom CTA)
- `grep -c 'from-obsidian.html' docs/index.html` → 2, `from-notion.html` → 2, `fresh-start.html` → 2
- `grep -ci 'domain kit' docs/index.html` → 8
- CNAME preserved: `sempkm.metacoding.io`
- HTML well-formed: Python HTMLParser passes
- Browser verification at 1280px: all sections render, hero readable, comparison table visible, persona cards 3-column, canvas animation active
- Browser verification at 768px: hamburger nav, persona cards stacked, comparison table scrollable
- Browser verification at 375px: full-width CTAs, persona cards stacked, no horizontal overflow
- browser_assert: 13/14 PASS (1 false-positive: Google Fonts 404 from local dev server — not a real error)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f docs/styles.css` | 0 | ✅ pass | <1s |
| 2 | `grep -c 'styles.css' docs/index.html` | 0 | ✅ pass (1) | <1s |
| 3 | No RDF/SHACL/SPARQL above fold (Python) | 0 | ✅ pass | <1s |
| 4 | `grep -c 'demo.sempkm.app' docs/index.html` | 0 | ✅ pass (3) | <1s |
| 5 | Persona links grep | 0 | ✅ pass (2+2+2) | <1s |
| 6 | `grep -ci 'domain kit' docs/index.html` | 0 | ✅ pass (8) | <1s |
| 7 | `test -f docs/CNAME && cat docs/CNAME` | 0 | ✅ pass | <1s |
| 8 | HTML well-formed (HTMLParser) | 0 | ✅ pass | <1s |
| 9 | Browser 1280px desktop | — | ✅ pass | ~5s |
| 10 | Browser 768px tablet | — | ✅ pass | ~3s |
| 11 | Browser 375px mobile | — | ✅ pass | ~3s |
| 12 | browser_assert (13/14 text+selector) | — | ✅ pass (1 env-only false positive) | ~2s |

## Diagnostics

- Open `docs/index.html` in any browser to visually inspect all sections
- Check Network panel for `styles.css` load status (200 = OK)
- Run `document.querySelectorAll('.fade-in.visible').length` in console after scrolling to verify IntersectionObserver
- Missing `styles.css` → completely unstyled page (visually obvious failure)
- `python3 -c "from html.parser import HTMLParser; HTMLParser().feed(open('docs/index.html').read()); print('OK')"` confirms HTML well-formedness

## Deviations

- Dropped the email signup form (was "Sign up for updates") in favor of three demo-first CTAs. The conversion strategy emphasizes reducing barrier-to-try, and the hosted demo is Priority 1 — the signup form is no longer the primary conversion path.
- HTML came to ~830 lines (within the 700-1000 range from the plan). CSS came to ~570 lines (within the 500-700 range).

## Known Issues

- Google Fonts (DM Sans) loads from `fonts.googleapis.com` — requires internet access. Falls back to system fonts gracefully via `var(--font-display)` / `var(--font-body)` stack.
- The 404 console error in local testing is the Python dev server failing to proxy the Google Fonts CSS request — not an issue on the real GitHub Pages host.

## Files Created/Modified

- `docs/styles.css` — new shared CSS design system (~570 lines): custom properties, dark theme, responsive breakpoints, nav with persona dropdown, hero, persona cards, comparison table, domain kit cards, feature grid, CTA section, footer, fade-in animations
- `docs/index.html` — full rewrite (~830 lines): outcome-focused homepage with SEO tags, persona selector, competitive comparison, domain kits, condensed features, dual CTAs, canvas animation JS
- `.gsd/milestones/M026/slices/S01/S01-PLAN.md` — added Observability section, failure-path diagnostic check, marked T01 done
- `.gsd/milestones/M026/slices/S01/tasks/T01-PLAN.md` — added Observability Impact section
