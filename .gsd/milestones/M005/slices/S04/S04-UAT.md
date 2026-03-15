# S04: Tag Autocomplete — UAT

**Milestone:** M005
**Written:** 2026-03-14

## UAT Type

- UAT mode: live-runtime
- Why this mode is sufficient: Tag autocomplete requires a running SPARQL triplestore with real tag data and a browser to verify the interactive dropdown behavior

## Preconditions

- Docker stack running (`docker compose up -d`)
- At least one model installed with objects that have tags (Ideaverse import provides rich tag data)
- Browser open to SemPKM workspace at `http://localhost:3000`

## Smoke Test

Navigate to any object with tags → click Edit → type a partial tag value in the Tags field → a suggestion dropdown should appear below the input with matching tags and frequency counts.

## Test Cases

### 1. Empty query returns top tags

1. Open any object edit form that has a Tags or Keywords field
2. Click into the tag input field (focus triggers the autocomplete)
3. **Expected:** A dropdown appears showing the most frequently used tags ordered by count descending, each with a count badge (e.g., "philosophy (42)")

### 2. Prefix filtering narrows results

1. In the tag input field, type "gar"
2. Wait ~200ms for the debounce
3. **Expected:** Dropdown updates to show only tags containing "gar" (e.g., "garden/plant", "garden/soil") — tags not containing "gar" are filtered out

### 3. Case-insensitive matching

1. Type "GARDEN" in all caps in the tag field
2. **Expected:** Tags containing "garden" still appear (matching is case-insensitive)

### 4. Clicking suggestion fills input

1. Type a partial tag to get suggestions
2. Click on one of the suggestion items
3. **Expected:** The input value is set to the clicked tag value, the suggestion dropdown clears/hides

### 5. Free-entry of new tags

1. Type a completely new tag value that doesn't exist (e.g., "my-unique-new-tag-2026")
2. Note that no suggestions match
3. Save the form
4. **Expected:** The new tag is accepted and saved — the field doesn't require selecting from suggestions

### 6. Multi-value add creates working clone

1. In the edit form, find the Tags field with a "+ Add Tags" button
2. Click "+ Add Tags"
3. A new empty tag input appears
4. Type a partial tag in the new cloned input
5. **Expected:** The cloned input has working autocomplete — suggestions appear in a dropdown anchored to the new input, not the original

### 7. Save with autocompleted tags

1. Open an object's edit form
2. Use autocomplete to select an existing tag
3. Click "+ Add Tags" and type a new tag freely
4. Save the form
5. **Expected:** "Changes saved successfully" — both the autocompleted and new tags appear in the object's properties

### 8. Endpoint direct access

1. In browser or curl: `GET /browser/tag-suggestions?q=test`
2. **Expected:** HTML fragment containing `.suggestion-item` divs with tag names matching "test" and count badges

## Edge Cases

### Empty tag field after clearing

1. Type something in the tag field, then select all and delete it
2. **Expected:** Dropdown shows top tags by frequency again (same as empty/focus behavior)

### Special characters in query

1. Type `"hello` (with a double quote) in the tag field
2. **Expected:** No error — the quote is escaped before SPARQL query. Either matching results appear or an empty dropdown (no server error/500)

### Multiple tag fields on same form

1. Open an object that has both `bpkm:tags` and `schema:keywords` fields
2. Type in the first tag field → see suggestions
3. Type in the second tag field → see suggestions
4. **Expected:** Each field's dropdown is independent — selecting in one doesn't affect the other

### Rapid typing

1. Type quickly in the tag field without pausing
2. **Expected:** Suggestions update after the 200ms debounce from the final keystroke — no stale suggestions from mid-typing queries

## Failure Signals

- No dropdown appears when typing in tag fields → check that `_field.html` tag branch is rendering `.tag-autocomplete-field` wrapper
- Dropdown appears but shows all tags unfiltered → check that `htmx:configRequest` listener is active (it injects the `q` parameter)
- `select#explorer-mode-select` gets focus instead of tag input → CSS selector mismatch, likely not matching `.tag-autocomplete-field`
- Server returns 500 on tag-suggestions request → check SPARQL escaping of user input
- Cloned inputs don't show suggestions → `addMultiValue()` tag cloning branch may not be updating IDs correctly
- Suggestions appear at wrong position on page → `.tag-autocomplete-field` CSS positioning (position: relative/absolute) may be missing

## Requirements Proved By This UAT

- TAG-05 — Tag input fields in edit forms offer autocomplete with existing tag values from the graph (test cases 1-7 prove full flow)

## Not Proven By This UAT

- E2E test automation (deferred to S09)
- Performance with very large tag sets (>10K unique tags)
- Keyboard-only navigation of suggestions (not implemented — mouse/touch only)
- Accessibility of suggestion dropdown (screen reader compatibility)

## Notes for Tester

- The Ideaverse import provides rich hierarchical tag data (tags with `/` delimiters like "garden/plant", "architect/build") — use these for meaningful autocomplete testing
- The suggestion dropdown includes a frequency count badge — verify these counts look reasonable (not all showing 0 or unrealistically high numbers)
- The 200ms debounce means you need to pause briefly after typing to see updated suggestions — this is intentional to avoid hammering the server
- Tag autocomplete only appears for tag/keyword properties — regular text fields like `rdfs:label` or `schema:description` should NOT show autocomplete
