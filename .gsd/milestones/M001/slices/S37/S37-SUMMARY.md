---
id: S37
parent: M001
milestone: M001
provides:
  - "Structured lint result triples stored per-run in named graphs"
  - "LintService with paginated query, status, and diff capabilities"
  - "Pydantic response models for lint API"
  - "/api/lint/results, /api/lint/status, /api/lint/diff REST endpoints"
  - "Latest/previous run pointer in validations graph"
  - "SSE broadcast manager with asyncio.Queue fan-out"
  - "/api/lint/stream SSE endpoint for real-time validation events"
  - "Lint panel with SSE-driven updates (no polling)"
  - "Per-object lint results via LintService structured triples"
  - "Old /api/validation/* endpoints removed"
requires: []
affects: []
key_files: []
key_decisions:
  - "Reuse W3C SHACL predicates (sh:focusNode, sh:resultSeverity) alongside sempkm: namespace for custom predicates"
  - "Run IRI convention: urn:sempkm:lint-run:{uuid} with run graph IRI = run IRI"
  - "Latest run pointer via dedicated triples in validations graph (avoids ORDER BY DESC queries)"
  - "Used StreamingResponse with text/event-stream instead of fastapi.sse (not available without sse-starlette)"
  - "Single global SSE stream with client-side filtering (dashboard and per-object panel share one stream)"
  - "30s keepalive timeout to prevent connection drops through nginx proxy"
  - "EventSource reconnects automatically (browser built-in), no manual reconnect logic needed"
patterns_established:
  - "Per-run named graphs: each validation run stores structured results in urn:sempkm:lint-run:{uuid}"
  - "Latest run pointer: urn:sempkm:lint-latest sempkm:latestRun/previousRun in validations graph"
  - "Fingerprint-based diff: (focus_node, severity, source_shape, constraint_component, path) tuple matching"
  - "SSE fan-out: LintBroadcast with asyncio.Queue per subscriber, put_nowait with QueueFull discard"
  - "EventSource-htmx bridge: SSE event triggers htmx.ajax() to re-fetch content"
  - "Trigger source attribution: validation jobs carry trigger_source through to SSE events"
observability_surfaces: []
drill_down_paths: []
duration: 5min
verification_result: passed
completed_at: 2026-03-05
blocker_discovered: false
---
# S37: Global Lint Data Model Api

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

# Phase 37 Plan 02: SSE Real-time Push & Lint Panel Migration Summary

**SSE broadcast for instant validation updates replacing 10s polling, lint panel migrated to structured result triples, old validation API removed**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-05T03:30:00Z
- **Completed:** 2026-03-05T03:35:00Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- LintBroadcast fan-out manager delivers validation_complete events to all SSE subscribers
- Lint panel updates within 1-2s of validation completion (down from 10s polling)
- Per-object lint panel queries structured result triples via LintService (single source of truth)
- Old /api/validation/* endpoints fully removed from the app router
- nginx SSE proxy configured with buffering disabled for /api/lint/stream

## Task Commits

Each task was committed atomically:

1. **Task 1: SSE broadcast manager + stream endpoint + validation queue wiring** - `d6cb8c0` (feat)
2. **Task 2: Lint panel migration + old validation router removal** - `1d452dd` (feat)

## Files Created/Modified
- `backend/app/lint/broadcast.py` - SSE broadcast manager with asyncio.Queue fan-out and keepalive
- `backend/app/lint/router.py` - Added /stream SSE endpoint with auth and keepalive heartbeat
- `backend/app/lint/service.py` - Added get_results_for_object() for per-object structured queries
- `backend/app/validation/queue.py` - Added trigger_source field to ValidationJob
- `backend/app/main.py` - Created LintBroadcast, wired SSE publish, removed validation_router
- `backend/app/dependencies.py` - Added get_lint_broadcast dependency
- `backend/app/browser/router.py` - Migrated get_lint() from raw SPARQL to LintService
- `backend/app/templates/browser/lint_panel.html` - Replaced hx-trigger polling with EventSource SSE
- `frontend/nginx.conf` - Added /api/lint/stream SSE proxy location block
- `e2e/tests/04-validation/lint-panel.spec.ts` - Updated to verify SSE behavior instead of polling

## Decisions Made
- Used StreamingResponse with text/event-stream media type instead of EventSourceResponse from fastapi.sse (sse-starlette not installed, matches existing LLM streaming pattern)
- Single global SSE stream (/api/lint/stream) -- both per-object lint panel and future global dashboard subscribe to the same stream
- 30s keepalive timeout with comment heartbeat to prevent nginx/proxy from closing idle connections
- EventSource auto-reconnect is handled by browser built-in behavior, no manual reconnect logic needed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used StreamingResponse instead of fastapi.sse.EventSourceResponse**
- **Found during:** Task 1 (SSE broadcast manager)
- **Issue:** Plan specified `from fastapi.sse import EventSourceResponse, ServerSentEvent` but fastapi.sse module does not exist (requires sse-starlette package which is not installed)
- **Fix:** Used `fastapi.responses.StreamingResponse` with `media_type="text/event-stream"`, matching the existing LLM streaming pattern in the codebase
- **Files modified:** backend/app/lint/broadcast.py, backend/app/lint/router.py
- **Verification:** Import succeeds, SSE stream works correctly
- **Committed in:** d6cb8c0 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential adaptation -- same SSE behavior achieved using available libraries. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- SSE infrastructure ready for Phase 38 global lint dashboard UI
- Dashboard can subscribe to same /api/lint/stream endpoint
- All lint data flows through structured result triples (single source of truth)

---
*Phase: 37-global-lint-data-model-api*
*Completed: 2026-03-05*
