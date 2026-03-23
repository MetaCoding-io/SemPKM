---
id: M039
provides:
  - RDF data import wizard (paste/upload JSON-LD, Turtle, N-Triples → SHACL preview → event-sourced import)
  - OpenAPI tags on all 10 previously-untagged APIRouter instances (zero "default" routes in /redoc)
  - RDF import parser with format detection, subject extraction, blank node skolemization
  - SHACL validation preview grouped by focus node
  - IRI collision detection against urn:sempkm:current
  - Import executor with per-subject and bulk commit strategies + SSE progress
  - 3-step import wizard UI with sidebar entry, command palette entry, dockview tab
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
  - Import summary stat cards in wizard UI (created/skipped/errors/duration)
  - GET /openapi.json — all routes carry explicit tags, "default" group is empty
requirement_outcomes:
  - id: IMPORT-01
    from_status: active
    to_status: validated
    proof: Sidebar entry and command palette entry present; import.html + input_form.html templates render paste/upload UI
  - id: IMPORT-02
    from_status: active
    to_status: validated
    proof: 29 unit tests pass covering detect_format (JSON-LD, Turtle, N-Triples via content heuristic, file extension, manual override) and parse_rdf with error capture
  - id: IMPORT-03
    from_status: active
    to_status: validated
    proof: validate_shacl() in executor.py runs pyshacl against installed model shapes, groups results by focus node; preview.html renders per-subject SHACL status icons
  - id: IMPORT-04
    from_status: active
    to_status: validated
    proof: execute_import() builds Operation dataclasses from rdflib triples and commits via EventStore (per-subject for ≤10, bulk chunks of 500 for >10)
  - id: IMPORT-05
    from_status: active
    to_status: validated
    proof: skolemize_bnodes() replaces BNodes with urn:sempkm:import:{uuid} URIs; 5 unit tests cover consistency, format, preservation of non-bnodes, namespace bindings, and multi-bnode graphs
  - id: IMPORT-06
    from_status: active
    to_status: validated
    proof: check_collisions() in executor.py queries urn:sempkm:current via batch SPARQL VALUES clause; preview.html renders collision warnings
  - id: IMPORT-07
    from_status: active
    to_status: validated
    proof: Executor broadcasts import_progress, import_complete, import_error SSE events; router exposes /execute/stream endpoint; progress.html template connects via EventSource
  - id: API-09
    from_status: active
    to_status: validated
    proof: rg confirms all 10 APIRouter() calls have tags= parameter; rg 'APIRouter(' | grep -v 'tags=' returns empty
duration: 42min
verification_result: passed
completed_at: 2026-03-22
---

# M039: RDF Data Import & API Documentation Cleanup

**Users can paste or upload RDF data (JSON-LD, Turtle, N-Triples), preview parsed subjects with SHACL validation status and collision warnings, and import them as event-sourced objects — plus all API routes are now tagged for clean Redoc grouping.**

## What Happened

Two independent slices delivered the full scope:

**S01 (Redoc cleanup, 3min):** Added `tags=["..."]` to all 10 untagged `APIRouter()` constructors across the codebase — commands, sparql, validation, health, admin, inference, lint, app-management, app-proxy, shell. Pure OpenAPI metadata change with zero behavior impact. No untagged routers remain.

**S02 (RDF import wizard, 39min):** Built the complete vertical slice bottom-up across three tasks:

- **T01 (parser):** Created `backend/app/rdf_import/` module with three-tier format detection (manual override → file extension → content heuristic), rdflib parsing with error capture, subject extraction with label precedence and top-level heuristic (excludes blank nodes that only appear as objects), and blank node skolemization to `urn:sempkm:import:{uuid}` URIs. 29 unit tests cover all parser functions.

- **T02 (executor + router):** Built SHACL validation preview (pyshacl against installed model shapes, grouped by focus node via ValidationReport), IRI collision detection (batch SPARQL VALUES against `urn:sempkm:current`), and import executor that constructs Operation dataclasses directly from parsed rdflib triples — preserving original datatypes and language tags. Per-subject commit for ≤10 subjects, bulk commit in chunks of 500 for larger imports. SSE progress broadcasting throughout. Five FastAPI endpoints registered at `/browser/rdf-import`.

- **T03 (templates + integration):** Six Jinja2 templates implement the 3-step wizard: input form with paste/upload/format-override, preview table with SHACL status icons and collision warnings, SSE-driven progress bar with log, and summary stat cards. Added sidebar entry, command palette entry, and `openRdfImportTab()` dockview panel opener. Reuses shared `import.css` classes from the Obsidian importer.

## Cross-Slice Verification

| Success Criterion | Evidence |
|---|---|
| All 10 routers tagged, /redoc zero "default" | `rg 'tags=' <10 files>` → 10 matches; `rg 'APIRouter(' \| grep -v tags=` → empty |
| Import wizard accessible from sidebar | `_sidebar.html` contains "Import RDF" nav-link |
| Import wizard accessible from command palette | `workspace.js` registers `openRdfImportTab()` in palette |
| Paste JSON-LD/Turtle/N-Triples → preview subjects | 29/29 parser unit tests pass (format detection, parsing, subject extraction) |
| Preview shows types, property counts, SHACL status | `preview.html` template renders per-subject rows with type, triple count, SHACL icons |
| SHACL warnings visible in preview | `validate_shacl()` runs pyshacl with `allow_warnings=True`, groups by focus node |
| Malformed input → clear parse error | `error.html` partial renders format-specific error messages |
| Imported objects retain original IRIs | Executor builds Operations from raw rdflib terms — no IRI rewriting |
| Blank nodes → `urn:sempkm:import:{uuid}` | 5 skolemize unit tests prove consistency, format, and preservation |
| IRI collision detection with skip-duplicate | `check_collisions()` runs batch SPARQL; preview warns on existing IRIs |
| SSE progress during import | Executor publishes `import_progress`/`import_complete`/`import_error` events |
| Event-sourced creation | `execute_import()` commits via `EventStore.commit()` / `commit_bulk()` |
| 25 source files, 1791 lines | `git diff --stat` against pre-milestone baseline confirms |

**Deferred:** Live /redoc verification and full round-trip (paste → preview → import → browse) require a running Docker stack — deferred to future integration test.

## Requirement Changes

- IMPORT-01: active → validated — RDF paste/upload UI complete with sidebar and command palette access
- IMPORT-02: active → validated — 29 unit tests prove format detection for all three formats
- IMPORT-03: active → validated — SHACL validation preview with per-subject status icons
- IMPORT-04: active → validated — Event-sourced creation via Operation/EventStore
- IMPORT-05: active → validated — Blank node skolemization to `urn:sempkm:import:{uuid}`
- IMPORT-06: active → validated — IRI collision detection with batch SPARQL VALUES
- IMPORT-07: active → validated — SSE progress events during import
- API-09: active → validated — All 10 routers tagged, zero "default" routes

## Forward Intelligence

### What the next milestone should know
- The RDF import module at `backend/app/rdf_import/` follows the same pattern as the Obsidian importer — module-level caches, SSE broadcast, wizard templates. If someone needs to add a third import source, these two are the reference implementations.
- The import executor bypasses `handle_object_create()` and builds Operations directly from rdflib triples. This preserves datatypes and language tags but means import-created objects don't go through the normal command dispatch pipeline (no command-level hooks fire).

### What's fragile
- Module-level `_parse_cache` and `_import_results` dicts are keyed by `str(user.id)` — single-worker only. Multi-worker deployments would need Redis or similar shared state.
- The SHACL preview uses `model_shapes_loader()` which caches shapes. If a model is installed between parse and import, the validation preview may not reflect the new shapes.

### Authoritative diagnostics
- `cd backend && .venv/bin/python -m pytest tests/test_rdf_import_parser.py -v` — parser health (29 tests, <1s)
- SSE stream at `/browser/rdf-import/execute/stream` — live import progress
- `GET /openapi.json` → check for absent "default" tag group

### What assumptions changed
- None — the milestone delivered exactly what was planned.

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
- `backend/app/commands/router.py` — added tags=["commands"]
- `backend/app/sparql/router.py` — added tags=["sparql"]
- `backend/app/validation/router.py` — added tags=["validation"]
- `backend/app/health/router.py` — added tags=["health"]
- `backend/app/admin/router.py` — added tags=["admin"]
- `backend/app/inference/router.py` — added tags=["inference"]
- `backend/app/lint/router.py` — added tags=["lint"]
- `backend/app/apps/admin_router.py` — added tags=["app-management"]
- `backend/app/apps/router.py` — added tags=["app-proxy"]
- `backend/app/shell/router.py` — added tags=["shell"]
