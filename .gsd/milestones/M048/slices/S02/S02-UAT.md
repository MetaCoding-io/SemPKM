# S02: Diff-Based Save — No Phantom Events — UAT

**Milestone:** M048
**Written:** 2026-04-05T18:29:38.364Z

## UAT: Diff-Based Save — No Phantom Events

### Preconditions
- SemPKM running via Docker Compose with at least one Mental Model installed
- At least one object exists with multiple properties (including a datetime property)
- Browser dev tools open to Network tab and event log panel accessible

### Test 1: Single Property Change Creates Minimal Event
1. Open an existing object in the workspace editor
2. Note the current values of all properties
3. Change exactly one text property (e.g., a title or description field)
4. Click Save
5. Open the Event Log panel
6. **Expected:** The most recent event is `object.patch` and lists ONLY the changed property + `dcterms:modified`. No other properties appear in the event diff.

### Test 2: No-Op Save Creates No Event
1. Open an existing object in the workspace editor
2. Do not change any property values
3. Click Save
4. Open the Event Log panel
5. **Expected:** No new `object.patch` event was created. The most recent event timestamp is older than the save action.

### Test 3: DateTime Property Unchanged Across Formats
1. Open an object that has a datetime property (e.g., `dcterms:created` or a custom date field)
2. Note the datetime value displayed in the form (HTML datetime-local shows `YYYY-MM-DDTHH:MM`)
3. Without changing anything, click Save
4. **Expected:** No event created — the datetime normalization correctly identifies `2026-04-05T12:30:45.123+00:00` (triplestore) as equal to `2026-04-05T12:30` (form)

### Test 4: Multi-Valued Property Change
1. Open an object with a multi-valued property (e.g., tags or categories)
2. Add one new value to the multi-valued field
3. Click Save
4. **Expected:** Event log shows only that property changed, with the full new value set

### Test 5: Body Content No-Op Short-Circuit
1. Open an object that has body/markdown content
2. Observe the Network tab in browser dev tools
3. Do not change the body content, click Save
4. **Expected:** No POST request for body content is sent (the `_sempkmSavedContent` short-circuit prevents it). Only the properties form POST fires (which itself may be a no-op per Test 2).

### Test 6: Body Content Actual Change
1. Open an object with body/markdown content
2. Add a line of text to the body editor
3. Click Save
4. **Expected:** A POST request for body content IS sent. The body.set event appears in the event log.

### Test 7: Multiple Properties Changed
1. Open an object and change 2-3 different properties
2. Click Save
3. **Expected:** The event log shows an `object.patch` with exactly those 2-3 properties + `dcterms:modified`. Properties that were not changed do NOT appear.

### Edge Cases

### Test 8: New Property Added to Object
1. If the object's shape has an optional property that currently has no value
2. Enter a value for that property
3. Click Save
4. **Expected:** Event shows the new property as added. dcterms:modified is present.

### Test 9: Property Value Cleared
1. Open an object with a filled optional property
2. Clear the property value (empty the field)
3. Click Save
4. **Expected:** Event shows the property as changed (deletion). dcterms:modified is present.

### Unit Test Verification
1. Run: `cd backend && .venv/bin/python -m pytest tests/test_save_diff.py -v`
2. **Expected:** 22 tests pass covering _normalize_value_for_compare (10 tests) and _compute_changed_properties (10 tests) and dcterms:modified integration (2 tests)
