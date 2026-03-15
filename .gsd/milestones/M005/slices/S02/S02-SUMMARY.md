---
id: S02
parent: M005
milestone: M005
provides:
  - OperationsLogService with log_activity(), list_activities(), get_activity(), count_activities()
  - PROV-O vocabulary usage patterns (prov:Activity, prov:startedAtTime, prov:endedAtTime, prov:wasAssociatedWith, prov:used)
  - Fire-and-forget ops log instrumentation at model install/remove, inference run, validation run
  - Admin UI page at /admin/ops-log with filter and cursor-based pagination
  - Operations Log sidebar nav link and admin index card
requires: []
affects:
  - S06
key_files:
  - backend/app/services/ops_log.py
  - backend/tests/test_ops_log.py
  - backend/app/main.py
  - backend/app/dependencies.py
  - backend/app/admin/router.py
  - backend/app/inference/router.py
  - backend/app/validation/queue.py
  - backend/app/templates/admin/ops_log.html
  - backend/app/templates/admin/index.html
  - backend/app/templates/components/_sidebar.html
key_decisions:
  - D079: Ops log calls in router layer, not service layer — router has user context from require_role()
  - D080: Direct SPARQL INSERT DATA to urn:sempkm:ops-log, not EventStore — ops log is metadata about operations, not data
  - D081: Single urn:sempkm:ops-log named graph for all entries — simple, low volume, matches QueryService pattern
  - D082: Fire-and-forget try/except around all log_activity() calls — never blocks primary operation
  - D083: htmx target-aware block rendering — HX-Target header decides which Jinja2 block to return
patterns_established:
  - OperationsLogService follows QueryService pattern — raw SPARQL, _esc(), _now_iso(), TriplestoreClient
  - Cursor-based pagination via FILTER(?startedAt < cursor) + LIMIT N+1 for next-page detection
  - Fire-and-forget ops logging — try/except with WARNING log on failure, never blocks primary operation
  - htmx target-aware block rendering — check HX-Target header to return appropriate Jinja2 block
observability_surfaces:
  - /admin/ops-log page renders prov:Activity instances with filter and pagination
  - logger.info("Logged ops activity: %s") on every successful write
  - WARNING log on triplestore write failure (fire-and-forget, never blocks)
  - Direct SPARQL query against urn:sempkm:ops-log via SPARQL console
drill_down_paths:
  - .gsd/milestones/M005/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M005/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M005/slices/S02/tasks/T03-SUMMARY.md
duration: 55m
verification_result: passed
completed_at: 2026-03-14
---

# S02: Operations Log & PROV-O Foundation

**Admin/debug UI at /admin/ops-log shows timestamped, PROV-O-modeled operations log entries; model install/remove, inference, and validation runs are instrumented with fire-and-forget logging to RDF.**

## What Happened

**T01 — OperationsLogService** (15m): Built `backend/app/services/ops_log.py` following the QueryService pattern — raw SPARQL strings, `_esc()` helper, `_now_iso()`, `TriplestoreClient`. Four methods: `log_activity()` (INSERT DATA with prov:Activity, PROV-O timestamps, actor, used resources, status/error), `list_activities()` (cursor-paginated SELECT with optional type filter, LIMIT N+1 for next-page detection), `get_activity()` (single-resource SELECT collecting prov:used IRIs), `count_activities()` (COUNT with optional type filter). IRI pattern `urn:sempkm:ops-log:{uuid}`. 35 unit tests validate SPARQL generation, escaping (backslash, quotes, newlines, combined), cursor construction, and result parsing.

**T02 — DI and Instrumentation** (15m): Wired `OperationsLogService` into FastAPI DI — instantiated in `main.py` lifespan, stored on `app.state.ops_log_service`, injectable via `get_ops_log_service()` in `dependencies.py`. Added fire-and-forget `log_activity()` calls at four instrumentation points: model install (success/failure), model remove (success/failure), inference run (with inferred/new counts), and validation run (with conforms/violations/warnings). All calls wrapped in try/except — failures logged at WARNING, never blocking the primary operation. User actor IRI pattern `urn:sempkm:user:{user.id}`; validation queue uses `urn:sempkm:system`.

**T03 — Admin UI** (25m): Added `GET /admin/ops-log` route with `require_role("owner")`, activity type filter, and cursor-based pagination. Template extends `base.html` with a reverse-chronological table (Time, Activity, Type, Actor, Status, Duration columns), expandable error details via `<details>`, and "Load more" pagination. htmx target-aware rendering: sidebar nav returns `content` block, filter/pagination returns `table_rows` block. Added Operations Log card to admin index page and sidebar nav link with `activity` Lucide icon.

## Verification

- ✅ `backend/tests/test_ops_log.py` — 35/35 unit tests pass (SPARQL generation, escaping, pagination, result parsing)
- ✅ `grep -rn "ops_log"` confirms instrumentation in all 5 target files (17 occurrences)
- ✅ Zero conflict markers in backend/ and frontend/
- ✅ All 6 key Python files parse without syntax errors
- ✅ Docker browser verification: /admin/ops-log renders with heading, filter dropdown, table
- ✅ Seeded activities display correctly with all columns
- ✅ Activity type filter narrows results without content duplication
- ✅ Error expansion shows detail in red monospace
- ✅ Sidebar link visible with activity icon, htmx navigation works
- ✅ Admin index card renders with "View Operations Log" button
- ✅ Owner role enforced (non-owner sees "Access Denied")

## Requirements Advanced

- LOG-01 — Operations log with PROV-O vocabulary fully implemented: service, instrumentation, and admin UI

## Requirements Validated

- LOG-01 — Ops log entries round-trip through triplestore and render in admin UI; PROV-O terms used correctly; four activity types instrumented

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- T03: Added HX-Target header detection for Jinja2 block selection — plan didn't specify htmx targeting strategy. Initial implementation caused content duplication on filter swap; fixed by inspecting HX-Target to return appropriate block.

## Known Limitations

- Pagination not exercised with real high-volume data — cursor logic validated in unit tests only
- No E2E Playwright tests yet (deferred to S09)
- No user guide docs yet (deferred to S09)
- Activity type labels are hardcoded strings — no registry or extensibility mechanism

## Follow-ups

- S06 (PROV-O Alignment Design) consumes this slice's PROV-O usage patterns as a concrete reference
- S09 (E2E Tests & Docs) will add Playwright tests and user guide page for /admin/ops-log

## Files Created/Modified

- `backend/app/services/ops_log.py` — new; OperationsLogService with 4 methods
- `backend/tests/test_ops_log.py` — new; 35 unit tests
- `backend/app/main.py` — import/instantiate OperationsLogService, pass to validation queue
- `backend/app/dependencies.py` — add get_ops_log_service() DI function
- `backend/app/admin/router.py` — add /admin/ops-log route, ops log calls in install/remove handlers
- `backend/app/inference/router.py` — add ops log call after inference run
- `backend/app/validation/queue.py` — accept optional ops_log_service, log after validation
- `backend/app/templates/admin/ops_log.html` — new; ops log page template
- `backend/app/templates/admin/index.html` — add Operations Log card
- `backend/app/templates/components/_sidebar.html` — add Operations Log nav link

## Forward Intelligence

### What the next slice should know
- PROV-O usage is straightforward: `prov:Activity` with `prov:startedAtTime`, `prov:endedAtTime`, `prov:wasAssociatedWith`, `prov:used`. SemPKM extensions: `sempkm:activityType`, `sempkm:status`, `sempkm:errorMessage`. S06 should audit these patterns for alignment completeness.
- The ops log service follows the QueryService pattern exactly — raw SPARQL, `_esc()`, mock-based unit tests. Any new service in this codebase should follow the same pattern.

### What's fragile
- htmx target-aware block rendering in the ops log route — the HX-Target check (`"app-content"` vs anything else) is a manual dispatch. Adding new htmx consumers that swap different targets could hit the wrong branch.

### Authoritative diagnostics
- `SELECT * WHERE { GRAPH <urn:sempkm:ops-log> { ?s ?p ?o } }` in SPARQL console — shows all raw ops log data
- `/admin/ops-log` page — the rendered view of the same data

### What assumptions changed
- PROV-O Starting Point terms were sufficient — no need for PROV-O Qualified or Extended terms. The vocabulary mapped cleanly to simple system activities.
