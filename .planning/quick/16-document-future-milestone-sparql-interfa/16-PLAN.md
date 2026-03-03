---
phase: 16-document-future-milestone-sparql-interfa
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/REQUIREMENTS.md
  - .planning/ROADMAP.md
autonomous: true
requirements: [DOC-16]

must_haves:
  truths:
    - "Future SPARQL interface milestone is fully documented with phases, requirements, and success criteria in the planning system"
    - "The milestone builds on existing SPARQL console (Phase 23) and captures all six feature areas: permissions, autocomplete, UI pills, query history, saved queries, named queries with views"
    - "Requirements are traceable and follow project conventions (requirement IDs, success criteria, phase mapping)"
  artifacts:
    - path: ".planning/REQUIREMENTS.md"
      provides: "New requirement IDs for SPARQL interface milestone under Future Requirements section"
      contains: "SQ-"
    - path: ".planning/ROADMAP.md"
      provides: "Future milestone entry with phase descriptions"
      contains: "SPARQL Interface"
  key_links:
    - from: ".planning/ROADMAP.md"
      to: ".planning/REQUIREMENTS.md"
      via: "requirement IDs referenced in phase details"
      pattern: "SQ-\\d+"
---

<objective>
Document a future milestone for a rich SPARQL interface that builds on the existing Yasgui-based SPARQL Console (Phase 23, v2.2). The milestone captures six feature areas: graph-aware permissions on SPARQL execution, SPARQL autocomplete (prefixes, classes, properties from loaded ontologies), UI pills for IRIs/prefixes in query editor, enhanced query history with search/filter, saved/bookmarked queries with sharing, and named queries that produce reusable views.

Purpose: Capture the user's vision for SPARQL interface evolution so it can be properly scoped, researched, and planned when the time comes. This is roadmap documentation, not implementation.

Output: Updated REQUIREMENTS.md (new SQ-* requirement IDs) and updated ROADMAP.md (new future milestone entry with phase sketches).
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add SPARQL interface requirements to REQUIREMENTS.md</name>
  <files>.planning/REQUIREMENTS.md</files>
  <action>
Add a new section under "Future Requirements" in `.planning/REQUIREMENTS.md` titled `### SPARQL Interface (future milestone)`.

Define the following requirement IDs, each with a one-line user-visible behavior description following the existing "User can..." pattern:

**Permissions:**
- **SQ-01**: User's SPARQL queries are automatically scoped to graphs they have permission to read; owner can opt into all-graphs mode; members/guests cannot access event graphs or other users' draft graphs
- **SQ-02**: Admin can define SPARQL execution policies (e.g., query timeout limits, result size caps, UPDATE prohibition) per role

**Autocomplete:**
- **SQ-03**: SPARQL editor offers prefix autocomplete from the project's prefix registry (user > model > LOV > built-in layers)
- **SQ-04**: SPARQL editor offers class and property autocomplete derived from installed Mental Model ontologies and SHACL shapes
- **SQ-05**: Autocomplete suggestions show human-readable labels alongside IRIs (using the label service precedence chain)

**UI Pills:**
- **SQ-06**: IRIs and prefixed names in the SPARQL editor render as compact, styled pills showing the human-readable label; clicking a pill navigates to the object or expands the full IRI
- **SQ-07**: Prefix declarations in the query header render as collapsed pill chips that can be expanded/removed inline

**Query History:**
- **SQ-08**: User can browse a searchable, filterable history of previously executed queries with execution timestamp, duration, and result count
- **SQ-09**: Query history is persisted server-side (not just localStorage) and accessible across devices/sessions

**Saved Queries:**
- **SQ-10**: User can save/bookmark a SPARQL query with a name and optional description; saved queries appear in a dedicated panel or palette section
- **SQ-11**: User can share a saved query with other workspace members via a shareable link or by publishing it to a shared query library
- **SQ-12**: Saved queries support parameterization (template variables like `$type` or `$label` that prompt the user on execution)

**Named Queries as Views:**
- **SQ-13**: User can promote a saved query to a "named query" that appears as a reusable view in the object browser's view switcher
- **SQ-14**: Named query views execute their SPARQL query on demand and render results using the standard view renderers (table, cards, graph)
- **SQ-15**: Named query views can be included in Mental Model manifests as model-provided views alongside built-in view specs

Do NOT mark any of these as complete (no `[x]`). Use `- [ ]` for all. Do NOT add them to the Traceability table yet (no phases assigned).

Also add to the "Out of Scope" table:
| SPARQL UPDATE as general write surface | By design -- bypasses event sourcing; named queries are read-only SELECT/CONSTRUCT |
| Federated SPARQL (SERVICE keyword) | Security and performance concerns; single-triplestore scope for now |
  </action>
  <verify>grep -c "SQ-" .planning/REQUIREMENTS.md should return 15. grep "SPARQL Interface" .planning/REQUIREMENTS.md should match the section header.</verify>
  <done>15 SQ-* requirements defined across 6 feature areas under Future Requirements, plus 2 out-of-scope entries. No requirements marked complete. No traceability entries added.</done>
</task>

<task type="auto">
  <name>Task 2: Add SPARQL interface future milestone to ROADMAP.md</name>
  <files>.planning/ROADMAP.md</files>
  <action>
Add a new future milestone entry to ROADMAP.md. Place it AFTER the v2.3 section but BEFORE the Progress table. Use the following structure:

Under the `## Milestones` list at the top, add:
```
- (future) **SPARQL Interface** -- Rich SPARQL query experience with permissions, autocomplete, pills, history, saved queries, and named query views
```

Then add a new section after the v2.3 phase details:

```
### (Future) SPARQL Interface

**Milestone Goal:** Transform the basic Yasgui SPARQL console into a first-class query interface with graph-aware permissions, intelligent autocomplete from loaded ontologies, visual IRI pills in the editor, server-side query history, saved/shared queries with parameterization, and named queries that serve as reusable views in the object browser.

**Depends on:** v2.3 complete (dockview panels, object view redesign, named layouts provide the shell infrastructure)

**Estimated Phases (sketch -- to be refined during milestone planning):**

1. **SPARQL Permissions and Policies** -- Graph-scoped query execution per role, admin-configurable execution policies (timeouts, result caps, UPDATE prohibition)
   - Requirements: SQ-01, SQ-02
   - Key risk: Performance impact of per-query graph scoping; may need query rewriting vs. RDF4J native graph access control

2. **SPARQL Autocomplete** -- Prefix, class, and property autocomplete in the query editor from prefix registry and installed Mental Model ontologies/SHACL shapes
   - Requirements: SQ-03, SQ-04, SQ-05
   - Key risk: Yasgui's CodeMirror integration may resist custom completers; may need to evaluate replacing Yasgui's editor with a standalone CodeMirror 6 instance + custom SPARQL mode
   - Research needed: Yasgui plugin architecture for autocompletion, CodeMirror 6 SPARQL language support landscape

3. **IRI Pills and Editor Enhancements** -- Visual pill rendering for IRIs and prefix declarations in the SPARQL editor; click-to-navigate and inline expand/collapse
   - Requirements: SQ-06, SQ-07
   - Key risk: CodeMirror decoration/widget API complexity; pills must not interfere with query parsing or copy-paste
   - Research needed: CodeMirror 6 decoration widgets, similar implementations in SPARQL editors (e.g., QLever UI, Wikidata Query Service)

4. **Server-Side Query History** -- Searchable, filterable query execution history persisted to the backend; cross-device access; execution metadata (duration, result count, timestamp)
   - Requirements: SQ-08, SQ-09
   - Key risk: Storage growth from query history; need retention policy and pagination
   - Likely approach: New SQLAlchemy model (QueryExecution) with user FK, query text, executed_at, duration_ms, result_count, status

5. **Saved Queries and Sharing** -- Named/bookmarked queries with descriptions, parameterization (template variables), sharing via links or published library
   - Requirements: SQ-10, SQ-11, SQ-12
   - Key risk: Template variable UX (how to define, prompt, and validate parameters); sharing permissions model
   - Likely approach: New SQLAlchemy model (SavedQuery) with owner, query text, name, description, params JSON, is_published flag

6. **Named Queries as Views** -- Promote saved queries to named views in the object browser; rendered via standard renderers (table, cards, graph); Mental Model manifest integration
   - Requirements: SQ-13, SQ-14, SQ-15
   - Key risk: Named query views must integrate with existing ViewSpecService and manifest view declaration format without breaking the current view pipeline
   - Depends on: Phase 5 (saved queries must exist), v2.3 Phase 32 (carousel view infrastructure)
```

Do NOT add phase numbers (these are future, unnumbered). Do NOT add these to the Progress table. Keep the "(Future)" prefix to distinguish from committed phases.
  </action>
  <verify>grep "SPARQL Interface" .planning/ROADMAP.md should return at least 2 matches (milestone list + section header). grep -c "SQ-" .planning/ROADMAP.md should return at least 6 (one per phase sketch).</verify>
  <done>Future SPARQL Interface milestone documented in ROADMAP.md with milestone goal, dependency note, 6 phase sketches with requirement mappings, key risks, and research needs identified per phase.</done>
</task>

</tasks>

<verification>
1. `grep -c "SQ-" .planning/REQUIREMENTS.md` returns 15
2. `grep -c "SQ-" .planning/ROADMAP.md` returns >= 6
3. `grep "SPARQL Interface" .planning/ROADMAP.md` matches milestone entry
4. No `[x]` markers on any SQ-* requirement (all are future/unchecked)
5. No SQ-* entries in the Traceability table (no phases assigned yet)
6. Out of Scope table includes SPARQL UPDATE and federated SPARQL entries
</verification>

<success_criteria>
- 15 SQ-* requirements documented across 6 feature areas in REQUIREMENTS.md
- Future milestone with 6 phase sketches in ROADMAP.md
- All requirements are `[ ]` (not started), none in traceability table
- Phase sketches include key risks and research needs
- Existing v2.3 content in both files is unchanged
</success_criteria>

<output>
After completion, create `.planning/quick/16-document-future-milestone-sparql-interfa/16-SUMMARY.md`
</output>
