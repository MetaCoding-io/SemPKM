# S02: Auto-Persona Rules Engine & Settings UI — UAT

## Preconditions

- Docker stack running (`docker compose up -d`)
- At least one Mental Model installed (basic-pkm)
- User logged in to workspace at `/browser/`
- At least two workspace personas exist (e.g., "Default" and "Work")
- S01 context API operational (`POST /api/context/update` returns 200)

---

## Test Case 1: Rule CRUD via API

**Objective:** Verify all 5 API endpoints work with proper auth.

1. `GET /api/context/rules` — expect 200, empty list `[]`
2. `POST /api/context/rules` with body:
   ```json
   {"name": "Office Work", "conditions": {"location_zone": "office", "time_period": "work_hours"}, "persona_id": "<work-persona-uuid>", "priority": 10, "enabled": true}
   ```
   — expect 201, response includes `id`, `name`, `conditions`, `persona_id`, `priority`, `enabled`, `created_at`
3. `GET /api/context/rules` — expect list with 1 rule
4. `PUT /api/context/rules/<rule_id>` with `{"name": "Office Work Updated"}` — expect 200, name updated
5. `DELETE /api/context/rules/<rule_id>` — expect 204
6. `GET /api/context/rules` — expect empty list again

**Auth enforcement:**
7. Repeat step 2 without auth header — expect 401
8. Repeat step 1 without auth header — expect 401

---

## Test Case 2: Rule Test Endpoint

**Objective:** Verify the test-against-current-context endpoint works without side effects.

1. Create a rule: `{"name": "Home Evening", "conditions": {"location_zone": "home", "time_period": "evening"}, "persona_id": "<persona-uuid>"}`
2. `POST /api/context/update` with `{"location_zone": "home", "time_period": "evening"}`
3. `POST /api/context/rules/test` — expect `{"matched": true, "persona_id": "<persona-uuid>", "rule_name": "Home Evening"}`
4. Verify the active persona did NOT change (test endpoint is read-only)
5. `POST /api/context/update` with `{"location_zone": "office"}` (break the match)
6. `POST /api/context/rules/test` — expect `{"matched": false}`
7. With no context stored: `POST /api/context/rules/test` — expect `{"matched": false}` (no error)

---

## Test Case 3: Priority Ordering

**Objective:** Verify first-match-wins by priority (descending).

1. Create rule A: `{"name": "Low Priority", "conditions": {"location_zone": "office"}, "persona_id": "<persona-A>", "priority": 1}`
2. Create rule B: `{"name": "High Priority", "conditions": {"location_zone": "office"}, "persona_id": "<persona-B>", "priority": 10}`
3. `POST /api/context/update` with `{"location_zone": "office"}`
4. **Expected:** Active persona switches to `<persona-B>` (higher priority wins)
5. Disable rule B: `PUT /api/context/rules/<B_id>` with `{"enabled": false}`
6. `POST /api/context/update` with `{"location_zone": "office"}`
7. **Expected:** Active persona switches to `<persona-A>` (B disabled, A now matches)

---

## Test Case 4: AND Condition Logic

**Objective:** Verify all non-null conditions must match.

1. Create rule: `{"name": "Full Match", "conditions": {"location_zone": "office", "time_period": "work_hours", "activity": "stationary"}, "persona_id": "<persona-uuid>", "priority": 5}`
2. `POST /api/context/update` with `{"location_zone": "office", "time_period": "work_hours"}` (missing `activity`)
3. **Expected:** Rule does NOT match (partial match fails AND logic)
4. `POST /api/context/update` with `{"location_zone": "office", "time_period": "work_hours", "activity": "stationary"}`
5. **Expected:** Rule matches, persona switches

---

## Test Case 5: Integration Hook — Context Update Triggers Persona Switch

**Objective:** Verify the full pipeline: context update → rule evaluation → persona activation → SSE event.

1. Open workspace in browser, open browser DevTools → Network → filter EventStream
2. Ensure the Default persona is active
3. Create rule: `{"name": "Office Rule", "conditions": {"location_zone": "office"}, "persona_id": "<work-persona-uuid>", "priority": 10}`
4. `POST /api/context/update` with `{"location_zone": "office"}`
5. **Expected in SSE stream:** `persona_switched` event with `{"persona_id": "<work-persona-uuid>", "persona_name": "Work", "rule_name": "auto"}`
6. **Expected in workspace:** Persona indicator shows "Work", toast notification appears: "Auto-switched to Work"
7. `POST /api/context/update` with `{"location_zone": "office"}` again (same context)
8. **Expected:** No duplicate persona_switched event (redundant switch skipped)

---

## Test Case 6: Settings UI — Full CRUD Flow

**Objective:** Verify the Settings UI renders and CRUD operations work through the browser.

1. Navigate to workspace → Settings (gear icon in user menu)
2. Click "Context Rules" in the sidebar
3. **Expected:** Panel loads with empty state ("No context rules configured yet")
4. Click "New Rule" section to expand it
5. Fill form: Name = "Home Night", Location = "home", Time = "evening", select a target persona, Priority = 5
6. Click "Create Rule"
7. **Expected:** Rule appears in the list with condition tags ("home", "evening"), persona badge, priority badge
8. Click "Edit" on the rule card → inline form appears with pre-filled values
9. Change name to "Home Night Updated" → click "Save"
10. **Expected:** Rule card updates with new name
11. Click "Test Against Current Context" button
12. **Expected:** If no context exists → "No match" red badge. If matching context exists → "Match: {persona}" green badge.
13. Click "Delete" on the rule card → confirm dialog → rule removed from list

---

## Test Case 7: Toast Notification and switchPersona

**Objective:** Verify the frontend auto-switch handler works visually.

1. Open workspace at `/browser/`
2. Ensure context-indicator.js SSE connection is active (check Network tab for EventStream)
3. Activate the "Default" persona manually
4. Create a rule matching some context → persona "Work"
5. POST a context update matching that rule
6. **Expected:** Toast appears at top-right of workspace: "Auto-switched to Work"
7. **Expected:** Toast auto-dismisses after ~3 seconds with fade-out animation
8. **Expected:** Workspace persona indicator (sidebar bottom) shows "Work"

---

## Test Case 8: No Rule Matches — No Side Effects

**Objective:** Verify that context updates with no matching rule don't affect persona.

1. Delete all rules
2. Activate "Work" persona manually
3. `POST /api/context/update` with `{"location_zone": "office"}`
4. **Expected:** Context update succeeds (200), active persona remains "Work", no `persona_switched` SSE event

---

## Test Case 9: Error Resilience

**Objective:** Verify rule evaluation failures don't break context updates.

1. This is validated by the unit test `test_rule_evaluation_error_does_not_break_update` in `test_rules_router.py`
2. Manual verification: if `app.state.persona_service` is misconfigured, `POST /api/context/update` should still return 200 with the updated context
3. Check backend logs for `context.rule_evaluation_failed` with traceback

---

## Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Empty conditions dict `{}` | Matches any context unconditionally (catch-all rule) |
| Null condition value `{"location_zone": null}` | Null values act as wildcards (skipped during evaluation) |
| Rule with `enabled: false` | Skipped during evaluation, still appears in list |
| Two rules with same priority | Tiebreaker: earlier `created_at` wins |
| POST context update with no matching rule | 200 response, no persona switch, `context.no_rule_matched` log |
| switchPersona undefined (workspace.js not loaded) | Console warning, toast still shows, no error |
| Malformed SSE data | Console error, no crash, event skipped |
| Create rule with empty name | 422 validation error |
| Update nonexistent rule | 404 |
| Delete nonexistent rule | 404 |
