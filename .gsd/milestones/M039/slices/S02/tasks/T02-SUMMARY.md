---
id: T02
parent: S02
milestone: M039
provides:
  - SHACL validation preview grouped by focus node
  - IRI collision detection against urn:sempkm:current graph
  - Import executor with per-subject and bulk commit strategies
  - SSE progress broadcasting during import execution
  - FastAPI router with 5 endpoints for the RDF import wizard flow
key_files:
  - backend/app/rdf_import/executor.py
  - backend/app/rdf_import/router.py
  - backend/app/main.py
key_decisions: []
patterns_established:
  - Executor builds Operation dataclasses directly from SubjectInfo.triples — preserves original rdflib URIRef/Literal terms (datatypes, language tags) without re-serialization
  - Module-level _parse_cache and _import_results dicts keyed by str(user.id) for cross-request state between wizard steps
  - SHACL validation and collision detection run in parallel via asyncio.gather during parse step
observability_surfaces:
  - SSE events via ScanBroadcast at /browser/rdf-import/execute/stream (import_progress, import_complete, import_error)
  - Logger rdf_import.executor — INFO on validation results and import completion, ERROR on per-subject or batch failures
  - _parse_cache and _broadcasts module-level dicts inspectable for active state
duration: 12m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T02: Build executor, router endpoints, and SHACL validation preview

**Built RDF import executor with SHACL validation, collision detection, SSE progress broadcasting, and 5-endpoint FastAPI router registered at /browser/rdf-import.**

## What Happened

Created two new files and modified main.py:

1. **executor.py** — Three async functions:
   - `validate_shacl()` — Loads installed model shapes via `model_shapes_loader()`, runs pyshacl in a thread, parses results via `ValidationReport.from_pyshacl()`, groups by focus node IRI → list of `{severity, message, path}`.
   - `check_collisions()` — Builds SPARQL SELECT with VALUES clause against `urn:sempkm:current` graph, returns set of existing IRIs.
   - `execute_import()` — Builds Operation dataclasses directly from SubjectInfo.triples (preserving original URIRef/Literal terms). Per-subject commit for ≤10 subjects, bulk commit in chunks of 500 for >10. Broadcasts SSE progress events throughout.

2. **router.py** — 5 endpoints following the obsidian router DI pattern:
   - `GET /` — Wizard page (full page or htmx partial via block_name)
   - `POST /parse` — Accepts paste content or file upload, detects format, parses, runs SHACL + collision check in parallel, caches result, returns preview partial
   - `POST /execute` — Retrieves cached parse result, starts background task, returns progress partial
   - `GET /execute/stream` — SSE stream with keepalive, handles race condition where import completes before client connects
   - `GET /summary` — Renders import results with stat cards

3. **main.py** — Added import and `app.include_router(rdf_import_router)` after notion_router.

## Verification

- `grep -n "rdf_import_router" backend/app/main.py` — matches at lines 34 and 658
- `cd backend && .venv/bin/python -c "from app.rdf_import.router import router; print(router.prefix)"` — outputs `/browser/rdf-import`
- `cd backend && .venv/bin/python -m pytest tests/test_rdf_import_parser.py -v` — 29/29 passed, no regressions
- Import smoke check confirmed all 5 routes registered: `/browser/rdf-import`, `/browser/rdf-import/parse`, `/browser/rdf-import/execute`, `/browser/rdf-import/execute/stream`, `/browser/rdf-import/summary`

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -n "rdf_import_router" backend/app/main.py` | 0 | ✅ pass | <1s |
| 2 | `cd backend && .venv/bin/python -c "from app.rdf_import.router import router; print(router.prefix)"` | 0 | ✅ pass | <1s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_rdf_import_parser.py -v` | 0 | ✅ pass | 5.3s |
| 4 | `cd backend && .venv/bin/python -c "from app.rdf_import.executor import validate_shacl, check_collisions, execute_import; print('OK')"` | 0 | ✅ pass | <1s |

## Diagnostics

- **Executor health:** `cd backend && .venv/bin/python -c "from app.rdf_import.executor import validate_shacl, check_collisions, execute_import; print('imports OK')"`
- **Route listing:** `cd backend && .venv/bin/python -c "from app.rdf_import.router import router; print([r.path for r in router.routes])"`
- **Logger:** `rdf_import.executor` — INFO for SHACL results, collision counts, import stats; ERROR for per-subject failures
- **SSE endpoint:** Connect to `/browser/rdf-import/execute/stream` during an active import for real-time progress

## Deviations

- The plan's step 4 mentioned `Depends(get_triplestore_client)` and `Depends(get_event_store)` — instead used `request.app.state.*` direct access, consistent with how the obsidian router actually works (the Depends wrappers exist but the direct pattern is more common in browser-facing routers).
- Added `_import_results` module-level cache to store completed import results for the summary endpoint — the plan didn't specify this but the summary endpoint needs to access results after the background task completes.

## Known Issues

- Module-level caches (`_parse_cache`, `_import_results`, `_broadcasts`) are not cleaned up on user session expiry — they're cleaned up when endpoints are called or after a 30-second delay. In a multi-worker deployment, the cache would need to be shared (e.g., Redis), but for the single-worker Docker setup this is fine.

## Files Created/Modified

- `backend/app/rdf_import/executor.py` — SHACL validation, collision detection, import execution with SSE progress
- `backend/app/rdf_import/router.py` — FastAPI router with 5 endpoints for the RDF import wizard flow
- `backend/app/main.py` — Added rdf_import_router import and registration
