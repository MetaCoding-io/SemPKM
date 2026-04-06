# S01: Autocomplete Dismiss & Dropdown Escape — UAT

**Milestone:** M051
**Written:** 2026-04-06T01:03:11.688Z

## UAT: Autocomplete Dismiss & Dropdown Escape

### Preconditions
- Dev Docker stack running (`docker compose up -d`)
- At least one Mental Model installed with types that have reference and tag fields (e.g., basic-pkm with Task type)
- Browser open to workspace at `http://localhost:3901/browser/`

### Test 1: Click-outside dismiss on reference field
1. Open any object in edit mode that has a reference field (e.g., a Task with a "relatedTo" field)
2. Click the reference field input and type 2-3 characters to trigger suggestion dropdown
3. **Expected:** `.suggestions-dropdown` appears with matching results
4. Click anywhere outside the dropdown and the input field (e.g., on the form title or blank space)
5. **Expected:** Dropdown disappears immediately. No stale suggestions remain visible.
6. Click the reference field again and type to re-trigger suggestions
7. **Expected:** Dropdown reappears normally — dismiss did not break htmx population.

### Test 2: Click-outside dismiss on tag field
1. On the same or different object, find a tag field (e.g., tags/keywords)
2. Type in the tag input to trigger tag suggestion dropdown
3. **Expected:** Tag suggestions appear
4. Click outside the tag field wrapper
5. **Expected:** Dropdown disappears

### Test 3: Escape key dismiss
1. Trigger a reference field suggestion dropdown (type in reference input)
2. Press Escape
3. **Expected:** Dropdown disappears. Focus remains on the input field (user can continue typing).
4. Press Escape again
5. **Expected:** No error. If a modal is behind it, the modal's Escape handler fires normally — Escape was not swallowed by the dropdown dismiss.

### Test 4: Suggestion selection still works
1. Trigger reference field suggestions by typing
2. Click on one of the suggestion items in the dropdown
3. **Expected:** The suggestion is selected — the hidden input gets the IRI value, the visible input shows the label, and the dropdown clears. The mousedown listener did NOT dismiss the dropdown before the selection click could fire.

### Test 5: Dropdown flips above when near panel bottom
1. Open an object edit form with multiple fields, ensuring a reference or tag field is near the bottom of the scrollable panel area
2. Scroll down so the field is near the bottom edge of the viewport
3. Type to trigger the suggestion dropdown
4. **Expected:** The dropdown appears ABOVE the input field (flipped), fully visible — not clipped by the panel's overflow boundary.
5. The dropdown width matches the input field width.

### Test 6: Scroll dismisses fixed dropdown
1. Trigger a suggestion dropdown on any field
2. Scroll the panel (mouse wheel or trackpad)
3. **Expected:** Dropdown disappears immediately. No orphaned fixed-position dropdown floating in space.

### Test 7: Dismiss resets inline styles
1. Trigger a dropdown near the bottom (so it flips above / gets position:fixed)
2. Dismiss it (click outside, Escape, or scroll)
3. Re-trigger the same dropdown
4. **Expected:** Dropdown repositions correctly based on current input position — no stale `position:fixed` or `top`/`bottom` values from the previous open.

### Edge Cases
- **Multiple dropdowns:** Open two reference fields in quick succession (tab between them fast). Only the most recently populated dropdown should be visible — the dismiss mechanism clears all others.
- **Window resize:** Trigger a dropdown, then resize the browser window. Dropdown should dismiss on resize.
- **Builder dropdowns:** Open a dashboard or workflow builder. Trigger an autocomplete in the builder. Builder dropdowns should NOT be repositioned (they skip the fixed-position logic) but SHOULD dismiss on click-outside and Escape.
