---
depends_on: [M011]
---

# M027: Notion Import Wizard

**Gathered:** 2026-03-16
**Status:** Queued — pending auto-mode execution

## Project Description

Interactive import flow for Notion workspace exports, mirroring the Obsidian import wizard pattern. ZIP export first (Notion's standard export), API integration later. Notion databases map to Mental Model types, rows to objects, relations to typed edges, with property type detection and mapping.

## Why This Milestone

Notion is the second largest target persona (after Obsidian). The import wizard doubles the addressable market by opening a second onramp. Research is complete (`.planning/notion-import-research.md`); the pattern is proven by the Obsidian importer.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Upload a Notion workspace ZIP export
- See scan results: database count, page count, detected property types, relation targets
- Map Notion databases to Mental Model types (or let auto-mapping suggest based on property overlap)
- Map Notion properties to RDF predicates per type
- See a preview of mapped objects before committing
- Run the import and see objects created with bodies, properties, and edges
- See Notion relations resolved as typed edges between imported objects
- See Notion rollups and formulas preserved as metadata (read-only properties)

### Entry point / environment

- Entry point: Admin > Import > Notion (or workspace command palette)
- Environment: Docker Compose
- Live dependencies involved: RDF4J triplestore

## Completion Class

- Contract complete means: ZIP parsing extracts databases/pages/properties/relations, mapping UI works, import creates valid objects
- Integration complete means: imported objects appear in object browser with correct types, relations render in relations panel, objects searchable via FTS
- Operational complete means: handles large exports (100+ databases, 1000+ pages), reports errors per page without aborting entire import

## Final Integrated Acceptance

- User uploads a Notion export with 3 databases (Tasks, Notes, Projects), all map to types
- Notion relations between databases resolve as edges between imported objects
- Property types detected correctly: dates, selects, multi-selects, URLs, numbers
- Import of 500+ page export completes without timeout or memory issues

## Risks and Unknowns

- **Notion export format** — Notion's ZIP export format is not officially documented. May contain markdown files, CSV databases, or both depending on export options.
- **Relation resolution** — Notion relations reference page IDs. Mapping page IDs to imported object IRIs requires a two-pass approach (create objects first, resolve relations second).
- **Formula/rollup preservation** — Notion formulas are computed server-side. Can only preserve the last computed value, not the formula itself.

## Existing Codebase / Prior Art

- `.planning/notion-import-research.md` — Feasibility research
- `backend/app/obsidian/` — Obsidian import wizard (scanner.py, executor.py) — reference implementation
- `backend/app/templates/obsidian/` — Import UI templates

## Relevant Requirements

- New: NOTION-01 (ZIP import), NOTION-02 (database→type mapping), NOTION-03 (relation→edge resolution)

## Scope

### In Scope

- Notion workspace ZIP parsing (markdown + CSV format)
- Database detection and property type inference
- Interactive type mapping UI (database → Mental Model type)
- Property mapping UI (Notion property → RDF predicate)
- Import preview with sample objects
- Batch import via Command API (with progress reporting)
- Relation resolution as typed edges
- Tag/multi-select → tag conversion
- Error reporting per page/database
- SSE progress events during import

### Out of Scope / Non-Goals

- Notion API integration (future — ZIP first)
- Formula/rollup re-computation
- Notion page comments import
- Notion page history
- Incremental/delta import (full import only)

## Technical Constraints

- Follow Obsidian import wizard pattern (scanner → mapping UI → preview → execute)
- htmx UI with SSE progress
- Batch EventStore for bulk creation
- Two-pass import (objects first, relations second)

## Integration Points

- **Obsidian importer** — architectural pattern to follow
- **Command API** — object.create, body.set, edge.create
- **EventStore** — bulk mode for large imports
- **ShapesService** — property mapping suggestions based on SHACL shapes
- **LabelService** — label resolution for mapped objects
