---
id: T03
parent: S01
milestone: M033
provides:
  - MirrorService class with mirror_results(), get_mirror_batches(), delete_mirror_batch()
  - Mirror API router at /api/sparql/mirror (POST), /api/sparql/mirror/batches (GET/DELETE)
  - "Mirror Results" button in SPARQL console toolbar
  - SERVICE clause detection and endpoint extraction in frontend
  - urn:sempkm:mirror: in frontend KNOWN_VOCAB_PREFIXES
key_files:
  - backend/app/federation/mirror_service.py
  - backend/app/federation/mirror_router.py
  - backend/app/main.py
  - frontend/static/js/sparql-console.js
  - backend/app/templates/browser/sparql_panel.html
  - frontend/static/css/workspace.css
  - backend/tests/test_mirror_service.py
key_decisions:
  - Binding conversion uses two-path strategy — SPO triple-pattern detection (s/p/o naming convention) with star-pattern fallback (first URI is subject, remaining vars become sempkm: predicates)
  - Provenance stored as prov:Entity with prov:wasAttributedTo (endpoint URI), prov:generatedAtTime, dcterms:source, and sempkm:queryHash for dedup tracking
  - Mirror button lives between the toolbar spacer and All Graphs checkbox — visible to all users, not just owners
patterns_established:
  - _bindings_to_triples() pattern for converting SPARQL JSON result format to rdflib Graph — reusable for any future binding-to-RDF conversion
  - Mirror button state management pattern — disabled by default, enabled after SERVICE query with results, transitions through loading/done states to prevent double-mirroring
observability_surfaces:
  - GET /api/sparql/mirror/batches — returns all mirror batches with provenance metadata
  - Structured logging in MirrorService — logs mirror operations with endpoint, triple count, batch ID, query hash
  - Error dict with {error, endpoint, timestamp} returned on storage failure; API returns 502 with detail
duration: 20m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T03: Mirror service and "Mirror Results" SPARQL console action

**Added MirrorService for converting SPARQL JSON bindings to RDF triples in urn:sempkm:mirrored with PROV-O provenance, mirror API endpoints, and "Mirror Results" button in the SPARQL console toolbar.**

## What Happened

1. Created `backend/app/federation/mirror_service.py` with `MirrorService` class. The `mirror_results()` method converts SPARQL JSON result bindings to RDF triples using two strategies: SPO triple-pattern detection (recognizes s/p/o variable naming conventions) and star-pattern fallback (first URI becomes subject, remaining variables become predicates in the sempkm: namespace). Provenance is attached using PROV-O vocabulary — each mirror batch gets a `urn:sempkm:mirror:{uuid}` IRI with `prov:wasAttributedTo`, `prov:generatedAtTime`, `dcterms:source`, `sempkm:queryHash`, and `sempkm:tripleCount`. Storage uses `insert_graph()` (Graph Store protocol) per Knowledge Pattern 3. Error path returns `{error, endpoint, timestamp}` dict instead of raising. Also implemented `get_mirror_batches()` (SPARQL query against mirrored graph for provenance) and `delete_mirror_batch()` (SPARQL DELETE WHERE with batch IRI validation).

2. Created `backend/app/federation/mirror_router.py` with three endpoints: `POST /api/sparql/mirror` (any authenticated user, calls MirrorService), `GET /api/sparql/mirror/batches` (list all batches), `DELETE /api/sparql/mirror/batches/{batch_id}` (owner-only). Uses FastAPI dependency injection for TriplestoreClient → MirrorService. Error responses use 502 for storage failures and 400 for invalid batch IDs.

3. Registered `mirror_router` in `main.py` right after `federation_allowlist_router`.

4. Added "Mirror Results" button to `sparql_panel.html` toolbar — positioned between the toolbar spacer and the All Graphs checkbox. Uses `database` Lucide icon, starts disabled.

5. Wired the button in `sparql-console.js`: after successful query execution, stores bindings and query text in module state, then enables the mirror button only if the query contained a SERVICE clause and had results. On click, extracts the SERVICE endpoint URL via regex, POSTs to `/api/sparql/mirror`, shows success/error toast via `window.showToast()`, and transitions button to "Mirrored" (done) state to prevent double-mirroring. Three visual states: disabled (0.4 opacity), loading (0.6 opacity + "Mirroring..." text), and done (green border + "Mirrored" text).

6. Added CSS for mirror button states in `workspace.css` — disabled, hover, loading, and done states with smooth transitions.

7. Added `urn:sempkm:mirror:` to frontend `KNOWN_VOCAB_PREFIXES` array (was already in backend `_VOCAB_PREFIXES` from T01 but missing from frontend).

8. Wrote 30 unit tests across 8 test classes covering: binding-to-term conversion (7 tests), SPO variable detection (5 tests), SPO binding conversion (4 tests), star-pattern conversion (2 tests), mirror_results integration (6 tests including provenance verification and error paths), batch listing (3 tests), and batch deletion (3 tests).

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_mirror_service.py -v` — all 30 tests pass
- `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py tests/test_mirror_service.py tests/test_federation_allowlist.py -v` — all 87 slice-level tests pass
- Import verification: `from app.federation.mirror_router import mirror_router` and `from app.federation.mirror_service import MirrorService` both succeed
- Template: mirror button correctly positioned in sparql_panel.html with disabled attribute and database icon

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_mirror_service.py -v` | 0 | ✅ pass | 0.18s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py tests/test_mirror_service.py tests/test_federation_allowlist.py -v` | 0 | ✅ pass | 0.67s |
| 3 | `python -c "from app.federation.mirror_router import mirror_router; print(mirror_router.prefix)"` | 0 | ✅ pass | <1s |
| 4 | `python -c "from app.federation.mirror_service import MirrorService, MIRROR_NS"` | 0 | ✅ pass | <1s |

## Diagnostics

- **Inspect mirror batches:** `GET /api/sparql/mirror/batches` (any authenticated user) returns `{"batches": [{batch_id, source_endpoint, timestamp, triple_count, query_hash}]}`.
- **Query mirrored triples:** Use SPARQL console with "All Graphs" checked, query `SELECT * FROM <urn:sempkm:mirrored> WHERE { ?s ?p ?o }` to see all mirrored data.
- **Check provenance:** Query `SELECT ?batch ?source ?timestamp WHERE { GRAPH <urn:sempkm:mirrored> { ?batch a prov:Entity . ?batch dcterms:source ?source . ?batch prov:generatedAtTime ?timestamp } }`.
- **Storage failures:** MirrorService logs at ERROR level with endpoint and batch ID. API returns 502 with `{error, endpoint, timestamp}` detail dict.
- **Mirror button state:** Button disabled = no SERVICE query run or no results. Button enabled = SERVICE query with results ready to mirror. Button shows "Mirrored" with green border = already mirrored.

## Deviations

- Added `urn:sempkm:mirror:` to frontend `KNOWN_VOCAB_PREFIXES` — not explicitly in the T03 plan but required for consistency (backend had it from T01, frontend didn't). Knowledge entry about keeping these lists in sync (M031/S05/T01) called this out.
- Added `sempkm:tripleCount` to provenance metadata beyond what plan specified — useful for the batches listing UI without re-counting triples.

## Known Issues

None.

## Files Created/Modified

- `backend/app/federation/mirror_service.py` — MirrorService class with mirror_results(), get_mirror_batches(), delete_mirror_batch(), binding conversion helpers
- `backend/app/federation/mirror_router.py` — API router with POST /mirror, GET /mirror/batches, DELETE /mirror/batches/{batch_id}
- `backend/app/main.py` — imported and registered mirror_router
- `frontend/static/js/sparql-console.js` — added mirror button wiring, SERVICE detection, lastQueryBindings/lastQueryText state, _updateMirrorButton(), _handleMirrorClick(), urn:sempkm:mirror: to KNOWN_VOCAB_PREFIXES
- `backend/app/templates/browser/sparql_panel.html` — added Mirror Results button to toolbar
- `frontend/static/css/workspace.css` — added .sparql-mirror-btn styles (disabled, hover, loading, done states)
- `backend/tests/test_mirror_service.py` — 30 unit tests across 8 test classes
