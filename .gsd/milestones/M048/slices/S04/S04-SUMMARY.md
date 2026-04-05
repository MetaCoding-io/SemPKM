---
id: S04
parent: M048
milestone: M048
provides:
  - Docker fresh-volume deploy works end-to-end
  - Business-planning model loads all 33 NodeShapes on clean install
  - Backend entrypoint ensures /app/data subdirectories exist
requires:
  []
affects:
  []
key_files:
  - backend/docker-entrypoint.sh
  - backend/Dockerfile
  - docker-compose.yml
  - backend/app/triplestore/setup.py
  - scripts/verify-docker-fresh.sh
key_decisions:
  - D385: Removed separate lucene_index volume — lucene data lives inside rdf4j_data volume to fix permission mismatch on fresh deploys
  - D386: Added _wait_for_repo_ready() polling /size endpoint with retry backoff after RDF4J repository creation
patterns_established:
  - RDF4J repository readiness check pattern: poll /size with retry backoff after fresh creation, retry sentinel INSERT with response body logging
  - Backend entrypoint pattern: shell script ensuring data directories exist before exec $@ handoff to CMD
observability_surfaces:
  - WARNING logs from setup.py when repository not ready after creation (includes status code and retry count)
  - ERROR log when sentinel INSERT fails after all retries (includes response body)
drill_down_paths:
  - .gsd/milestones/M048/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M048/slices/S04/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-05T19:48:44.697Z
blocker_discovered: false
---

# S04: Docker Permissions + Model Loading Diagnosis

**Docker fresh-volume deploys now succeed end-to-end with robust entrypoint and triplestore readiness checks; business-planning model confirmed loading all 33 NodeShapes on clean install.**

## What Happened

This slice addressed two distinct problems: (1) the backend container had no entrypoint to create required data directories on startup, and (2) the business-planning model appeared to have only 2 NodeShapes instead of 33.

**T01 — Entrypoint script.** Created `backend/docker-entrypoint.sh` (mkdir -p for /app/data/apps and /app/data/imports, then exec "$@") and wired it into the Dockerfile as ENTRYPOINT between USER sempkm and CMD. The script runs unprivileged — no gosu/su-exec needed because /app/data is already owned by sempkm via existing chown in the Dockerfile. Deliberately omitted Alembic migrations since they're already handled in the app's lifespan startup.

**T02 — Fresh-volume deploy verification and fixes.** Running `docker compose down -v && docker compose up --build -d` exposed two issues:

1. **Lucene volume permission mismatch:** The separate `lucene_index` named volume was created with root ownership by Docker, but RDF4J runs as tomcat. LuceneSail couldn't write its index → RepositoryLockedException on every access. Fix: removed the separate volume; lucene data now lives as a subdirectory inside the `rdf4j_data` volume (which is tomcat-owned).

2. **Repository readiness race:** After PUT creates a new RDF4J repository, LuceneSail + NativeStore needs initialization time. The sentinel INSERT could fail with 500. Fix: added `_wait_for_repo_ready()` that polls `/size` with retry backoff after creation.

After both fixes, the full cycle works: fresh volumes → triplestore healthy → API creates repo → readiness check passes → sentinel triple inserted → Basic PKM auto-installed → business-planning model installed via API → SPARQL confirms 33 NodeShapes. The stale data theory was confirmed — the original install used an older archive with only 2 shapes.

Created `scripts/verify-docker-fresh.sh` for reproducible verification of the complete deploy cycle.

## Verification

- `docker compose build api` succeeds (entrypoint copied and chmod'd)
- `docker compose down -v && docker compose up --build -d` — all 3 services healthy
- Entrypoint creates /app/data/apps and /app/data/imports (owned by sempkm)
- Business-planning model install via API succeeds
- Direct triplestore SPARQL query confirms count = 33 NodeShapes in shapes graph
- `scripts/verify-docker-fresh.sh` exists and is executable

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

T02 required two code fixes (removing lucene_index volume from docker-compose.yml, adding _wait_for_repo_ready() to setup.py) that the plan classified as "code changes only if issues are discovered". The plan anticipated this possibility.

## Known Limitations

None.

## Follow-ups

None.

## Files Created/Modified

- `backend/docker-entrypoint.sh` — New entrypoint script ensuring /app/data/apps and /app/data/imports exist before handing off to CMD
- `backend/Dockerfile` — Added COPY, chmod, and ENTRYPOINT directives for docker-entrypoint.sh
- `docker-compose.yml` — Removed separate lucene_index volume — lucene data now lives inside rdf4j_data volume
- `backend/app/triplestore/setup.py` — Added _wait_for_repo_ready() readiness check and retry logic on sentinel INSERT
- `scripts/verify-docker-fresh.sh` — Runnable verification script for fresh-volume deploy + model install cycle
