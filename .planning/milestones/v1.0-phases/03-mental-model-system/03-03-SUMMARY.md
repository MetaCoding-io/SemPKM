---
phase: 03-mental-model-system
plan: 03
subsystem: api
tags: [model-service, fastapi, sparql-transactions, shacl, auto-install, event-sourcing, prefix-registry]

# Dependency graph
requires:
  - phase: 03-mental-model-system
    provides: ManifestSchema, load_archive, validate_archive, ModelGraphs, registry SPARQL operations
  - phase: 03-mental-model-system
    provides: Basic PKM starter model files (manifest, ontology, shapes, views, seed)
  - phase: 01-core-data-foundation
    provides: TriplestoreClient with transaction support, EventStore for materialization
  - phase: 02-semantic-services
    provides: PrefixRegistry, ValidationService with shapes_loader callable
provides:
  - ModelService orchestrating install/remove/list pipelines with transactional writes
  - API endpoints for model management (POST install, DELETE remove, GET list)
  - Real shapes loader replacing empty_shapes_loader for SHACL validation
  - Auto-install of Basic PKM starter model on first startup
  - FastAPI dependency injection for ModelService
affects: [04-admin-shell, 05-renderers]

# Tech tracking
tech-stack:
  added: []
  patterns: [RDF4J transaction wrapping for atomic model install, seed materialization via EventStore.commit, real shapes loader closure in lifespan, container-absolute path for starter model]

key-files:
  created:
    - backend/app/services/models.py
    - backend/app/models/router.py
  modified:
    - backend/app/main.py
    - backend/app/dependencies.py

key-decisions:
  - "Seed data materialized via EventStore.commit() outside model graph transaction for event sourcing consistency"
  - "Starter model path hardcoded to /app/models/basic-pkm (container mount path) rather than relative resolution"
  - "Seed materialization failure treated as warning, not install failure, since model graphs are already committed"

patterns-established:
  - "ModelService: orchestration pattern with structured InstallResult/RemoveResult dataclasses"
  - "Shapes loader closure: async closure in lifespan captures client for real shapes loading"
  - "Auto-install pattern: ensure_starter_model() as idempotent startup hook"

requirements-completed: [MODL-01, MODL-02, MODL-03]

# Metrics
duration: 12min
completed: 2026-02-21
---

# Phase 3 Plan 03: Model Service and API Wiring Summary

**ModelService with transactional install/remove/list pipelines, 3 API endpoints, real SHACL shapes loader, and Basic PKM auto-install on startup**

## Performance

- **Duration:** 12 min
- **Started:** 2026-02-21T23:33:10Z
- **Completed:** 2026-02-21T23:45:25Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- ModelService.install() runs full validated pipeline: parse manifest, check duplicates, load JSON-LD, validate archive, write to named graphs in RDF4J transaction, materialize seed data via EventStore, register prefixes
- ModelService.remove() blocks removal when user data exists for model types (409 Conflict), clears all named graphs on success
- Three API endpoints: POST /api/models/install (201/400), DELETE /api/models/{model_id} (200/404/409), GET /api/models (200)
- Real shapes loader replaces empty_shapes_loader: fetches SHACL shapes from all installed model shapes graphs via SPARQL CONSTRUCT with FROM clauses
- Basic PKM auto-installs on first startup when no models detected, with full seed data materialization

## Task Commits

Each task was committed atomically:

1. **Task 1: ModelService with install, remove, and list pipelines** - `cba1a2d` (feat)
2. **Task 2: API endpoints and application wiring** - `856a637` (feat)

## Files Created/Modified
- `backend/app/services/models.py` - ModelService class with install/remove/list, model_shapes_loader, ensure_starter_model
- `backend/app/models/router.py` - FastAPI router with 3 endpoints, Pydantic request/response models
- `backend/app/main.py` - Lifespan wiring: EventStore, ModelService, auto-install, real shapes loader closure
- `backend/app/dependencies.py` - Added get_model_service dependency injection

## Decisions Made
- Seed data materialized via EventStore.commit() outside the model graph transaction to maintain event sourcing consistency (per Research open question 1 recommendation)
- Starter model path set to `/app/models/basic-pkm` (absolute container path) since models/ is mounted at /app/models in docker-compose.yml
- Seed materialization failure treated as a warning rather than a full install failure -- model graphs are already committed in the transaction, and seed data is supplementary

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 3 complete: Mental Model system fully operational with install, remove, list, auto-install, and real SHACL validation
- GET /api/models returns installed model metadata for admin UI consumption
- SHACL shapes from installed models now drive validation (no more synthetic conforms=True)
- Model prefixes registered in PrefixRegistry for IRI compaction
- Seed data materialized into current state graph and visible via existing SPARQL endpoints

## Self-Check: PASSED

- All 4 files verified on disk (2 created, 2 modified)
- Commit cba1a2d (Task 1) verified in git log
- Commit 856a637 (Task 2) verified in git log
- API health check passes after restart
- GET /api/models returns Basic PKM model (auto-installed)
- Duplicate install returns 400 with clear error
- Delete with user data returns 409 Conflict
- Delete nonexistent model returns 404

---
*Phase: 03-mental-model-system*
*Completed: 2026-02-21*
