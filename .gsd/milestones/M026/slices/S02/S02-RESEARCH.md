# S02 — Persona Landing Path Pages — Research

**Date:** 2026-03-20
**Status:** Complete

## Summary

S02 creates three persona landing pages (`docs/from-obsidian.html`, `docs/from-notion.html`, `docs/fresh-start.html`) that the homepage persona selector cards and nav dropdown already link to. These links currently 404. Each page uses the shared `docs/styles.css` design system from S01 and replicates the nav/footer HTML pattern from `docs/index.html`.

This is straightforward work — three HTML files following an established pattern with content sourced from `.gsd/design/USER-CONVERSION-STRATEGY.md`. The CSS design system is comprehensive enough that persona pages need minimal new CSS (only a few persona-specific components like step lists and before/after comparisons). No JS beyond the existing fade-in IntersectionObserver and mobile nav toggle is needed.

## Recommendation

Build all three pages in parallel using `docs/index.html` as the structural template. Each page shares: the same `<head>` (meta tags, font link, styles.css), the same nav HTML, the same footer HTML, the same fade-in JS, and the same mobile nav toggle JS. They differ only in hero content and body sections.

**Build order:** Start with `from-obsidian.html` (richest content — vault import, WebDAV mount, Dataview comparison, graph view), then `from-notion.html` (databases, views, dashboards), then `fresh-start.html` (simplest — domain kit picker, guided tour, onboarding steps). This order matches content complexity and lets the first page establish the persona page template that the other two follow.

## Implementation Landscape

### Key Files

- `docs/index.html` — **Template source.** The nav HTML (lines 36–60), footer HTML (lines 345–368), fade-in JS (lines 370–383), and mobile nav toggle JS (lines 385–395) must be copied identically into each persona page. The canvas animation JS (lines 397+) should also be included for visual consistency across the site.
- `docs/styles.css` — **Shared design system.** Already has all component classes needed: `.hero`, `.section-alt`, `.section-label`, `.section-title`, `.section-subtitle`, `.container`, `.btn-*`, `.comparison-table`, `.features-grid`, `.feature-card`, `.kit-card`, `.kits-grid`, `.cta-section`, `.cta-buttons`, `.fade-in`. Persona pages will need ~60-80 lines of new CSS for persona-specific components (step lists, before/after comparisons, pain-point cards).
- `.gsd/design/USER-CONVERSION-STRATEGY.md` — **Content source.** Contains per-persona messaging, competitive angles, onboarding flows, feature mappings, and "what NOT to lead with" rules. All copy must be derived from this document per D255.

### New Files to Create

- `docs/from-obsidian.html` — Hero: "Everything you built in Dataview — but reliable." Sections: pain points (brittle queries, informal YAML, untyped links), SemPKM answers (vault import, typed frontmatter → schemas, typed relationships, graph view, WebDAV mount), mini comparison table (Obsidian vs SemPKM on 4-5 dimensions), migration steps (upload vault → map frontmatter → explore graph → mount via WebDAV), CTAs.
- `docs/from-notion.html` — Hero: "Everything you love about Notion databases — but enforceable, portable, and future-proof." Sections: pain points (vendor lock-in, performance cliffs, flat relations, optional properties), SemPKM answers (table/card views, dashboards, type creation = "create a database", SHACL forms = enforced property types, self-hosted), mini comparison table (Notion vs SemPKM on 4-5 dimensions), getting started steps, CTAs.
- `docs/fresh-start.html` — Hero: "Pick a workflow, start building." Sections: no-baggage intro, domain kit showcase (reuse `.kits-grid` from homepage with more detail per kit), onboarding path (pick kit → guided tour → create first object → explore views), what you get out of the box, CTAs.

### Shared Structure Per Page

Every persona page follows this skeleton:

```
<!DOCTYPE html>
<html lang="en">
<head>
  [meta charset, viewport, title, description, og tags — persona-specific]
  [Google Fonts preconnect + DM Sans link — identical]
  <link rel="stylesheet" href="styles.css">
  [inline critical CSS for hero fadeUp — identical]
</head>
<body>
  [nav — identical to index.html]
  [canvas#heroGraph — identical]
  
  [hero — persona-specific headline/subtitle/CTA]
  [content sections — persona-specific, using existing CSS classes]
  [CTA section — shared pattern, persona-specific copy]
  
  [footer — identical to index.html]
  [fade-in JS — identical]
  [mobile nav toggle JS — identical]
  [canvas animation JS — identical]
</body>
</html>
```

### CSS Additions Needed in styles.css

A few new component classes for persona page elements not present on the homepage:

1. **`.steps-grid` / `.step-card`** — Numbered step cards for migration/onboarding flows (e.g., "Step 1: Upload your vault"). Similar layout to `.features-grid` / `.feature-card` but with a large step number and sequential visual flow.
2. **`.pain-grid` / `.pain-card`** — Pain point cards showing "the problem" with the user's current tool. Simple grid of short problem statements with icons.
3. **`.before-after`** — Optional side-by-side comparison showing "In Obsidian: ..." vs "In SemPKM: ..." for specific workflows.

These are ~60-80 lines of CSS added to the end of `styles.css`, following existing naming conventions and using existing custom properties.

### Content Derivation from USER-CONVERSION-STRATEGY.md

| Page | Strategy Doc Section | Key Messages |
|------|---------------------|--------------|
| from-obsidian | "Tier 1: Obsidian Power Users", "For Obsidian users", "vs Obsidian", "The Obsidian Refugee Path" | Brittle Dataview → reliable queries; informal YAML → enforced schemas; untyped links → typed relationships; local files → still local (self-hosted) |
| from-notion | "Tier 2: Notion Escapees", "For Notion users", "vs Notion", "The Notion Escapee Path" | Cloud lock-in → self-hosted; optional properties → enforced schemas; flat relations → typed graph; performance cliffs → local speed |
| fresh-start | "The Fresh Start Path", "Mental Model Expansion", "Domain Kits" | Pick a domain kit → instant types/forms/views; guided tour in 3 min; no blank-page syndrome; grow your system over time |

### Build Order

1. **Add new CSS components to `docs/styles.css`** — step cards, pain cards, before-after. This unblocks all three pages.
2. **Build `docs/from-obsidian.html`** — Richest content, establishes the persona page pattern. Proves the template works.
3. **Build `docs/from-notion.html`** — Second page, follows the pattern. Different content, same structure.
4. **Build `docs/fresh-start.html`** — Simplest page, leans heavily on domain kit cards (reuse from homepage).
5. **Browser verification** — Open all three pages at desktop (1280px) and mobile (375px), verify layout, links, no horizontal overflow.

### Verification Approach

```bash
# All three files exist
test -f docs/from-obsidian.html && test -f docs/from-notion.html && test -f docs/fresh-start.html

# All link to shared styles.css
grep -l 'styles.css' docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html

# No RDF/SHACL/SPARQL in hero sections (above the fold)
python3 -c "
import re
for f in ['docs/from-obsidian.html', 'docs/from-notion.html', 'docs/fresh-start.html']:
    content = open(f).read()
    hero = content[:content.index('</section>')] if '</section>' in content else content[:2000]
    for term in ['RDF', 'SHACL', 'SPARQL']:
        assert term not in hero, f'{term} found above fold in {f}'
print('OK — no tech jargon above the fold')
"

# All pages have SEO meta tags
for f in docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html; do
  grep -q 'meta name="description"' "$f" && grep -q 'og:title' "$f" && echo "$f: SEO OK"
done

# All pages have nav with persona dropdown (site-wide consistency)
for f in docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html; do
  grep -q 'nav-dropdown' "$f" && echo "$f: nav OK"
done

# All pages have demo CTA link
grep -c 'demo.sempkm.app' docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html

# HTML well-formedness
python3 -c "
from html.parser import HTMLParser
for f in ['docs/from-obsidian.html', 'docs/from-notion.html', 'docs/fresh-start.html']:
    HTMLParser().feed(open(f).read())
print('All 3 pages: HTML OK')
"

# No conflict markers
grep -rn '<<<<<<< ' docs/from-obsidian.html docs/from-notion.html docs/fresh-start.html || echo 'No conflict markers'

# Browser verification at 3 viewports (manual or Playwright)
# - Desktop 1280px: all sections visible, comparison table renders, CTAs clickable
# - Tablet 768px: grid collapses correctly, nav hamburger works
# - Mobile 375px: single column, no horizontal overflow, buttons full-width
```

## Constraints

- **No build step** — vanilla HTML only. Each page is a self-contained HTML file linking to the shared `styles.css` (D254).
- **Content from strategy doc** — All messaging derived from USER-CONVERSION-STRATEGY.md, not invented (D255).
- **Nav must be identical** — The nav HTML (logo, links, persona dropdown, GitHub, Try Demo CTA) must match `docs/index.html` exactly for site-wide consistency. Persona dropdown links should use relative paths (same directory).
- **Canvas animation included** — The network graph canvas JS should be included on all persona pages for visual consistency. It's ~180 lines of JS but provides the distinctive animated background.

## Common Pitfalls

- **Nav link paths** — Persona pages are siblings of `index.html` in `docs/`. Links to `guide/index.html`, `guide/20-production-deployment.html`, and `styles.css` use the same relative paths as the homepage. But anchor links like `#why` and `#features` that work on the homepage won't work on persona pages — they should either be removed from the nav or changed to `index.html#why`.
- **Nav z-index fragility** — S01 Forward Intelligence warns that `.nav` has `position: fixed; z-index: 100` and must NOT be caught in any bulk position/z-index rule. When adding new CSS, keep nav rules isolated.
- **Canvas bleed-through** — Every section must have an opaque background (`var(--bg-primary)` or `var(--bg-secondary)` via `.section-alt`). The `.hero` section is the only one with `background: transparent`. Adding a section without a background will show the fixed canvas through it.
- **Notion import not shipped** — The from-notion page should NOT promise a Notion import wizard (NOTION-01 is deferred). Focus on "start fresh with SemPKM and get what Notion gives you, but better" rather than "import your Notion workspace."
