# Academic Workspace Design & PKM Research Analysis

**Created:** 2026-03-05
**Context:** Analysis of a Perplexity Deep Research chat examining academic UI design patterns, PKM/PIM research literature, and research-backed feature requirements for knowledge management tools. This document captures all insights and cross-references them against SemPKM's existing roadmap.

---

## Executive Summary

A comprehensive deep research analysis explored three interconnected areas relevant to SemPKM's future development: academic workspace UI design, the PKM/PIM research landscape, and a research-backed feature checklist organized into seven themes.

The **academic UI layout proposal** describes a three-pane workspace with top-level modes aligned to academic verbs (Read, Think, Organize, Plan, Publish). This maps naturally onto SemPKM's existing dockview-based workspace architecture and the installable mental models concept -- modes could be model-contributed view configurations rather than hardcoded application states.

The **PKM/PIM research landscape** traces the field from its emergence in the late 1990s through current multi-disciplinary approaches incorporating AI integration and "second brain" practices. Key takeaways include the importance of structured personal spaces, the socio-technical nature of PKM, explicit support for reflection and learning loops, and the parallel between reusable workflow templates and SemPKM's installable mental models.

The **research-backed feature checklist** spans seven themes: Capture, Organize, Retrieve & Sensemaking, Plan & Execute, Reflect & Learn, Share & Publish, and Collaboration & Social PKM. Cross-referencing these against SemPKM's roadmap reveals that the core Organize and Retrieve capabilities are well-covered by shipped milestones (v1.0 through v2.4), several features naturally extend planned milestones (RSS Reader, Collaboration, Identity), and a meaningful set of features -- particularly around reading capture, review cycles, learning metrics, and draft-from-graph publishing -- represent entirely new territory not yet on the roadmap.

This document is purely informational input for future milestone planning. No changes to ROADMAP.md are proposed or made.

---

## 1. Academic UI Layout Proposal

### 1.1 Three-Pane Workspace Design

The research proposes a three-pane layout organized around academic workflows:

**Left Pane -- Navigation & Context Selection:**
- Workspaces and projects (scoping what the user is working on)
- Saved views and filters (quick access to curated result sets)
- Persistent navigation tree for the active workspace

**Center Pane -- Active Mode:**
- The primary working area, switching between modes:
  - **PDF/HTML Reader** -- reading and annotating source material
  - **Argument Map** -- structuring claims, evidence, and reasoning
  - **Concept Map** -- visual knowledge organization
  - **Draft Editor** -- writing and composition
  - **Task Board** -- project and action management

**Right Pane -- Contextual Information:**
- Annotations list for the current document/object
- Semantic metadata (types, properties, provenance)
- Local graph neighborhood (related objects)
- Linked tasks and projects

### 1.2 Top-Level Modes Aligned with Academic Verbs

The proposed modes align with the core activities of academic knowledge work:

| Mode | Verb | Primary Activity |
|------|------|-----------------|
| **Read** | Consume & annotate | PDF/HTML reading with inline annotation |
| **Think** | Analyze & synthesize | Argument maps, concept maps, claim linking |
| **Organize** | Curate & classify | Library management, tagging, type assignment |
| **Plan** | Coordinate & schedule | Project templates, task boards, dependencies |
| **Publish** | Compose & export | Draft editing, reference formatting, export pipelines |

### 1.3 Mapping to SemPKM Architecture

SemPKM's existing dockview workspace (shipped in v2.3, Phase 30) provides the infrastructure for this kind of multi-pane, mode-switching interface:

- **Left pane**: Already exists as the sidebar with nav tree, type picker, and command palette access
- **Center pane**: Dockview panels already support tabbed object views, graph visualization, SPARQL console, and lint dashboard
- **Right pane**: Object detail views already show relations, lint results, and metadata in collapsible sections

The key gap is not architectural but content-level: SemPKM lacks a PDF/HTML reader, argument mapping tool, and draft editor. The dockview infrastructure could host these as new panel types.

### 1.4 Modes as Model-Contributed Views

The "Academic Persona" framing connects directly to SemPKM's installable mental models concept. Rather than hardcoding modes into the application, they could be:

- **Named layouts** (shipped in v2.3, Phase 33) that arrange dockview panels for specific workflows
- **Model-contributed view configurations** where a mental model's manifest declares "when in Read mode, show these panels in this arrangement"
- **Installable ontologies** that bring both the data types (Claim, Evidence, Argument) and the UI modes that work with them

This would allow an "Academic Research" mental model to install Read/Think/Organize/Plan/Publish modes alongside the entity types those modes operate on.

---

## 2. PKM/PIM Research Landscape

### 2.1 Origins and Evolution

PKM (Personal Knowledge Management) emerged in the late 1990s as an extension and critique of organizational KM. Where traditional KM focused on capturing and sharing institutional knowledge, PKM shifted focus to individual processes and tools -- how a person captures, organizes, retrieves, and applies knowledge in their own practice.

The field frames PKM as a response to information overload, spanning three concerns:
- **Personal information management** -- organizing digital artifacts
- **Contextualization** -- connecting information to personal meaning and projects
- **Personalization** -- adapting tools and workflows to individual needs
- **Lightweight sharing** -- selectively externalizing personal knowledge for collaboration

### 2.2 Key Literature

**Razmerita et al.** cataloged capture/organize/retrieve strategies across the PKM literature, establishing a vocabulary of core operations that recurs in tool design. Their reviews span HCI, KM, and education domains.

**Frand & Hixson** contributed early frameworks for understanding PKM as a learnable skill set, not just a tool category. Their work emphasizes that PKM tools succeed when they support cognitive processes, not just file management.

### 2.3 Empirical Work

Research on PKM support using wikis and Web 2.0 tools in online courses demonstrated that **structured personal spaces plus social features** help learners externalize and apply knowledge. Key findings:

- Students who maintained structured personal knowledge bases (not just notes) showed better retention and application
- Social features (sharing, commenting, collaborative curation) amplified individual PKM effectiveness
- The structure of the personal space mattered more than the specific tool -- templates and guided workflows outperformed blank-page approaches

### 2.4 Recent Trends

The PKM field has become increasingly multi-disciplinary, with tensions between individual and organizational goals. Notable developments:

- **AI integration**: LLM-assisted capture, summarization, and linking are becoming expected features in PKM tools
- **"Second brain" practices**: Popularized by Tiago Forte and others, emphasizing systematic capture-organize-distill-express workflows
- **Digital garden / networked thought**: Graph-based tools (Obsidian, Roam, Logseq) have mainstreamed the idea of interconnected notes over hierarchical filing

### 2.5 PIM Methodologies

Library and information science guides have formalized PKM for academics using established productivity frameworks:

- **GTD (Getting Things Done)**: Capture everything, clarify next actions, organize by context, review regularly, engage with confidence
- **PARA (Projects, Areas, Resources, Archives)**: Organize by actionability, not topic
- **Annotation + concept mapping workflows**: Structured annotation during reading supports later mapping and synthesis -- the reading-to-thinking pipeline

### 2.6 Project Management as Knowledge Work

Research highlights that control-oriented project management tools are insufficient for emergent, innovative tasks typical of academic work. Integrating KM principles into project management means:

- **Reflective practice**: Built-in review cycles, not just task completion
- **Learning loops**: Projects generate knowledge (not just deliverables) that feeds future work
- **Collaboration as knowledge exchange**: Team interactions are information-sharing events, not just coordination
- **Information dependency visualization**: Tools that surface "this task depends on understanding these concepts" improve productivity over simple task-to-task dependencies

### 2.7 Takeaways for SemPKM

1. **Vocabulary of core operations**: The PKM literature provides evidence-backed names for the operations a tool must support (capture, organize, retrieve, synthesize, express). SemPKM's typed entities and SHACL-driven forms align with the "structured personal spaces" that research shows are effective.

2. **Socio-technical nature of PKM**: Tools alone are insufficient -- PKM is a practice. SemPKM's mental models concept (installable ontologies with views and workflows) supports this by encoding practices as installable packages.

3. **Explicit support for reflection and learning**: Research projects need review cycles, not just task boards. This is a gap in SemPKM's current roadmap.

4. **Reusable workflow templates**: The research emphasis on templates for academic workflows parallels SemPKM's installable mental models. An "Empirical Study" or "Literature Review" template is essentially a specialized mental model.

---

## 3. Research-Backed Feature Checklist

### 3.1 Capture

**Integrated reading capture**: PDF/HTML reader with inline annotation and highlighting, producing structured notes (claims, evidence, questions, concepts). The research evidence shows that annotation combined with mapping improves comprehension and synthesis -- the pipeline from reading to structured knowledge is a critical path.

**Low-friction inboxes**: "Quick capture" from anywhere (browser extension, mobile, CLI) into a unified inbox. PKM literature consistently emphasizes frictionless capture as the first defense against information overload. If capture requires context-switching to the main application, material is lost.

**Multi-modal capture**: Text, images, links, code snippets, email excerpts, and chat fragments all become first-class nodes in the knowledge graph. The diversity of academic input sources (papers, slides, code, email threads, Slack conversations) demands multi-modal treatment.

### 3.2 Organize

**Typed entities with templates**: Distinct types (Work, Concept, Claim, Evidence, Project, Task, Review) with minimal templates defining required fields and relations, rather than relying solely on tags. PKM/PIM guidance consistently shows that structured personal spaces outperform unstructured ones -- but the structure must be lightweight and domain-appropriate.

**Flexible but opinionated hierarchies**: PPV-like chains (Pillar to Goal to Project to Action) AND lightweight patterns (PARA, GTD) as installable ontologies. The key insight is that no single hierarchy fits all users, but having no hierarchy leads to entropy. Installable ontologies let users choose their organizational framework.

**Faceted navigation**: Filter by type, topic, author, project, status, and context simultaneously. Library PIM advice and academic PKM guides emphasize that retrieval fails when the only access path is search -- faceted browsing complements full-text search for re-finding.

### 3.3 Retrieve & Sensemaking

**Graph-based search**: Semantic search over concepts, claims, projects, and annotations -- not just full-text keyword matching. PKM literature emphasizes re-finding and contextualization: "I know I read something about X in the context of project Y" requires graph-aware search.

**Argument and concept maps**: Visual maps constructed from annotations and links, using frameworks like AIF (Argument Interchange Format) and structured concept representations. Research evidence shows that reading combined with mapping improves understanding for complex academic tasks -- the visual synthesis step is where comprehension deepens.

**Question-centric views**: Explicit "research questions" and "problems" as first-class entities with linked evidence, claims, and open sub-questions. Knowledge work research shows that problem framing and iterative refinement drive quality -- questions are not just search queries but persistent investigative threads.

### 3.4 Plan & Execute

**Research project templates**: Reusable project templates encoding typical academic workflows such as "Empirical Study," "Theory Paper," and "Literature Review." Each template defines phases, expected deliverables, common subtask patterns, and linked entity types. Research on knowledge-intensive settings shows reusable workflows reduce cognitive overhead and encode institutional best practices.

**Integrated task boards**: Tasks as first-class nodes linked to Works, claims, and projects -- not isolated to-do items. States follow GTD/PPV patterns (Next, Waiting, Future, Done) with contexts (energy level, location, available time). The integration between tasks and knowledge objects distinguishes academic task management from generic project management.

**Dependency and information-flow views**: Visualizing "this task depends on understanding these claims / reading these Works" rather than just task-to-task sequencing. Research on team information interactions shows that revealing knowledge dependencies improves productivity and reduces redundant work.

### 3.5 Reflect & Learn

**Review cycles**: Built-in weekly, monthly, quarterly, and yearly review entities (following PPV methodology) with prompts and metrics. Metrics include claims clarified, open questions resolved, new concepts integrated, and projects advanced. The project-as-knowledge-work literature emphasizes that reflection and learning loops are what distinguish knowledge work from rote task execution.

**Learning metrics**: Non-gamified indicators that help users understand their knowledge growth without reducing it to points or streaks. Examples: "concepts strengthened" (claims with increasing evidence), "open decisions with weak evidence" (areas needing investigation), "papers annotated but not integrated" (capture without synthesis). PKM research focuses on learning and understanding over quantity.

### 3.6 Share & Publish

**Draft-from-graph workflows**: Generate outlines and drafts from argument and concept graphs. A user builds an argument map linking claims to evidence to sources, then the system generates a structured outline following the argument's logical flow. This implements the "express" phase from Tiago Forte's distill/express framework and maps to the academic writing process of moving from notes to draft.

**Export pipelines**: Multiple output formats preserving provenance and structure:
- **Markdown/LaTeX** for academic writing workflows
- **Reference manager formats** (BibTeX, RIS) for bibliography management
- **Nanopublications** for structured, attributable scientific claims
- **ClaimReview** for fact-checking and claim verification contexts
- **Institutional repository formats** for archival and discovery

### 3.7 Collaboration & Social PKM

**Shared annotation and argument spaces**: Group annotation layers where multiple users annotate the same documents, and shared argument graphs where team members contribute claims and evidence to collective reasoning. Research on wiki-based PKM in education and collaborative annotation shows that social knowledge construction amplifies individual understanding.

**Team/project dashboards**: Multi-person project views showing shared reading progress (who has read what), argument coverage (which claims have evidence, which are contested), and knowledge gaps (areas where the team lacks expertise or evidence). Project management as knowledge work research shows that making knowledge state visible across a team improves coordination.

---

## 4. Key Integrations & Standards

### 4.1 Hypothes.is / W3C Web Annotation

[Hypothes.is](https://web.hypothes.is/) is an open annotation layer for the web, implementing the [W3C Web Annotation Data Model](https://www.w3.org/TR/annotation-model/). Annotations are structured JSON-LD with selectors (TextQuoteSelector, TextPositionSelector, etc.) pointing to specific content ranges.

**Relevance to SemPKM:** The RSS Reader & Hypothesis Integration milestone already plans Hypothesis annotation sync (Phase 6 of that milestone). The academic workspace research reinforces this as a high-priority integration -- annotations are the bridge between reading capture and structured knowledge. W3C Web Annotation is inherently RDF-compatible (JSON-LD), making it a natural fit for SemPKM's triplestore.

### 4.2 BIBFRAME

[BIBFRAME (Bibliographic Framework)](https://www.loc.gov/bibframe/) is the Library of Congress's RDF-based replacement for MARC records. It models bibliographic description as Works (abstract intellectual content), Instances (specific editions/formats), and Items (individual copies).

**Relevance to SemPKM:** BIBFRAME could serve as the vocabulary for a "Library" or "Bibliography" mental model, providing structured metadata for academic sources. This extends the mental model system (v1.0 Phase 3) with a domain-specific ontology. BIBFRAME's Work/Instance/Item hierarchy maps well to how academics think about sources (the paper vs. the PDF vs. the annotated copy).

### 4.3 Nanopublications / ClaimReview

[Nanopublications](https://nanopub.net/) are minimal units of publishable information: an assertion (the claim), provenance (who said it, based on what), and publication info (when, where). [ClaimReview](https://schema.org/ClaimReview) is Schema.org's vocabulary for fact-checking.

**Relevance to SemPKM:** These represent structured, attributable knowledge claims -- exactly what SemPKM's typed entities could model. A "Research Claims" mental model could define Claim, Evidence, and Review types that export as nanopublications. This is entirely new territory for SemPKM's roadmap.

### 4.4 Reference Managers (Zotero, Mendeley)

Academic workflows depend on reference managers for bibliography management. Integration points include:
- **Import**: Zotero RDF export, BibTeX import, CSL-JSON
- **Sync**: Zotero API for bidirectional library sync
- **Citation**: Generate citations from SemPKM objects in standard formats

**Relevance to SemPKM:** Not currently on the roadmap. Reference manager integration is a common expectation for academic tools and could be implemented as a mental model (types + sync service) or a dedicated integration milestone.

### 4.5 ORCID

[ORCID](https://orcid.org/) provides persistent digital identifiers for researchers. The ORCID API allows retrieving researcher profiles, publications, and affiliations.

**Relevance to SemPKM:** ORCID integration connects to the Identity: WebID + IndieAuth milestone. WebID profiles could include ORCID identifiers, and Person entities could link to ORCID profiles for disambiguation. This is a natural extension of the planned identity work.

### 4.6 Relationship to Existing SemPKM Standards

SemPKM already uses several standards that the academic workspace features build upon:

| Standard | Current Use | Academic Extension |
|----------|------------|-------------------|
| **RDF** | Core data model | All proposed features are RDF-native |
| **SHACL** | Form generation, validation | Shapes for Claim, Evidence, Argument types |
| **OWL** | Inference (v2.4) | Ontological relationships between academic concepts |
| **SKOS** | Concept hierarchies | Thesaurus/taxonomy for research domains |
| **Dublin Core** | Basic metadata | Extended bibliographic metadata |
| **FOAF** | Person entities | Researcher profiles, co-authorship |
| **Schema.org** | General metadata | Article, CreativeWork, Review types |

---

## 5. Cross-Reference with SemPKM Roadmap

### 5.A Already Covered by Existing/Shipped Milestones

These features are substantially addressed by SemPKM's current implementation:

| Feature | Roadmap Coverage |
|---------|-----------------|
| Typed entities with templates | v1.0 Phase 3: Mental Model System -- SHACL shapes define types with fields and relations |
| Flexible hierarchies (PPV, PARA, GTD) | v1.0 Phase 3 + Quick Task 24: PPV mental model installed; any hierarchy is an installable ontology |
| Graph visualization | v1.0 Phase 5: Data Browsing and Visualization -- force-directed graph with navigation |
| Dark mode and visual polish | v2.0 Phase 13: Dark Mode and Visual Polish |
| Faceted navigation (by type) | v2.0 Phase 12: Sidebar and Navigation -- nav tree filtered by type |
| Full-text keyword search | v2.2 Phase 24: FTS Keyword Search + v2.3 Phase 29: FTS Fuzzy Search |
| SPARQL query interface | v2.2 Phase 23: SPARQL Console |
| Flexible panel workspace | v2.3 Phase 30: Dockview Migration -- arbitrary panel arrangement |
| Named layouts / saved workspaces | v2.3 Phase 33: Named Layouts |
| Object views (read/edit/flip) | v2.3 Phase 31: Object View Redesign |
| OWL inference / bidirectional links | v2.4 Phase 35: OWL 2 RL Inference |
| SHACL-AF derived triples | v2.4 Phase 36: SHACL-AF Rules Support |
| Global lint/validation dashboard | v2.4 Phases 37-38: Lint Data Model, API, and Dashboard UI |
| Settings system | v2.0 Phase 15: Settings System |

### 5.B Extends Planned Milestones

These features build on existing roadmap items but go further than currently planned:

| Feature | Extends Milestone | How It Extends |
|---------|------------------|----------------|
| Hypothes.is annotation sync | RSS Reader & Hypothesis Integration | Already planned as Phase 6; academic research reinforces priority and adds structured annotation-to-claim pipelines |
| W3C Web Annotation storage | RSS Reader & Hypothesis Integration | Already planned; academic use case adds annotation-to-concept-map workflows |
| Argument/concept maps | Graph visualization (v1.0 Phase 5) | Current graph shows entity relationships; argument maps need typed edges (supports, contradicts, qualifies) and layout algorithms for argumentation |
| BIBFRAME bibliographic metadata | Mental Model System (v1.0 Phase 3) | New mental model using BIBFRAME vocabulary -- extends the model packaging pattern |
| Export pipelines (Markdown/LaTeX) | Web Components for Mental Models (Potential Idea) | Export could be a model-contributed capability; LaTeX/BibTeX generation is domain-specific |
| Integrated task boards | Low-Code UI Builder & Workflows (Potential Idea) | Task boards linked to knowledge objects extend the workflow orchestration concept |
| Shared annotation spaces | Collaboration & Federation | Shared annotation layers extend the named graph sync with annotation-specific UI |
| Team/project dashboards | Collaboration & Federation (Phase E) | Already sketched as "Collaboration UI"; academic use case adds knowledge-gap analysis |
| Graph-based semantic search | SPARQL Interface (Phase 2: Autocomplete) | Ontology-aware autocomplete is planned; semantic similarity search (embeddings) goes further |
| ORCID researcher identity | Identity: WebID + IndieAuth | WebID profiles could include ORCID links; natural extension of identity work |
| Dependency/info-flow views | Low-Code UI Builder & Workflows (Potential Idea) | Information dependency visualization extends basic task dependency tracking |

### 5.C Entirely New Feature Areas Not on Roadmap

These features have no current roadmap coverage and would require new milestones or significant additions to existing ones:

| Feature | Description | Alignment with SemPKM Architecture |
|---------|-------------|-------------------------------------|
| **PDF/HTML reading capture** | In-app reader with inline annotation producing structured notes | High -- annotations are RDF (W3C Web Annotation); needs PDF rendering component |
| **Low-friction inboxes** | Quick capture from browser, mobile, CLI into unified inbox | Medium -- requires browser extension, mobile app, or API endpoint; inbox is a typed entity |
| **Multi-modal capture** | Images, code snippets, email, chat fragments as first-class nodes | Medium -- extends object creation; needs file attachment support and content extractors |
| **Question-centric views** | Research questions as persistent entities with linked evidence/claims | High -- naturally modeled as a mental model type with SHACL shapes; needs dedicated view |
| **Research project templates** | Reusable templates for "Empirical Study," "Lit Review," etc. | High -- directly maps to mental models with pre-configured types, views, and workflows |
| **Review cycles** | Weekly/monthly/quarterly review entities with prompts and metrics | High -- review is a typed entity; metrics computed from graph queries; needs scheduling |
| **Learning metrics** | Non-gamified indicators (concepts strengthened, gaps identified) | High -- computed from SPARQL queries over the knowledge graph; needs dashboard UI |
| **Draft-from-graph publishing** | Generate outlines/drafts from argument and concept maps | Medium -- requires text generation from graph traversal; optional LLM integration |
| **Nanopublication export** | Export structured claims as nanopublications | High -- nanopub format is RDF; SemPKM's typed entities map directly |
| **ClaimReview export** | Export fact-checking structured data | Medium -- Schema.org ClaimReview is RDF; needs claim type definition |
| **Reference manager integration** | Zotero/Mendeley sync, BibTeX import/export | Medium -- Zotero has an API; BibTeX is parseable; needs sync service |
| **Concept/argument mapping tool** | Visual argument construction with typed edges | Medium -- extends graph viz with editable argument-specific layout |

---

## 6. Implications for SemPKM

### 6.1 Highest Architectural Alignment

The following new feature areas align most naturally with SemPKM's existing RDF/SHACL architecture and could be implemented with the least friction:

1. **Question-centric views and research project templates** -- These are essentially new mental models. A "Research Methodology" model could define Question, Hypothesis, Method, Finding, and Review types with SHACL shapes, views, and named layouts. No new infrastructure required; just model packaging.

2. **Review cycles and learning metrics** -- Reviews are typed entities. Metrics are SPARQL queries over the existing graph (count of claims with evidence, open questions without answers, annotated-but-unintegrated sources). The lint dashboard pattern (v2.4 Phase 38) provides a template for the metrics UI.

3. **Nanopublication and ClaimReview export** -- Both formats are RDF. SemPKM already stores structured claims as typed entities. Export is a serialization problem, not an architectural one. Could be implemented as an API endpoint or model-contributed export action.

4. **BIBFRAME bibliographic model** -- Another installable mental model. The Work/Instance/Item hierarchy maps to SHACL node shapes. Import from BibTeX/RIS could be a model-contributed utility.

### 6.2 Mental Model vs. Core Platform

| Approach | Features |
|----------|----------|
| **Installable Mental Model** | Research project templates, BIBFRAME bibliography, question-centric entities, review cycle entities, nanopub types, ClaimReview types, PPV-style hierarchies (already done) |
| **Core Platform Extension** | PDF/HTML reader, low-friction capture (browser extension), multi-modal file attachments, argument mapping UI, draft-from-graph generation, reference manager sync, learning metrics dashboard |
| **Integration Service** | Zotero sync, ORCID lookup, Hypothes.is sync (already planned), LLM-assisted linking |

The mental model approach handles entity types and views; core platform extensions handle new UI components and external service integrations. This distinction is important: mental models should not require new platform capabilities to function.

### 6.3 Suggested Priority Ordering for Future Consideration

Based on architectural alignment, user value, and implementation effort:

**Tier 1 -- High alignment, low effort (mental model packages):**
1. Research methodology mental model (questions, hypotheses, findings, reviews)
2. BIBFRAME bibliography mental model
3. Review cycles and learning metrics (SPARQL-computed, dashboard UI)

**Tier 2 -- High value, moderate effort (platform extensions):**
4. PDF/HTML reading with annotation (W3C Web Annotation, extends RSS Reader milestone)
5. Reference manager integration (Zotero API, BibTeX import)
6. Nanopublication/ClaimReview export endpoints

**Tier 3 -- High value, high effort (new subsystems):**
7. Argument/concept mapping tool (visual editor with typed edges)
8. Draft-from-graph publishing (text generation from graph traversal)
9. Low-friction capture ecosystem (browser extension, mobile, CLI)

**Tier 4 -- Dependent on other milestones:**
10. Shared annotation spaces (depends on Collaboration & Federation)
11. Team knowledge dashboards (depends on Collaboration & Federation)
12. Multi-modal capture (depends on file attachment infrastructure)

### 6.4 Note on Scope

This analysis is purely informational. The features identified here represent research-backed possibilities, not commitments. Many of the Tier 1 items could be created as community-contributed mental models rather than project-maintained features. The strength of SemPKM's architecture is that domain-specific knowledge structures (academic research, bibliographic management, project methodology) can be packaged and shared without modifying the core platform.

---

*Research conducted: 2026-03-05*
*Source: Perplexity Deep Research chat analyzing academic workspace UI design, PKM/PIM literature, and research-backed feature requirements*
*Cross-referenced against: SemPKM ROADMAP.md (milestones v1.0 through v2.4 + future milestones)*
