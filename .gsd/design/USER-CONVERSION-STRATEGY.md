# User Conversion Strategy: Obsidian & Notion Users

**Created:** 2026-03-16
**Status:** Draft — strategic direction document
**Context:** Discussion session exploring how to make SemPKM appealing to Obsidian and Notion power users as the platform approaches feature completeness.

---

## Executive Summary

SemPKM is approaching feature parity with the core workflows of both Obsidian and Notion, while offering structural advantages neither can match (schema enforcement, typed relationships, event sourcing, full data ownership). The conversion challenge is not feature gaps — it's **time to value** and **messaging clarity**.

---

## Target Personas

### Tier 1: Obsidian Power Users
- Use Dataview heavily, maintain complex YAML frontmatter
- Frustrated by brittle queries and informal structure
- Want typed links and reliable queries at scale
- Care deeply about data ownership and local-first
- Comfortable with Docker / self-hosting
- **They already feel the pain SemPKM solves**

### Tier 2: Notion Escapees
- Love databases, views, and clean UI
- Frustrated by lock-in, performance at scale, flat relations
- Want ownership without losing structure
- **SemPKM's table/card views, dashboards, and SHACL forms map to their mental model**

### Tier 3: Academic Researchers
- Care about claims, citations, provenance
- Use Zotero + Obsidian or similar stacks
- Want reproducible, formal knowledge structures
- **Wave two — serve after Tier 1 is won**

### Not Yet (defer)
- Casual note-takers, "second brain" beginners, students wanting templates
- Do not dilute messaging for this audience in v1

---

## Competitive Position

| Capability | Obsidian | Notion | Tana | Capacities | **SemPKM** |
|---|---|---|---|---|---|
| Structure enforcement | Weak | Soft | Medium | Medium | **Strong (SHACL)** |
| Data ownership | Strong | Weak | Weak | Weak | **Strong (self-hosted)** |
| Typed relationships | Weak | Weak | Medium | Medium | **Strong (RDF + OWL)** |
| Queryable views | Fragile (Dataview) | Medium | Medium | Weak | **Strong (SPARQL)** |
| Audit trail | None | None | None | None | **Full (event sourcing)** |
| Plugin/app ecosystem | Strong | Medium | Weak | Weak | **Coming (M009)** |

**Unique quadrant:** High structure + high ownership. No competitor occupies this cleanly.

---

## Current Feature Mapping (What Already Exists)

### For Obsidian users — "you already have this, but better"
- **Obsidian vault import** — ZIP upload, frontmatter mapping, wiki-link resolution, tag conversion (shipped)
- **Backlinks** — Relations panel shows both outbound (→) and inbound (←) with typed predicates, provenance, timestamps, and inference badges. Richer than Obsidian's backlinks.
- **Graph view** — Cytoscape.js with force/hierarchical layouts, type-based styling
- **Spatial canvas** — Resizable nodes, property flip, live iframe embeds (M008, shipped)
- **WebDAV mount** — Objects projected as Markdown files with SHACL frontmatter. Obsidian users can mount and browse alongside their vault.
- **Tags** — Hierarchical tag tree with `/`-delimited nesting
- **Full-text search** — Integrated into Ctrl+K command palette (fuzzy + keyword)
- **Dark mode** — Tri-state toggle with 35+ CSS variable tokens
- **Markdown body editor** — Read/edit flip with CSS 3D animation

### For Notion users — "same paradigm, no lock-in"
- **Table views** — Sortable columns, filtering, pagination, column preferences
- **Card views** — Group-by support, type filtering, carousel layout
- **Dashboards** — CSS Grid, 6 block types, builder UI, cross-view context filtering
- **In-app type creation** — Name, icon, parent class, properties (= "create a database" in Notion terms)
- **SHACL-driven forms** — Auto-generated from schema with validation (= Notion property types, but enforced)
- **Workflows** — Stepper runner UI, builder, multiple step types

### For both — "things neither tool does"
- **Schema enforcement** — SHACL validation + lint panel catches inconsistencies automatically
- **OWL inference** — Automatic inverse property materialization
- **Event sourcing** — Every change is an immutable event, full audit trail, undo via compensating events
- **Typed relationships** — Edges are first-class: clickable, annotatable, versionable, with provenance
- **Mental Models** — Install a domain bundle, get instant types + forms + views + validation

---

## Conversion Priorities (Ordered)

### Priority 1: Hosted Demo Instance
**Impact:** Removes the #1 conversion barrier (Docker requirement)
**What:** Pre-populated SemPKM instance with a Mental Model loaded and 30-50 interconnected objects. No install, click a link, explore for 3 minutes.
**Includes:**
- Guided tour (Driver.js) optimized for first-time visitors
- Pre-built dashboard showing the graph, table, and canvas together
- Sample objects that demonstrate typed relationships, validation, and inference
- "Import your own vault" CTA at the end of the tour

### Priority 2: Homepage Rewrite
**Impact:** Converts visitors who land on the site but bounce on "RDF/SHACL/SPARQL"
**Key shifts:**

| Current Messaging | New Messaging |
|---|---|
| "Semantics-native platform" | "Structure that enforces itself" |
| "Built on RDF, SHACL, SPARQL" | "Powered by open standards" (details page) |
| "Mental Model" (unexplained) | Explained inline: "domain kits with types, forms, views, and validation" |
| "Install a bundle" | "Pick a workflow, start building" |
| "SPARQL-powered views" | "Query anything, reliably, forever" |

**Lead with outcomes:**
- "Your notes become structured, queryable, and future-proof"
- "Stop collecting notes. Start building knowledge."
- "Notion power. Obsidian ownership. Semantic guarantees."

**Standards support the pitch, not ARE the pitch.**

### Priority 3: Additional Mental Models (2-3 more)
**Impact:** Wider "aha moment" coverage at first touch
**Candidates:**
- **Personal CRM** — Contacts, companies, interactions, follow-ups. Notion users love this pattern.
- **Project Management** — Tasks, projects, milestones, dependencies. Universal appeal.
- **Zettelkasten+** — Atomic notes, sequence IDs, bridge notes, structure notes. Obsidian crowd's favorite methodology.
- **Research Workflow** — Papers, claims, evidence chains, argument maps. Strongest differentiator for academics.

**Minimum:** 5-6 models available at public launch (currently 3 shipped: basic-pkm, ppv, gist).

**Free forever:** Basic PKM, Personal CRM, Project Management
**Premium/Marketplace:** Research Workflow, Zettelkasten+, domain-specific packs

### Priority 4: Browser Extension
**Impact:** Enables the "capture while browsing" workflow that both Obsidian and Notion users expect
**Capabilities (progressive):**
1. **Quick clip** — Save page/selection as typed object (Claim, Reference, Note, etc.) via right-click or popup
2. **Clip with relationships** — Link new object to existing objects with typed predicates (supports, refutes, cites)
3. **Tag + classify on capture** — Mental Model-aware type selector, tag input, property fields from SHACL shapes
4. **Context overlay** — Sidebar showing "you already have N objects related to this page/topic, including 1 contradicting claim"

The context overlay is the killer differentiator. Obsidian's Web Clipper is fire-and-forget. SemPKM's extension shows **what you already know** about what you're currently reading.

**Technical:** Talks to local/cloud instance via existing `POST /api/commands` + SPARQL endpoint. No dependency on M009 app platform.

### Priority 5: Notion Import Wizard
**Impact:** Doubles addressable market by opening a second onramp
**Status:** Research complete (`.planning/notion-import-research.md`), design needed
**Approach:** ZIP export first (mirrors Obsidian import pattern), API integration later
**Maps:** Notion databases → types, rows → objects, relations → edges

---

## Onboarding Flows by Persona

### The Obsidian Refugee Path
1. Upload vault ZIP (importer already shipped)
2. SemPKM shows: "Found N notes, N tags, N wiki-links. Here's your knowledge graph."
3. "N notes have frontmatter. Map fields to a Mental Model?" — bridge from markdown-with-metadata to schema-enforced objects
4. "N notes have inconsistent frontmatter. SemPKM caught that." — **aha moment**: their system was already rotting

### The Notion Escapee Path
1. Upload Notion export ZIP (requires Priority 5)
2. SemPKM shows: "Found N databases, N pages, N relations."
3. Databases become types, relations become typed edges, views auto-generate
4. **Aha moment:** "Your flat Notion relations are now a navigable, queryable graph"

### The Fresh Start Path
1. Pick a Mental Model from 5-6 options
2. Guided tour creates 3-4 sample objects interactively
3. Tour demonstrates: create object → table view → graph view → add relationship → validation catches a mistake
4. Under 3 minutes to "this is different"

---

## Messaging Strategy

### Core Positioning
**"Build knowledge that doesn't decay."**

SemPKM is a local-first knowledge platform with structured types, enforced relationships, and queryable views. Bring your Obsidian vault or Notion export — your data stays yours, and your system holds together at any scale.

### Competitive Angles

**vs Obsidian:** "Everything you built in Dataview — but reliable. Typed links, enforced schemas, real queries. And you keep your Markdown."

**vs Notion:** "Everything you love about Notion databases — but enforceable, portable, and future-proof. No vendor lock-in, no performance cliffs."

**vs Both:** "Your backlinks now have meaning. Not just 'linked from' — but the type of relationship, who created it, when, and whether it was inferred."

### What NOT to Lead With
- RDF, SHACL, SPARQL (backend language, not user language)
- "Semantic web" (academic connotation, triggers skepticism)
- Event sourcing (implementation detail; say "full history + undo" instead)
- OWL inference (say "automatic relationship discovery" instead)

---

## Monetization Alignment

This strategy aligns with the tiered monetization model:

**Free (local forever):**
- Full local engine, unlimited usage
- Core Mental Models (Basic PKM, CRM, Project Management)
- Import/export (Obsidian, eventually Notion)
- Browser extension (connects to local instance)

**Pro ($10-15/month):**
- Encrypted sync
- Premium Mental Models
- AI features (claim detection, contradiction finding, structured suggestions)
- Advanced SPARQL dashboards

**Marketplace:**
- Community Mental Models (20-30% revenue split)
- Verified/curated premium packs
- Domain-specific bundles (legal, research, engineering)

**Team/Cloud:**
- Managed hosting (the hosted demo becomes the onramp)
- Collaboration, permissions, shared graphs

---

## Strategic Risks

1. **Over-indexing on semantic web purity** — The product must feel like a powerful app, not an ontology lab. Hide complexity ruthlessly.
2. **Trying to win both personas simultaneously** — Messaging must be persona-specific (separate landing pages or tabs), not blended.
3. **Docker as a wall** — The hosted demo and eventual cloud option are existential for reaching beyond the self-hosting crowd.
4. **Mental Model discoverability** — 3 models feels thin. 5-6 is minimum viable for "pick one that fits you."
5. **The "aha moment" depth** — Currently too many steps to "wow." Each onboarding path must reach it in under 3 minutes.

---

## Relationship to Existing Roadmap

- **M009 (App Platform)** — Enables the ecosystem play (third-party apps, custom renderers). Not a conversion blocker but deepens the moat.
- **M010 (RSS Reader + Hypothesis)** — First real app. Validates "your PKM pulls knowledge to you" narrative. Relevant for the browser extension story.
- **Notion Import** — Should be scheduled as M011 or squeezed into post-M010 work.
- **MCP Server** — Enables AI agent access. Relevant for the "AI that works because data is structured" positioning.
- **Backlinks** — Already shipped in the Relations panel. Not a gap.
