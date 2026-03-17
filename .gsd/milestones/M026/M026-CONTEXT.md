---
depends_on: [M025]
---

# M026: Homepage & Messaging Rewrite

**Gathered:** 2026-03-16
**Status:** Queued — pending auto-mode execution

## Project Description

Rewrite the SemPKM homepage and marketing site to lead with outcomes instead of technology. Replace "semantics-native platform built on RDF/SHACL/SPARQL" with "Structure that enforces itself" and persona-specific landing paths. Standards support the pitch — they don't ARE the pitch.

## Why This Milestone

The current messaging leads with implementation details (RDF, SHACL, SPARQL) that scare away exactly the users who would benefit most. Obsidian users don't care about RDF — they care about "your Dataview queries but reliable." Notion users don't care about SHACL — they care about "your databases but enforceable and portable."

## User-Visible Outcome

### When this milestone is complete, the user can:

- Visit the homepage and immediately understand what SemPKM does in outcome terms
- Click a persona path ("Coming from Obsidian" / "Coming from Notion" / "Starting fresh") for tailored messaging
- See competitive comparison tables that highlight SemPKM's unique position (high structure + high ownership)
- Click "Try the Demo" to reach the hosted demo (M025)
- Click "Self-host" for quick-start Docker instructions
- Understand Mental Models as "domain kits" without needing to know about ontologies

### Entry point / environment

- Entry point: `https://sempkm.app` (or equivalent)
- Environment: Static site (GitHub Pages, Netlify, or similar)
- Live dependencies involved: None (static content linking to demo instance)

## Completion Class

- Contract complete means: new homepage deployed, persona paths render, CTA buttons link correctly
- Integration complete means: demo link works, self-host instructions are accurate, screenshots match current UI
- Operational complete means: site loads fast, looks good on mobile, SEO basics covered

## Final Integrated Acceptance

- Visitor lands on homepage, reads "Build knowledge that doesn't decay" (not "RDF-native PKM")
- Visitor clicks "Coming from Obsidian" and sees tailored messaging about Dataview → SPARQL, frontmatter → schemas
- Visitor clicks "Try the Demo" and reaches the live demo instance
- Page loads in under 2 seconds on mobile

## Risks and Unknowns

- **Messaging testing** — Hard to know if the messaging resonates without user feedback. May need iteration.
- **Screenshot maintenance** — Screenshots of the UI need updating when the UI changes.

## Existing Codebase / Prior Art

- `.gsd/design/USER-CONVERSION-STRATEGY.md` — messaging strategy, competitive positioning, persona paths, what not to lead with
- M025 — hosted demo instance (linked from homepage)

## Relevant Requirements

- New: SITE-01 (homepage rewrite), SITE-02 (persona paths), SITE-03 (competitive positioning)

## Scope

### In Scope

- Homepage with outcome-focused hero messaging
- 3 persona paths (Obsidian, Notion, Fresh Start) with tailored copy
- Competitive comparison section
- Mental Models explained as "domain kits"
- Feature overview with screenshots
- "Try the Demo" and "Self-host" CTAs
- Mobile-responsive design
- Basic SEO (meta tags, OG images, structured data)

### Out of Scope / Non-Goals

- Blog, documentation site (separate concern)
- Pricing page (premature)
- User accounts / signup flow
- Analytics beyond basic page views
- A/B testing infrastructure

## Technical Constraints

- Static site (no backend)
- Fast loading (< 2s on mobile)
- SEO-friendly (server-rendered or pre-rendered)
- Screenshots from current SemPKM UI

## Integration Points

- **M025 demo instance** — "Try the Demo" CTA links here
- **Docker quickstart docs** — "Self-host" CTA links to existing docs
- **Screenshots** — captured from running SemPKM instance
