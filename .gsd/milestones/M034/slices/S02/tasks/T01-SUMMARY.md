---
id: T01
parent: S02
milestone: M034
provides:
  - _build_timeline_select() SPARQL query builder for timeline view
  - execute_timeline_query() with multi-row dependency grouping
  - "timeline" renderer registered in router (generic_view + generic_view_data)
  - 15 unit tests covering SPARQL construction, dep grouping, date fallback, empty results
key_files:
  - backend/app/views/service.py
  - backend/app/views/router.py
  - backend/tests/test_timeline.py
key_decisions:
  - Used bpkm:dependsOn/priority/taskStatus IRIs directly in SPARQL rather than detecting them dynamically — these are specific to the basic-pkm model and timeline is a task-oriented view
  - Status-to-CSS-class mapping lives as a class dict (_TIMELINE_STATUS_CLASSES) for easy extension
patterns_established:
  - Timeline SPARQL groups multi-row results by task IRI to collect dependency arrays — same pattern could be reused for any view that needs to aggregate multi-valued properties
observability_surfaces:
  - logger.info("execute_timeline_query: type=%s tasks=%d deps=%d") structured log
  - logger.info("generic_view: renderer=timeline ...") request log
  - /browser/views/generic/timeline/data?type=<iri> JSON endpoint returns raw task+dependency data
  - Empty results return {"tasks": [], "dependency_count": 0}
duration: 25m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T01: Backend timeline data layer — service methods, router endpoints, unit tests

**Added _build_timeline_select() and execute_timeline_query() to ViewSpecService with dependency grouping, date stripping, and status mapping; registered timeline renderer in router; wrote 15 unit tests all passing**

## What Happened

Added two new methods to `ViewSpecService`:
- `_build_timeline_select()` — static method following the `_build_calendar_select()` pattern. Builds a SPARQL SELECT fetching `?s ?label ?startDate ?endDate ?dep ?priority ?status` for tasks of a given type, with OPTIONALs for endDate, dependencies (via `bpkm:dependsOn`), priority, and status.
- `execute_timeline_query()` — executes the SPARQL and groups results by task IRI (since tasks with N `bpkm:dependsOn` edges produce N rows). Strips datetime values to YYYY-MM-DD for Frappe Gantt compatibility. Falls back to start+1day when endDate is absent. Maps status values to Frappe Gantt CSS classes (done→bar-done, in-progress→bar-active).

Registered `"timeline"` in `_VALID_RENDERERS` in the router and added `elif renderer == "timeline":` blocks in both `generic_view()` (renders template with context including `timeline_data_url`) and `generic_view_data()` (returns JSON directly). The `generic_view()` handler follows the calendar/map pattern: checks for type, detects date fields, builds data URL, and renders template with full context dict.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_timeline.py -v` — 15/15 passed
- `cd backend && .venv/bin/python -m pytest tests/test_timeline.py tests/test_calendar.py -v` — 37/37 passed (no calendar regressions)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_timeline.py -v` | 0 | ✅ pass | 4.2s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_timeline.py tests/test_calendar.py -v` | 0 | ✅ pass | 3.5s |

## Diagnostics

- Check backend logs for `renderer=timeline` entries to verify requests reaching the endpoint
- Hit `/browser/views/generic/timeline/data?type=urn:sempkm:model:basic-pkm:Task` directly for raw JSON
- Empty/error states: no type → `{"tasks": [], "dependency_count": 0}`; type with no dates → template renders error_message; SPARQL failure → empty tasks without crash

## Deviations

None — implementation followed the task plan exactly. The `bpkm:dependsOn` IRI confirmed as `urn:sempkm:model:basic-pkm:dependsOn` matching the plan.

## Known Issues

- The `_build_timeline_select()` hardcodes `bpkm:dependsOn`, `bpkm:priority`, and `bpkm:taskStatus` IRIs. If another Mental Model defines tasks with different dependency/status predicates, timeline won't pick them up. This is acceptable for now since timeline is inherently task-oriented and basic-pkm is the only model with these properties.
- The `timeline_view.html` template does not exist yet — T02 will create it. The router will return a TemplateNotFound error until then.

## Files Created/Modified

- `backend/app/views/service.py` — Added `_build_timeline_select()`, `execute_timeline_query()`, and `_TIMELINE_STATUS_CLASSES` dict
- `backend/app/views/router.py` — Added `"timeline"` to `_VALID_RENDERERS`, `elif renderer == "timeline":` blocks in `generic_view()` and `generic_view_data()`
- `backend/tests/test_timeline.py` — New test file with 15 tests (4 SPARQL construction + 11 query execution)
- `.gsd/milestones/M034/slices/S02/S02-PLAN.md` — Marked T01 done, added failure-path verification step
