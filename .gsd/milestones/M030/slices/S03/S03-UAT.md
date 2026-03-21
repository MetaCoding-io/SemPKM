# S03: Lint Filter System (Suppress, Dismiss, Presets) — UAT

**Milestone:** M030
**Written:** 2026-03-21

## UAT Type

- UAT mode: mixed (artifact-driven + live-runtime)
- Why this mode is sufficient: Unit tests prove CRUD and filtering logic; Docker runtime proves UI interactions, htmx refresh patterns, and cross-component integration.

## Preconditions

- Docker stack running with current code: `cd /path/to/SemPKM && docker compose up -d`
- At least one Mental Model installed (basic-pkm) with seed data or user-created objects
- At least one object with lint warnings (e.g., a Note with empty body, or a Task with past due date)
- Authenticated user session (logged in via browser)

## Smoke Test

Navigate to workspace → open LINT tab in bottom panel → verify lint results are visible with suppress buttons (eye-off icons on hover). If results appear with action buttons, the filter system is wired correctly.

## Test Cases

### 1. Dismiss a specific lint result from per-object lint panel

1. Navigate to an object that has lint warnings (e.g., a Note with empty body)
2. Open the object to see the LINT section in the right pane
3. Locate a warning result item — it should have a small × button
4. Click the × dismiss button
5. **Expected:** The warning disappears from the list. A "1 dismissed" indicator appears below the results.
6. Reload the page
7. **Expected:** The dismissed result remains hidden (persisted in SQLite).

### 2. Verify violations are NOT dismissable

1. Navigate to an object that has a lint violation (structural SHACL failure)
2. Open the object to see the LINT section
3. Inspect the violation result items
4. **Expected:** Violations have NO dismiss (×) button. Only warnings and infos have dismiss buttons.

### 3. Suppress a rule type from lint dashboard

1. Open the LINT tab in the bottom panel (global lint dashboard)
2. Hover over a result row (e.g., "EmptyBody" rule)
3. Click the eye-off suppress button that appears on hover
4. **Expected:** All results for that rule type disappear from the dashboard. A "1 rule suppressed" badge appears in the sidebar.
5. Navigate to an object that previously had a result from that rule
6. **Expected:** The per-object lint panel also excludes results from the suppressed rule.

### 4. Save and apply a filter preset

1. In the lint dashboard, suppress one or more rules (per test 3)
2. In the sidebar, click "Save Current" (save icon) next to the preset dropdown
3. Enter a name when prompted (e.g., "Focus Mode")
4. **Expected:** The preset appears in the dropdown
5. Select "No preset" from the dropdown
6. **Expected:** All suppressions are cleared — full unfiltered results reappear
7. Select "Focus Mode" from the dropdown
8. **Expected:** The previously saved suppressions are restored — filtered results return

### 5. Manage filters from lint settings

1. In the lint dashboard sidebar, scroll down and click "Manage Filters"
2. **Expected:** A settings section appears with three collapsible sections: Suppressions (N), Dismissals (N), Presets (N)
3. Expand the Suppressions section
4. **Expected:** Each suppressed rule is listed with its name and a "Remove" button
5. Click "Remove" on a suppression
6. **Expected:** The item disappears, count decrements
7. Click "← Back to Dashboard"
8. **Expected:** The lint dashboard reappears with the removed rule's results now visible again

### 6. Clear all dismissals

1. Dismiss two or more lint results on different objects (per test 1)
2. Navigate to lint settings ("Manage Filters")
3. Expand the Dismissals section
4. **Expected:** Dismissed results listed, grouped by object
5. Click "Clear All Dismissals"
6. **Expected:** A confirmation dialog appears
7. Confirm
8. **Expected:** All dismissals are removed, section shows "No results dismissed."
9. Return to an object whose warning was previously dismissed
10. **Expected:** The previously dismissed warning reappears in the lint panel

### 7. Rename a preset

1. Create a preset (per test 4)
2. Navigate to lint settings ("Manage Filters")
3. Expand the Presets section
4. Click "Rename" on the preset
5. Enter a new name when prompted (e.g., "My Custom Filter")
6. **Expected:** The preset name updates in the list
7. Return to dashboard
8. **Expected:** The dropdown shows the new preset name

### 8. Delete a preset

1. Create a preset if none exists
2. Navigate to lint settings
3. Expand the Presets section
4. Click "Delete" on a preset
5. **Expected:** A confirmation dialog appears
6. Confirm
7. **Expected:** The preset disappears from the list
8. Return to dashboard
9. **Expected:** The dropdown no longer shows the deleted preset

## Edge Cases

### Empty state display

1. Clear all suppressions and dismissals
2. Navigate to lint settings
3. **Expected:** Suppressions section shows "No rules suppressed." Dismissals section shows "No results dismissed."

### Dismiss a result, then suppress its entire rule

1. Dismiss one specific result from an object
2. Suppress the entire rule type from the dashboard
3. Navigate to lint settings
4. **Expected:** The dismissal still appears in the Dismissals section (independent of suppression)
5. Clear the suppression
6. **Expected:** The individually dismissed result stays dismissed (dismissal is independent)

### API validation errors

1. Send `POST /api/lint/suppress` with empty `rule_source_iri`
2. **Expected:** HTTP 422 with error message "rule_source_iri must not be empty"
3. Send `DELETE /api/lint/suppress/not-a-uuid`
4. **Expected:** HTTP 422 (invalid UUID format)
5. Send `DELETE /api/lint/suppress/00000000-0000-0000-0000-000000000000`
6. **Expected:** HTTP 404 with "Suppression not found"

### Preset with same name

1. Create a preset named "Test"
2. Try to create another preset named "Test"
3. **Expected:** HTTP 422 error (duplicate name rejected)

## Failure Signals

- Dismiss button click produces no visible change → check browser DevTools for JS errors or failed fetch() calls
- Suppress button doesn't appear on hover → check CSS for `.lint-suppress-btn` rules and `opacity` transitions
- Preset dropdown empty after saving → check `GET /api/lint/presets` returns the saved preset
- "Manage Filters" link not visible → check template for the link element in dashboard sidebar
- Settings section shows wrong counts → check `GET /api/lint/suppressions` and `GET /api/lint/dismissals` response lengths
- Cleared dismissals don't reappear → check that the lint panel route is fetching fresh filter state (not cached)

## Requirements Proved By This UAT

- LINT-18 (suppress by rule type) — Tests 3, 5, 6 prove suppress/remove/clear cycle
- LINT-19 (dismiss individual results) — Tests 1, 2, 6 prove dismiss/remove/clear cycle
- LINT-20 (named filter presets) — Tests 4, 7, 8 prove create/apply/rename/delete cycle

## Not Proven By This UAT

- E2E Playwright automation — deferred to S04
- Performance under high result counts (>500 lint results with filters active)
- Multi-user isolation (two users see only their own filters) — proven by unit tests, not UAT
- Filter persistence across Docker container restarts — SQLite data persists via volume mount, but not explicitly tested here

## Notes for Tester

- The lint dashboard must have at least 2-3 different rule types producing results to meaningfully test suppression. Install multiple models (basic-pkm + CRM + zettelkasten) and create objects that trigger various rules.
- The "eye-off" suppress buttons only appear on hover — move your mouse over a result row to see them.
- Violations (red severity) intentionally lack dismiss buttons. If you only have violations and no warnings/infos, create a Note with an empty body or a Task with a past due date to generate dismissable results.
- All filter state is per-user and per-SQLite-database. If you reset the database, all filters are lost.
