# Phase 46: Obsidian Mapping UI - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can interactively configure how Obsidian vault content maps to their installed Mental Model types before importing. This covers type mapping (note categories → RDF types), property mapping (frontmatter keys → RDF properties), and a preview step showing what the import will produce. The actual import execution is Phase 47.

</domain>

<decisions>
## Implementation Decisions

### Wizard Flow
- Import page uses a linear wizard with steps: Upload → Scan → Type Map → Property Map → Preview → Import
- Phase 46 adds steps 3-5 (Type Map, Property Map, Preview)
- Step bar at top with numbered circles and labels, current step highlighted, completed steps show checkmark
- Linear navigation: forward requires completing current step, back is always available
- "Next" button enables when step is valid
- Each step replaces content area via htmx

### Type Mapping
- Dropdown per detected group row listing installed Mental Model types
- Each dropdown includes "— Skip —" option to exclude groups from import
- Many-to-one allowed: multiple detected groups can map to the same Mental Model type
- Expandable sample notes per group row (click to see up to 10 sample note paths from scan data)
- Table columns: Detected Group | Count | Signal | Map To dropdown

### Property Mapping
- Per-type mapping: after type mapping, each mapped type shows its own property table
- Dropdown lists SHACL properties from the target type's NodeShape
- Also allows typing a custom RDF property IRI for keys that don't match any shape property
- Inline sample values from FrontmatterKeySummary shown per row to help user decide
- Skip option available for keys user doesn't want to import
- Markdown body content auto-maps to object body (body.set) — not configurable, mentioned in UI

### Preview
- Summary table: type, object count, properties mapped count
- 2-3 sample objects per type rendered as simplified key-value lists (not full SHACL form)
- "Back to Mapping" button for iteration between mapping and preview
- "Import" button proceeds to Phase 47 batch import

### Mapping Persistence
- Saved as mapping_config.json alongside scan_result.json in import directory
- Auto-save on each dropdown change via htmx POST — user never loses progress
- One-off per scan: tied to specific scan result, not reusable across vault uploads
- Cleaned up when import is discarded (existing discard endpoint handles the directory)

### Claude's Discretion
- Exact step bar visual design and CSS
- mapping_config.json schema structure
- How to fetch and display SHACL properties for the type dropdown
- Custom IRI input UX (inline text field, modal, etc.)
- How many sample objects to render per type in preview
- htmx endpoint design for auto-save and step transitions

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `VaultScanResult` / `NoteTypeGroup` / `FrontmatterKeySummary`: Phase 45 scan data models with `to_dict()`/`from_dict()` — mapping UI reads these
- `ShapesService` (`backend/app/services/shapes.py`): Extracts `NodeShapeForm` with `PropertyShape` list per type — property mapping dropdown source
- `scan_result.json`: Persisted scan results at `/app/data/imports/{user_id}/{timestamp}/` — co-locate mapping_config.json here
- Obsidian router (`backend/app/obsidian/router.py`): Existing endpoints for import page, upload, scan, discard — add mapping endpoints here

### Established Patterns
- htmx partial responses: `block_name = "content" if is_htmx else None` — use for wizard step transitions
- Import page at `/browser/import` via htmx page navigation (Phase 45 gap closure established this pattern)
- SSE broadcast for progress (reusable for import progress in Phase 47)

### Integration Points
- Import page template: `backend/app/templates/obsidian/import.html` — add wizard step bar and step partials
- ShapesService dependency: `backend/app/dependencies.py` — inject into mapping endpoints
- Installed model types: Query triplestore for `sh:targetClass` from all NodeShapes
- Phase 47 handoff: mapping_config.json is the contract between Phase 46 and Phase 47

</code_context>

<specifics>
## Specific Ideas

- Step bar inspired by common wizard patterns: numbered circles connected by lines, completed steps get a checkmark
- Type mapping table matches the lint dashboard table aesthetic (clean rows, muted headers, clear status)
- "Uncategorized" group should still be visually distinct (as decided in Phase 45 context)
- Preview sample objects should feel like lightweight object cards — just key-value pairs, not full form rendering

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 46-obsidian-mapping-ui*
*Context gathered: 2026-03-08*
