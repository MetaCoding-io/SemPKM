---
id: T03
parent: S04
milestone: M034
provides:
  - window.initRecurrenceEditor(inputEl) — enhances text input with RRULE preset/custom editor popover
  - window.initExdateEditor(inputEl) — enhances text input with exception dates add/remove popover
  - Lazy-loaded JS wiring in _field.html for recurrenceRule and exceptionDates property paths
  - CSS styles for recurrence editor popovers, presets, day checkboxes, EXDATE list
key_files:
  - frontend/static/js/recurrence-editor.js
  - backend/app/templates/forms/_field.html
  - frontend/static/css/views.css
key_decisions:
  - Lazy-load recurrence-editor.js inline via script tag creation rather than adding to base.html — only loads when a form has recurrenceRule/exceptionDates fields
  - Skipped Jinja2 partial (recurrence_editor.html) — all DOM is built in JS, no server-side template needed
  - Popover appended to document.body with position:fixed to escape dockview stacking context (per KNOWLEDGE.md pattern)
patterns_established:
  - Guard against double-init on htmx re-swap using data-rrule-init/data-exdate-init attributes
  - Human-readable summary overlay: input text made transparent via CSS class, summary span positioned absolutely over it
  - Lazy script loading pattern for field-specific JS in _field.html (check if function exists → load script → call on load)
observability_surfaces:
  - Console log "[recurrence-editor] loaded" confirms script initialization
  - data-rrule-init="1" and data-exdate-init="1" attributes on initialized inputs for inspection
duration: 18m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T03: Build recurrence editor UI with presets and EXDATE picker

**Created recurrence-editor.js with RRULE preset/custom popover editor and EXDATE date list manager, wired into SHACL form via lazy-loaded conditional in _field.html**

## What Happened

Three files created/modified:

1. **`frontend/static/js/recurrence-editor.js`** — Self-contained IIFE exporting two functions:
   - `initRecurrenceEditor(inputEl)`: wraps the input in a flex row, adds a ↻ button that opens a popover on document.body. Popover has 6 preset radio buttons (Daily, Weekdays, Weekly, Biweekly, Monthly, Custom) that write the correct RRULE string to the input. Custom mode provides frequency dropdown, interval number, day-of-week checkboxes (weekly only), and end condition (never / after N / until date). Displays human-readable summary (e.g., "Every Friday") overlaying the raw RRULE value. Reverse-parses existing RRULE to pre-select the matching preset on open.
   - `initExdateEditor(inputEl)`: wraps the input, adds a ✕ button that opens a popover with the current exception dates list (parsed from comma-separated values), each with a remove button, plus a date picker to add new exceptions. Displays "N exceptions" summary.
   - Both editors: click-outside and Escape dismiss the popover; guard attributes prevent double-init on htmx re-swap.

2. **`backend/app/templates/forms/_field.html`** — Added conditional in the `{% else %}` xsd:string block: when `prop.path` contains `recurrenceRule` or `exceptionDates`, an inline `<script>` checks whether the editor function is already loaded and either calls it directly or lazy-loads `recurrence-editor.js` first.

3. **`frontend/static/css/views.css`** — Added 250 lines of recurrence editor styles: wrapper flex layout, editor trigger button, popover (fixed position, dark-theme tokens, shadow-elevated), preset radio group, custom controls section (frequency dropdown, interval input, day-of-week checkbox grid), end condition rows, popover footer with Clear/Done buttons, EXDATE list with remove buttons, add-date row, and human-readable summary overlay.

## Verification

- JS syntax validation: `node --check frontend/static/js/recurrence-editor.js` → passed
- RRULE building logic verified via Node.js extraction test (4/4 custom RRULE patterns correct)
- Human-readable summary function verified (7/7 translations correct): FREQ=DAILY→"Every day", FREQ=WEEKLY→"Every week", FREQ=WEEKLY;BYDAY=FR→"Every Friday", weekdays→"Every weekday", INTERVAL=2→"Every 2 weeks", MONTHLY→"Every month", COUNT=10→"Every day, 10 times"
- Backend RRULE expansion tests: 24/24 passed (confirming T02 code still works after template changes)
- Template conditional confirmed: `bpkm:recurrenceRule` matches `'recurrenceRule' in prop.path` and `bpkm:exceptionDates` matches `'exceptionDates' in prop.path`

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `node --check frontend/static/js/recurrence-editor.js` | 0 | ✅ pass | <1s |
| 2 | `node -e "...buildCustomRrule tests..."` (4 custom RRULE patterns) | 0 | ✅ pass | <1s |
| 3 | `node -e "...rruleToSummary tests..."` (7 summary translations) | 0 | ✅ pass | <1s |
| 4 | `cd backend && .venv/bin/python -m pytest tests/test_rrule_expansion.py -v` | 0 | ✅ pass (24/24) | 0.5s |

## Diagnostics

- Browser console: `[recurrence-editor] loaded` confirms script initialization
- Inspect any Task edit form → recurrenceRule field should show ↻ button; exceptionDates field should show ✕ button
- If buttons are missing: check network tab for 404 on `/static/js/recurrence-editor.js`, or inspect HTML around the `<input>` for the `<script>` tag (Jinja2 conditional may not have matched)
- Check input values after preset selection: `document.querySelector('[name*="recurrenceRule"]').value` should contain a valid RRULE string

## Deviations

- Skipped `backend/app/templates/browser/recurrence_editor.html` (Jinja2 partial) — the plan noted this was "not currently needed" since the editor JS creates its own DOM. Wiring is done via inline `<script>` tags in `_field.html` instead.
- Used lazy script loading (create `<script>` element on demand) instead of adding a static `<script src>` to `object_tab.html` — this avoids loading the editor JS on pages that don't have recurrence fields.

## Known Issues

- The editor is not yet exercised in the running app — T04 will wire virtual event rendering and write the E2E test that proves the full stack including this UI.
- The summary overlay uses absolute positioning which may not align perfectly if the form input has unusual padding in some themes — visual polish can be refined in T04 browser testing.

## Files Created/Modified

- `frontend/static/js/recurrence-editor.js` — New file: RRULE preset/custom editor and EXDATE date list editor (IIFE, ~340 lines)
- `backend/app/templates/forms/_field.html` — Added conditional script init for recurrenceRule and exceptionDates fields in the xsd:string block
- `frontend/static/css/views.css` — Added ~250 lines of recurrence editor CSS (popover, presets, custom controls, EXDATE list, summary overlay)
- `.gsd/milestones/M034/slices/S04/tasks/T03-PLAN.md` — Added Observability Impact section (pre-flight fix)
