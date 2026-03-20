# M027: Notion Import Wizard

**Vision:** Users can upload a Notion workspace ZIP export and import their databases, pages, properties, and relations into SemPKM as typed objects with edges — mirroring the proven Obsidian import wizard pattern.

## Success Criteria

- User uploads a Notion ZIP export and sees scan results: database count, page count, detected property types, relation targets
- User maps Notion databases to Mental Model types and Notion properties to RDF predicates
- User sees a preview of mapped objects before committing the import
- Import creates objects with bodies, properties, and typed edges from Notion relations
- A 500+ page Notion export completes without timeout or memory issues
- Entry point accessible from Admin > Import > Notion and workspace command palette

## Key Risks / Unknowns

- **CSV parsing correctness** — Notion's ZIP export format is not officially documented. CSV files may have UTF-8 BOM, locale-dependent date formats, and inconsistent quoting. Must be proven against realistic fixture data.
- **Relation resolution by title matching** — Notion CSV exports store relations as page title strings, not IDs. Duplicate titles in a target database create ambiguity. Two-pass import (objects first, relations second) adds a title→IRI lookup phase that must be tested.
- **Notion ID stripping** — Every filename/folder has a 32-hex-char Notion ID appended. Regex must match exactly 32 chars to avoid stripping user-chosen hex sequences in filenames.

## Proof Strategy

- CSV parsing + relation detection → retire in S01 by building the real scanner with unit tests against synthetic fixture data and showing scan results in the UI
- Two-pass import + title-based relation resolution → retire in S03 by executing a real import with cross-database relations and verifying edges exist in the triplestore

## Verification Classes

- Contract verification: pytest unit tests for scanner (CSV parsing, ID stripping, column type inference, relation detection), mapping logic, executor passes
- Integration verification: full wizard flow against Docker test stack — upload ZIP, scan, map, preview, execute, verify objects and edges via SPARQL
- Operational verification: SSE progress events during scan and import, error reporting per page/database
- UAT / human verification: none required — E2E Playwright test exercises the full wizard flow

## Milestone Definition of Done

This milestone is complete only when all are true:

- Scanner correctly parses Notion CSV databases, strips IDs, infers column types, and detects cross-DB relations
- Upload + scan results UI shows databases with column summaries, standalone pages, and detected relations
- Type mapping, property mapping, and relation mapping steps all work with auto-suggestions
- Preview shows sample mapped objects with properties and edges before committing
- Two-pass executor creates objects (Pass 1) and resolves relations as edges (Pass 2) with SSE progress
- Import of a 500+ row fixture export completes without timeout
- Unresolvable relations (duplicate titles, missing targets) are reported clearly in import summary
- E2E Playwright test exercises the full wizard flow
- User guide chapter documents the Notion import workflow
- Entry point exists in Admin > Import and command palette

## Requirement Coverage

- Covers: NOTION-01 (ZIP import — S01+S03), NOTION-02 (database→type mapping — S02), NOTION-03 (relation→edge resolution — S02+S03)
- Partially covers: none
- Leaves for later: Notion API integration (explicitly out of scope per CONTEXT), DashboardSpec preservation, rollup/formula re-computation, comments import, incremental import
- Orphan risks: NOTION-01 is currently deferred in REQUIREMENTS.md — this milestone activates and validates it

## Slices

- [ ] **S01: Notion ZIP Scanner + Upload UI** `risk:high` `depends:[]`
  > After this: user uploads a Notion workspace ZIP via Admin > Import > Notion, sees scan results showing detected databases with column summaries, standalone pages, and cross-database relation candidates
- [ ] **S02: Type, Property & Relation Mapping + Preview** `risk:medium` `depends:[S01]`
  > After this: user maps databases to Mental Model types, maps CSV columns to RDF predicates, configures relation columns as typed edges, and sees a preview of sample mapped objects with properties and edges before committing
- [ ] **S03: Two-Pass Import Executor + Full Flow** `risk:medium` `depends:[S01,S02]`
  > After this: user clicks Import and objects are created from CSV rows + standalone pages (Pass 1), relations resolved as edges by title matching (Pass 2), with SSE progress throughout and an import summary showing stats and any unresolvable relations
- [ ] **S04: E2E Tests + User Guide** `risk:low` `depends:[S01,S02,S03]`
  > After this: Playwright E2E test exercises the full wizard flow against Docker test stack with a fixture Notion export, and user guide chapter documents the complete Notion import workflow

## Boundary Map

### S01 → S02

Produces:
- `backend/app/notion/scanner.py` — `NotionScanner` class with `scan(zip_path)` returning `NotionScanResult` dataclass (databases with columns/types/row counts, standalone pages, detected relations)
- `backend/app/notion/models.py` — `NotionScanResult`, `NotionDatabase`, `NotionColumn`, `NotionPage`, `DetectedRelation` dataclasses with `to_dict()`/`from_dict()` serialization
- `backend/app/notion/router.py` — Upload endpoint (`POST /browser/notion/upload`), scan trigger (`POST /browser/notion/scan`), scan results endpoint (`GET /browser/notion/scan-results`)
- `backend/app/notion/broadcast.py` — SSE broadcast helper (copied/adapted from Obsidian)
- `backend/app/templates/notion/` — Upload page, scan results partial showing databases/pages/relations
- Scan result stored in session/temp for downstream mapping steps

Consumes:
- nothing (first slice)

### S02 → S03

Produces:
- `backend/app/notion/models.py` — Extended with `MappingConfig`, `TypeMapping`, `PropertyMapping`, `RelationMapping` dataclasses
- `backend/app/notion/router.py` — Type mapping POST, property mapping POST, relation mapping POST, preview endpoint
- `backend/app/templates/notion/` — Type mapping, property mapping, relation mapping, and preview partials
- Stored `MappingConfig` ready for executor consumption

Consumes:
- `NotionScanResult` from S01 (databases, columns, relations)
- ShapesService for auto-suggest (existing platform service)

### S03 → S04

Produces:
- `backend/app/notion/executor.py` — `NotionImportExecutor` with two-pass import (objects + relations), SSE progress, error-per-page reporting
- `backend/app/notion/router.py` — Execute endpoint (`POST /browser/notion/execute`), import status endpoint
- Complete working wizard flow from upload through import
- Command palette entry "Import > Notion"

Consumes:
- `MappingConfig` from S02
- `NotionScanResult` from S01
- Command API (object.create, body.set, edge.create) — existing platform
- EventStore bulk mode — existing platform

### S04 (terminal)

Produces:
- `e2e/tests/XX-notion-import/notion-import.spec.ts` — Full wizard E2E test
- `e2e/fixtures/notion-export/` — Synthetic Notion export ZIP fixture
- `docs/guide/39-notion-import.md` — User guide chapter
- README TOC, index.html sidebar, guide.html in-app page updates

Consumes:
- Complete wizard flow from S01+S02+S03
- Docker test stack
