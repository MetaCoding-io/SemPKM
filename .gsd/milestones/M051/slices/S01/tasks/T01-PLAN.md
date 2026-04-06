---
estimated_steps: 27
estimated_files: 2
skills_used: []
---

# T01: Add click-outside and Escape dismiss to all suggestion dropdowns

## Description

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

## Inputs

- ``frontend/static/css/forms.css` — existing dropdown CSS (`:not(:empty)` display rule)`
- ``backend/app/templates/forms/object_form.html` — existing autocomplete JS (selectReference, tag selection)`
- ``backend/app/templates/forms/_field.html` — htmx-driven dropdown targets`
- ``backend/app/templates/base.html` — script loading order`

## Expected Output

- ``frontend/static/js/dropdown-dismiss.js` — new file with document-level dismiss listeners`
- ``backend/app/templates/base.html` — updated with dropdown-dismiss.js script tag`

## Verification

Start the dev Docker stack. Open an object edit form with a reference field. Type to trigger suggestions. Click outside the dropdown — it should disappear. Type again to re-trigger. Press Escape — it should disappear. Select a suggestion by clicking — it should populate the hidden input. Repeat for a tag field. Verify: `rg 'dismissAllDropdowns' frontend/static/js/dropdown-dismiss.js` returns matches; `rg 'dropdown-dismiss' backend/app/templates/base.html` returns the script tag.
