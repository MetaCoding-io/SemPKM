# S02: Calendar View Renderer — UAT

**Milestone:** M033
**Written:** 2026-03-21

## UAT Type

- UAT mode: mixed (artifact-driven + live-runtime)
- Why this mode is sufficient: Unit tests verify backend logic (date detection, query building, event transformation). Live runtime confirms frontend rendering, interaction, and visual correctness.

## Preconditions

- Docker stack running (`docker compose up -d` from project root)
- At least one Mental Model installed that has types with date properties (basic-pkm includes bpkm:Event with schema:startDate/schema:endDate and seed data)
- Frontend assets built (`cd frontend && npm ci && node build.js`)
- User logged in to the workspace at `/browser/`

## Smoke Test

Navigate to `/browser/views/generic/calendar`. A FullCalendar month grid should render. If bpkm:Event seed data exists, events should appear on the grid.

## Test Cases

### 1. Calendar renders from explorer sidebar

1. Navigate to `/browser/`
2. In the VIEWS section of the explorer sidebar, locate "Calendar View"
3. Click "Calendar View"
4. **Expected:** A new tab opens titled "Calendar View" with a FullCalendar month grid. Current month is displayed with navigation arrows and today button.

### 2. Events display on calendar grid

1. Open Calendar View (from explorer or `/browser/views/generic/calendar`)
2. Look at the month grid
3. **Expected:** bpkm:Event seed instances appear as colored event bars on their respective dates. Events have readable titles.

### 3. Click event opens object tab

1. Open Calendar View with visible events
2. Click on any event bar in the calendar
3. **Expected:** A new workspace tab opens showing the object detail page for that event. The tab title matches the event name.

### 4. Month/week/day view switching

1. Open Calendar View
2. Click the "week" button in the top-right toolbar area
3. **Expected:** Calendar switches to a week view with time slots on the left axis
4. Click the "day" button
5. **Expected:** Calendar switches to a single-day view with hourly time slots
6. Click the "month" button
7. **Expected:** Calendar returns to month grid view

### 5. Type filter pills narrow events

1. Open Calendar View
2. Note the type filter pills above the calendar (e.g., "Event", "Task", "Project")
3. Click a type pill to filter to a single type
4. **Expected:** Only events of that type remain on the calendar. Other type events disappear.
5. Click the same pill again to deselect
6. **Expected:** All events return

### 6. Dark mode rendering

1. Switch the app to dark mode (toggle in UI preferences)
2. Open Calendar View
3. **Expected:** Calendar renders with dark background, light text, no white flashes. Event colors are visible against the dark background. Navigation buttons and today button are readable.

### 7. Calendar data endpoint returns valid JSON

1. Open browser dev tools or use curl
2. Request `GET /browser/views/generic/calendar/data?type=urn:bpkm:Event` (use the actual bpkm:Event IRI)
3. **Expected:** JSON array returned. Each element has `id`, `title`, `start` (ISO date string), optional `end`, and `extendedProps` with `iri` and `type` fields.

### 8. Saved view support via toolbar

1. Open Calendar View
2. Click the "Save View" button in the view toolbar
3. **Expected:** Calendar view is saved. Appears in the Saved Views folder in the explorer.
4. Close the calendar tab
5. Click the saved view entry in explorer
6. **Expected:** Calendar view re-opens with the same state

## Edge Cases

### Empty type — no date properties

1. Open `/browser/views/generic/calendar` (no type filter)
2. If a type has no date properties (e.g., bpkm:Tag), select it via type pills
3. **Expected:** Calendar renders but shows no events. An informational message or empty grid is shown — no error, no 500.

### Nonexistent type returns empty array

1. Request `GET /browser/views/generic/calendar/data?type=urn:nonexistent:Type`
2. **Expected:** HTTP 200 with response body `[]` (empty JSON array), not a 500 error.

### CDN fallback when vendor bundle missing

1. Temporarily rename `frontend/dist/fullcalendar-*.min.js`
2. Navigate to calendar view
3. **Expected:** FullCalendar loads from jsdelivr CDN as fallback. Calendar still renders (with slight load delay).
4. Restore the vendor bundle file

### Canvas drag of calendar view

1. In the VIEWS explorer section, drag the "Calendar View" entry onto the workspace canvas
2. **Expected:** A calendar view panel is created via drag-drop with the correct label and URL.

## Failure Signals

- Calendar container shows blank white area instead of grid → FullCalendar JS failed to load (check console for `[calendar]` messages)
- Events missing from grid → check data endpoint response at `/browser/views/generic/calendar/data?type=<iri>`
- Click on event does nothing → `openTab` function not available (check if workspace.js loaded)
- Dark mode shows white background → `--fc-*` CSS overrides not applied (check views.css)
- Explorer sidebar missing Calendar entry → views_explorer.html not updated
- "Calendar View" tab opens but shows error → template rendering issue (check server logs for template errors)

## Requirements Proved By This UAT

- CAL-01 — Calendar renderer registered and selectable (tests 1, 8)
- CAL-02 — Date property auto-detection (tests 2, 7, edge case "empty type")
- CAL-03 — FullCalendar lazy-loaded with CDN fallback (test 2, edge case "CDN fallback")
- CAL-04 — Month/week/day view switching (test 4)
- CAL-05 — Click-to-open object tab (test 3)
- CAL-06 — Dark mode support (test 6)

## Not Proven By This UAT

- Drag-to-reschedule events (not implemented — deferred)
- Performance with large datasets (100+ events on a single day/week)
- Cross-browser FullCalendar rendering (relies on FullCalendar library's own compatibility)

## Notes for Tester

- The FullCalendar vendor bundle hash (`fullcalendar-b101204b.min.js`) will change if the package version changes. The manifest.json entry is the authoritative reference.
- Type filter pills are shared infrastructure from M031. If they look wrong, the issue is likely in the pills include template, not the calendar code.
- FullCalendar v6 self-injects its CSS, so there's no separate CSS bundle to verify — only the JS bundle needs to load.
