# M039: RDF Data Import & API Documentation Cleanup

**Vision:** Users can paste or upload RDF data (JSON-LD, Turtle, N-Triples) and import it as event-sourced objects with SHACL validation preview. Developers can browse all API endpoints organized by functional group in Redoc.

## Success Criteria

- User pastes valid JSON-LD with 5 typed objects into the import UI, sees all 5 subjects in a preview table with detected types, property counts, and SHACL status
- User sees SHACL warnings in preview (e.g., missing required property), imports anyway, objects appear in the workspace object browser with correct types
- User pastes malformed Turtle, sees a clear parse error — not a 500 or a blank screen
- User uploads a `.jsonld` file with cross-referencing objects, imported objects retain their original IRIs and cross-references resolve
- `/redoc` shows zero routes under "default" — every endpoint is under a descriptive tag

## Key Risks / Unknowns

- **Subject grouping accuracy** — Some RDF data uses blank nodes for structured values (schema:PostalAddress, etc.) or reified statements. Naive "group all triples by subject" produces too many subjects. Top-level subject detection needs a heuristic.
- **Blank node skolemization** — Blank nodes referenced by multiple triples must map to the same URI across all occurrences (subject and object positions). Internal consistency is critical.
- **Format detection from pasted text** — rdflib can't auto-detect JSON-LD or N-Triples from string content. The heuristic must be reliable enough that users rarely need the manual override.

## Proof Strategy

- Subject grouping and blank node skolemization → retire in S02 by building the real parser and testing with JSON-LD containing nested blank nodes and Turtle with `_:label` references
- Format detection → retire in S02 by implementing the heuristic and verifying all three formats parse correctly through the UI

## Verification Classes

- Contract verification: pytest unit tests for parser, format detection, blank node skolemization, subject extraction, SHACL preview; grep verification for Redoc tags
- Integration verification: full import round-trip via the UI — paste RDF, preview, import, verify objects appear in workspace with correct types and properties
- Operational verification: none (single-request import, no long-running services)
- UAT / human verification: visual check that Redoc tag groupings are clear; import UI follows existing wizard patterns

## Milestone Definition of Done

This milestone is complete only when all are true:

- All 10 routers have `tags=` on their `APIRouter()` constructor, `/redoc` shows zero "default" routes
- RDF import wizard is accessible from the workspace sidebar and command palette
- Pasting valid JSON-LD, Turtle, or N-Triples into the import UI shows parsed subjects with types, property counts, and SHACL validation status
- Importing creates event-sourced objects in `urn:sempkm:current` with full provenance
- Imported objects appear in the workspace object browser, are searchable via FTS, and render SHACL forms
- Parse errors (malformed input, unknown format) display clear user-visible error messages
- Blank nodes are skolemized to `urn:sempkm:import:{uuid}` URIs consistently
- Final acceptance scenarios from M039-CONTEXT.md pass against the running Docker stack

## Requirement Coverage

- Covers: IMPORT-01 (RDF paste/upload UI), IMPORT-02 (parse + format detection), IMPORT-03 (SHACL validation preview), IMPORT-04 (event-sourced object creation), IMPORT-05 (blank node skolemization), IMPORT-06 (IRI collision detection), IMPORT-07 (SSE progress events), API-09 (Redoc tag cleanup)
- Partially covers: none
- Leaves for later: none
- Orphan risks: none — all new requirements are fully mapped

## Slices

- [x] **S01: Redoc API Tag Cleanup** `risk:low` `depends:[]`
  > After this: opening `/redoc` shows all 85 routes organized under descriptive tags (commands, sparql, validation, health, admin, inference, lint, app-management, app-proxy, shell) with zero routes under "default"
- [x] **S02: RDF Data Import Wizard** `risk:medium` `depends:[]`
  > After this: user can paste JSON-LD/Turtle/N-Triples or upload a file, see parsed subjects with types and SHACL validation preview, selectively import as event-sourced objects, and find them in the workspace object browser — accessible from sidebar and command palette

## Boundary Map

### S01

Produces:
- `tags=["..."]` parameter on 10 `APIRouter()` constructors — purely OpenAPI metadata, zero behavior change

Consumes:
- nothing (standalone)

### S02

Produces:
- `backend/app/rdf_import/` module: router (prefix `/browser/rdf-import`), parser (rdflib format detection + subject extraction + blank node skolemization), executor (EventStore integration with SSE progress), models (dataclasses for parse/import results)
- Templates at `backend/app/templates/rdf_import/` for the multi-step wizard UI
- Sidebar entry and command palette entry for "Import RDF Data"
- `openRdfImportTab()` function in workspace.js for dockview panel integration

Consumes:
- nothing from S01 (independent)
- Existing infrastructure: EventStore, ValidationService, ShapesService, LabelService, SSE broadcast pattern, import.css
