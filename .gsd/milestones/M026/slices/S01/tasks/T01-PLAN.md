---
estimated_steps: 7
estimated_files: 3
---

# T01: Rewrite homepage with shared CSS extraction and outcome-focused content

**Slice:** S01 — Homepage rewrite with outcome-focused messaging
**Milestone:** M026

## Description

Replace the existing 1928-line technology-first `docs/index.html` with an outcome-focused homepage. Extract all CSS to a shared `docs/styles.css` (which S02 persona pages will also consume). Write all new content sections grounded in the messaging strategy from `.gsd/design/USER-CONVERSION-STRATEGY.md`.

The existing site has a dark theme with orange/amber accents, canvas animation background, scroll-based fade-in animations, a screenshot carousel, and a mobile hamburger nav. The new site should preserve the dark theme aesthetic and animation quality while completely rewriting the content structure and messaging.

**Skill to load:** `frontend-design` — this task produces a full landing page with distinctive design.

## Steps

1. **Read the messaging strategy** at `.gsd/design/USER-CONVERSION-STRATEGY.md` for: persona definitions (Tier 1: Obsidian Power Users, Tier 2: Notion Escapees, Tier 3: Fresh Start), competitive positioning table (6×6 matrix), messaging shifts table (current → new), "what not to lead with" rules, and core positioning ("Build knowledge that doesn't decay").

2. **Create `docs/styles.css`** with the complete design system:
   - CSS custom properties (colors, typography, spacing, max-width, border-radius) — keep the dark theme palette (bg `#0a0a0f`/`#12121a`, accent orange `#e8772e`/amber `#f59e0b`, text `#e8e8f0`/`#9898b0`)
   - Base reset, body, link styles
   - Nav: fixed header with blur backdrop, logo, nav links with persona dropdown, hamburger menu for mobile
   - Hero: centered text with gradient accent, two CTA buttons (primary/secondary), tagline
   - Persona selector: 3-card grid that stacks on mobile, each card with icon, title, subtitle, and link
   - Competitive comparison: responsive table with sticky first column on mobile (horizontal scroll fallback), checkmark/strength indicators
   - Domain kits (Mental Models): card grid showing 4-5 model cards with icon, name, type count, description
   - Feature overview: condensed grid (8 cards max) with icon + title + outcome-focused description
   - CTA section: dual buttons with prominent styling
   - Footer: links row with copyright
   - Utility classes: `.fade-in` / `.visible` for scroll animation, `.container` for max-width centering
   - Responsive breakpoints: `@media (max-width: 768px)` for tablet, `@media (max-width: 480px)` for mobile
   - The CSS should be self-contained so persona pages in S02 can link to it and get the full design system

3. **Rewrite `docs/index.html`** with this section structure:
   - `<head>`: charset, viewport, title "SemPKM — Build knowledge that doesn't decay", meta description (outcome-focused, no RDF/SHACL/SPARQL), OG tags (og:title, og:description, og:type, og:url, og:image), link to `styles.css`
   - **Nav**: Logo "SemPKM", links: Why SemPKM, Features, a "Coming From" dropdown with 3 persona links (`from-obsidian.html`, `from-notion.html`, `fresh-start.html`), "Try Demo" CTA button (→ `https://demo.sempkm.app`), User Guide (→ `guide/index.html`), GitHub icon link
   - **Hero**: Heading "Build knowledge that doesn't decay" (or similar from strategy doc), subtitle focusing on outcomes ("Your notes become structured, queryable, and future-proof — and you own every byte"), two CTAs: "Try the Demo" (primary, → `https://demo.sempkm.app`) and "Self-Host with Docker" (secondary, → `guide/20-production-deployment.html` or GitHub README), tagline "Self-hosted · Open source · Powered by open standards"
   - **Persona Selector**: Section label "Find Your Path", 3 cards: "Coming from Obsidian" (vault import, typed frontmatter, graph view), "Coming from Notion" (tables, dashboards, type creation), "Starting Fresh" (pick a Mental Model, guided tour). Each card links to its persona page.
   - **What Makes SemPKM Different**: The competitive comparison table from USER-CONVERSION-STRATEGY.md. 6 capabilities (Structure enforcement, Data ownership, Typed relationships, Queryable views, Audit trail, Plugin ecosystem) × 5 tools (Obsidian, Notion, Tana, Capacities, SemPKM). Use strength indicators (Weak/Medium/Strong or visual checkmarks). SemPKM column highlighted.
   - **Mental Models as Domain Kits**: Section explaining Mental Models without ontology jargon. "Install a domain kit → get types, forms, views, and validation rules instantly." Show 4-5 model cards: Basic PKM (Notes, Projects, Tasks, Events), Personal CRM (Contacts, Companies, Interactions, Deals), Zettelkasten+ (Fleeting → Literature → Permanent → Structure notes), Research Workflow (Papers, Claims, Evidence, Arguments). Each card shows icon + type count + 1-line description.
   - **Feature Overview**: Condensed to ~8 key features with outcome language (NOT "SHACL-Driven Forms" but "Forms that build themselves from your schema"). Keep: Typed Relationships, Graph Visualization, Spatial Canvas, Command Palette, Event Sourcing ("Full history & undo"), WebDAV/Obsidian compatibility, Dark Mode, Dashboards & Workflows.
   - **CTAs bottom**: "Ready to try it?" section with "Try the Demo" + "Self-Host with Docker" + "Read the User Guide" buttons
   - **Footer**: Copyright MetaCoding Solutions LLC 2025, links to User Guide, GitHub, Features, Screenshots

4. **Keep the canvas animation JS** from the existing site — the network graph background in the hero section. Copy the IntersectionObserver fade-in JS and the mobile nav toggle JS. Keep the screenshot carousel JS if screenshots section remains.

5. **Preserve `docs/CNAME`** — do not modify or delete this file. Contents: `sempkm.metacoding.io`.

6. **Content rules** (from USER-CONVERSION-STRATEGY.md "What NOT to Lead With"):
   - NO "RDF", "SHACL", or "SPARQL" in hero, subtitle, or any above-the-fold content
   - NO "semantic web" (academic connotation)
   - NO "event sourcing" (say "full history + undo")
   - NO "OWL inference" (say "automatic relationship discovery")
   - Standards can appear in detail sections BELOW the fold, phrased as "Powered by open standards (RDF, SHACL, SPARQL)" — never as the lead
   - Every feature description should pass: "Would an Obsidian user understand this without knowing what RDF is?"

7. **SEO meta tags** in `<head>`:
   - `<meta name="description" content="...">` — outcome-focused, ~155 chars
   - `<meta property="og:title" content="SemPKM — Build knowledge that doesn't decay">`
   - `<meta property="og:description" content="...">` — same as meta description
   - `<meta property="og:type" content="website">`
   - `<meta property="og:url" content="https://sempkm.metacoding.io">`
   - `<meta property="og:image" content="screenshots/01-workspace-overview-dark.png">`
   - `<meta name="twitter:card" content="summary_large_image">`
   - `<link rel="canonical" href="https://sempkm.metacoding.io">`

## Must-Haves

- [ ] `docs/styles.css` exists with complete design system (colors, typography, layout, responsive, dark theme, all component styles)
- [ ] `docs/index.html` links to `styles.css` (no inline `<style>` block for component styles — small inline CSS for critical path is OK)
- [ ] Hero section has outcome-focused messaging, no RDF/SHACL/SPARQL
- [ ] Two CTAs: "Try the Demo" → `https://demo.sempkm.app`, "Self-host" → Docker quickstart docs
- [ ] 3 persona selector cards linking to `from-obsidian.html`, `from-notion.html`, `fresh-start.html`
- [ ] Competitive comparison table with 5+ tools and 5+ capabilities
- [ ] Mental Models section using "domain kits" framing
- [ ] Nav includes persona dropdown links
- [ ] SEO meta tags and OG tags in `<head>`
- [ ] `docs/CNAME` file untouched

## Verification

- `test -f docs/styles.css && echo "styles.css exists"` — CSS file created
- `grep -c 'styles.css' docs/index.html` — returns ≥ 1
- `python3 -c "html=open('docs/index.html').read(); fold=html[:html.lower().find('persona') if 'persona' in html.lower() else 3000]; assert 'RDF' not in fold and 'SHACL' not in fold and 'SPARQL' not in fold, 'Tech jargon above fold'; print('No tech jargon above fold')"` — passes
- `grep -c 'demo.sempkm.app' docs/index.html` — returns ≥ 1
- `grep -c 'from-obsidian.html' docs/index.html && grep -c 'from-notion.html' docs/index.html && grep -c 'fresh-start.html' docs/index.html` — each returns ≥ 1
- `grep -c 'domain kit' docs/index.html` — returns ≥ 1
- `test -f docs/CNAME && cat docs/CNAME` — shows `sempkm.metacoding.io`

## Inputs

- `.gsd/design/USER-CONVERSION-STRATEGY.md` — messaging strategy, persona definitions, competitive positioning table, "what NOT to lead with" rules, core positioning statement
- `docs/index.html` (current) — existing 1928-line site with dark theme, canvas animation JS, fade-in observer JS, mobile nav toggle JS. **Extract and adapt the JS sections.** The CSS and HTML content is being completely rewritten.
- `docs/screenshots/` — existing screenshot files (referenced by carousel). Current filenames: `01-workspace-overview-dark.png` through `20-bottom-panel-dark.png`
- `docs/CNAME` — must be preserved untouched

## Expected Output

- `docs/styles.css` — complete shared CSS design system (~500-700 lines) with dark theme, responsive breakpoints, all component styles. This file is the S01→S02 boundary contract — persona pages will link to it.
- `docs/index.html` — fully rewritten homepage (~700-1000 lines) with outcome-focused messaging, linked CSS, persona selector, competitive comparison, domain kits section, condensed features, dual CTAs, canvas animation JS, and SEO meta tags.

## Observability Impact

- **New signals:** `docs/styles.css` load status visible in browser DevTools Network panel (200 = success, 404 = missing file).
- **Inspection:** Open `docs/index.html` in any browser → verify all sections render. Run `document.querySelectorAll('.fade-in.visible').length` in console after scrolling to confirm IntersectionObserver is active.
- **Failure visibility:** Missing `styles.css` → unstyled page (immediately obvious). Broken canvas JS → blank hero background. Missing persona links → 404 on click. All failures are visually self-evident.
- **Diagnostic command:** `python3 -c "from html.parser import HTMLParser; HTMLParser().feed(open('docs/index.html').read()); print('OK')"` confirms HTML well-formedness.
