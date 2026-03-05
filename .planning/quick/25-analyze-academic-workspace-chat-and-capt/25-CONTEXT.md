# Quick Task 25: Analyze academic workspace chat and capture insights as research document - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning

<domain>
## Task Boundary

Analyze a Perplexity Deep Research chat about academic workspace UI design and PKM research-backed features for SemPKM. Produce a structured research document and cross-reference insights against the existing ROADMAP.md.

Source material covers:
1. Academic UI layout proposal (three-pane workspace, mode-specific views)
2. PKM/PIM research landscape (academic literature, workflow methodologies)
3. Research-backed feature checklist (7 themes: Capture, Organize, Retrieve & Sensemaking, Plan & Execute, Reflect & Learn, Share & Publish, Collaboration & Social PKM)

</domain>

<decisions>
## Implementation Decisions

### Output Format
- Structured research document at `.planning/research/academic-workspace.md`
- Follows existing research doc conventions (see other files in `.planning/research/`)

### Scope of Analysis
- Full capture: document everything from the chat (UI layout, all 7 feature themes, PKM research context, integrations, collaboration features)
- Do not filter or prioritize at this stage -- capture comprehensively

### Roadmap Cross-Reference
- Cross-reference all chat features against existing ROADMAP.md milestones (shipped and future)
- Identify: (a) features already covered by existing/planned milestones, (b) features that extend planned milestones, (c) entirely new feature areas not yet on the roadmap
- Do NOT modify ROADMAP.md itself -- the research doc provides input for future milestone planning

### Claude's Discretion
- Internal document organization and section structure
- How to categorize/group the cross-reference (by theme vs by milestone vs hybrid)

</decisions>

<specifics>
## Specific Ideas

- Reference existing research docs in `.planning/research/` for format conventions
- The "Academic Persona" framing from the chat maps well to SemPKM's installable mental models concept
- Key integrations mentioned: Hypothes.is/Web Annotation, BIBFRAME, nanopublications/ClaimReview, reference managers, ORCID
- The chat's "top-level modes" (Read, Think, Organize, Plan, Publish) could inform future workspace layout planning

</specifics>
