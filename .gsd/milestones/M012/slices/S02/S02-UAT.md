# S02: Body.Diff — Incremental Storage & Rendering — UAT

**Milestone:** M012
**Written:** 2026-03-17

## UAT Type

- UAT mode: mixed (artifact-driven for unit tests, live-runtime for browser verification)
- Why this mode is sufficient: Unit tests prove all code paths including backward compatibility and undo. Live runtime confirms the full user flow visually — edit body, see diff in event log.

## Preconditions

- Docker dev stack running (`docker compose up -d` from project root)
- At least one mental model installed (basic-pkm recommended)
- At least one object exists with a body (Note type has markdown body by default)
- User is logged in to the workspace

## Smoke Test

1. Open an existing Note object that has body content
2. Edit the body — change one paragraph
3. Save
4. Open the Event Log (sidebar or Ctrl+K → "Event Log")
5. Expand the most recent event
6. **Expected:** Event shows `body.diff` operation type with green/red diff highlighting showing only the changed paragraph

## Test Cases

### 1. Body.diff on existing body edit

1. Navigate to workspace, open a Note with existing body content
2. Click Edit mode
3. Change one line in the body text (e.g., add a sentence to the first paragraph)
4. Click Save
5. Open Event Log, expand the most recent event for this object
6. **Expected:** Event detail shows:
   - Operation type includes `body.diff`
   - Diff panel shows removed line(s) in red and added line(s) in green
   - Context lines (unchanged) appear without highlighting
   - The full body text is NOT shown — only the diff

### 2. Body.set on first body creation

1. Create a new Note object (+ button → select Note type → fill title)
2. Switch to Edit mode
3. Type body content: "This is the first body content."
4. Click Save
5. Open Event Log, expand the most recent event
6. **Expected:** Event detail shows:
   - Operation type includes `body.set` (NOT `body.diff`)
   - Body content displayed as full text (green lines showing the added content)

### 3. No-op save when body unchanged

1. Open an existing Note with body content
2. Switch to Edit mode
3. Do NOT change anything
4. Click Save
5. Check Event Log
6. **Expected:** No new event appears for this object — the save was a no-op

### 4. Backward compatibility — old body.set events still render

1. Open Event Log
2. Find an older event that was created before body.diff was implemented (any `body.set` event)
3. Expand the event detail
4. **Expected:** The diff panel still renders correctly — shows green/red diff computed on-the-fly from the before/after body values stored in the event

### 5. Multiple sequential edits produce multiple body.diff events

1. Open a Note with body content
2. Edit body — add a line at the end → Save
3. Edit body again — change the line you just added → Save
4. Open Event Log
5. **Expected:** Two separate `body.diff` events appear, each with its own diff showing only the respective change

### 6. Large body edit — multiple paragraph changes

1. Open a Note with multi-paragraph body
2. Edit body — change text in the first paragraph AND the last paragraph
3. Save
4. Open Event Log, expand the most recent event
5. **Expected:** Diff shows both changed sections with context lines between them. Only the changed lines are highlighted, not the entire body.

## Edge Cases

### Empty body replaced with content

1. Find or create an object that has had its body cleared (empty body)
2. Edit and type new body content → Save
3. **Expected:** Event shows `body.diff` (because empty string → non-empty string is still a change from an existing body value) with all-green lines

### Body cleared entirely

1. Open a Note with existing body content
2. Edit → select all → delete → Save (empty body)
3. **Expected:** Event shows `body.diff` with all-red lines (everything removed)

### Undo a body.diff event

1. Open Event Log
2. Find a `body.diff` event
3. Click the Undo button (if available in the event detail)
4. **Expected:** A new `body.set` event is created that restores the pre-diff body content. The object's body reverts to its previous state.

### Custom predicate body (non-default)

1. If any installed model uses a custom body predicate (not `sempkm:body`), edit that object's body
2. **Expected:** body.diff still works — the diff stores both the custom predicate and the diff text

## Failure Signals

- Event log shows `body.set` instead of `body.diff` when editing an existing body — save_body() branching logic broken
- Event log shows no diff panel for a `body.diff` event — template condition or _parse_stored_diff() broken
- Saving an unchanged body creates a new event — no-op detection broken
- Undo on a body.diff event produces garbled body text — _reverse_apply_diff() or diff normalization broken
- 500 error on save — SPARQL query for existing body may be failing
- Diff shows the entire body instead of just changes — diff computation may be falling through to body.set

## Requirements Proved By This UAT

- BDIFF-01 — Body changes store incremental diffs (test cases 1, 5, 6)
- BDIFF-02 — Event log renders body.diff events with highlighting (test cases 1, 5, 6)
- BDIFF-03 — Existing body.set events continue to display correctly (test case 4)

## Not Proven By This UAT

- Performance under high concurrency (multiple rapid saves) — not tested
- Diff rendering with very large bodies (>100KB) — not tested
- body.diff events in federation sync — not tested (federation consumes events but was not modified)

## Notes for Tester

- The diff rendering CSS is shared between body.set and body.diff — both use the same green/red highlighting styles. The difference is that body.diff reads stored diff text while body.set computes it on-the-fly.
- If the Docker stack was freshly started, all existing events will be body.set (pre-feature). You need to make at least one edit to see body.diff.
- The no-op detection (test case 3) compares raw text. Whitespace-only changes DO count as changes and produce a body.diff event.
- Undo for body.diff events produces a body.set (not body.diff) because undo is a full restoration, not an incremental change.
