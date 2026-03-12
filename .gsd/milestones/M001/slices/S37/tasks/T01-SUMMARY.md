---
id: T01
parent: S37
milestone: M001
provides:
  - "Structured lint result triples stored per-run in named graphs"
  - "LintService with paginated query, status, and diff capabilities"
  - "Pydantic response models for lint API"
  - "/api/lint/results, /api/lint/status, /api/lint/diff REST endpoints"
  - "Latest/previous run pointer in validations graph"
requires: []
affects: []
key_files: []
key_decisions: []
patterns_established: []
observability_surfaces: []
drill_down_paths: []
duration: 5min
verification_result: passed
completed_at: 2026-03-05
blocker_discovered: false
---
# T01: 37-global-lint-data-model-api 01

**# Phase 37 Plan 01: Lint Data Model & API Summary**

## What Happened

# Phase 37 Plan 01: Lint Data Model & API Summary

**Structured SHACL lint result triples stored per-run in named graphs with paginated REST API endpoints for querying, filtering, and diffing validation results**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-05T03:23:03Z
- **Completed:** 2026-03-05T03:28:00Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- ValidationReport.to_structured_triples() generates per-result RDF triples with run metadata
- LintService provides paginated, filterable result queries with inline label resolution
- Three REST endpoints live: /api/lint/results, /api/lint/status, /api/lint/diff
- Latest/previous run pointers maintained for O(1) run lookup and diffing
- All endpoints require authentication

## Task Commits

Each task was committed atomically:

1. **Task 1: Structured result triples + LintService + Pydantic models** - `d14fef9` (feat)
2. **Task 2: Lint API router + dependency wiring** - `98a300b` (feat)

## Files Created/Modified
- `backend/app/lint/__init__.py` - Empty package init
- `backend/app/lint/models.py` - Pydantic response models (LintResultItem, LintResultsResponse, LintStatusResponse, LintDiffResponse) + RDF schema constants
- `backend/app/lint/service.py` - LintService with query, pagination, diff, status, and label resolution
- `backend/app/lint/router.py` - FastAPI router with /api/lint/results, /status, /diff endpoints
- `backend/app/validation/report.py` - Added to_structured_triples() method and _severity_uri() helper
- `backend/app/services/validation.py` - Extended _store_report() to store structured triples and update latest run pointer
- `backend/app/dependencies.py` - Added get_lint_service dependency
- `backend/app/main.py` - Wired LintService into lifespan and registered lint_router

## Decisions Made
- Reused W3C SHACL predicates (sh:focusNode, sh:resultSeverity, sh:resultPath, sh:sourceShape, sh:sourceConstraintComponent) alongside sempkm: namespace for custom predicates (sempkm:inRun, sempkm:triggerSource, sempkm:sourceModel, sempkm:orphaned)
- Run IRI convention: urn:sempkm:lint-run:{uuid}, with the named graph IRI equal to the run IRI for simplicity
- Latest run pointer via urn:sempkm:lint-latest subject with sempkm:latestRun and sempkm:previousRun predicates in the validations graph, avoiding expensive ORDER BY DESC timestamp queries
- Fingerprint-based diff algorithm uses (focus_node, severity, source_shape, constraint_component, path) tuple -- message text changes don't create false new/resolved signals

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Lint data model and API ready for Phase 38 dashboard UI consumption
- SSE stream endpoint (/api/lint/stream) and lint panel migration planned for Plan 02
- Old validation endpoints still active (removal in Plan 02)

---
*Phase: 37-global-lint-data-model-api*
*Completed: 2026-03-05*
