---
phase: 04-admin-shell-and-object-creation
plan: 02
subsystem: api
tags: [shacl, rdflib, webhooks, httpx, fastapi, dependency-injection, rdf]

# Dependency graph
requires:
  - phase: 03-mental-model-system
    provides: "Model registry, shapes named graphs, model_shapes_loader"
provides:
  - "ShapesService with get_node_shapes(), get_form_for_type(), get_types() for SHACL-driven form generation"
  - "WebhookService with CRUD operations and fire-and-forget event dispatch"
  - "Webhook dispatch wired into command commit flow"
affects: [04-admin-shell-and-object-creation, 04-03, 04-04, 04-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "rdflib Collection traversal for RDF lists (sh:in)"
    - "SPARQL CONSTRUCT + rdflib Python traversal for shape extraction"
    - "Fire-and-forget webhook dispatch with error isolation"
    - "RDF-stored webhook configs in dedicated named graph"

key-files:
  created:
    - backend/app/services/shapes.py
    - backend/app/services/webhooks.py
  modified:
    - backend/app/dependencies.py
    - backend/app/main.py
    - backend/app/commands/router.py

key-decisions:
  - "ShapesService fetches entire shapes graph via CONSTRUCT then traverses with rdflib Python API, not complex SPARQL"
  - "WebhookService uses delete-all/re-insert pattern for atomic updates"
  - "Command-to-event mapping: object.create/patch/body.set -> object.changed, edge.create/patch -> edge.changed"
  - "validation.completed webhook deferred to future queue callback mechanism"

patterns-established:
  - "rdflib.Collection for sh:in RDF list traversal (avoids SPARQL property path complexity)"
  - "Webhook configs as RDF triples in urn:sempkm:webhooks named graph"
  - "Fire-and-forget dispatch pattern: try/except around webhook loop, log warnings, never raise"

requirements-completed: [SHCL-03, SHCL-04, ADMN-03]

# Metrics
duration: 4min
completed: 2026-02-22
---

# Phase 04 Plan 02: Shapes and Webhooks Services Summary

**ShapesService extracts SHACL NodeShape form metadata via rdflib graph traversal; WebhookService provides RDF-stored config CRUD and fire-and-forget HTTP dispatch wired into command commit flow**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-22T06:39:54Z
- **Completed:** 2026-02-22T06:44:20Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- ShapesService correctly extracts NodeShape forms with PropertyShape metadata (path, name, datatype, class, order, group, minCount, maxCount, in_values, defaultValue, description) from installed model shapes graphs
- sh:in RDF lists properly traversed via rdflib.Collection
- WebhookService provides full CRUD for webhook configs stored as RDF triples with fire-and-forget HTTP POST dispatch
- Both services wired into FastAPI dependency injection via app.state singletons
- Webhook dispatch integrated into command router after EventStore.commit()

## Task Commits

Each task was committed atomically:

1. **Task 1: ShapesService for SHACL shape extraction and form metadata** - `fd08faa` (feat)
2. **Task 2: WebhookService and dependency injection wiring** - `3a714ad` (feat)
3. **Task 3: Wire WebhookService.dispatch() into command commit flow** - `7532e83` (feat)

## Files Created/Modified
- `backend/app/services/shapes.py` - ShapesService with SPARQL CONSTRUCT + rdflib traversal for SHACL form metadata extraction
- `backend/app/services/webhooks.py` - WebhookService with CRUD operations and event dispatch via httpx
- `backend/app/dependencies.py` - Added get_shapes_service() and get_webhook_service() dependency injectors
- `backend/app/main.py` - ShapesService and WebhookService created during lifespan startup
- `backend/app/commands/router.py` - Webhook dispatch wired after EventStore.commit() with command-to-event mapping

## Decisions Made
- Used rdflib Python API traversal (not complex SPARQL) for shape extraction per Research Pattern 1 -- more reliable for sh:in lists and nested structures
- WebhookService uses delete-all/re-insert pattern for updates rather than field-level DELETE/INSERT WHERE -- simpler and avoids partial update issues
- Command-to-event mapping uses a static dict for clarity; unknown command types produce no webhook
- validation.completed webhook dispatch deferred as TODO -- AsyncValidationQueue does not currently support completion callbacks

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- ShapesService ready for form generation UI (Plans 04-04, 04-05)
- WebhookService ready for admin UI CRUD (Plan 04-03)
- Both services accessible via FastAPI dependency injection for any router

## Self-Check: PASSED

All files verified present. All commits verified in git log.

---
*Phase: 04-admin-shell-and-object-creation*
*Completed: 2026-02-22*
