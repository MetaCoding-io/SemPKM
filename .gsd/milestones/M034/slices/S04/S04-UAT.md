# S04: Recurring Tasks & RRULE Expansion — UAT Script

## Preconditions

- Docker stack running (`docker compose up -d`)
- basic-pkm model installed (v2.2.0 with scheduledStart/scheduledEnd/recurrenceRule/exceptionDates)
- At least one Task object exists with `scheduledStart` set (from S01)
- Logged in as owner

---

## Test Case 1: RRULE Schema Properties Exist on Task Form

1. Open workspace → Create new Task (Ctrl+K → "Create Task")
2. In the SHACL form, scroll to the **Dates** field group
3. **Expected:** Fields appear in order: Due Date, Do Date, Scheduled Start, Scheduled End, Estimated Duration, **Recurrence Rule**, **Exception Dates**
4. Recurrence Rule field should show help text about RFC 5545 RRULE format
5. Exception Dates field should show help text about comma-separated ISO dates

## Test Case 2: Recurrence Editor Opens from Form Field

1. Click the **↻** button next to the Recurrence Rule text input
2. **Expected:** A popover appears with 6 preset radio buttons: Daily, Weekdays, Weekly, Biweekly, Monthly, Custom
3. Click **Weekly**
4. **Expected:** The text input value updates to `FREQ=WEEKLY` and a human-readable summary "Every week" appears overlaying the input
5. Click the ↻ button again
6. **Expected:** Popover opens with "Weekly" pre-selected (reverse-parse of existing value)

## Test Case 3: Custom Recurrence Rule Building

1. Open recurrence editor popover → select **Custom**
2. **Expected:** Additional controls appear: frequency dropdown, interval input, day-of-week checkboxes (when frequency is Weekly), end condition
3. Set frequency to Weekly, interval to 2, check Friday
4. **Expected:** Input value becomes `FREQ=WEEKLY;INTERVAL=2;BYDAY=FR`, summary shows "Every 2 weeks on Fri"
5. Set end condition to "After" → enter 10
6. **Expected:** Input value becomes `FREQ=WEEKLY;INTERVAL=2;BYDAY=FR;COUNT=10`, summary appends "10 times"
7. Click **Done** to close popover
8. **Expected:** Popover closes, value persists in input

## Test Case 4: EXDATE Editor

1. Click the **✕** button next to the Exception Dates text input
2. **Expected:** A popover appears with "No exception dates" message and a date picker
3. Pick a date (e.g., next Friday)
4. **Expected:** Date appears in the exception list with a remove (×) button. Input value updates to the ISO date string.
5. Add a second date
6. **Expected:** Two dates in list, input shows comma-separated ISO dates
7. Click the × on the first date
8. **Expected:** First date removed, input updates to show only the second date
9. Click outside the popover
10. **Expected:** Popover closes, values persist

## Test Case 5: Recurring Task Shows Virtual Calendar Instances

1. Create a new Task with:
   - Title: "Weekly Review UAT"
   - Scheduled Start: next Monday at 10:00
   - Scheduled End: next Monday at 11:00
   - Recurrence Rule: `FREQ=WEEKLY;COUNT=4` (use preset "Weekly" then switch to Custom and add COUNT=4)
2. Save the task
3. Open Calendar view (merged mode — shows both Events and Tasks)
4. Navigate to the week containing next Monday
5. **Expected:** See "Weekly Review UAT" on Monday at 10:00-11:00
6. Navigate forward through weeks
7. **Expected:** See the same task title on the next 3 consecutive Mondays (4 total instances)
8. **Expected:** Virtual instances have a dashed border and ↻ prefix distinguishing them from the master event

## Test Case 6: Clicking Virtual Event Opens Master Task

1. From the calendar in Test Case 5, click one of the virtual recurring instances (not the first/master one)
2. **Expected:** The master task "Weekly Review UAT" opens in an object tab — not a new nonexistent object
3. Verify the object tab shows the original title, recurrence rule, and all properties

## Test Case 7: EXDATE Excludes Virtual Instance

1. Open the master "Weekly Review UAT" task from Test Case 5
2. Switch to edit mode
3. In the Exception Dates field, add the date of the second Monday occurrence
4. Save
5. Open Calendar view and navigate through the 4 weeks
6. **Expected:** Only 3 instances visible (Mondays 1, 3, 4). The second Monday instance is gone.

## Test Case 8: Graceful Degradation on Malformed RRULE

1. Create a task with Scheduled Start set
2. Manually type a malformed RRULE in the Recurrence Rule field: `NOT_A_VALID_RRULE`
3. Save the task
4. Open Calendar view
5. **Expected:** The task appears once (at its scheduledStart) with NO virtual instances. No error in the UI.
6. Check server logs: **Expected:** Warning message containing the task IRI and "failed to parse RRULE"

## Test Case 9: Calendar Data Endpoint Returns Virtual Events

1. After creating the recurring task from Test Case 5, open browser DevTools Network tab
2. Open Calendar view
3. Find the calendar data request (URL containing `/data?merged=true` or similar)
4. Inspect the JSON response
5. **Expected:** Response contains events where some have `extendedProps.isVirtual: true` and `extendedProps.masterIri` set to the real task's IRI
6. **Expected:** Virtual events have synthetic IDs matching pattern `{iri}__recurrence__{isodate}`

## Test Case 10: Non-Recurring Tasks Unaffected

1. Open Calendar view with a mix of recurring and non-recurring tasks
2. **Expected:** Non-recurring tasks appear exactly once at their scheduled time with solid borders (no dashed border, no ↻ prefix)
3. Click a non-recurring task
4. **Expected:** Opens the task directly (no masterIri indirection)

---

## Edge Cases

- **Recurrence with no scheduledStart:** Task has `recurrenceRule` but no `scheduledStart` → should appear in calendar based on other date fields (dueDate) without virtual expansion
- **Monthly recurrence on 31st:** `FREQ=MONTHLY` starting Jan 31 → dateutil handles month-end gracefully (skips months without 31st)
- **Very long recurrence (no COUNT/UNTIL):** `FREQ=DAILY` with no end → capped at 52 instances within ±6 month window
- **Editor popover in narrow panel:** Popover uses `position:fixed` on `document.body` → should not clip inside narrow dockview panels
