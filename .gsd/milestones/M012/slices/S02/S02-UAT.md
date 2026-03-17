# S02: Body.Diff — Incremental Storage & Rendering — UAT

**Milestone:** M012
**Written:** 2026-03-17

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All behavior is in backend Python code (handler, save endpoint, event detail parsing, undo). 34 unit tests cover every code path. Full live-runtime browser verification is deferred to S04's E2E Playwright tests.

## Preconditions

- Docker stack running (`docker compose up -d`)
- At least one Mental Model installed (basic-pkm recommended)
- At least one object with a body exists (e.g., a Note with markdown content)
- User is logged in as owner

## Smoke Test

Edit an existing Note's body text (change one word), save. Open Event Log (Ctrl+J → Event Log tab). Expand the most recent event. The operation type should show `body.diff` and the detail should display green/red diff lines showing only the changed text, not the full body.

## Test Cases

### 1. Body.diff emitted for existing body edit

1. Open an existing Note that has body content
2. Switch to Edit mode (flip card)
3. Change one paragraph in the body text
4. Click Save
5. Open Event Log (Ctrl+J → Event Log tab)
6. Find the most recent event for this object
7. Expand the event detail
8. **Expected:** Operation type shows `body.diff`. Detail panel shows green/red diff lines highlighting only the changed paragraph. Unchanged paragraphs are NOT shown (or shown as gray context lines).

### 2. Body.set emitted for first body creation

1. Create a new object (e.g., a Note) — leave body empty initially
2. Switch to Edit mode
3. Type some markdown content in the body area
4. Click Save
5. Open Event Log
6. Find the most recent event for this object
7. Expand the event detail
8. **Expected:** Operation type shows `body.set` (NOT `body.diff`). Full body text displayed as green (addition) lines.

### 3. No-op save produces no event

1. Open an existing Note with body content
2. Switch to Edit mode
3. Do NOT change any text
4. Click Save
5. Open Event Log
6. Check events for this object — note the most recent event timestamp
7. **Expected:** No new event was created. The event log shows the same most recent event as before the save. The save completes successfully (no error) with a "Saved" response.

### 4. Backward compatibility — old body.set events still render

1. Open Event Log
2. Find an older event that was created before body.diff was implemented (any `body.set` event from prior usage)
3. Expand the event detail
4. **Expected:** The diff view renders correctly with green/red lines showing the body change. The on-the-fly diff computation still works for old events.

### 5. Undo of body.diff event

1. Edit an existing Note's body (change some text)
2. Save (creates a `body.diff` event)
3. Open Event Log, find the body.diff event
4. Click the Undo button on that event
5. **Expected:** A compensation event is created with type `body.set` that restores the original body text. The object's body returns to its pre-edit state.

### 6. Multiple sequential body edits

1. Open a Note with existing body content
2. Edit → change first paragraph → Save
3. Edit → change second paragraph → Save
4. Open Event Log
5. **Expected:** Two separate `body.diff` events, each showing only the paragraph that was changed in that edit. The diffs are independent — each reflects only that edit's delta.

## Edge Cases

### Large body with small change

1. Open a Note with a long body (10+ paragraphs)
2. Change one word in the middle paragraph
3. Save
4. Expand event detail
5. **Expected:** Diff shows only the changed line (plus 2-3 context lines). NOT the full 10+ paragraphs.

### Body replaced entirely

1. Open a Note with existing body content
2. Select all body text and replace with completely different content
3. Save
4. Expand event detail
5. **Expected:** `body.diff` event with all old lines shown as red (removed) and all new lines as green (added). This is correct behavior — the diff captures the full replacement as removals + additions.

### Empty body to content

1. Open a Note that currently has no body (body field is empty/null)
2. Add body content
3. Save
4. **Expected:** `body.set` event (not `body.diff`), since there was no prior body to diff against.

### Content to empty body

1. Open a Note with body content
2. Clear all body text (make it empty)
3. Save
4. **Expected:** `body.diff` event showing all previous content as red (removed) lines.

## Failure Signals

- Event log shows `body.set` for an edit to an existing body (save_body branching broken)
- Event log shows a new event after saving without changes (no-op detection broken)
- Diff panel is empty or shows raw unified diff text instead of formatted green/red lines (template rendering broken)
- Undo button produces an error or doesn't restore original content (build_compensation broken)
- 500 error on save (SPARQL query for existing body failing)
- Event detail shows no diff panel for body.diff events (template condition not matching)

## Requirements Proved By This UAT

- BDIFF-01 — Body changes store incremental diffs (test cases 1, 6, edge cases)
- BDIFF-02 — Event log renders body.diff events with add/deletion highlighting (test cases 1, 6)
- BDIFF-03 — Existing body.set events continue to display correctly (test case 4)

## Not Proven By This UAT

- Cross-browser rendering of diff highlighting (only tested in one browser)
- Performance under very large bodies (>100KB)
- Concurrent body edits by multiple users
- body.diff behavior when triplestore is under load

## Notes for Tester

- The diff rendering reuses the same CSS that already existed for body.set diffs (green/red line highlighting). The visual appearance should be identical — the only difference is where the diff comes from (stored vs computed on-the-fly).
- The "Undo" test (case 5) creates a `body.set` compensation event, not a `body.diff`. This is by design — undo restores the full old body, there's no incremental reverse to apply.
- If no old body.set events exist (fresh install), skip test case 4 — it requires pre-existing events from before this feature.
