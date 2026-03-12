# Ontology Modeling & Visualization Tools — Research Summary

**Date:** 2026-03-12  
**Context:** SemPKM needs an integrated ontology viewer/editor so users can see their overall collection of mental models, with clear TBox/ABox/RBox separation and cross-model hierarchy browsing. Gist (Semantic Arts) is the candidate upper ontology.

---

## 1. The Landscape: Existing Tools

### Tier 1 — Full Ontology Editors (Standalone)

| Tool | License | Stack | Strengths | Weaknesses for SemPKM |
|------|---------|-------|-----------|----------------------|
| **Protégé Desktop** | BSD | Java/Swing | Gold standard, full OWL 2, reasoning | Desktop-only, no web embedding, heavy UX |
| **WebProtégé** | BSD | Java/GWT/MongoDB | Collaborative, web-based, OWL 2 | Legacy GWT stack, hard to embed/restyle, limited visualization |
| **VocBench 3** (v13) | BSD-3 | Angular + Semantic Turkey (OSGi/Karaf) + RDF4J | Best open-source collaborative editor, SKOS+OWL+OntoLex, RBAC, Docker-ready | Heavy Java stack (Karaf), not embeddable as a component — it's a full app. REST API exists but building custom UI on it is substantial work |
| **PoolParty** | Commercial | SaaS | Enterprise NLP + taxonomy, AI text mining | Proprietary, expensive, overkill for PKM |
| **Stardog Designer** | Freemium | Web | Visual no-code modeling, maps to live data | Tied to Stardog platform |
| **TopBraid EDG** | Commercial | Web | Enterprise data governance | Very expensive, enterprise-only |

### Tier 2 — Visualization-Only (Read/Browse)

| Tool | License | Stack | Strengths | Weaknesses |
|------|---------|-------|-----------|------------|
| **WebVOWL** | MIT | D3.js | Industry-standard VOWL notation, beautiful force-directed graphs | Primarily TBox — ABox/individuals cause clutter. Read-only. Last major update ~2020 |
| **Grapholscape** | Open Source | Cytoscape.js + Lit Web Components | **Best embeddable option.** NPM package, explicit TBox/ABox/RBox support, Floaty mode, path finding | Requires Graphol format (not raw OWL/Turtle), learning curve |
| **OntView** | Academic | Java | Unique RBox axiom visualization (transitivity, property chains), inferred hierarchies | Academic prototype, not web-embeddable |
| **SemSpect** | Commercial | Web | Scales to massive KGs, semantic exploration | Commercial, not embeddable |
| **OWLGrEd** | Free | Desktop | UML-style diagrams of OWL | Desktop app, not web |

### Tier 3 — General Graph Libraries (Build Your Own)

| Library | License | Notes |
|---------|---------|-------|
| **Cytoscape.js** | MIT | Gold standard for web graph viz. Used under the hood by Grapholscape. Excellent layout algorithms, huge plugin ecosystem |
| **D3.js** | BSD | Maximum visual flexibility — radial trees, sunburst, force-directed. More work to build ontology-specific features |
| **yFiles for HTML** | Commercial | Enterprise-grade, highest performance for large graphs. Expensive |
| **Graphology** | MIT | Graph analysis library (centrality, community detection). Pairs well with Sigma.js for rendering |

---

## 2. Gist as Upper Ontology — Fit for SemPKM

### What Gist Is
- **~100 classes, ~100 properties** — deliberately minimalist
- CC BY 4.0 licensed (free, attribution required, terms stay in gist namespace)
- Current version: **14.0.0** (Oct 2025) — actively maintained, biweekly dev meetings
- Uses everyday terms (Person, Organization, Agreement, Event) not philosophical jargon (endurant, perdurant)
- Strong disjointness at top level — catches logical errors via reasoning
- New in v14: **KnowledgeConcept** class for "knowledge distilled from experience" — directly relevant to mental models

### Core Class Hierarchy (The "Periodic Table")

| Constellation | Key Classes | SemPKM Relevance |
|--------------|-------------|-----------------|
| **People & Orgs** | Person, Organization | Who created/owns knowledge |
| **Agreements** | Agreement, Commitment, Account | Could model shared knowledge contracts |
| **Acts & Events** | Event, TemporalRelation, Assignment | Learning events, task assignments |
| **Places** | GeographicRegion | Context for knowledge |
| **Things** | PhysicalIdentifiableItem, PhysicalSubstance | Physical referents |
| **Intellectual** | IntellectualProperty, **KnowledgeConcept**, Message, Language | **Core fit** — mental models, concepts, frameworks |
| **Measurement** | Aspect, Magnitude, UnitOfMeasure | Quantitative mental models |
| **Categories** | Collection, Category, ControlledVocabulary | Taxonomy/tagging structure |

### Why Gist Fits SemPKM
1. **KnowledgeConcept** (v14) maps directly to what mental models are — "knowledge distilled from experience"
2. The minimalist design means users see a clean hierarchy, not hundreds of abstract classes
3. Domain-independent — works across any mental model domain
4. The "Periodic Table" visual metaphor aligns with the goal of making the TBox approachable
5. Already designed for enterprise extension — SemPKM mental models would be gist extensions
6. Disjointness catches errors when users accidentally cross-type things

### Alternatives to Gist (for completeness)
- **BFO (Basic Formal Ontology):** More philosophical, uses terms like "continuant"/"occurrent". Standard in biomedical ontology. Heavier, less intuitive for PKM users.
- **DOLCE:** Academic, even more philosophical. Not practical for end-user-facing tools.
- **Schema.org:** Practical but shallow — no formal axiomatization, no reasoning support.
- **SUMO:** Comprehensive but massive (~20K terms). Overkill.
- **Gist wins** for PKM because it's the only upper ontology designed to be *readable by business users*, not just ontologists.

---

## 3. TBox / ABox / RBox — Visualization Strategy

### The Core Problem
Most ontology tools treat everything as one big graph. For SemPKM users, the critical insight is separation:

| Box | What It Contains | User Mental Model | Visualization Need |
|-----|-----------------|-------------------|-------------------|
| **TBox** (Terminology) | Classes, class hierarchies, restrictions | "What kinds of things exist in my world?" | Tree/hierarchy view, class diagram |
| **ABox** (Assertions) | Individuals, their types, relationships | "What specific things do I know?" | Instance browser, property sheets |
| **RBox** (Roles) | Property hierarchies, property characteristics (transitive, symmetric, etc.) | "How do things relate to each other?" | Property tree, relationship legend |

### What SemPKM Already Has
- Mental Models = OWL ontology + SHACL shapes + view specs — this IS a TBox
- Objects created by users = ABox
- Properties defined in models = RBox
- The system already has RDF4J as triplestore and SPARQL querying
- The workspace already has a canvas view (spatial graph)

### What's Missing
- No unified view that shows the TBox across ALL installed mental models
- No hierarchy browser that lets users drill from gist → mental model → their instances
- No visual distinction between "the schema" and "my data"
- No property hierarchy view

---

## 4. Recommendation: Build Custom (with Libraries)

### Why Not Integrate an Existing Tool

| Option | Why Not |
|--------|---------|
| **Embed WebProtégé** | Legacy GWT, massive Java stack, can't restyle to match SemPKM, designed for ontologists not end users |
| **Embed VocBench** | Even heavier stack (Karaf/OSGi), would need a separate Java service, REST API integration is possible but you'd still build the UI |
| **Embed WebVOWL** | Read-only, TBox-only, D3 v3 (dated), no ABox support |
| **Use Grapholscape** | Closest option but requires Graphol format conversion, Lit web components may conflict with htmx approach |

### The Case for Building Custom
SemPKM already has:
- A working SPARQL endpoint over RDF4J
- An htmx/Jinja2 frontend with a workspace paradigm
- Mental models that define the TBox
- A canvas for spatial graph views

What you actually need is **3 purpose-built views**, not a general ontology editor:

#### View 1: TBox Explorer ("Schema Map")
- **Purpose:** Show all installed mental models as a unified class hierarchy rooted at gist
- **Visualization:** Collapsible tree (like a file browser) with gist classes at top, mental model classes below
- **Tech:** Pure htmx + server-rendered HTML. SPARQL `SELECT ?class ?superclass WHERE { ?class rdfs:subClassOf ?superclass }` drives the data. No JS graph library needed for a tree.
- **Enhancement:** Add a force-directed "map view" toggle using Cytoscape.js for seeing relationships between classes across models

#### View 2: ABox Browser ("My Knowledge")
- **Purpose:** Show instances grouped by type, with quick navigation
- **Visualization:** Faceted list grouped by class, with instance counts. Clicking a class shows its instances.
- **Tech:** htmx partial rendering — already the SemPKM pattern

#### View 3: RBox Legend ("Relationship Guide")
- **Purpose:** Show what properties exist, their domains/ranges, and characteristics
- **Visualization:** Grouped property list — object properties, datatype properties, with domain→range arrows
- **Tech:** Table/list view, server-rendered. Optionally a simple Cytoscape.js diagram showing domain-range connections

### Recommended JS Libraries (if/when needed)

| Need | Library | Why |
|------|---------|-----|
| Force-directed class graph | **Cytoscape.js** | MIT, battle-tested, great layouts, huge ecosystem. Already used by Grapholscape under the hood |
| Hierarchy tree | **None (HTML/CSS)** | A collapsible `<ul>` tree with htmx lazy-loading is simpler and more consistent with SemPKM's stack |
| Property diagram | **Cytoscape.js** | Same lib, different layout (dagre/hierarchical for domain→range) |

---

## 5. Gist Integration Path

### Phase 1: Import Gist as Foundation
1. Download gist 14.0.0 Turtle files
2. Load into RDF4J as a named graph (`urn:gist:core`)
3. Make existing mental model ontologies declare `rdfs:subClassOf` relationships to gist classes
4. Example: `basic-pkm:Note rdfs:subClassOf gist:IntellectualProperty`

### Phase 2: Build TBox Explorer
1. SPARQL query across gist + all mental model graphs to build unified class tree
2. Render as collapsible tree in workspace panel
3. Color-code by source (gist = neutral, each mental model = distinct color)

### Phase 3: Cross-Model Hierarchy
1. Show how classes from different mental models share common ancestors in gist
2. Example: PPV's `Goal` and Basic-PKM's `Project` both descend from gist's `Intention`
3. This is where the "seeing hierarchy across mental models" goal is realized

### Phase 4: ABox/RBox Views
1. Instance browser with type-based grouping
2. Property reference panel
3. Both server-rendered with htmx, consistent with existing workspace

---

## 6. Key Decisions to Make

1. **Gist version pinning:** Lock to 14.0.0 or track latest? Recommend: pin, update deliberately.
2. **Mental model → gist alignment:** Who maps mental model classes to gist? Auto-suggest via LLM? Manual by model author? Both?
3. **Reasoning:** Enable OWL 2 RL reasoning to infer subclass chains? SemPKM already has an inference engine — this would make the hierarchy richer.
4. **Edit vs. browse:** Should users edit the ontology through this viewer, or is it read-only? Recommend: read-only initially, editing via mental model authoring workflow.
5. **Cytoscape.js scope:** Full graph view vs. tree-only? Recommend: start with tree, add graph later as canvas enhancement.

---

## Sources
- Semantic Arts gist: https://www.semanticarts.com/gist/ / https://github.com/semanticarts/gist
- WebProtégé: https://github.com/protegeproject/webprotege
- WebVOWL: https://github.com/VisualDataWeb/WebVOWL
- Grapholscape: https://github.com/obdasystems/grapholscape
- VocBench 3: https://vocbench.uniroma2.it/
- Cytoscape.js: https://js.cytoscape.org/
