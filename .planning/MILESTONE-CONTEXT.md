# Milestone Context: v2.3

**Captured:** 2026-03-01
**Status:** Scope defined — ready for requirements + roadmap in fresh context

## Milestone Name

**v2.3 Shell, Navigation & Views**

## Goal

Complete the committed dockview-core Phase A migration (fixing split pane bugs as a side effect), redesign the object view to be markdown-first with manifest-driven carousel views, add named workspace layouts, improve FTS fuzzy search, and close a set of v2.2 bugs mixed into phases.

## In Scope

### Dockview-core Phase A (DEC-04 — committed v2.1)
- Replace Split.js editor-pane area with dockview-core panels
- Fixes (as side effect): wrong content in old pane after split, split zone too close to edges, want vertical split
- Keep sidebar panels as-is (Phase B for later)
- Use dockview-sempkm-bridge.css from v2.2

### Object View Redesign (headline feature)
- **Default view**: Full-page Markdown — body takes whole panel, properties HIDDEN by default
- **Property reveal**: button/key to reveal properties panel (slide-in or overlay)
- **Carousel views**: for object types that declare multiple views in the Mental Model manifest, show carousel UI to rotate through them (like cube flip)
  - Mental Model manifest declares views per type
  - Example: Workflow type → ["markdown", "workflow-diagram"] views in carousel
  - Notes type → just "markdown" (no carousel needed)
- Research: what manifest schema changes are needed for per-type view declarations

### Named Workspace Layouts (DOCK-02)
- After dockview migration, allow users to save/restore panel arrangements
- Include model-provided default layouts from Mental Model manifest

### FTS Improvement
- Better tokenization on indexing (reduce literal-match-only results)
- Fuzzy search support

### Bug Fixes (mix into relevant phases)
- Group-by in concept cards view broken → fix
- VFS Settings UI lost during debugging → restore to working state (no new features)
- Graph/card/table view switch buttons broken → remove broken buttons entirely
- Split pane bugs → resolved by dockview migration

## Out of Scope (v2.4+)
- SHACL editor environment (research + custom editor) → v2.4
- Low-code GUI builder / Notion-Airflow-like functionality → v2.4+
- VFS custom setups + disable toggle → v2.4+
- Full dockview Phase B (sidebar panels into dockview) → v2.4

## Phase Numbering
Continues from Phase 28. Next phase is **Phase 29**.

## User Notes (verbatim)
- "construct path towards notion / airflow functionality: constructing views or forms or small guis with objects that tie to our custom actions. maybe this small gui is essentially what obsidian is doing with excalidraw integration" → v2.4+
- "shacl environment: editor research on what exists + maybe build our own; where do these custom rules live? there should be some new views on left hand side and when we open a shacl rule, it has a custom editor" → v2.4
- "redesign edit and read view: properties hidden by default, can be exposed by menu; both modes focus on markdown for most views but some views can have multiple views with a ui to support rotating thru them like a cube. for example, a 'workflow' when opened will have a similar view (properties on top half and bottom half is a rotating carousel of options, first one being a visual representation of the workflow definition, and another markdown view like everything else." → v2.3 (headline)

## Resume Instructions
Run `/gsd:new-milestone` in fresh context. MILESTONE-CONTEXT.md will be found and used automatically. Skip to requirements definition.
