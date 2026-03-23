---
id: T01
parent: S01
milestone: M040
provides:
  - Calendar View section in chapter 7 with drag-to-reschedule, resize, click-to-create, recurrence editor, cross-view drag, composable planning
  - Timeline/Gantt View section in chapter 7 with zoom levels, dependencies, drag-to-reschedule
  - Map View section in chapter 7 with marker clusters, geo field detection
key_files:
  - docs/guide/07-browsing-and-visualizing.md
key_decisions: []
patterns_established:
  - Documentation sections follow Opening → How Types Qualify → Features → Interactions structure
observability_surfaces:
  - none
duration: 25m
verification_result: passed
completed_at: 2026-03-22T23:56:00-04:00
blocker_discovered: false
---

# T01: Add Calendar, Timeline, and Map View sections to chapter 7

**Added Calendar View, Timeline/Gantt View, and Map View sections to chapter 7 with accurate feature documentation derived from source code.**

## What Happened

Read all four implementation files (`calendar.js`, `recurrence-editor.js`, `timeline_view.html`, `map_view.html`) and the `_detect_date_fields()` / `_detect_geo_fields()` methods in `ViewSpecService` to document features accurately rather than inventing descriptions.

Added three new `##` sections to chapter 7, growing it from 295 to 478 lines:

1. **Calendar View** — the largest section, covering: type qualification via date field detection heuristics, calendar modes (month/week/day), color coding, drag-to-reschedule with optimistic rollback, resize-to-change-duration, click-to-create with date pre-fill, recurring tasks and the recurrence editor (RRULE presets, custom mode with frequency/interval/day-selection/end-conditions, EXDATE exception dates), cross-view drag from kanban/explorer, composable planning pattern (calendar + kanban side by side), and scope synchronization between sibling views.

2. **Timeline / Gantt View** — covering: shared date field detection, zoom levels (Quarter Day through Year), task bars with click-to-open, dependency arrows, drag-to-reschedule via the calendar patch endpoint, and recurring task instances.

3. **Map View** — covering: two-pass geo field detection (well-known IRI match then local-name heuristic), OpenStreetMap tiles, marker clusters with chunked loading, marker popups with click-to-open, and responsive resizing via ResizeObserver.

Also updated the chapter intro paragraph to mention Calendar, Timeline/Gantt, and Map views alongside the existing renderers.

## Verification

All five task-level checks pass. Slice-level checks for chapter 7 also pass (line count 478 ≥ 450 target, "Calendar View|Timeline.*View|Map View" count 21 ≥ 3).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -c "^## " docs/guide/07-browsing-and-visualizing.md` → 13 | 0 | ✅ pass (≥ 10) | <1s |
| 2 | `grep -q "Calendar View" docs/guide/07-browsing-and-visualizing.md` | 0 | ✅ pass | <1s |
| 3 | `grep -q "Timeline" docs/guide/07-browsing-and-visualizing.md` | 0 | ✅ pass | <1s |
| 4 | `grep -q "Map View" docs/guide/07-browsing-and-visualizing.md` | 0 | ✅ pass | <1s |
| 5 | `grep -qi "recurrence\|recurring" docs/guide/07-browsing-and-visualizing.md` | 0 | ✅ pass | <1s |
| 6 | `wc -l docs/guide/07-browsing-and-visualizing.md` → 478 | 0 | ✅ pass (≥ 450) | <1s |
| 7 | `grep -c "Calendar View\|Timeline.*View\|Map View" docs/guide/07-browsing-and-visualizing.md` → 21 | 0 | ✅ pass (≥ 3) | <1s |

## Diagnostics

This is a documentation-only task. No runtime signals, logs, or failure state to inspect. Verify content accuracy by comparing section text against the source files listed in the Inputs section of the task plan.

## Deviations

None. Followed the task plan steps 1–8 as written.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/07-browsing-and-visualizing.md` — Extended with Calendar View, Timeline/Gantt View, and Map View sections (295 → 478 lines)
