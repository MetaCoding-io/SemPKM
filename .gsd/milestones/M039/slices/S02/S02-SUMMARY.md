---
id: S02
parent: M039
milestone: M039
provides:
  - RDF import parser with format detection (JSON-LD, Turtle, N-Triples), subject extraction, blank node skolemization
  - SHACL validation preview grouped by focus node
  - IRI collision detection against urn:sempkm:current
  - Import executor with per-subject and bulk commit strategies + SSE progress
  - FastAPI router at /browser/rdf-import with 5 endpoints
  - 3-step import wizard UI (input → preview → import) with 6 templates
  - Sidebar entry, command palette entry, dockview tab opener
  - 29 unit tests for parser functions
requires: []
affects: []
key_files:
  - backend/app/rdf_import/__init__.py
  - backend/app/rdf_import/models.py
  - backend/app/rdf_import/parser.py
  - backend/app/rdf_import/executor.py
  - backend/app/rdf_import/router.py
  - backend/app/main.py
  - backend/app/templates/rdf_import/import.html
  - backend/app/templates/rdf_import/partials/input_form.html
  - backend/app/templates/rdf_import/partials/preview.html
  - backend/app/templates/rdf_import/partials/progress.html
  - backend/app/templates/rdf_import/partials/summary.html
  - backend/app/templates/rdf_import/partials/error.html
  - backend/app/templates/components/_sidebar.html
  - frontend/static/js/workspace.js
  - backend/tests/test_rdf_import_parser.py
key_decisions: []
patterns_established:
  - SubjectInfo/RdfParseResult/RdfImportResult dataclass trio follows Obsidian ImportResult pattern
  - Executor builds Operation dataclasses directly from rdflib terms — preserves datatypes and language tags
  - Module-level caches keyed by str(user.id) for cross-request wizard state
  - SHACL + collision detection run in parallel via asyncio.gather during parse
  - Reuses shared import.css classes from obsidian importer (step-bar, stat-cards, progress)
observability_surfaces:
  - SSE events at /browser/rdf-import/execute/stream (import_progress, import_complete, import_error)
  - Loggers rdf_import.parser and rdf_import.executor
  - Import summary stat cards (created/skipped/errors/duration)
  - Parse error notices in wizard UI
drill_down_paths:
  - .gsd/milestones/M039/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M039/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M039/slices/S02/tasks/T03-SUMMARY.md
duration: 39min
verification_result: passed
completed_at: 2026-03-22
---

# S02: RDF Data Import Wizard

**Users can paste or upload RDF data (JSON-LD, Turtle, N-Triples), preview parsed subjects with SHACL validation status, and import them as event-sourced objects visible in the workspace.**

## What Happened

Three tasks built the full vertical slice bottom-up:

**T01 (parser):** Created `backend/app/rdf_import/` with format detection (three-tier: override → file extension → content heuristic), rdflib parsing with error capture, subject extraction with label precedence and top-level heuristic, and blank node skolemization to `urn:sempkm:import:{uuid}` URIs. 29 unit tests cover all parser functions.

**T02 (executor + router):** Built SHACL validation preview (pyshacl against installed model shapes, grouped by focus node), IRI collision detection (batch SPARQL ASK against `urn:sempkm:current`), and import executor that constructs Operation dataclasses directly from parsed triples. Per-subject commit for ≤10 subjects, bulk commit in chunks of 500 for larger imports. SSE progress broadcasting throughout. Five FastAPI endpoints registered at `/browser/rdf-import`.

**T03 (templates + workspace integration):** Six Jinja2 templates implement the 3-step wizard UI: input form with paste/upload/format-override, preview table with SHACL status icons and collision warnings, SSE-driven progress bar with log, and summary stat cards. Added sidebar entry ("Import RDF"), command palette entry ("Import > RDF Data"), and `openRdfImportTab()` dockview integration. Reuses shared `import.css` classes from the obsidian importer.

## Verification

- 29/29 parser unit tests pass
- Router registered in main.py (lines 34, 658)
- `openRdfImportTab` and `import-rdf` present in workspace.js
- Sidebar entry present in `_sidebar.html`
- All 6 template files exist
- Zero `/static/css/` paths in templates (correct nginx paths used)

## Requirements Advanced

- IMPORT-01 — RDF paste/upload UI complete
- IMPORT-02 — parse + format detection implemented and tested
- IMPORT-03 — SHACL validation preview with per-subject status
- IMPORT-04 — event-sourced object creation via Operation/EventStore
- IMPORT-05 — blank node skolemization to urn:sempkm:import:{uuid}
- IMPORT-06 — IRI collision detection with skip-duplicate default
- IMPORT-07 — SSE progress events during import

## Requirements Validated

- none (end-to-end round-trip requires running Docker stack — deferred to milestone validation)

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- Created `error.html` partial not in the original plan — required by the router's error handling paths.
- Used `request.app.state.*` direct access instead of `Depends()` wrappers for DI, matching the obsidian router pattern.
- Added `_import_results` cache for the summary endpoint to access results after background task completion.

## Known Limitations

- Module-level caches (`_parse_cache`, `_import_results`, `_broadcasts`) are not cleaned up on session expiry — fine for single-worker Docker, would need Redis for multi-worker.
- End-to-end round-trip (paste → preview → import → browse objects) not yet verified against running Docker stack.

## Follow-ups

- Milestone validation should verify the full round-trip with a running Docker stack.

## Files Created/Modified

- `backend/app/rdf_import/__init__.py` — module init
- `backend/app/rdf_import/models.py` — SubjectInfo, RdfParseResult, RdfImportResult dataclasses
- `backend/app/rdf_import/parser.py` — detect_format, parse_rdf, extract_subjects, skolemize_bnodes
- `backend/app/rdf_import/executor.py` — SHACL validation, collision detection, import execution
- `backend/app/rdf_import/router.py` — FastAPI router with 5 endpoints
- `backend/app/main.py` — registered rdf_import_router
- `backend/app/templates/rdf_import/import.html` — main wizard page
- `backend/app/templates/rdf_import/partials/input_form.html` — paste/upload form
- `backend/app/templates/rdf_import/partials/preview.html` — subject preview with SHACL status
- `backend/app/templates/rdf_import/partials/progress.html` — SSE progress bar
- `backend/app/templates/rdf_import/partials/summary.html` — import result stat cards
- `backend/app/templates/rdf_import/partials/error.html` — error notice
- `backend/app/templates/components/_sidebar.html` — added "Import RDF" sidebar entry
- `frontend/static/js/workspace.js` — added openRdfImportTab() and command palette entry
- `backend/tests/test_rdf_import_parser.py` — 29 unit tests

## Forward Intelligence

### What the next slice should know
- No next slice — S02 is the final slice of M039.

### What's fragile
- Module-level _parse_cache is keyed by user ID string — if user model changes, cache keys break silently.

### Authoritative diagnostics
- `cd backend && .venv/bin/python -m pytest tests/test_rdf_import_parser.py -v` — parser health
- SSE stream at `/browser/rdf-import/execute/stream` — live import progress
- Logger `rdf_import.executor` — import stats and errors

### What assumptions changed
- None
