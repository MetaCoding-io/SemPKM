---
phase: 21-research-ux-ui-flow-for-interactive-obsi
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/research/obsidian-import-wizard-ux.md
autonomous: true
requirements: [QUICK-21]

must_haves:
  truths:
    - "UX flow document describes an end-to-end interactive import wizard with clear step sequence"
    - "OpenRefine-style type mapping pattern is documented with glob-based and manual file-to-type assignment"
    - "Property mapping step shows how YAML frontmatter keys map to SHACL shape predicates per type, with fuzzy auto-suggestion"
    - "Wizard applies type-level property mappings globally (e.g. mapping 'related' to skos:related for all Notes)"
    - "Document identifies which existing backend services (ShapesService, Command API, SearchService) support each wizard step"
    - "Document includes ASCII wireframes or structured screen descriptions for each wizard step"
  artifacts:
    - path: ".planning/research/obsidian-import-wizard-ux.md"
      provides: "Complete UX/UI flow design for interactive Obsidian import wizard"
      min_lines: 200
  key_links:
    - from: "wizard type mapping step"
      to: "ShapesService.get_node_shapes()"
      via: "API call to fetch available types and their SHACL property shapes"
      pattern: "get_node_shapes|get_types"
    - from: "wizard property mapping step"
      to: "PropertyShape dataclass"
      via: "fuzzy match frontmatter keys against PropertyShape.path/name"
      pattern: "PropertyShape"
    - from: "wizard import execution step"
      to: "POST /api/commands"
      via: "batch Command API calls (object.create, body.set, edge.create)"
      pattern: "/api/commands"
---

<objective>
Research and design the UX/UI flow for an interactive Obsidian import wizard with OpenRefine-style type and property mapping.

Purpose: The current Obsidian onboarding workflow (Chapter 24) relies on external Python scripts and LLM-assisted classification run outside SemPKM. The user wants an in-app interactive wizard that provides a guided, visual experience -- similar to OpenRefine's column-type reconciliation flow -- where users map files to types, map YAML frontmatter keys to SHACL properties, and apply mappings globally per type before executing the import.

Output: A research document at `.planning/research/obsidian-import-wizard-ux.md` with complete UX flow design, screen-by-screen descriptions, interaction patterns, data model for import jobs, and implementation notes referencing existing backend services.
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@docs/guide/24-obsidian-onboarding.md
@backend/app/services/shapes.py
@backend/app/commands/router.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Design the interactive Obsidian import wizard UX flow</name>
  <files>.planning/research/obsidian-import-wizard-ux.md</files>
  <action>
Create a comprehensive UX/UI flow design document for an interactive Obsidian import wizard. The document must cover the following sections:

**1. Overview and Design Goals**
- Compare current workflow (Chapter 24: external scripts + LLM) with proposed in-app wizard
- State design principles: progressive disclosure, OpenRefine-style reconciliation, batch-then-review, no data loss
- Reference OpenRefine's column reconciliation and type assignment UX as the inspiration

**2. Wizard Step Sequence (5-6 steps)**

Step 1 -- **Start Import Job**: User selects a folder of .md files (via file picker or paste path). Backend scans the folder, extracts file list with metadata (folder structure, frontmatter keys, tag counts, file sizes). Display summary stats (total files, files with frontmatter, unique frontmatter keys, folder distribution). This is the vault audit step from Chapter 24, but interactive.

Step 2 -- **Type Mapping (OpenRefine-style)**: Display all files in a table grouped by detected patterns (folder, tags, frontmatter type key). Default type assignment: Note. User can:
  - Select individual files and assign a type
  - Use glob patterns (e.g. `People/**` -> Person, `Projects/**` -> Project) to bulk-assign types
  - Click a folder group header to assign all files in that folder to a type
  - See a live type distribution summary (pie chart or bar: "142 Notes, 28 Persons, 31 Projects, 19 Concepts")
  - Available types come from ShapesService.get_types() -- not hardcoded to Basic PKM

Step 3 -- **Property Mapping (per type)**: For each type that has files assigned, show a mapping panel:
  - Left column: unique YAML frontmatter keys found across files of this type (e.g. "date", "tags", "status", "related")
  - Right column: available SHACL properties for this type (from ShapesService.get_form_for_type())
  - Fuzzy auto-suggestion: for each frontmatter key, auto-suggest the best-matching SHACL property using string similarity (e.g. "status" -> bpkm:status, "title" -> dcterms:title, "name" -> foaf:name)
  - User can accept/reject/change each suggestion
  - Unmapped keys get a "skip" or "store as tag" option
  - KEY BEHAVIOR: mappings apply to ALL files of this type (not per-file). If user maps "related" to "skos:related" for type Note, every Note file with a "related" frontmatter key gets that mapping applied.

Step 4 -- **Relationship Mapping**: Show wiki-link patterns detected across files. User can:
  - See the auto-detected type-pair -> predicate heuristic (from Chapter 24's EDGE_PREDICATES table)
  - Override any type-pair mapping
  - Choose a default fallback predicate (default: skos:related)
  - Preview sample edges with their inferred predicates

Step 5 -- **Preview and Confirm**: Show a summary of the import:
  - Object counts by type
  - Property mappings by type
  - Edge count and predicate distribution
  - Sample preview of 3-5 objects with their full mapped properties
  - Dry-run validation: check for duplicate titles, missing required properties per SHACL shapes
  - "Start Import" button

Step 6 -- **Import Execution and Progress**: Execute the import via batched Command API calls. Show:
  - Progress bar (X of Y objects created)
  - Phase indicators (Creating objects -> Setting bodies -> Creating edges)
  - Error log for any failed commands
  - "Import Complete" summary with links to browse imported objects

**3. Data Model for Import Jobs**
- ImportJob: id, status (scanning, mapping, previewing, importing, complete, failed), source_path, created_at, file_count
- ImportFileMapping: job_id, file_path, assigned_type, frontmatter_keys (JSON)
- ImportPropertyMapping: job_id, type_iri, frontmatter_key, target_predicate, mapping_mode (auto-suggested, user-set, skip, tag)
- ImportEdgeMapping: job_id, source_type, target_type, predicate
- Consider: SQLAlchemy models or in-memory session state? Pros/cons of each.

**4. Backend Integration Points**
- Which existing services support each step:
  - ShapesService.get_types() and get_form_for_type() for type/property enumeration
  - Command API (POST /api/commands) for batch import execution
  - SearchService for duplicate detection during preview
  - Markdown parsing for body extraction (strip frontmatter)
- What new endpoints would be needed:
  - POST /api/import/scan (accept folder path, return file metadata)
  - GET /api/import/{job_id}/status
  - POST /api/import/{job_id}/execute
  - WebSocket or SSE for progress updates during import

**5. Fuzzy Matching Algorithm**
- Research and recommend a string similarity approach for auto-suggesting property mappings
- Options: Levenshtein distance, Jaro-Winkler, token-based (split on camelCase/underscore and compare tokens), or a combination
- Consider: frontmatter key "related" should match SHACL property with path containing "related" even if full IRI is "http://www.w3.org/2004/02/skos/core#related"
- Recommend matching against both PropertyShape.name (human label) and the local name extracted from PropertyShape.path

**6. UI Technology Notes**
- htmx compatibility: wizard steps as partial page loads via hx-get/hx-post
- State management: wizard state stored server-side in session or SQLAlchemy, not in browser JS
- Table rendering: existing table view patterns in SemPKM for file list display
- Drag-and-drop or checkbox selection for file-to-type assignment

**7. ASCII Wireframes**
- Include ASCII wireframes or structured screen descriptions for each wizard step
- Show the type mapping table with columns: File Path | Folder | Frontmatter Keys | Assigned Type [dropdown]
- Show the property mapping panel: Frontmatter Key | Suggested Mapping | Confidence | Action [accept/change/skip]
- Show the preview/confirm screen layout

**8. Open Questions and Future Enhancements**
- LLM-assisted classification as optional enhancement (use existing LLM service connection)
- Incremental/delta imports (import only new files since last job)
- Undo/rollback of an import job
- Support for non-Obsidian markdown sources
  </action>
  <verify>
    File exists at .planning/research/obsidian-import-wizard-ux.md with 200+ lines.
    Document contains sections for all 6 wizard steps.
    Document references ShapesService, Command API, and PropertyShape by name.
    Document includes ASCII wireframes or structured screen descriptions.
  </verify>
  <done>
    Complete UX/UI flow design document for the interactive Obsidian import wizard exists in .planning/research/, covering the full wizard step sequence, data model, backend integration points, fuzzy matching approach, htmx-compatible UI notes, and wireframes. The document is detailed enough to serve as a specification for a future implementation milestone.
  </done>
</task>

</tasks>

<verification>
- .planning/research/obsidian-import-wizard-ux.md exists and is 200+ lines
- All 6 wizard steps are described with interaction details
- Backend integration points reference real service names (ShapesService, Command API, SearchService)
- Fuzzy matching approach is specified with algorithm recommendation
- Data model for import jobs is defined
- ASCII wireframes or screen descriptions are included for key steps
</verification>

<success_criteria>
A developer reading this document can understand the complete user journey, screen layouts, data flow, and backend wiring needed to implement the import wizard without asking clarifying questions about the UX intent.
</success_criteria>

<output>
After completion, create `.planning/quick/21-research-ux-ui-flow-for-interactive-obsi/21-SUMMARY.md`
</output>
