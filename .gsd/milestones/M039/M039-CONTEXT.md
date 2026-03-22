---
depends_on: [M033]
---

# M039: RDF Data Import & API Documentation Cleanup

**Gathered:** 2026-03-22
**Status:** Queued — pending auto-mode execution

## Project Description

Two complementary improvements to platform usability: (1) a workspace UI for importing structured RDF data (JSON-LD, Turtle, N-Triples) with SHACL validation preview and event-sourced object creation, and (2) a cleanup pass on the OpenAPI/Redoc documentation to properly categorize 84 routes currently grouped under "default."

## Why This Milestone

**RDF import gap.** SemPKM has import wizards for Obsidian vaults (Markdown + frontmatter) and Notion exports (CSV + Markdown), but no way to load native RDF data — the format the system is built on. Users with existing JSON-LD datasets, Turtle files from external tools, or RDF exports from other systems have no import path. They must either create objects one-by-one through the UI or write custom scripts against the Command API. A direct RDF import with SHACL validation preview closes this gap.

**Redoc is unusable.** The API documentation at `/redoc` (and `/docs` for Swagger UI) has 84 routes under the "default" tag — commands, SPARQL, validation, health, admin, inference, lint, app management, and shell routes all lumped together. Developers looking for a specific endpoint must scroll through an undifferentiated list. Adding `tags=` to 10 routers is a mechanical fix with outsized developer experience impact.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Open Import > RDF Data from the workspace sidebar or command palette
- Paste JSON-LD or Turtle content into a text area, or upload a .jsonld/.ttl/.nt file
- See parse results: format detected, triple count, subject count, any parse errors
- See SHACL validation preview: which subjects would have violations or warnings if imported
- See an object preview table: each detected subject with its rdf:type, label (if present), and property count
- Choose to import all subjects or deselect specific ones
- See objects created as event-sourced entities in `urn:sempkm:current` with full provenance
- See SSE progress for large imports
- Browse `/redoc` and find every endpoint organized under a descriptive tag (commands, sparql, validation, health, admin, inference, lint, app-management)

### Entry point / environment

- Entry point: `http://localhost:3000/browser/import/rdf` (workspace), Ctrl+K "Import RDF Data"
- Environment: Docker Compose (api + triplestore + frontend/nginx)
- Live dependencies involved: RDF4J triplestore, SHACL shapes from installed Mental Models

## Completion Class

- Contract complete means: rdflib parses all 3 formats, SHACL validation runs against parsed data, EventStore creates objects from parsed subjects, all 10 routers have tags
- Integration complete means: imported objects appear in object browser with correct types, are searchable via FTS, SHACL forms render, edges between imported objects resolve
- Operational complete means: 500+ triple import completes without timeout, parse errors don't crash the import, Redoc shows clean tag groupings

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- User pastes valid JSON-LD with 5 typed objects into the import UI, sees 5 subjects in preview with their types and property counts
- User sees SHACL warnings in preview (e.g., missing title on an object), decides to import anyway
- After import, all 5 objects appear in the object browser with correct types and properties
- User pastes malformed Turtle, sees a clear parse error message (not a 500)
- User uploads a .jsonld file with objects referencing each other via edges — edges resolve correctly post-import
- `/redoc` shows zero routes under "default" — all organized under descriptive tags

## Risks and Unknowns

- **Type detection from imported RDF** — Imported subjects may use `rdf:type` values that don't match any installed Mental Model type. Import with warning is safest — the data is valid RDF regardless of model state.
- **IRI collision** — Imported subjects may have IRIs that already exist in `urn:sempkm:current`. Skip duplicates with warning for v1.
- **Blank node handling** — JSON-LD and Turtle can contain blank nodes. These need to be skolemized (converted to URIs like `urn:sempkm:import:{uuid}`) before EventStore ingestion, since blank node identity doesn't persist across SPARQL operations.
- **Large file performance** — A 10,000-triple Turtle file needs rdflib parsing (fast), SHACL validation (potentially slow), and EventStore commits (batched). May need to skip SHACL preview for files above a threshold and validate post-import instead.
- **Edge creation ordering** — If imported data contains edges between imported subjects, objects must exist before edges can reference them. The two-pass pattern from Obsidian/Notion importers (Pass 1: objects, Pass 2: edges) handles this.

## Existing Codebase / Prior Art

- `backend/app/obsidian/executor.py` — Obsidian import executor using handle_object_create, handle_body_set, handle_edge_create + EventStore. Two-pass pattern (objects then edges). Reference implementation for event-sourced import. Verified on main.
- `backend/app/notion/executor.py` — Notion import executor with similar two-pass pattern and SSE progress broadcasting. Verified on main.
- `backend/app/services/validation.py` — ValidationService.validate() with pyshacl advanced=True. Loads shapes via model_shapes_loader. Can validate a parsed rdflib Graph against shapes without committing. Verified on main.
- `backend/app/triplestore/client.py` — TriplestoreClient with insert_graph() for Turtle data via Graph Store protocol. Verified on main.
- `backend/app/events/store.py` — EventStore.commit() and commit_bulk() for event-sourced writes. Verified on main.
- `backend/app/commands/handlers/object_create.py` — handle_object_create() with _resolve_predicate() for property type inference. Verified on main.
- `backend/app/services/shapes.py` — ShapesService.get_form_for_type() and get_types() for type detection and validation context. Verified on main.
- `backend/app/rdf/jsonld.py` — Existing JSON-LD utilities. Verified on main.
- `backend/app/obsidian/broadcast.py` — SSE broadcast helper for import progress events. Reusable pattern. Verified on main.
- 10 router files without tags: `commands/router.py` (2 routes), `sparql/router.py` (18), `validation/router.py` (2), `health/router.py` (1), `admin/router.py` (21), `inference/router.py` (6), `lint/router.py` (17), `apps/admin_router.py` (11), `apps/router.py` (1), `shell/router.py` (5). All verified on main.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions.

## Relevant Requirements

- New requirements to be created: IMPORT-01 (RDF paste/upload UI), IMPORT-02 (parse + format detection), IMPORT-03 (SHACL validation preview), IMPORT-04 (event-sourced object creation), API-09 (Redoc tag cleanup)

## Scope

### In Scope

**RDF Import Wizard:**
- Workspace page at `/browser/import/rdf` with paste area and file upload
- Format detection: JSON-LD, Turtle, N-Triples (rdflib auto-detect with manual override)
- rdflib parsing with error capture (SyntaxError, ParserError to user-visible messages)
- Subject extraction: group parsed triples by subject, detect rdf:type, resolve labels
- SHACL validation preview: run pyshacl against parsed data using installed model shapes, show warnings/violations per subject before committing
- Object preview table: subject IRI, detected type (label), property count, SHACL status
- Selective import: checkboxes per subject, deselect to skip
- Two-pass event-sourced import: Pass 1 creates objects via EventStore, Pass 2 creates edges between imported subjects
- SSE progress events during import (reuse broadcast pattern)
- Blank node skolemization to `urn:sempkm:import:{uuid}` URIs
- IRI collision detection: warn if subject IRI already exists, skip by default
- Sidebar entry and command palette entry

**Redoc Tag Cleanup:**
- Add `tags=["commands"]` to `commands/router.py` (2 routes)
- Add `tags=["sparql"]` to `sparql/router.py` (18 routes)
- Add `tags=["validation"]` to `validation/router.py` (2 routes)
- Add `tags=["health"]` to `health/router.py` (1 route)
- Add `tags=["admin"]` to `admin/router.py` (21 routes)
- Add `tags=["inference"]` to `inference/router.py` (6 routes)
- Add `tags=["lint"]` to `lint/router.py` (17 routes)
- Add `tags=["app-management"]` to `apps/admin_router.py` (11 routes)
- Add `tags=["app-proxy"]` to `apps/router.py` (1 route)
- Add `tags=["shell"]` to `shell/router.py` (5 routes)
- Zero behavior change — purely OpenAPI metadata

### Out of Scope / Non-Goals

- SPARQL UPDATE import (INSERT DATA via API — bypasses event sourcing by design)
- Raw named graph insertion (for ontologies/reference data — different use case)
- RDF export from SemPKM
- Import from remote URL (fetch + parse — follow-up)
- Automated type mapping (RDF data already has types)
- OpenAPI description text improvements beyond tag assignment

## Technical Constraints

- rdflib for parsing (already a dependency)
- pyshacl for SHACL validation preview (already a dependency)
- EventStore for object creation (existing pattern)
- Frontend: htmx + vanilla JS (follows existing import wizard patterns)
- SSE for progress broadcasting (existing broadcast.py pattern)
- Imported data must go through EventStore — no direct SPARQL INSERT to urn:sempkm:current
- Tag additions must not change any route paths, methods, or behavior

## Integration Points

- **EventStore** — commit() / commit_bulk() for object creation from parsed RDF subjects
- **ValidationService / pyshacl** — SHACL validation of parsed data against installed model shapes
- **ShapesService** — type detection and property shape matching for preview enrichment
- **LabelService** — label resolution for preview table
- **Object browser** — imported objects appear immediately after commit
- **FTS / LuceneSail** — imported literal values indexed for search
- **Existing importers** — follow Obsidian/Notion patterns (broadcast, two-pass, EventStore)
- **OpenAPI / FastAPI** — tags parameter on APIRouter for Redoc organization

## Open Questions

- **Import granularity** — Should each subject become a separate EventStore.commit() call (fine-grained provenance, N events) or use commit_bulk() (one summary event, faster)? Bulk is better for imports of 10+ subjects. Could auto-select based on count.
- **Property type inference** — rdflib provides typed literals (xsd:date, xsd:integer, etc.) but the EventStore command handlers expect specific property formats. The _resolve_predicate() helper handles some of this. May need adaptation for the full range of XSD types.
- **Unknown type handling** — When imported RDF uses a type IRI not in any installed model: show a warning icon and import anyway (simplest and most correct).
