---
phase: 35-owl2-rl-inference
plan: 01
subsystem: api
tags: [owlrl, rdflib, owl2-rl, inference, sparql, sqlalchemy]

# Dependency graph
requires:
  - phase: models-install
    provides: model registry, ontology named graphs, manifest schema
provides:
  - InferenceService with full recompute OWL 2 RL inference
  - Selective entailment classification (5 types)
  - SQLite inference_triple_state table for dismiss/promote tracking
  - API endpoints for run, list, dismiss, promote, config
  - owlrl dependency installed in backend container
  - Manifest entailment_defaults in basic-pkm
affects: [35-02-PLAN, 35-03-PLAN, 35-04-PLAN, admin-panel, object-views]

# Tech tracking
tech-stack:
  added: [owlrl 7.1.4]
  patterns: [inference service pattern (separate from validation), full recompute strategy, entailment classification heuristics]

key-files:
  created:
    - backend/app/inference/__init__.py
    - backend/app/inference/service.py
    - backend/app/inference/entailments.py
    - backend/app/inference/models.py
    - backend/app/inference/router.py
    - backend/migrations/versions/004_inference_triple_state.py
  modified:
    - backend/pyproject.toml
    - backend/app/main.py
    - backend/migrations/env.py
    - models/basic-pkm/manifest.yaml

key-decisions:
  - "Full recompute strategy (not incremental) for simplicity and correctness at PKM scale"
  - "SQLite table for per-triple state tracking (not RDF reification) for fast lookups"
  - "Entailment classification via ontology heuristics rather than rule tracing"
  - "owlrl 7.1.4 standalone (not via pyshacl inference parameter) for decoupled manual trigger"

patterns-established:
  - "InferenceService: separate from ValidationService, manual trigger only"
  - "urn:sempkm:inferred named graph: all inferred triples stored separately from user data"
  - "compute_triple_hash: deterministic SHA-256 of (s, p, o) for stable triple identification"
  - "Entailment classification: classify_entailment() assigns type labels to inferred triples"

requirements-completed: [INF-01]

# Metrics
duration: 8min
completed: 2026-03-04
---

# Phase 35 Plan 01: Backend Inference Engine Summary

**OWL 2 RL inference engine with owlrl, selective entailment filtering, 6 API endpoints, and SQLite triple state tracking**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-04T06:00:45Z
- **Completed:** 2026-03-04T06:08:38Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Installed owlrl 7.1.4 for OWL 2 RL forward-chaining inference on rdflib graphs
- Built InferenceService with full recompute strategy: load data + ontology, run closure, diff, classify, filter, store
- Implemented selective entailment classification for 5 OWL 2 RL entailment types
- Created 6 API endpoints: run inference, list triples, dismiss, promote, get config, update config
- Added Alembic migration for inference_triple_state SQLite table
- Added entailment_defaults to basic-pkm manifest (owl:inverseOf enabled by default)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add owlrl dependency, InferenceService, entailments, models, and metadata table** - `b172899` (feat)
2. **Task 2: Create inference API router and register in main.py** - `6c17a07` (feat)

## Files Created/Modified
- `backend/app/inference/__init__.py` - Module init with docstring
- `backend/app/inference/service.py` - InferenceService with run_inference, get_inferred_triples, dismiss_triple, promote_triple
- `backend/app/inference/entailments.py` - classify_entailment() for 5 entailment types, filter_by_enabled()
- `backend/app/inference/models.py` - InferenceTripleState SQLAlchemy model, compute_triple_hash()
- `backend/app/inference/router.py` - FastAPI router with 6 endpoints and htmx HTML rendering
- `backend/migrations/versions/004_inference_triple_state.py` - Alembic migration for new table
- `backend/pyproject.toml` - Added owlrl>=7.0 dependency
- `backend/app/main.py` - Registered inference_router
- `backend/migrations/env.py` - Import InferenceTripleState for Alembic autogenerate
- `models/basic-pkm/manifest.yaml` - Added entailment_defaults section

## Decisions Made
- Used full recompute strategy (drop and recompute urn:sempkm:inferred each run) for simplicity and correctness at PKM scale
- Used SQLite table for per-triple state (dismiss/promote) rather than RDF reification -- faster lookups, simpler queries
- Classified entailments via ontology heuristics (check axioms in ontology graph) rather than rule tracing through owlrl internals
- Used owlrl standalone rather than pyshacl's inference parameter to keep inference decoupled from validation (manual trigger only)
- Batched SPARQL INSERT DATA in chunks of 500 triples to avoid overly large statements

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Docker compose service is named `api` not `backend` -- adjusted verification commands accordingly
- Nginx frontend needed restart after api container recreation due to DNS resolution -- standard Docker networking behavior

## User Setup Required

None - no external service configuration required. Docker rebuild needed for owlrl dependency (included in build step).

## Next Phase Readiness
- Inference engine fully operational, ready for Plan 02 (dual-graph SPARQL query modification)
- urn:sempkm:inferred named graph strategy established, queries in Plan 02 will add FROM clauses
- InferenceService API endpoints ready for Plan 03 (Inference bottom panel UI)
- Entailment config endpoints ready for Plan 04 (admin panel integration)

## Self-Check: PASSED

All 8 created files verified present. Both task commits (b172899, 6c17a07) verified in git log.

---
*Phase: 35-owl2-rl-inference*
*Completed: 2026-03-04*
