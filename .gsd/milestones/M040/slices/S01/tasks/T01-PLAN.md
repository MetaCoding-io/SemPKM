---
estimated_steps: 8
estimated_files: 1
---

# T01: Add Calendar, Timeline, and Map View sections to chapter 7

**Slice:** S01 — M034 Feature Documentation
**Milestone:** M040

## Description

Expand chapter 7 (Browsing and Visualizing Data) with three new renderer sections: Calendar View, Timeline/Gantt View, and Map View. The Calendar section is the largest — it covers editable calendar interactions (drag-to-reschedule, resize-to-change-duration, click-to-create), the recurrence editor for recurring tasks, cross-view drag from kanban, and the composable planning pattern (side-by-side calendar + kanban). Timeline covers Frappe Gantt with dependency arrows, zoom levels, and drag-to-reschedule. Map covers Leaflet with marker clusters and geo field auto-detection.

## Steps

1. Read `frontend/static/js/calendar.js` to document all calendar interactions (event handlers for drag, resize, click-to-create, cross-view drop handling)
2. Read `frontend/static/js/recurrence-editor.js` to document the recurrence UI (presets, custom RRULE mode, EXDATE exclusions)
3. Read `backend/app/templates/browser/timeline_view.html` to document Gantt features (zoom levels, dependency arrows, drag callbacks)
4. Read `backend/app/templates/browser/map_view.html` to document map features (Leaflet setup, MarkerCluster, popup content)
5. Read `backend/app/views/service.py` for `_detect_date_fields()` and `_detect_geo_fields()` to document how types qualify for calendar/timeline/map views
6. Write Calendar View section following the existing chapter 7 pattern (Opening, Features, Interactions subsections), including Recurring Tasks, Cross-View Drag, and Composable Planning subsections
7. Write Timeline/Gantt View section (Opening, Zoom Levels, Dependencies, Rescheduling)
8. Write Map View section (Opening, Markers and Clusters, Geo Field Detection)

## Must-Haves

- [ ] Calendar View section with drag-to-reschedule, resize, click-to-create, recurrence editor, cross-view drag
- [ ] Timeline/Gantt View section with zoom, dependencies, drag-to-reschedule
- [ ] Map View section with clusters and geo field detection
- [ ] All sections follow the existing chapter 7 pattern (heading structure, description → opening → features → interactions)

## Verification

- `grep -c "^## " docs/guide/07-browsing-and-visualizing.md` returns >= 10
- `grep -q "Calendar View" docs/guide/07-browsing-and-visualizing.md`
- `grep -q "Timeline" docs/guide/07-browsing-and-visualizing.md`
- `grep -q "Map View" docs/guide/07-browsing-and-visualizing.md`
- `grep -q "recurrence\|recurring" docs/guide/07-browsing-and-visualizing.md` (case-insensitive)

## Inputs

- `docs/guide/07-browsing-and-visualizing.md` — existing chapter to extend
- `frontend/static/js/calendar.js` — calendar interaction implementation
- `frontend/static/js/recurrence-editor.js` — recurrence UI implementation
- `backend/app/templates/browser/timeline_view.html` — timeline template
- `backend/app/templates/browser/map_view.html` — map template
- `backend/app/views/service.py` — date/geo field detection logic

## Expected Output

- `docs/guide/07-browsing-and-visualizing.md` — extended with Calendar View, Timeline/Gantt View, and Map View sections
