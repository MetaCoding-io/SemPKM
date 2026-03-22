---
id: T02
parent: S01
milestone: M033
provides:
  - MirrorService in app.sparql.mirror with mirror_results, validate_endpoint, clear_mirrored, get_mirror_stats
  - Mirror API router at /api/sparql/mirror with POST, GET, DELETE endpoints
  - federation_allowed_endpoints config setting with get_allowed_endpoints() parser
  - MirrorResult dataclass and MIRROR_PROV_PREFIX constant
key_files:
  - backend/app/sparql/mirror.py
  - backend/app/sparql/mirror_router.py
  - backend/app/config.py
  - backend/app/main.py
  - backend/tests/test_mirror_service.py
key_decisions:
  - Secure default — empty federation_allowed_endpoints blocks all endpoints; requires explicit opt-in
  - Triple extraction from SPARQL JSON bindings uses positional URI strategy — 3 URIs → s,p,o; 2 URIs → s, rdfs:seeAlso, o
  - Provenance metadata stored in per-batch named graphs (urn:sempkm:mirror-prov:{uuid}) with prov:wasAttributedTo and prov:generatedAtTime
  - POST /api/sparql/mirror requires owner role; GET endpoints require any authenticated user
patterns_established:
  - MirrorService follows InferenceService constructor pattern — takes TriplestoreClient, instantiated per-request in router
  - Batched INSERT DATA with 500-triple batch size for both data and provenance storage
observability_surfaces:
  - logger.info for mirror operations (endpoint, triple count, provenance graph IRI)
  - logger.warning for blocked endpoint attempts (includes endpoint URL and user email)
  - GET /api/sparql/mirror/endpoints returns allowlist configuration
  - GET /api/sparql/mirror/stats returns triple count and source endpoint list
  - Structured JSON error responses — 403 for blocked endpoints, 502 for query failures, 500 for storage failures
duration: 10min
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T02: Mirror service, endpoint allowlist, and API endpoints

**Built MirrorService with endpoint allowlist validation, triple mirroring into urn:sempkm:mirrored with provenance tracking, and 4 API endpoints mounted at /api/sparql/mirror**

## What Happened

Added `federation_allowed_endpoints` setting to `backend/app/config.py` with a `get_allowed_endpoints()` helper that parses the comma-separated list. The secure default is an empty string (no endpoints allowed).

Created `backend/app/sparql/mirror.py` with `MirrorService` class that:
- Validates endpoints against the allowlist via `validate_endpoint()`
- Extracts triples from SPARQL JSON result bindings (3 URI vars → s,p,o triple; 2 URI vars → rdfs:seeAlso link; deduplicates)
- Stores extracted triples in `urn:sempkm:mirrored` via batched INSERT DATA (500-triple batches)
- Creates per-batch provenance metadata in `urn:sempkm:mirror-prov:{uuid}` named graphs with `prov:wasAttributedTo`, `prov:generatedAtTime`, and triple count
- Clears all mirrored data and provenance graphs via `clear_mirrored()`
- Returns mirror statistics via `get_mirror_stats()`

Created `backend/app/sparql/mirror_router.py` with 4 endpoints:
- `POST /api/sparql/mirror` — validates endpoint, executes query, mirrors results (owner-only)
- `GET /api/sparql/mirror/endpoints` — returns allowlist configuration
- `GET /api/sparql/mirror/stats` — returns triple count and source endpoints
- `DELETE /api/sparql/mirror` — clears all mirrored data (owner-only)

Mounted the router in `backend/app/main.py` adjacent to the existing SPARQL router.

Wrote 28 unit tests across 8 test classes covering config parsing, endpoint validation, triple extraction, mirror storage, provenance, clear, stats, and router behavior.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_mirror_service.py -v` — 28/28 passed
- `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py tests/test_mirror_service.py -v` — 78/78 passed (no regressions)
- `rg "mirror_router" backend/app/main.py` — router mounted (import + include_router)
- `rg "MIRRORED_GRAPH_IRI" backend/app/rdf/namespaces.py` — constant exists

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_mirror_service.py -v` | 0 | ✅ pass | 0.56s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_sparql_client.py tests/test_mirror_service.py -v` | 0 | ✅ pass | 0.56s |
| 3 | `rg "mirror_router" backend/app/main.py` | 0 | ✅ pass | <0.1s |
| 4 | `rg "MIRRORED_GRAPH_IRI" backend/app/rdf/namespaces.py` | 0 | ✅ pass | <0.1s |

## Diagnostics

- `GET /api/sparql/mirror/endpoints` — inspect configured allowlist without needing shell access
- `GET /api/sparql/mirror/stats` — check mirror health: triple count and source endpoints
- Blocked endpoint attempts logged at `logger.warning` level with endpoint URL and user email
- Mirror operations logged at `logger.info` level with endpoint, triple count, and provenance graph IRI
- Error responses include structured detail messages distinguishing blocked endpoints (403), query failures (502), and storage failures (500)

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/config.py` — added federation_allowed_endpoints setting and get_allowed_endpoints() method
- `backend/app/sparql/mirror.py` — new MirrorService with mirror_results, validate_endpoint, clear_mirrored, get_mirror_stats
- `backend/app/sparql/mirror_router.py` — new FastAPI router with POST/GET/DELETE endpoints at /api/sparql/mirror
- `backend/app/main.py` — imported and mounted mirror_router
- `backend/tests/test_mirror_service.py` — 28 unit tests across 8 test classes
- `.gsd/milestones/M033/slices/S01/tasks/T02-PLAN.md` — added Observability Impact section per pre-flight requirement
