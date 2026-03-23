# S02: RDF Data Import Wizard

**Goal:** Users can paste or upload RDF data (JSON-LD, Turtle, N-Triples), preview parsed subjects with SHACL validation status, and import them as event-sourced objects visible in the workspace.
**Demo:** Paste JSON-LD with 5 typed objects → preview table shows 5 subjects with types, property counts, and SHACL status → import → objects appear in workspace object browser with correct types and properties.

## Must-Haves

- Format detection heuristic reliably identifies JSON-LD, Turtle, and N-Triples from pasted text
- rdflib parsing with clear error messages for malformed input
- Subject extraction groups triples by subject with type, label, and property count
- Blank node skolemization to `urn:sempkm:import:{uuid}` with consistent mapping across subject and object positions
- SHACL validation preview against installed model shapes before import
- IRI collision detection with skip-duplicate default
- Direct Operation construction preserving original IRIs, datatypes, and language tags
- SSE progress events during import execution
- EventStore integration with per-subject commit (≤10 subjects) or bulk commit (>10)
- 3-step wizard UI: Input → Preview → Import, reusing `import.css` patterns
- Sidebar "Import RDF" entry and command palette "Import > RDF Data" entry
- Dockview tab integration via `openRdfImportTab()` using `special-panel` component
- Router at `/browser/rdf-import` prefix (NOT `/browser/import/rdf` — avoids collision with obsidian `/{import_id}` routes)

## Proof Level

- This slice proves: integration (parsed RDF → SHACL preview → EventStore commit → triplestore materialization → workspace visibility)
- Real runtime required: yes (triplestore + EventStore + pyshacl)
- Human/UAT required: yes (visual check of wizard flow and imported objects)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_rdf_import_parser.py -v` — unit tests for format detection, parsing, subject extraction, skolemization
- Manual: paste valid JSON-LD in import wizard → preview shows subjects → import → objects visible in workspace
- Manual: paste malformed Turtle → clear error message (not 500 or blank)
- `grep -n "rdf_import_router" backend/app/main.py` returns a match (router registered)
- `grep -n "import-rdf\|Import RDF\|Import.*RDF" frontend/static/js/workspace.js` returns matches (command palette + tab function)
- `grep -n "rdf-import\|Import RDF" backend/app/templates/components/_sidebar.html` returns a match (sidebar entry)

## Observability / Diagnostics

- Runtime signals: SSE events (`import_progress`, `import_complete`, `import_error`) broadcast during import execution; structured logging in parser and executor with subject counts, error details
- Inspection surfaces: SSE stream endpoint at `/browser/rdf-import/execute/stream`; import summary page with stat cards (created/skipped/errors/duration)
- Failure visibility: parse errors surface as user-visible messages in the UI; SHACL validation results shown per-subject in preview; import errors logged and displayed in summary
- Redaction constraints: none (RDF data is not secret)

## Integration Closure

- Upstream surfaces consumed: `app.events.store.EventStore` + `Operation` for commits; `app.obsidian.broadcast.ScanBroadcast` + `SSEEvent` + `stream_sse` for SSE; `app.validation.report.ValidationReport.from_pyshacl()` for SHACL parsing; `app.services.models.model_shapes_loader()` for installed shapes; `import.css` for shared styling
- New wiring introduced in this slice: `rdf_import_router` registered in `main.py`; sidebar entry in `_sidebar.html`; command palette entry + `openRdfImportTab()` in `workspace.js`
- What remains before the milestone is truly usable end-to-end: nothing — S01 (Redoc tags) is already done, S02 completes the milestone

## Tasks

- [x] **T01: Build RDF parser module with format detection, subject extraction, and unit tests** `est:2h`
  - Why: Core novel code — format detection heuristic, rdflib parsing, subject grouping, blank node skolemization. This is where all 3 key risks (P1-P3) live. Unit tests retire the risks immediately.
  - Files: `backend/app/rdf_import/__init__.py`, `backend/app/rdf_import/parser.py`, `backend/app/rdf_import/models.py`, `backend/tests/test_rdf_import_parser.py`
  - Do: Implement `detect_format()` heuristic (JSON-LD via `{`/`[`, Turtle via `@prefix`/`@base`, N-Triples via `<...> <...>` pattern, file extension via `rdflib.util.guess_format`). Implement `parse_rdf()` that calls `Graph.parse(data=..., format=detected)` with error capture. Implement `extract_subjects()` that groups triples by subject, extracts rdf:type, resolves labels via precedence chain, counts properties, and applies top-level subject heuristic. Implement `skolemize_bnodes()` that builds `BNode→URIRef` mapping in single pass, applying to both subject and object positions. Write dataclasses in models.py (`SubjectInfo`, `RdfParseResult`). Write pytest unit tests covering: format detection for all 3 formats + edge cases, parsing valid/invalid input, subject extraction with types/labels/counts, top-level subject heuristic, blank node skolemization consistency.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_rdf_import_parser.py -v` — all tests pass
  - Done when: Parser handles all 3 formats, skolemization is consistent, subject extraction is correct, and unit tests prove it

- [ ] **T02: Build executor, router endpoints, and SHACL validation preview** `est:2h`
  - Why: The API layer that connects the parser to the triplestore. Handles SHACL validation preview, IRI collision detection, EventStore commit with SSE progress, and all HTTP endpoints.
  - Files: `backend/app/rdf_import/executor.py`, `backend/app/rdf_import/router.py`, `backend/app/main.py`
  - Do: Build `RdfImportExecutor` class with: `validate_shacl()` using pyshacl against `model_shapes_loader()` shapes, grouping results by focus node; `check_collisions()` with batch ASK query against `urn:sempkm:current`; `execute_import()` that builds `Operation` dataclasses directly from parsed triples (NOT through `handle_object_create`), commits via `EventStore.commit()` for ≤10 subjects or `EventStore.commit_bulk()` for larger batches, broadcasts SSE progress events. Build router with prefix `/browser/rdf-import`, tag `rdf-import`, endpoints: GET `/` (main page), POST `/parse` (parse pasted/uploaded RDF, return preview), POST `/execute` (trigger import), GET `/execute/stream` (SSE), GET `/summary` (post-import summary). Store parse results in module-level dict keyed by session/user. Register router in `main.py` after the notion router.
  - Verify: `cd backend && .venv/bin/python -m pytest tests/test_rdf_import_parser.py -v` still passes; `grep -n "rdf_import_router" backend/app/main.py` returns a match; `python -c "from app.rdf_import.router import router; print(router.prefix)"` outputs `/browser/rdf-import`
  - Done when: All router endpoints exist, SHACL preview works, executor builds Operations correctly, router is registered in main.py

- [ ] **T03: Build import wizard templates, sidebar entry, command palette, and dockview tab** `est:1.5h`
  - Why: The user-facing layer — without this, the backend works but nobody can reach it. Completes the end-to-end feature.
  - Files: `backend/app/templates/rdf_import/import.html`, `backend/app/templates/rdf_import/partials/input_form.html`, `backend/app/templates/rdf_import/partials/preview.html`, `backend/app/templates/rdf_import/partials/progress.html`, `backend/app/templates/rdf_import/partials/summary.html`, `backend/app/templates/components/_sidebar.html`, `frontend/static/js/workspace.js`
  - Do: Create `import.html` extending `base.html` with `<link rel="stylesheet" href="/css/import.css">` (NOT `/static/css/`), 3-step bar (Input/Preview/Import), `#import-container` wrapper. Create `input_form.html` with paste textarea, file upload zone, format override `<select>`, and htmx POST to `/browser/rdf-import/parse`. Create `preview.html` with subject table (checkbox, IRI, type, label, property count, SHACL status), import button that POSTs to `/browser/rdf-import/execute`. Create `progress.html` with EventSource connecting to `/browser/rdf-import/execute/stream`, progress bar, log div. Create `summary.html` with stat cards (created/skipped/errors/duration) and "Browse Objects" action button. Add sidebar entry after "Import Notion" with `file-code-2` Lucide icon, href `/browser/rdf-import`. Add `openRdfImportTab()` function in workspace.js (follows `openImportTab()` pattern with `specialType: 'rdf-import'`). Add command palette entry `{id: 'import-rdf', title: 'Import > RDF Data', ...}` after the import-notion entry.
  - Verify: `grep -n "rdf-import" backend/app/templates/components/_sidebar.html` returns a match; `grep -n "openRdfImportTab\|import-rdf" frontend/static/js/workspace.js` returns matches; `test -f backend/app/templates/rdf_import/import.html && test -f backend/app/templates/rdf_import/partials/input_form.html && test -f backend/app/templates/rdf_import/partials/preview.html && echo "OK"`
  - Done when: All templates exist, sidebar shows "Import RDF", command palette has "Import > RDF Data", `openRdfImportTab()` opens a dockview tab that loads `/browser/rdf-import`

## Files Likely Touched

- `backend/app/rdf_import/__init__.py`
- `backend/app/rdf_import/parser.py`
- `backend/app/rdf_import/models.py`
- `backend/app/rdf_import/executor.py`
- `backend/app/rdf_import/router.py`
- `backend/app/main.py`
- `backend/app/templates/rdf_import/import.html`
- `backend/app/templates/rdf_import/partials/input_form.html`
- `backend/app/templates/rdf_import/partials/preview.html`
- `backend/app/templates/rdf_import/partials/progress.html`
- `backend/app/templates/rdf_import/partials/summary.html`
- `backend/app/templates/components/_sidebar.html`
- `frontend/static/js/workspace.js`
- `backend/tests/test_rdf_import_parser.py`
