# S01: Autocomplete Dismiss & Dropdown Escape

**Goal:** All autocomplete suggestion dropdowns (reference fields, tag fields, builder fields) dismiss on click-outside and Escape key. Tag/reference dropdowns near panel edges are fully visible — not clipped by overflow ancestors.
**Demo:** After this: Open edit form → click reference field → type → see suggestions → click outside → dismissed. Tag field near bottom of panel → type → dropdown visible outside overflow → Escape → dismissed.

## Tasks
- [x] **T01: Created dropdown-dismiss.js with document-level mousedown and Escape handlers that dismiss all open .suggestions-dropdown elements on click-outside or Escape key** — ## Description

All `.suggestions-dropdown` elements in the workspace (reference fields, tag fields, dashboard/workflow builder fields) lack dismiss-on-click-outside and dismiss-on-Escape behavior. Once a dropdown opens, it stays open until the user selects an item or clears the input. This traps focus and leaves stale suggestions visible.

**Current state:**
- Reference field autocomplete: htmx populates `#suggestions-{field_id}` div via `/browser/search`. Selecting calls `SemPKM.selectReference()` which clears innerHTML. No click-outside or Escape handling.
- Tag field autocomplete: htmx populates via `/browser/tag-suggestions`. Selecting is handled by inline onclick in `tag_suggestions.html` partial. No click-outside or Escape.
- Builder autocomplete: dashboard/workflow builders create `.suggestions-dropdown.builder-suggestions` divs. Selection clears them. No click-outside or Escape.
- The `.suggestions-dropdown` CSS uses `display: none` by default, `display: block` when `:not(:empty)`. Clearing innerHTML hides the dropdown.

**Approach:** Create a new `frontend/static/js/dropdown-dismiss.js` that registers two document-level event listeners:
1. `mousedown` on `document` — if click target is NOT inside a `.suggestions-dropdown` and NOT inside its associated input (`.reference-search`, `.tag-autocomplete-field input`, or builder input), clear all open `.suggestions-dropdown` elements.
2. `keydown` on `document` for Escape — if any `.suggestions-dropdown` is non-empty and visible, clear all of them and refocus the associated input.

Using `mousedown` instead of `click` ensures the dropdown dismisses before the click target receives focus.

## Steps

1. Create `frontend/static/js/dropdown-dismiss.js` with an IIFE containing:
   - A `_dismissAllDropdowns()` helper that finds all `.suggestions-dropdown:not(:empty)` and sets `innerHTML = ''`.
   - A `mousedown` document listener: if `e.target.closest('.suggestions-dropdown')` or `e.target.closest('.reference-field')` or `e.target.closest('.tag-autocomplete-field')` or `e.target.closest('.builder-suggestions')` — do nothing. Otherwise call `_dismissAllDropdowns()`.
   - A `keydown` document listener: if `e.key === 'Escape'`, call `_dismissAllDropdowns()`. Don't `preventDefault()` — let Escape bubble for other uses (modal close, etc.).
   - Export `SemPKM.dismissAllDropdowns = _dismissAllDropdowns` for programmatic use.

2. Add `<script src="{{ 'dropdown-dismiss.js' | asset_url }}"></script>` to `backend/app/templates/base.html` — insert after `workspace.js` and before `sempkm-shims.js`.

3. Verify that htmx-driven population still works: the htmx `hx-swap="innerHTML"` sets new content which triggers `:not(:empty)` display. The dismiss listeners only fire on user interaction (mousedown, keydown), not on htmx swaps.

4. Verify no interference with `SemPKM.selectReference()` — the onclick handler in suggestion items calls `selectReference()` which clears the dropdown. The mousedown listener fires first but the click target IS inside `.suggestions-dropdown`, so it's a no-op.

## Must-Haves

- [ ] `mousedown` listener dismisses dropdowns on click outside
- [ ] `Escape` key dismisses all open dropdowns
- [ ] Clicking a suggestion item still selects it (not dismissed before onclick fires)
- [ ] htmx-driven dropdown population still works after dismiss
- [ ] Works for reference fields, tag fields, and builder fields
- [ ] No duplicate listener registration on htmx partial reloads
  - Estimate: 30m
  - Files: frontend/static/js/dropdown-dismiss.js, backend/app/templates/base.html
  - Verify: Start the dev Docker stack. Open an object edit form with a reference field. Type to trigger suggestions. Click outside the dropdown — it should disappear. Type again to re-trigger. Press Escape — it should disappear. Select a suggestion by clicking — it should populate the hidden input. Repeat for a tag field. Verify: `rg 'dismissAllDropdowns' frontend/static/js/dropdown-dismiss.js` returns matches; `rg 'dropdown-dismiss' backend/app/templates/base.html` returns the script tag.
- [ ] **T02: Fix dropdown overflow clipping near panel edges with position:fixed repositioning** — ## Description

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
  - Estimate: 45m
  - Files: frontend/static/js/dropdown-dismiss.js, frontend/static/css/forms.css
  - Verify: Start the dev Docker stack. Open an object edit form with several fields so a reference or tag field is near the bottom of the panel. Type to trigger suggestions. The dropdown should appear above the input (flipped) or be fully visible — not clipped. Scroll the panel — dropdown should dismiss. Verify: `rg '_repositionDropdown' frontend/static/js/dropdown-dismiss.js` returns matches.
