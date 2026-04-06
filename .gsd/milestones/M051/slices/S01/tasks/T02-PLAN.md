---
estimated_steps: 36
estimated_files: 2
skills_used: []
---

# T02: Fix dropdown overflow clipping near panel edges with position:fixed repositioning

## Description

When a reference or tag field is near the bottom of a scrollable dockview panel, the `.suggestions-dropdown` renders below the input via `position: absolute; top: 100%` — but gets clipped by the panel's `overflow-y: auto`. The user can't see or interact with the suggestions.

**Current CSS state:**
- `.suggestions-dropdown` in `forms.css`: `position: absolute; top: 100%; z-index: 9999; max-height: 200px`
- `.reference-field` and `.tag-autocomplete-field`: `position: relative` (dropdown anchor)
- Dockview panels: scrollable content area with `overflow-y: auto`
- Comment in `workspace.js` line 738 says "position:fixed already escapes overflow:hidden containers" — but the actual CSS uses `position: absolute`, not `position: fixed`

**Approach:** Add a repositioning function that runs when a dropdown becomes non-empty. Use a `MutationObserver` on `.suggestions-dropdown` elements to detect when content is inserted (htmx swap). When content appears:
1. Get the input element's `getBoundingClientRect()` for screen position
2. Measure available space below and above the input within the viewport
3. If the dropdown would be clipped below, flip it above the input
4. Apply `position: fixed` + computed `top`/`left`/`width` from the input's rect
5. On dismiss (innerHTML cleared), reset to `position: absolute` defaults

This follows the same pattern as dockview popover escape (KNOWLEDGE: "Popovers inside dockview panels must escape stacking context via document.body"), but instead of appending to `document.body`, we switch to `position: fixed` which also escapes overflow containers without moving the element in the DOM. This is simpler and avoids breaking htmx targeting (htmx expects the dropdown div at its original location in the DOM).

## Steps

1. In `frontend/static/js/dropdown-dismiss.js`, add a `_repositionDropdown(dropdown)` function:
   - Find the parent input: `dropdown.closest('.reference-field')?.querySelector('.reference-search')` or `dropdown.closest('.tag-autocomplete-field')?.querySelector('input')`
   - If no parent input found (builder context), skip repositioning (builders render in modal-like containers that don't clip)
   - Get `inputRect = input.getBoundingClientRect()`
   - Compute `spaceBelow = window.innerHeight - inputRect.bottom`
   - If `spaceBelow < 220` (dropdown max-height 200px + 20px margin), position above: `dropdown.style.bottom = (window.innerHeight - inputRect.top) + 'px'; dropdown.style.top = 'auto'`
   - Else position below: `dropdown.style.top = inputRect.bottom + 'px'; dropdown.style.bottom = 'auto'`
   - Set `dropdown.style.position = 'fixed'`; `dropdown.style.left = inputRect.left + 'px'`; `dropdown.style.width = inputRect.width + 'px'`

2. Add a `_resetDropdownPosition(dropdown)` function that removes the inline styles: `dropdown.style.cssText = ''`

3. Set up a `MutationObserver` that watches for `childList` changes on all `.suggestions-dropdown` elements. When children are added (dropdown populated), call `_repositionDropdown()`. When children are removed or innerHTML cleared, call `_resetDropdownPosition()`.

4. Since dropdowns are created dynamically (htmx swaps, multi-value clones), use a delegated approach: observe `document.body` with `{ childList: true, subtree: true }` but filter mutations to only act on `.suggestions-dropdown` elements. Alternatively, use the existing dismiss mousedown listener to also handle repositioning on the htmx `htmx:afterSwap` event.

5. Update `_dismissAllDropdowns()` in the same file to also call `_resetDropdownPosition()` on each cleared dropdown.

6. Update `frontend/static/css/forms.css` — ensure `.suggestions-dropdown` has a `z-index` high enough for fixed positioning (9999 is already set, good). No other CSS changes needed since the JS overrides position inline.

## Must-Haves

- [ ] Dropdown near bottom of scrollable panel flips above the input instead of being clipped
- [ ] Dropdown in normal position (plenty of space below) renders below as before
- [ ] Fixed positioning includes correct left/width matching the input field
- [ ] Dismiss resets position to defaults (no stale inline styles)
- [ ] Works for both reference fields and tag fields
- [ ] No regression on builder dropdowns (they should skip repositioning)
- [ ] Scroll/resize while dropdown is open does not leave dropdown orphaned (dismiss on scroll)

## Inputs

- ``frontend/static/js/dropdown-dismiss.js` — dismiss logic from T01`
- ``frontend/static/css/forms.css` — dropdown CSS positioning rules`
- ``backend/app/templates/forms/_field.html` — dropdown HTML structure`

## Expected Output

- ``frontend/static/js/dropdown-dismiss.js` — updated with repositioning logic`
- ``frontend/static/css/forms.css` — minor updates if needed for fixed-position z-index`

## Verification

Start the dev Docker stack. Open an object edit form with several fields so a reference or tag field is near the bottom of the panel. Type to trigger suggestions. The dropdown should appear above the input (flipped) or be fully visible — not clipped. Scroll the panel — dropdown should dismiss. Verify: `rg '_repositionDropdown' frontend/static/js/dropdown-dismiss.js` returns matches.
