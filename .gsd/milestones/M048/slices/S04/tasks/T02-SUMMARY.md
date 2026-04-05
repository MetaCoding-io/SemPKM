---
id: T02
parent: S04
milestone: M048
provides:
  - Fresh-volume Docker deploy verified end-to-end
  - Business-planning model confirmed loading all 33 NodeShapes on clean install
  - Verification script for reproducible testing
key_files:
  - scripts/verify-docker-fresh.sh
  - backend/app/triplestore/setup.py
  - docker-compose.yml
key_decisions:
  - Removed separate lucene_index volume — lucene data lives inside rdf4j_data volume to fix permission mismatch
  - Added _wait_for_repo_ready() retry loop in setup.py after repository creation
patterns_established:
  - RDF4J repository readiness check pattern with retry after fresh creation
observability_surfaces:
  - WARNING logs from setup.py when repository not ready after creation (includes status code and retry count)
  - ERROR log when sentinel INSERT fails after all retries (includes response body)
duration: 25m
verification_result: passed
completed_at: 2026-04-05T19:43:00.000Z
blocker_discovered: false
---

# T02: Verified fresh-volume Docker deploy and confirmed business-planning model loads all 33 NodeShapes

**Fixed two Docker fresh-volume deploy blockers (lucene volume permissions, repo readiness race) and verified business-planning model installs with all 33 NodeShapes on clean volumes.**

## What Happened

The fresh-volume deploy (`docker compose down -v && docker compose up --build -d`) was failing because of two issues discovered during execution:

1. **Lucene volume permission mismatch**: The `lucene_index` named volume in docker-compose.yml was mounted at `/var/rdf4j/lucene` as a separate Docker volume. Docker creates named volumes with root ownership by default, but the RDF4J triplestore runs as the `tomcat` user. The LuceneSail couldn't write to the lucene directory, causing `RepositoryLockedException` (500 errors) on every repository access after creation. **Fix**: Removed the separate `lucene_index` volume declaration and mount. The lucene directory now lives as a subdirectory inside the `rdf4j_data` volume (mounted at `/var/rdf4j`), which is owned by `tomcat`. This is correct because `/var/rdf4j/lucene` is a child of `/var/rdf4j`.

2. **Repository readiness race**: After `ensure_repository()` creates a new RDF4J repository (PUT returns 204), the LuceneSail + NativeStore needs time to fully initialise before accepting SPARQL operations. The sentinel INSERT immediately after creation could fail with 500 if the store wasn't ready. **Fix**: Added `_wait_for_repo_ready()` helper that polls `/size` with retry backoff after creation, plus retry logic on the sentinel INSERT itself.

After both fixes, the full cycle works: fresh volumes → triplestore healthy → API creates repo → readiness check passes → sentinel triple inserted → Basic PKM auto-installed → business-planning model installed via API → SPARQL confirms 33 NodeShapes.

Created `scripts/verify-docker-fresh.sh` for reproducible verification of the full cycle.

## Verification

- `docker compose down -v && docker compose up --build -d` — all 3 services healthy (api, frontend, triplestore)
- Entrypoint creates `/app/data/apps` and `/app/data/imports` (owned by sempkm)
- `POST /api/models/install` with `{"path": "/app/models/business-planning"}` — succeeded
- Direct triplestore SPARQL query: `SELECT (COUNT(?s) AS ?count) WHERE { GRAPH <urn:sempkm:model:business-planning:shapes> { ?s a sh:NodeShape } }` → count = 33
- `test -f scripts/verify-docker-fresh.sh` → exists, executable

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `docker compose down -v && docker compose up --build -d` | 0 | ✅ pass | 24000ms |
| 2 | `docker compose ps` (all healthy) | 0 | ✅ pass | 500ms |
| 3 | `curl -X POST .../api/models/install {"path":"/app/models/business-planning"}` | 0 | ✅ pass | 3000ms |
| 4 | SPARQL NodeShape count = 33 | 0 | ✅ pass | 500ms |
| 5 | `test -f scripts/verify-docker-fresh.sh` | 0 | ✅ pass | 10ms |

## Diagnostics

- `docker compose logs api | grep 'setup\|Repository'` — shows repo creation, readiness check, and sentinel triple timing
- `docker compose exec -T api ls -la /app/data/apps /app/data/imports` — entrypoint directory creation
- Direct triplestore query (bypassing API graph scoping): `docker compose exec -T api curl -X POST http://triplestore:8080/rdf4j-server/repositories/sempkm -H 'Content-Type: application/sparql-query' -d 'SELECT ...'`

## Deviations

Two code fixes were required that the plan classified as "code changes only if issues are discovered":

1. `docker-compose.yml` — Removed `lucene_index` volume and its mount to fix root-ownership permission issue on fresh volumes
2. `backend/app/triplestore/setup.py` — Added `_wait_for_repo_ready()` with retry and enhanced sentinel INSERT retry with response body logging

The plan anticipated this possibility ("code changes only if issues are discovered").

## Known Issues

None.

## Files Created/Modified

- `scripts/verify-docker-fresh.sh` — Runnable verification script for fresh-volume deploy + model install cycle
- `backend/app/triplestore/setup.py` — Added `_wait_for_repo_ready()` readiness check after repo creation, retry logic on sentinel INSERT
- `docker-compose.yml` — Removed separate `lucene_index` volume; lucene data now lives inside `rdf4j_data` volume
