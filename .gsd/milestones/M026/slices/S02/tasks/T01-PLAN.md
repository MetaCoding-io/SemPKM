---
estimated_steps: 6
estimated_files: 2
---

# T01: Add persona CSS components and build from-obsidian.html

**Slice:** S02 — Persona landing path pages
**Milestone:** M026

## Description

This task adds new CSS component classes to the shared `docs/styles.css` (step cards, pain cards, before-after comparisons) and creates the first persona landing page `docs/from-obsidian.html`. This page is the richest content-wise and establishes the template pattern that T02 will follow for the other two pages.

The Obsidian persona page targets Tier 1 users from USER-CONVERSION-STRATEGY.md — power users frustrated by brittle Dataview queries and informal YAML frontmatter. The hero leads with "Everything you built in Dataview — but reliable." Content sections cover pain points, SemPKM answers, a mini comparison table (Obsidian vs SemPKM), migration steps, and CTAs.

**Relevant skill:** `frontend-design` — load this skill for guidance on creating distinctive, production-grade HTML/CSS.

## Steps

1. **Add CSS components to `docs/styles.css`** — append ~60-80 lines at the end of the file for:
   - `.steps-grid` / `.step-card` — numbered step cards for migration/onboarding flows. Similar layout to `.features-grid` / `.feature-card` but with a large step number (`.step-number`) and sequential visual flow. Grid: `repeat(auto-fit, minmax(220px, 1fr))` with gap. Step number: large font, accent color, semi-bold.
   - `.pain-grid` / `.pain-card` — pain point cards showing "the problem" with the user's current tool. Grid of short problem statements. Card has a subtle left border in a warning/red color, padding, background.
   - `.before-after` — optional side-by-side comparison section. Two columns (`.before-col`, `.after-col`) with labeled headers ("In Obsidian" / "In SemPKM"), responsive stack on mobile.
   - All new classes must use existing custom properties from styles.css (colors, spacing, fonts).
   - Responsive: stack to single column at 768px breakpoint (matching existing pattern).

2. **Create `docs/from-obsidian.html`** with this structure:

   **`<head>`** — Copy the `<head>` pattern from `docs/index.html` but with persona-specific content:
   - `<title>SemPKM — Coming from Obsidian</title>`
   - `<meta name="description" content="Everything you built in Dataview — but reliable. Import your vault, get typed properties, enforced schemas, and a real graph view. Self-hosted, open source.">` 
   - OG tags: `og:title`, `og:description`, `og:type=website`, `og:url`
   - Same Google Fonts preconnect + DM Sans link
   - Same `<link rel="stylesheet" href="styles.css">`
   - Same inline critical CSS for hero fadeUp animation

   **`<body>`** — Structure:

   a. **Nav** — Copy nav HTML from `docs/index.html` identically, but change anchor links:
      - `href="#why"` → `href="index.html#why"`
      - `href="#features"` → `href="index.html#features"`
      - `href="#personas"` → `href="index.html#personas"`
      - Keep `from-obsidian.html`, `from-notion.html`, `fresh-start.html` links as-is (relative siblings)
      - Keep `guide/index.html`, GitHub, and `demo.sempkm.app` links as-is

   b. **Canvas** — `<canvas class="hero-graph" id="heroGraph"></canvas>` (identical)

   c. **Hero section** — class="hero":
      - Headline: "Everything you built in Dataview —<br><span class="gradient">but reliable</span>"
      - Subtitle: "Import your Obsidian vault. Your YAML frontmatter becomes typed properties. Your wiki-links become typed relationships. Your queries actually work at scale."
      - CTA buttons: "Try the Demo" (btn-primary → demo.sempkm.app) + "Self-Host with Docker" (btn-secondary → guide/20-production-deployment.html)

   d. **Pain points section** — class="section-alt":
      - Section label: "Sound Familiar?"
      - Title: "The problems Obsidian power users know too well"
      - `.pain-grid` with 4 `.pain-card` items:
        1. "Dataview queries break when you rename a frontmatter key"
        2. "YAML frontmatter is informal — nothing stops you from putting a string where a date should be"
        3. "Wiki-links are untyped — 'linked from' tells you nothing about the relationship"
        4. "Your vault works great at 500 notes. At 5,000, queries slow and consistency crumbles"

   e. **SemPKM answers section**:
      - Section label: "How SemPKM Solves This"
      - Title: "Your vault, but with structure that holds"
      - `.features-grid` with 4-6 `.feature-card` items covering:
        - Vault import (upload ZIP, frontmatter mapping, wiki-link resolution)
        - Typed properties (YAML → schema-enforced fields, validation catches mistakes)
        - Typed relationships (not just "linked from" but the type, direction, provenance)
        - Graph view (Cytoscape.js with type-based styling, multiple layouts)
        - WebDAV mount (browse alongside your vault in Obsidian)
        - Full history (every change tracked, undo anything)

   f. **Mini comparison table** — using existing `.comparison-table` class:
      - 2 columns: Obsidian vs SemPKM
      - 5-6 rows: Structure enforcement, Typed links, Query reliability, Full history, Data ownership, WebDAV access
      - Use existing `.str-weak`, `.str-strong`, `.str-medium` classes

   g. **Migration steps section** — class="section-alt":
      - Section label: "Get Started"
      - Title: "From vault to structured knowledge in 4 steps"
      - `.steps-grid` with 4 `.step-card` items:
        1. Upload your vault (ZIP import)
        2. Map frontmatter to types (SemPKM suggests mappings)
        3. Explore your graph (see typed relationships)
        4. Mount via WebDAV (edit in Obsidian side-by-side)

   h. **CTA section** — reuse `.cta-section` pattern:
      - "Ready to upgrade your vault?"
      - "Stop fighting Dataview. Start building structured knowledge."
      - Three CTAs: Try Demo, Self-Host, Read User Guide

   i. **Footer** — identical to `docs/index.html`, but anchor links (`#features`, `#kits`) changed to `index.html#features`, `index.html#kits`

   j. **JS blocks** — Copy all three JS blocks from `docs/index.html` identically:
      - Fade-in IntersectionObserver
      - Mobile nav toggle
      - Canvas animation

3. **Verify the page opens in browser** — run `python3 -m http.server 8899 -d docs &` and open in browser briefly to confirm no obvious structural issues. Kill the server after.

## Must-Haves

- [ ] New CSS classes (`.steps-grid`, `.step-card`, `.pain-grid`, `.pain-card`) added to `docs/styles.css`
- [ ] `docs/from-obsidian.html` created with all sections
- [ ] Nav has corrected anchor links (prefixed with `index.html#`)
- [ ] Footer has corrected anchor links
- [ ] SEO meta tags present (title, description, og:title, og:description)
- [ ] "Try the Demo" links to `https://demo.sempkm.app`
- [ ] "Self-Host" links to `guide/20-production-deployment.html`
- [ ] No RDF/SHACL/SPARQL in hero section
- [ ] All messaging derived from USER-CONVERSION-STRATEGY.md Obsidian sections
- [ ] Every non-hero section has an opaque background (prevents canvas bleed-through)
- [ ] Canvas animation JS, fade-in JS, mobile nav toggle JS included

## Verification

- `test -f docs/from-obsidian.html && echo "file exists"`
- `grep -q 'styles.css' docs/from-obsidian.html && echo "links to styles.css"`
- `grep -q 'demo.sempkm.app' docs/from-obsidian.html && echo "has demo CTA"`
- `grep -q 'og:title' docs/from-obsidian.html && echo "has OG tags"`
- `grep -q 'nav-dropdown' docs/from-obsidian.html && echo "has nav"`
- `python3 -c "from html.parser import HTMLParser; HTMLParser().feed(open('docs/from-obsidian.html').read()); print('HTML OK')"`
- `python3 -c "c=open('docs/from-obsidian.html').read(); h=c[:c.index('</section>')]; assert 'RDF' not in h and 'SHACL' not in h and 'SPARQL' not in h; print('No tech jargon above fold')"`
- `python3 -c "import re; c=open('docs/from-obsidian.html').read(); bare=re.findall(r'href=\"#(why|features|personas|kits)\"', c); assert len(bare)==0, f'bare anchors: {bare}'; print('Anchor links OK')"`
- `grep -c 'steps-grid\|step-card\|pain-grid\|pain-card' docs/styles.css` → at least 4 matches (new CSS classes present)

## Inputs

- `docs/styles.css` — existing shared CSS design system (~926 lines) to append new components to
- `docs/index.html` — nav/footer/JS pattern to replicate (with anchor link corrections)
- `.gsd/design/USER-CONVERSION-STRATEGY.md` — content source for Obsidian persona messaging (Tier 1, "The Obsidian Refugee Path", competitive angles vs Obsidian)

Key content from USER-CONVERSION-STRATEGY.md for Obsidian persona:
- **Hero:** "Everything you built in Dataview — but reliable"
- **vs Obsidian:** "Typed links, enforced schemas, real queries. And you keep your Markdown."
- **Pain points:** Brittle Dataview, informal YAML, untyped links, scale issues
- **Answers:** Vault import, typed frontmatter → schemas, typed relationships, graph view, WebDAV mount
- **Path:** Upload vault → Map frontmatter → Explore graph → Mount via WebDAV
- **What NOT to lead with:** RDF, SHACL, SPARQL, "Semantic web", event sourcing

Key pattern from S01 Forward Intelligence:
- Nav `.nav` has `position: fixed; z-index: 100` — must NOT be in any bulk position/z-index rule
- Every section except `.hero` must have opaque background to prevent canvas bleed-through
- `section-alt` class provides alternating background colors

## Observability Impact

- **What signals change:** New CSS classes (`.steps-grid`, `.step-card`, `.pain-grid`, `.pain-card`) become available in the design system — detectable via `grep` on `docs/styles.css`. New persona page at `docs/from-obsidian.html` becomes accessible via HTTP.
- **How a future agent inspects this task:** `test -f docs/from-obsidian.html` confirms file exists. `python3 -m http.server -d docs` + browser visit confirms rendering. `grep` checks verify SEO tags, nav links, CTA links, and absence of tech jargon above fold.
- **Failure state visibility:** Missing CSS classes → unstyled step/pain cards (visible on page load). Bare anchor links → scroll-to-nothing on persona page (detectable via regex check). Missing SEO meta → blank social previews. JS errors → visible in browser console.

## Expected Output

- `docs/styles.css` — extended with ~60-80 lines of new CSS component classes at the end
- `docs/from-obsidian.html` — complete persona landing page (~500-600 lines) with all content sections, SEO tags, nav/footer, and JS
