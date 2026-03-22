---
id: T02
parent: S01
milestone: M034
provides:
  - execute_merged_calendar_query() method on ViewSpecService — merges Event + Task into one FullCalendar event list with sourceType annotation and color coding
  - POST /browser/views/calendar/patch endpoint — persists calendar drag/resize via object.patch command dispatch
  - Updated _detect_date_fields() to recognize scheduledStart/scheduledEnd as well-known date paths with highest priority
  - generic_view_data() merged=true parameter for multi-type calendar data
  - generic_view() calendar renderer falls through to merged mode when no type is selected
key_files:
  - backend/app/views/service.py
  - backend/app/views/router.py
  - backend/tests/test_calendar_editable.py
key_decisions:
  - Used type lookup query (SELECT ?type WHERE { GRAPH <urn:sempkm:current> { <iri> a ?type } }) in PATCH endpoint to determine correct predicates per object type rather than requiring the client to specify type
  - Added "scheduledstart" at highest priority in _START_DATE_PRIORITY and "scheduledend" with priority above "enddate" in end-field detection, so Task scheduling properties always win over generic date fields
patterns_established:
  - Calendar PATCH endpoint uses full command dispatch pipeline (dispatch → EventStore.commit → validation queue → webhooks) rather than direct triplestore writes, ensuring event log consistency
  - _CALENDAR_TYPE_COLORS dict maps type IRIs to hex colors — extensible for future calendar-visible types
observability_surfaces:
  - execute_merged_calendar_query logs per-type event count at INFO level
  - calendar_patch logs IRI, start, end, and event_iri at INFO on success; logs warning on type query failure; logs exception on dispatch failure
  - PATCH endpoint returns structured JSON errors with 400/500 status codes
  - GET /browser/views/generic/calendar/data?merged=true returns types_found array indicating which types produced events
duration: 25m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T02: Extend backend calendar data endpoint with merged Task+Event query and PATCH handler

**Add merged multi-type calendar query, PATCH endpoint for drag/resize persistence, and fix scheduledStart/scheduledEnd detection in date field heuristics**

## What Happened

Extended the calendar backend in three areas:

1. **Date field detection fix**: T01 discovered that `_detect_date_fields()` wouldn't auto-detect `scheduledStart`/`scheduledEnd` because `"startdate" not in "scheduledstart"` (no substring match). Added both terms to `_WELL_KNOWN_DATE_PATHS` and put `"scheduledstart"` at highest priority in `_START_DATE_PRIORITY`. Updated end-field detection to check `"scheduledend"` before `"enddate"` using a keyword priority loop.

2. **Merged calendar query**: Added `execute_merged_calendar_query()` to `ViewSpecService`. Iterates over `_CALENDAR_TYPE_COLORS` (Event → purple #8b5cf6, Task → green #10b981), detects date fields per type, runs `execute_calendar_query()` for each, and annotates results with `backgroundColor`, `borderColor`, and `extendedProps.sourceType`. Types without detectable date fields are silently skipped. Updated `generic_view_data()` to accept `merged=true` query parameter that invokes this method. Updated `generic_view()` calendar renderer to use merged mode when no type is selected (instead of showing an error).

3. **Calendar PATCH endpoint**: Added `POST /browser/views/calendar/patch` accepting `{iri, start?, end?}`. The endpoint queries the object's RDF type, looks up the correct predicates from `_CALENDAR_DATE_PREDICATES` (Event uses schema:startDate/endDate, Task uses bpkm:scheduledStart/scheduledEnd), then dispatches an `object.patch` command through the full pipeline (dispatch → EventStore.commit → validation → webhooks). Returns 400 for invalid IRI, missing dates, or unsupported type; 500 for triplestore/dispatch failures.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_calendar.py tests/test_calendar_editable.py -v` — 35/35 pass (22 existing + 13 new)
- `cd backend && .venv/bin/python -m pytest tests/test_calendar_editable.py -v -k "merged or patch"` — 9/9 pass
- Shapes integrity check: 3 scheduling properties confirmed on TaskShape

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v` | 0 | ✅ pass | 0.5s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_calendar_editable.py -v` | 0 | ✅ pass | 0.6s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_calendar.py tests/test_calendar_editable.py -v` | 0 | ✅ pass | 0.6s |
| 4 | `cd backend && .venv/bin/python -m pytest tests/test_calendar_editable.py -v -k "merged or patch"` | 0 | ✅ pass | 0.5s |
| 5 | Shapes integrity check (3 scheduling props) | 0 | ✅ pass | <1s |
| 6 | `python3 -c "import ast; ast.parse(open('backend/app/views/router.py').read())"` | 0 | ✅ pass | <1s |
| 7 | `python3 -c "import ast; ast.parse(open('backend/app/views/service.py').read())"` | 0 | ✅ pass | <1s |

## Diagnostics

- Merged query inspection: `GET /browser/views/generic/calendar/data?merged=true` → JSON with `events` array and `types_found` list
- PATCH endpoint test: `POST /browser/views/calendar/patch` with `{"iri": "...", "start": "...", "end": "..."}` → `{"ok": true, "event_iri": "..."}` on success
- Error inspection: PATCH returns `{"error": "..."}` with 400/500 status on failure
- Backend logs: search for `execute_merged_calendar_query` or `calendar_patch` in log output

## Deviations

- T01 flagged that `_detect_date_fields()` wouldn't recognize `scheduledStart`/`scheduledEnd` via existing substring matching. This was addressed as part of T02 by adding both to `_WELL_KNOWN_DATE_PATHS` and updating `_START_DATE_PRIORITY` — this is additional work not in the T02 plan but was explicitly called out as a T01 deviation that T02 must fix.
- The end-field detection was changed from a simple loop to a priority-keyword loop (`_END_KEYWORDS = ("scheduledend", "enddate")`) to match the start-field pattern. Previously it only checked `"enddate"`.
- Created `test_calendar_editable.py` in this task rather than waiting for T04, since the plan says "test file written in T04, but the endpoint code must be correct" and tests are verification, not an afterthought. T04 can extend this file with additional edge-case tests.

## Known Issues

- None

## Files Created/Modified

- `backend/app/views/service.py` — Added `scheduledstart`/`scheduledend` to `_WELL_KNOWN_DATE_PATHS`, `scheduledstart` to `_START_DATE_PRIORITY`, updated end-field detection with `_END_KEYWORDS`, added `_CALENDAR_TYPE_COLORS` dict and `execute_merged_calendar_query()` method
- `backend/app/views/router.py` — Added imports for TriplestoreClient/AsyncValidationQueue/WebhookService/_validate_iri, added `merged` query param to `generic_view_data()`, added `_CALENDAR_DATE_PREDICATES` map, `CalendarPatchRequest` model, and `POST /calendar/patch` endpoint, changed calendar no-type-selected to use merged mode
- `backend/tests/test_calendar_editable.py` — Created with 13 tests: 4 for scheduling date detection, 5 for merged query, 4 for PATCH endpoint validation
- `.gsd/milestones/M034/slices/S01/S01-PLAN.md` — Added failure-path verification check, marked T02 done
- `.gsd/milestones/M034/slices/S01/tasks/T02-PLAN.md` — Added Observability Impact section
