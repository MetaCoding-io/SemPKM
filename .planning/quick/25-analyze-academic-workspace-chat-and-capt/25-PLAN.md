---
phase: quick-25
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/research/academic-workspace.md
autonomous: true
requirements: [QUICK-25]

must_haves:
  truths:
    - "Research document captures all 7 feature themes from the chat (Capture, Organize, Retrieve & Sensemaking, Plan & Execute, Reflect & Learn, Share & Publish, Collaboration & Social PKM)"
    - "Academic UI layout proposal (three-pane, top-level modes) is fully documented"
    - "PKM/PIM research landscape and literature references are recorded"
    - "Every feature is cross-referenced against existing ROADMAP.md milestones with clear categorization (already covered / extends planned / entirely new)"
    - "Key integrations (Hypothes.is, BIBFRAME, nanopublications, ORCID, reference managers) are documented with relevance to SemPKM"
  artifacts:
    - path: ".planning/research/academic-workspace.md"
      provides: "Comprehensive research document analyzing academic workspace chat"
      min_lines: 200
  key_links:
    - from: ".planning/research/academic-workspace.md"
      to: ".planning/ROADMAP.md"
      via: "Cross-reference section mapping features to milestones"
      pattern: "(v2\\.[0-9]|SPARQL Interface|Obsidian Import|Identity|Collaboration|RSS Reader)"
---

<objective>
Analyze a Perplexity Deep Research chat about academic workspace UI design and PKM research-backed features. Produce a structured research document that comprehensively captures all insights and cross-references them against the existing ROADMAP.md.

Purpose: Create a referenceable research artifact that informs future milestone planning for SemPKM, particularly around academic/research workflow support.
Output: `.planning/research/academic-workspace.md`
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/quick/25-analyze-academic-workspace-chat-and-capt/25-CONTEXT.md
@.planning/research/future-milestones.md (format reference)
@.planning/research/collaboration-architecture.md (format reference)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create comprehensive academic workspace research document</name>
  <files>.planning/research/academic-workspace.md</files>
  <action>
Create `.planning/research/academic-workspace.md` following the conventions of existing research docs (header with Created date and Context, Executive Summary, numbered sections, horizontal rule separators).

Structure the document with these sections:

**Header:** Title "Academic Workspace Design & PKM Research Analysis", Created date, Context explaining source (Perplexity Deep Research chat analyzing academic UI design and PKM literature).

**Executive Summary:** 3-5 paragraph overview of the chat's three main areas and their relevance to SemPKM's roadmap.

**Section 1: Academic UI Layout Proposal**
- Three-pane workspace design (Left: workspaces/projects/saved views/filters; Center: active mode; Right: context/annotations/semantic metadata/local graph/linked tasks)
- Top-level modes aligned with academic verbs: Read, Think (arguments/concepts), Organize (library), Plan (projects), Publish (drafts/exports)
- How this maps to SemPKM's existing dockview workspace architecture
- Note: the "Academic Persona" framing connects to SemPKM's installable mental models concept — modes could be model-contributed views

**Section 2: PKM/PIM Research Landscape**
- PKM emergence (late 1990s, extension of organizational KM)
- Key literature: Razmerita et al., Frand & Hixson (capture/organize/retrieve strategies)
- Empirical work: wiki/Web 2.0 PKM in courses; structured personal spaces + social features
- Recent trends: multi-disciplinary approaches, AI integration, "second brain" practices
- PIM methodologies: GTD, PARA, annotation+concept mapping workflows
- Project management as knowledge work: reflective practice, learning loops, info dependency visualization

**Section 3: Research-Backed Feature Checklist** (one subsection per theme, 7 total):

3.1 Capture
- Integrated reading capture (PDF/HTML + annotation to structured notes)
- Low-friction inboxes
- Multi-modal capture (voice, image, web clip)

3.2 Organize
- Typed entities with templates (Work, Concept, Claim, Evidence, Project, Task, Review)
- Flexible hierarchies (PPV, PARA, GTD as installable ontologies)
- Faceted navigation

3.3 Retrieve & Sensemaking
- Graph-based search
- Argument/concept maps (AIF + KnowledgeConcepts)
- Question-centric views

3.4 Plan & Execute
- Research project templates
- Integrated task boards (linked to Works/claims)
- Dependency & info-flow views

3.5 Reflect & Learn
- Review cycles (weekly/monthly/quarterly/yearly)
- Learning metrics (non-gamified)

3.6 Share & Publish
- Draft-from-graph workflows
- Export pipelines (Markdown/LaTeX, nanopubs, ClaimReview, repos)

3.7 Collaboration & Social PKM
- Shared annotation/argument spaces
- Team/project dashboards

**Section 4: Key Integrations & Standards**
- Hypothes.is / W3C Web Annotation (already planned in RSS Reader milestone)
- BIBFRAME-based metadata (bibliographic description)
- Nanopublications / ClaimReview (structured claims)
- Reference managers (Zotero, Mendeley interop)
- ORCID (researcher identity)
- Relationship to existing SemPKM standards: RDF, SHACL, OWL, SKOS, Dublin Core, FOAF, Schema.org

**Section 5: Cross-Reference with SemPKM Roadmap**

Organize as a table or grouped list with three categories:

(a) **Already Covered by Existing/Shipped Milestones:**
- Map each feature to the specific milestone/phase that addresses it
- Examples: typed entities (v1.0 Mental Models), graph visualization (v1.0 Phase 5), dark mode (v2.0 Phase 13), installable ontologies (v1.0 Phase 3 + quick task 24 PPV), FTS search (v2.2), dockview workspace (v2.3), inference/bidirectional links (v2.4), SHACL validation (v2.4)

(b) **Extends Planned Milestones:**
- Features that build on existing roadmap items but go further
- Examples: Hypothes.is sync extends RSS Reader milestone, argument maps extend graph visualization, BIBFRAME extends mental model system, export pipelines extend potential Web Components milestone, task boards extend possible future workflow milestone

(c) **Entirely New Feature Areas Not on Roadmap:**
- Features with no current roadmap coverage
- Examples: PDF/HTML reading capture with annotation, question-centric views, review cycles/spaced repetition, learning metrics, draft-from-graph publishing, nanopublication export, ORCID integration, reference manager integration, multi-modal capture

**Section 6: Implications for SemPKM**
- Which new feature areas have the highest alignment with SemPKM's semantic/RDF architecture
- Which could be implemented as installable Mental Models vs core platform features
- Suggested priority ordering for future milestone consideration
- Note: this is analysis only — ROADMAP.md is NOT modified

Do NOT modify ROADMAP.md. This document is purely informational input for future planning.
  </action>
  <verify>
    <automated>test -f .planning/research/academic-workspace.md && wc -l .planning/research/academic-workspace.md | awk '{if ($1 >= 200) print "PASS: "$1" lines"; else print "FAIL: only "$1" lines"}'</automated>
  </verify>
  <done>
    - Research document exists at `.planning/research/academic-workspace.md`
    - All 7 feature themes documented with specific features listed
    - Academic UI layout (three-pane, modes) fully described
    - PKM research landscape with literature references captured
    - Key integrations section covers Hypothes.is, BIBFRAME, nanopubs, ORCID, reference managers
    - Cross-reference section maps every feature to one of three categories (covered / extends / new)
    - ROADMAP.md is unchanged
  </done>
</task>

</tasks>

<verification>
- `.planning/research/academic-workspace.md` exists and is >= 200 lines
- Document contains all 7 feature themes as sections
- Cross-reference section references specific ROADMAP milestones by name
- No modifications to ROADMAP.md or any other existing files
</verification>

<success_criteria>
- Comprehensive research document captures everything from the Perplexity chat
- Every feature is categorized in the cross-reference (already covered / extends planned / entirely new)
- Document follows existing research doc conventions (header, sections, separators)
- Useful as input for future milestone planning sessions
</success_criteria>

<output>
After completion, create `.planning/quick/25-analyze-academic-workspace-chat-and-capt/25-SUMMARY.md`
</output>
