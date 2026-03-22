---
estimated_steps: 5
estimated_files: 4
skills_used:
  - frontend-design
  - make-interfaces-feel-better
---

# T03: Build recurrence editor UI with presets and EXDATE picker

**Slice:** S04 — Recurring Tasks & RRULE Expansion
**Milestone:** M034

## Description

Create a recurrence editor UI that enhances the plain text input for `bpkm:recurrenceRule` in the SHACL form. The editor provides preset selections (Daily, Weekdays, Weekly, Biweekly, Monthly, Custom) and an EXDATE picker for exception dates. It produces valid RRULE strings from user selections.

The SHACL form renderer (`_field.html`) currently renders xsd:string properties as plain `<input type="text">`. We'll add a conditional check: when the property path contains `recurrenceRule`, render a special recurrence editor widget instead. Similarly for `exceptionDates`, render a date-list editor.

## Steps

1. **Create `frontend/static/js/recurrence-editor.js`** — A self-contained IIFE exporting `window.initRecurrenceEditor(inputEl)`:
   - Adds a small button (↻ icon) next to the input that opens a popover
   - Popover contains preset radio buttons:
     - Daily → `FREQ=DAILY`
     - Weekdays → `FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR`
     - Weekly → `FREQ=WEEKLY`
     - Biweekly → `FREQ=WEEKLY;INTERVAL=2`
     - Monthly → `FREQ=MONTHLY`
     - Custom → shows advanced controls
   - Custom mode shows:
     - Frequency dropdown (Daily, Weekly, Monthly, Yearly)
     - Interval number input (every N days/weeks/months/years)
     - Day-of-week checkboxes (for weekly frequency): MO, TU, WE, TH, FR, SA, SU
     - End condition: Never / After N occurrences (COUNT) / Until date (UNTIL)
   - On preset or custom confirm: writes RRULE string to the input's `value` and dispatches `input` event
   - On the visible input: show human-readable summary (e.g., "Every Friday" instead of raw RRULE)
   - Reverse-parse existing RRULE in input to pre-select the matching preset on open
   - Click-outside or Escape dismisses the popover
   - Position the popover below the input using `getBoundingClientRect()` + `document.body.appendChild()` (escape dockview stacking context per KNOWLEDGE.md)

2. **Create EXDATE editor** — Also in `recurrence-editor.js`, export `window.initExdateEditor(inputEl)`:
   - Renders a small "manage" button next to the `exceptionDates` input
   - Opens a popover with a list of dates (parsed from comma-separated value) and an "Add date" picker
   - Each date has a remove button (×)
   - On change, writes comma-separated ISO dates back to the input
   - Human-readable display: "3 exceptions" or "No exceptions"

3. **Create `backend/app/templates/browser/recurrence_editor.html`** — A Jinja2 partial (not currently needed — the editor JS creates its own DOM). Instead, this step is about wiring the JS to the form field.

4. **Edit `backend/app/templates/forms/_field.html`** — In the `{% else %}` default xsd:string block at the bottom, add a conditional after the `<input>` tag:
   ```jinja2
   {% if 'recurrenceRule' in prop.path %}
   <script>document.addEventListener('DOMContentLoaded', function() {
     var el = document.getElementById('{{ input_id }}');
     if (el && typeof initRecurrenceEditor === 'function') initRecurrenceEditor(el);
   });</script>
   {% elif 'exceptionDates' in prop.path %}
   <script>document.addEventListener('DOMContentLoaded', function() {
     var el = document.getElementById('{{ input_id }}');
     if (el && typeof initExdateEditor === 'function') initExdateEditor(el);
   });</script>
   {% endif %}
   ```
   Also add a `<script src="/static/js/recurrence-editor.js"></script>` include in the object_tab.html or ensure it's loaded when the form renders.

5. **Add CSS to `frontend/static/css/views.css`** — Styles for:
   - `.rrule-editor-btn` — small button next to input (flex-shrink: 0, icon sizing)
   - `.rrule-popover` — fixed-position popover on document.body (dark theme consistent with existing popovers)
   - `.rrule-presets` — radio button group styling
   - `.rrule-custom` — advanced controls section
   - `.rrule-day-checkboxes` — day-of-week checkbox grid (7 items, compact)
   - `.exdate-list` — date list with remove buttons
   - `.rrule-summary` — human-readable display overlaying the input value

## Must-Haves

- [ ] Recurrence editor popover opens from button next to recurrenceRule field
- [ ] All 6 presets produce correct RRULE strings
- [ ] Custom mode builds valid RRULE with frequency, interval, BYDAY, COUNT/UNTIL
- [ ] EXDATE editor manages comma-separated dates with add/remove
- [ ] Popovers escape dockview stacking context (appended to document.body)
- [ ] Click-outside and Escape dismiss popovers
- [ ] Human-readable summary displayed on inputs

## Verification

- Open a Task in edit mode → recurrenceRule field shows editor button
- Click button → popover opens with presets
- Select "Weekly" → input value becomes `FREQ=WEEKLY`, display shows "Every week"
- Switch to Custom → select Weekly, check FR → input becomes `FREQ=WEEKLY;BYDAY=FR`, display shows "Every Friday"
- Exception dates editor: add a date → input updates with ISO date string

## Inputs

- `backend/app/templates/forms/_field.html` — existing SHACL form field renderer (the `{% else %}` xsd:string block)
- `frontend/static/css/views.css` — existing view styles
- `backend/app/templates/browser/object_tab.html` — may need script include for recurrence-editor.js

## Expected Output

- `frontend/static/js/recurrence-editor.js` — recurrence editor and EXDATE editor modules
- `backend/app/templates/forms/_field.html` — conditional wiring for recurrenceRule/exceptionDates fields
- `frontend/static/css/views.css` — recurrence editor popover and control styles
- `backend/app/templates/browser/recurrence_editor.html` — Jinja2 partial (optional, may be JS-only)

## Observability Impact

- **Console signal:** `[recurrence-editor] loaded` logged when the JS module initializes — confirms the script loaded successfully in the browser.
- **Inspection:** Open any Task in edit mode → the recurrenceRule field should show the ↻ button. If the button is missing, the script either failed to load (check network tab for 404 on `recurrence-editor.js`) or the Jinja2 `prop.path` conditional didn't match (inspect the `<input>` element's surrounding HTML for the `<script>` tag).
- **RRULE validation:** Click the editor button → select a preset or build custom → the hidden input's `.value` should contain a valid RFC 5545 RRULE string. Check via browser devtools: `document.querySelector('[name*="recurrenceRule"]').value`.
- **Failure visibility:** If `initRecurrenceEditor` or `initExdateEditor` is called on an element that's already initialized (e.g., htmx re-swap), the `data-rrule-init`/`data-exdate-init` guard prevents double-initialization.
