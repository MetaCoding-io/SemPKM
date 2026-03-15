---
estimated_steps: 4
estimated_files: 3
---

# T02: Wire tag autocomplete into edit forms and verify in browser

**Slice:** S04 — Tag Autocomplete
**Milestone:** M005

## Description

Add a tag-property branch in the `_render_input` macro in `_field.html` that renders autocomplete-enabled inputs for tag fields. Wrap the input in a `.tag-autocomplete-field` container with `hx-get="/browser/tag-suggestions"`, a suggestion dropdown div, and proper htmx trigger attributes. Update `addMultiValue()` to handle cloning of tag autocomplete fields (same pattern as reference field cloning). Add CSS rules for the tag autocomplete wrapper. Verify end-to-end in the browser.

## Steps

1. Add tag property branch in `_render_input` macro in `backend/app/templates/forms/_field.html`:
   - Insert new `{% elif 'tags' in prop.path or 'keywords' in prop.path %}` branch BEFORE the default `{% else %}` text input
   - Render a `.tag-autocomplete-field` wrapper div (follows `.reference-field` positioning pattern)
   - Inside: text input with `name="{{ input_name }}"`, `hx-get="/browser/tag-suggestions"`, `hx-trigger="input changed delay:200ms, focus"`, `hx-target="#tag-suggestions-{{ field_id }}{{ '-' ~ index if index is not none else '' }}"`, `hx-swap="innerHTML"`, `autocomplete="off"`
   - Inside: suggestions dropdown div with matching ID `tag-suggestions-{{ field_id }}...` and class `suggestions-dropdown`
   - Input keeps the existing value, form input name, and required attribute

2. Add `.tag-autocomplete-field` CSS rules in `frontend/static/css/forms.css`:
   - `position: relative` (same as `.reference-field`)
   - Tag pill item styling preserved — the `.tag-pill-item` class on the parent multi-value-item still applies
   - Ensure suggestions dropdown positions correctly inside pill items

3. Update `addMultiValue()` in `backend/app/templates/forms/object_form.html`:
   - Add detection for `.tag-autocomplete-field` wrapper (similar to existing `.reference-field` detection)
   - Clone the wrapper, update: input ID, `hx-target` attribute to new suggestions div ID, suggestions div `id` and clear innerHTML
   - Call `htmx.process()` on the new item so htmx recognizes the cloned attributes

4. Browser verification:
   - Open edit form for an object with `bpkm:tags` — confirm autocomplete input renders
   - Type partial text — confirm suggestion dropdown appears with matching tags
   - Click a suggestion — confirm input value is set and dropdown clears
   - Type a completely new tag — confirm it's accepted (no suggestion selected)
   - Click "+ Add Tags" — confirm new cloned input has working autocomplete
   - Save the object — confirm both autocompleted and new tags are saved

## Must-Haves

- [ ] Tag fields render with autocomplete-enabled input (not plain text)
- [ ] Typing triggers htmx request to `/browser/tag-suggestions`
- [ ] Clicking suggestion fills input value and closes dropdown
- [ ] `addMultiValue()` correctly clones tag autocomplete inputs with updated IDs
- [ ] New tags (not from suggestions) still work as normal text input
- [ ] `.tag-pill-item` styling still applies to tag inputs in edit forms

## Verification

- Browser: open object edit → type in tag field → suggestions appear → click fills input
- Browser: add new multi-value tag input → autocomplete works on cloned input
- Browser: save object with mix of autocompleted and new tags → all saved correctly

## Inputs

- `backend/app/browser/search.py` — T01's tag-suggestions endpoint (must exist)
- `backend/app/templates/browser/tag_suggestions.html` — T01's suggestion template
- `frontend/static/css/forms.css` — existing `.reference-field` and `.suggestions-dropdown` CSS
- `backend/app/templates/forms/object_form.html` — existing `addMultiValue()` function

## Expected Output

- `backend/app/templates/forms/_field.html` — modified with tag autocomplete branch in `_render_input`
- `frontend/static/css/forms.css` — extended with `.tag-autocomplete-field` rules
- `backend/app/templates/forms/object_form.html` — `addMultiValue()` updated for tag autocomplete cloning

## Observability Impact

- **What signals change:** Tag fields in edit forms now render as `.tag-autocomplete-field` wrappers with htmx-driven autocomplete instead of plain text inputs. Every keystroke (after 200ms debounce) triggers a GET to `/browser/tag-suggestions?q=<term>`, visible in the existing `logger.debug("Tag suggestions for q='%s': %d results", ...)` server log.
- **How a future agent inspects:** Open any object edit form with `bpkm:tags` or `schema:keywords` → check that `document.querySelectorAll('.tag-autocomplete-field').length > 0`. Type in a tag field → network tab shows `GET /browser/tag-suggestions?q=...` → dropdown populates. The `htmx:configRequest` event listener on `document.body` rewrites params for tag-suggestions requests (injects `q` from input value).
- **Failure visibility:** If the `htmx:configRequest` listener is missing, requests go to `/browser/tag-suggestions` without `q` → endpoint returns ALL tags unfiltered (works but no filtering). If tag-autocomplete-field CSS is missing, suggestion dropdown won't position correctly (visually broken but functional).
