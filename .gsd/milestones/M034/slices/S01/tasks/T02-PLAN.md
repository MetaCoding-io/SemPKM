---
estimated_steps: 5
estimated_files: 3
skills_used: []
---

# T02: Extend backend calendar data endpoint with merged Task+Event query and PATCH handler

**Slice:** S01 — Editable Calendar & Task Time-Blocking
**Milestone:** M034

## Description

The calendar data endpoint (`/browser/views/generic/calendar/data`) currently queries a single type. This task extends the backend to:

1. Support a merged query that combines Events (via schema:startDate) and Tasks (via bpkm:scheduledStart) into one FullCalendar event list, annotating each with `sourceType: "task"|"event"` and priority-based `backgroundColor`.
2. Add a POST endpoint for calendar drag/resize that persists new dates via `object.patch`.

The merged query approach: when `merged=true` is passed (or when no type filter is set), detect date fields for both `bpkm:Event` and `bpkm:Task`, run `execute_calendar_query()` for each, merge results, and annotate with sourceType/colors.

The PATCH endpoint: accepts JSON `{iri, scheduledStart?, scheduledEnd?}`, validates the IRI, and dispatches an `object.patch` command with the changed properties.

Key namespace references:
- `bpkm:Event` = `urn:sempkm:model:basic-pkm:Event`
- `bpkm:Task` = `urn:sempkm:model:basic-pkm:Task`
- `bpkm:scheduledStart` = `urn:sempkm:model:basic-pkm:scheduledStart`
- `bpkm:scheduledEnd` = `urn:sempkm:model:basic-pkm:scheduledEnd`
- `schema:startDate` = `https://schema.org/startDate`
- `schema:endDate` = `https://schema.org/endDate`

## Steps

1. In `backend/app/views/service.py`, add `execute_merged_calendar_query()` method to `ViewSpecService`:
   - Define `_CALENDAR_TYPES` list: `[("urn:sempkm:model:basic-pkm:Event", "#8b5cf6"), ("urn:sempkm:model:basic-pkm:Task", "#10b981")]` (purple for events, green for tasks — matches manifest icon colors).
   - For each type: call `_detect_date_fields()`, skip if None. Call `execute_calendar_query()`. Annotate each event dict with `extendedProps.sourceType` ("event" or "task") and `backgroundColor`/`borderColor` with the type color.
   - Merge all event lists. Return `{"events": [...], "types_found": [...]}`.
   - Log the count per type.

2. In `backend/app/views/router.py`, modify `generic_view_data()`:
   - Add `merged: str = Query(default="")` parameter.
   - When `renderer == "calendar"` and `merged == "true"`: call `execute_merged_calendar_query()` instead of the single-type path. Still respect `scope_filter_text` by passing it through.
   - The existing single-type path remains untouched for when a specific type is selected.

3. In `backend/app/views/router.py`, add a new POST endpoint:
   ```python
   @router.post("/calendar/patch")
   async def calendar_patch(request: Request, user: User = Depends(get_current_user)):
   ```
   - Parse JSON body: `{iri: str, scheduledStart?: str, scheduledEnd?: str}`.
   - Validate `iri` with `_validate_iri()`.
   - Build `object.patch` properties dict from non-null fields, using full predicate IRIs (`urn:sempkm:model:basic-pkm:scheduledStart`, etc.) — or detect which predicates to use based on the object's type (Event uses schema:startDate/endDate, Task uses bpkm:scheduledStart/scheduledEnd).
   - Dispatch via `execute_command()` helper (import from `app.commands.router`).
   - Return `{"ok": true}` on success, 400/500 on failure.

4. In `generic_view()` (the HTML view handler), update the `calendar_data_url` construction for the calendar renderer: when `type_iri` is None/empty, set `merged=true` in the data URL so the frontend gets all types merged.

5. Add `scope_filter` parameter support to `execute_merged_calendar_query()` — pass it through to each `execute_calendar_query()` call.

## Must-Haves

- [ ] `execute_merged_calendar_query()` returns events from both Event and Task types with `sourceType` annotation
- [ ] `generic_view_data()` with `merged=true` calls the merged query
- [ ] POST `/browser/views/calendar/patch` persists date changes via object.patch
- [ ] PATCH endpoint validates IRI and returns 400 for invalid input
- [ ] Existing single-type calendar query path is unbroken

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_calendar_editable.py -v -k "merged or patch"` — relevant tests pass (test file written in T04, but the endpoint code must be correct)
- `cd backend && .venv/bin/python -m pytest tests/test_calendar.py -v` — existing calendar tests still pass (no regression)

## Inputs

- `backend/app/views/service.py` — existing ViewSpecService with `execute_calendar_query()`, `_detect_date_fields()`
- `backend/app/views/router.py` — existing `generic_view_data()` and `generic_view()` functions
- `backend/app/commands/router.py` — existing command dispatch (for the PATCH handler to call)

## Expected Output

- `backend/app/views/service.py` — new `execute_merged_calendar_query()` method
- `backend/app/views/router.py` — extended `generic_view_data()` + new `calendar_patch()` endpoint
