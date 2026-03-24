# S02 UAT: Schedule Rules Engine + Daily Plan Generation

## Preconditions

- Media Scheduler app installed and running (S01 complete)
- At least one podcast feed subscribed with discovered episodes (MediaItems in triplestore)
- Access to Media Scheduler app via workspace sidebar Apps section

---

## Test Case 1: Tab Navigation

**Steps:**
1. Open the Media Scheduler app from the sidebar
2. Verify the tab bar shows three tabs: Today, Episodes, Rules
3. Click the "Rules" tab
4. Verify the rules view loads in the content area
5. Click the "Episodes" tab
6. Verify the episodes list (from S01) loads
7. Click the "Today" tab
8. Verify the today view loads with either a plan or an empty state prompt

**Expected:** Tab switching is instant, active tab gets visual highlight, content area swaps via htmx fragment load.

---

## Test Case 2: Create a Schedule Rule

**Steps:**
1. Navigate to the Rules tab
2. Click "Add Rule" button
3. Fill in rule name: "Commute Podcasts"
4. Set Activity condition to "commuting"
5. Set Time Period to "morning"
6. Leave Location Zone empty (wildcard)
7. Select action type: "Source Type"
8. Set action value: "podcast"
9. Set priority: 10
10. Click Save

**Expected:** Rule appears in the rules list with name "Commute Podcasts", priority badge showing "10", conditions summary showing "commuting / morning", and action summary showing "podcast (by type)".

---

## Test Case 3: Toggle Rule Enabled/Disabled

**Steps:**
1. In the Rules tab, find the "Commute Podcasts" rule
2. Click the toggle button to disable
3. Verify the rule card shows disabled state
4. Click the toggle button again to re-enable
5. Verify the rule card returns to enabled state

**Expected:** Toggle is immediate via htmx, rule list re-renders with updated state.

---

## Test Case 4: Delete a Rule

**Steps:**
1. Create a temporary rule (name: "Delete Me", any conditions)
2. Click the delete button on the "Delete Me" rule
3. Confirm the deletion dialog

**Expected:** Rule disappears from the list. Re-loading the Rules tab confirms it's gone.

---

## Test Case 5: Generate Daily Plan (Happy Path)

**Steps:**
1. Ensure at least one enabled rule exists that matches a broad context (e.g., wildcard conditions with source_type="podcast")
2. Navigate to the Today tab
3. Click "Generate Plan" button
4. Wait for the page to refresh

**Expected:** Today view shows an agenda with time-slotted entries:
- Each entry shows a time range (e.g., "08:00 – 08:30")
- Entry card shows media item title, source name, duration badge
- Status badges show "pending" for future entries
- Entry currently in the time window (if any) shows "active" with now-playing highlight

---

## Test Case 6: Generate Plan Replaces Previous Plan

**Steps:**
1. Generate a plan (Test Case 5)
2. Note the entries shown
3. Click "Generate Plan" again
4. Verify the plan regenerates

**Expected:** Old entries disappear (patched to "replaced" status, excluded from view). New entries appear with fresh time slots. No duplicate entries from the previous generation.

---

## Test Case 7: Empty Plan Generation

**Steps:**
1. Delete or disable all rules
2. Navigate to the Today tab
3. Click "Generate Plan"

**Expected:** Today view shows empty state message prompting the user to create rules. No error. The plan still gets created in RDF (with zero entries).

---

## Test Case 8: Rule with Time Range Condition

**Steps:**
1. Create a rule with:
   - Name: "Evening Music"
   - Check the "Time Range" checkbox
   - Start time: "18:00"
   - End time: "23:00"
   - Action type: "Source Type", value: "spotify"
   - Priority: 5
2. Save the rule
3. Verify the rule card shows the time range in conditions summary

**Expected:** Rule shows "18:00–23:00" in the conditions area. When plan generates with a context where `current_time` is within range, this rule matches. When outside range, it doesn't match.

---

## Test Case 9: Midnight-Wrapping Time Range

**Steps:**
1. Create a rule with time range start: "22:00", end: "06:00" (wraps past midnight)
2. Save and verify it appears in the rules list

**Expected:** Rule saves successfully. At evaluation time, 23:00 matches (within 22:00–06:00 wrapping range) and 12:00 does not match.

---

## Test Case 10: Rule Priority Ordering

**Steps:**
1. Create Rule A: priority 5, source_type "podcast"
2. Create Rule B: priority 10, source_type "youtube"
3. Both with wildcard conditions (match any context)
4. Generate a plan

**Expected:** Rule B (priority 10) matches first. Plan entries from Rule B's youtube items appear before Rule A's podcast items in the agenda (higher priority rules contribute items first).

---

## Test Case 11: Current Suggestion Endpoint

**Steps:**
1. Generate a plan with at least one entry
2. Navigate to `GET /app/media-scheduler/_fragments/current-suggestion`

**Expected:** Returns minimal HTML fragment showing the currently active or next-up media item. This is the endpoint S05 will use for the mobile widget.

---

## Edge Cases

### EC-1: Rule with all null conditions
Create a rule with no conditions set (all wildcard). It should match any context and always contribute items to the plan.

### EC-2: Rule with no matching items
Create a rule targeting source_type "spotify" when no Spotify sources exist. Plan generates successfully with zero entries from this rule — no error.

### EC-3: Disabled rules excluded
Disable all rules. Generate plan. Result should be an empty plan, not an error.

### EC-4: Duplicate item dedup across rules
Create two rules both targeting source_type "podcast". Generate plan. Each media item should appear at most once in the plan, even though two rules matched it.

### EC-5: Invalid rule form submission
Submit the rule form with an empty name. Expected: error message displayed in the UI, rule not saved.
