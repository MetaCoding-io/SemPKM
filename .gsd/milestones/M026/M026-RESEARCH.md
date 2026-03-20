# M026 — Homepage & Messaging Rewrite — Research

**Date:** 2026-03-20
**Status:** Complete

## Summary

M026 replaces the existing `docs/index.html` homepage — a 1928-line single-file site that leads with "Semantics-Native Personal Knowledge Management" and mentions "RDF, SHACL, and SPARQL" in the hero subtitle — with an outcome-focused homepage featuring persona-specific landing paths, competitive positioning, and CTAs linking to the M025 hosted demo.

The existing site is well-built technically (dark theme, responsive, carousel, canvas animation, fade-in scroll) but its messaging is exactly what the USER-CONVERSION-STRATEGY.md identifies as the conversion barrier: technology-first language that scares away the target audience. The rewrite is primarily a **content and information architecture** change, not a technology change. The same static-site deployment (GitHub Pages via `docs/` directory with CNAME `sempkm.app`) can serve the new content.

The main risk is scope creep — the temptation to rebuild the entire site infrastructure (add a static site generator, build system, component library) when the core need is new copy, restructured sections, and 3 persona path pages. The existing vanilla HTML/CSS/JS approach is sufficient and consistent with the project's "no build step" philosophy.

## Recommendation

**Rewrite `docs/index.html` in-place** with new messaging, persona paths, and competitive positioning. Keep the same technology (vanilla HTML/CSS/JS, no build step, no static site generator). Add 3 persona sub-pages as separate HTML files. Update screenshots to reflect the current UI state (many features shipped since the existing screenshots were taken).

**Prove first:** The hero section and one persona path ("Coming from Obsidian") — this validates the messaging approach and the persona-page navigation pattern before investing in all three paths.

## Implementation Landscape

### Key Files

- `docs/index.html` — Current 1928-line homepage. Dark theme, responsive, canvas animation, screenshot carousel, feature grid, Obsidian import section, deployment section, email signup. **This is the primary rewrite target.**
- `docs/CNAME` — Contains `sempkm.app`. GitHub Pages custom domain config. **No changes needed.**
- `docs/screenshots/` — Screenshot images referenced by the carousel. Currently shows ~17 screenshots from earlier versions. **Screenshots need updating** to reflect current UI (dashboards, canvas embeds, lint panel, persona selector, etc.).
- `docs/guide/index.html` — User guide docs site. **Not in scope** for M026 but the homepage should link to it.
- `docs/guide/README.md` — User guide table of contents. **Not in scope.**
- `.gsd/design/USER-CONVERSION-STRATEGY.md` — The messaging strategy document. **Primary content source.** Contains persona definitions, competitive positioning table, messaging shifts (current → new), what not to lead with, and onboarding flow descriptions.

### Existing Site Structure

The current `docs/index.html` has these sections (in order):
1. **Nav** — Logo, Features, Screenshots, Import, Deploy, User Guide, Get Started CTA
2. **Hero** — "Your knowledge, semantically structured" + RDF/SHACL/SPARQL subtitle
3. **Problem/Solution** — "PKM tools force a tradeoff" grid (problem card + SemPKM answer card)
4. **Features** — 16-card grid (Mental Models, SHACL Forms, Typed Relationships, Graph, SPARQL, Canvas, Command Palette, Lint, Inference, Standards, Webhooks, WebID, LLM, Event Sourcing, Self-Hosted, Coming Soon)
5. **Screenshots** — 17-slide carousel with captions
6. **Obsidian Import** — 6-step import wizard walkthrough
7. **Deployment** — Self-hosted (available) + Cloud (coming soon) cards
8. **Email Signup** — "Get notified when SemPKM launches" form
9. **Footer** — Copyright, links, social icons

### New Site Structure (Proposed)

Based on USER-CONVERSION-STRATEGY.md messaging shifts:

1. **Nav** — Logo, Why SemPKM, Features, Coming From [dropdown: Obsidian/Notion/Fresh Start], Try Demo, Self-Host
2. **Hero** — "Build knowledge that doesn't decay" (or "Structure that enforces itself") + outcome-focused subtitle. Two CTAs: "Try the Demo" (→ M025 instance) + "Self-host" (→ Docker quickstart)
3. **Persona Selector** — 3 cards: "Coming from Obsidian" / "Coming from Notion" / "Starting Fresh" — each links to a dedicated path page
4. **What Makes SemPKM Different** — Competitive positioning (the quadrant: high structure + high ownership). NOT the full 16-feature dump.
5. **Mental Models Explained** — "Domain kits" framing with 4-5 model cards (Basic PKM, CRM, Zettelkasten+, Research). Each shows what you get (types, views, validation rules).
6. **Screenshots** — Updated carousel (fewer slides, better captioned, showing current UI)
7. **Feature Overview** — Condensed from 16 to ~8 key features, outcome-language (not "SHACL-Driven Forms" but "Forms that generate themselves from your schema")
8. **CTAs** — "Try the Demo" + "Self-host with Docker" + "Read the User Guide"
9. **Footer** — Same structure, updated links

### Persona Path Pages (New Files)

- `docs/from-obsidian.html` — Tailored for Obsidian power users. Leads with: "Everything you built in Dataview — but reliable." Covers: vault import, WebDAV mount, wiki-link resolution, typed frontmatter → SHACL schemas, graph view comparison.
- `docs/from-notion.html` — Tailored for Notion escapees. Leads with: "Everything you love about Notion databases — but enforceable, portable, and future-proof." Covers: table/card views, dashboards, type creation = "create a database", SHACL forms = property types but enforced.
- `docs/fresh-start.html` — For new users. Leads with: "Pick a workflow, start building." Covers: Mental Model selection, guided tour, 3-minute onboarding path.

### Competitive Comparison Table

From USER-CONVERSION-STRATEGY.md — the 6×6 capability matrix (Obsidian/Notion/Tana/Capacities/SemPKM). This should appear on the homepage and be more prominent than a feature dump.

### Build Order

1. **S01: Homepage rewrite** — New hero, persona selector, competitive positioning, condensed features, updated CTAs. This is the highest-impact change. Proves the messaging approach.
2. **S02: Persona path pages** — Three separate HTML files with tailored copy. Can be done in parallel but depends on S01 for nav structure and shared CSS.
3. **S03: Screenshot refresh** — Capture current UI screenshots from running Docker stack. Update carousel. This is mechanical work but time-consuming.
4. **S04: Polish & verification** — Mobile responsive check, SEO meta tags, OG images, page speed verification, link verification (demo instance, Docker quickstart, user guide).

### Verification Approach

- **Visual:** Open each page in browser at desktop and mobile widths. Verify layout, readability, no broken images.
- **Links:** All CTAs resolve (demo instance URL from M025, GitHub repo, user guide, Docker quickstart).
- **Performance:** Lighthouse audit targeting <2s mobile load time.
- **SEO:** Meta description, OG tags, structured data (Organization schema.org).
- **Content:** No mentions of RDF/SHACL/SPARQL in hero, persona paths, or above-the-fold content. Standards mentioned only in "Powered by open standards" detail sections.

## Constraints

- **No build step** — The `docs/` directory is served directly by GitHub Pages. No static site generator, no bundler, no npm. Vanilla HTML/CSS/JS only. This is consistent with the project's frontend philosophy (htmx + vanilla JS).
- **GitHub Pages deployment** — Files must be in `docs/` directory on the deployed branch. CNAME file must remain.
- **Existing screenshots** are in `docs/screenshots/`. New screenshots must be captured from the running Docker stack (which requires Docker Compose up with test data).
- **M025 demo instance URL** — The "Try the Demo" CTA needs to link to the actual deployed demo. URL should be configurable or use a known domain.
- **Shared CSS** — The persona path pages should share the same CSS as the homepage to maintain visual consistency. Consider extracting common styles to a shared `docs/styles.css` file rather than inline `<style>` blocks in each HTML file.

## Common Pitfalls

- **Scope creep into SSG territory** — Don't introduce Jekyll, Hugo, Astro, or any static site generator. The existing single-file approach works. At most, extract shared CSS into a separate file.
- **Screenshot staleness** — The existing screenshots show v2.0-era UI. Features like dashboards, canvas embeds, lint panel improvements, persona selector, and the new explorer modes are not shown. Screenshots must be freshly captured.
- **Messaging regression** — Easy to slip back into tech-first language when writing feature descriptions. Every feature description should pass the test: "Would an Obsidian user understand this without knowing what RDF is?"
- **Mobile nav complexity** — Adding persona dropdown to mobile nav needs careful UX. The existing hamburger menu works; extending it with a sub-menu risks breaking it.
- **Demo instance availability** — The "Try the Demo" CTA is only useful if M025 is actually deployed and reachable. Need a fallback if the demo is down (link to Docker quickstart instead).

## Open Risks

- **Messaging effectiveness unknown** — The USER-CONVERSION-STRATEGY.md provides strategic direction but hasn't been tested with real users. The copy may need iteration post-launch. Plan for easy content updates.
- **Screenshot capture dependency** — Capturing fresh screenshots requires a running Docker stack with populated data (ideally the M025 demo seed data). This is a dependency that could block S03.
- **Demo instance URL** — M025 context mentions Caddy + Let's Encrypt but the actual public URL is not confirmed in the codebase. The homepage needs this URL.
- **OG images** — Social sharing preview images require graphic design work or at least composited screenshots. No tooling exists for this in the repo.

## Candidate Requirements

The M026 context mentions SITE-01, SITE-02, SITE-03 as "new" requirements but they don't exist in REQUIREMENTS.md yet. Based on research, these should be:

| ID | Description | Notes |
|---|---|---|
| SITE-01 | Homepage rewrite with outcome-focused hero, condensed features, dual CTAs (demo + self-host) | Core deliverable. Must not lead with RDF/SHACL/SPARQL in hero or above-the-fold. |
| SITE-02 | Three persona landing paths (Obsidian / Notion / Fresh Start) with tailored messaging | Separate HTML pages linked from homepage persona selector cards. |
| SITE-03 | Competitive comparison section highlighting high-structure + high-ownership quadrant | Table or visual showing SemPKM vs Obsidian/Notion/Tana/Capacities. |
| SITE-04 | Mental Models explained as "domain kits" with model cards | Homepage section showing 4-5 available models with what each provides. |
| SITE-05 | Updated screenshots reflecting current UI state | Capture from M025 demo stack or equivalent. Replace stale carousel. |
| SITE-06 | Mobile-responsive design with <2s load time | Lighthouse audit, responsive breakpoints, optimized images. |
| SITE-07 | SEO basics: meta tags, OG images, structured data | Standard web presence requirements. |

SITE-04 through SITE-07 are table-stakes quality requirements that the context doc implies but doesn't enumerate explicitly. They should be advisory, not scope-expanding — they're natural parts of the homepage rewrite work, not separate features.

## Shared CSS Extraction

The current `docs/index.html` has ~600 lines of CSS in an inline `<style>` block. With 3 new persona pages sharing the same design language, this CSS should be extracted to `docs/styles.css` and linked from all 4 pages. This is a small refactor that prevents copy-paste CSS divergence across pages.

## What NOT to Build

- **No static site generator** — Keep vanilla HTML/CSS/JS
- **No signup backend** — The email form can use a simple service (Formspree, etc.) or remain non-functional for now
- **No blog** — Out of scope per context doc
- **No A/B testing** — Out of scope per context doc
- **No analytics beyond basics** — A simple analytics script (Plausible, Umami) is acceptable but not required

## Sources

- `.gsd/design/USER-CONVERSION-STRATEGY.md` — Primary messaging strategy, persona definitions, competitive positioning
- `docs/index.html` — Current homepage (1928 lines, inline CSS/JS, dark theme, responsive)
- `docs/CNAME` — GitHub Pages domain: `sempkm.app`
- `docs/screenshots/` — Existing screenshot assets (need refresh)
- M025 context — Demo instance deployment details (docker-compose.demo.yml, Caddy SSL, seed data)
