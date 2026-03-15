---
id: T02
parent: S04
milestone: M005
provides:
  - Tag autocomplete UI wired into edit forms for bpkm:tags and schema:keywords properties
  - addMultiValue() cloning support for tag autocomplete fields
  - htmx:configRequest listener to inject q parameter for tag-suggestions requests
key_files:
  - backend/app/templates/forms/_field.html
  - frontend/static/css/forms.css
  - backend/app/templates/forms/object_form.html
key_decisions:
  - Used htmx:configRequest event listener to inject q parameter instead of hx-vals, because hx-vals with js: prefix did not reliably pass query params on GET requests
  - Tag autocomplete uses same positioning pattern as reference-field (.position: relative wrapper with absolute dropdown)
patterns_established:
  - Tag autocomplete htmx wiring — input triggers hx-get to /browser/tag-suggestions, htmx:configRequest rewrites params to {q: input.value}, suggestion dropdown positioned via .tag-autocomplete-field wrapper
  - addMultiValue tag cloning — detect .tag-autocomplete-field, clone wrapper, update input ID + hx-target + suggestions div ID, call htmx.process()
observability_surfaces:
  - htmx:configRequest listener on document.body intercepts /browser/tag-suggestions requests and injects q param
  - Network tab shows GET /browser/tag-suggestions?q=<term> on every keystroke after 200ms debounce
  - document.querySelectorAll('.tag-autocomplete-field').length reveals count of active tag autocomplete inputs
duration: 25m
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T02: Wire tag autocomplete into edit forms and verify in browser

**Added tag autocomplete UI to edit forms — typing in tag fields shows filtered suggestions from the graph, clicking fills the input, cloned inputs via "+ Add" have working autocomplete**

## What Happened

Added a new branch in the `_render_input` macro in `_field.html` that detects tag properties (`'tags' in prop.path or 'keywords' in prop.path`) and renders a `.tag-autocomplete-field` wrapper containing a text input with htmx attributes (`hx-get="/browser/tag-suggestions"`, `hx-trigger="input changed delay:200ms, focus"`, `hx-target` pointing to a per-input suggestions dropdown div). The input retains its form name (`prop.path[]`) for form submission.

Added `.tag-autocomplete-field` CSS rules in `forms.css` — `position: relative` for dropdown anchoring, `flex: 1; min-width: 0` for flex container compatibility, and `.tag-count` styling for frequency badges in suggestions.

Updated `addMultiValue()` in `object_form.html` to detect `.tag-autocomplete-field` wrappers (alongside existing `.reference-field` detection), clone them with updated input IDs, `hx-target` attributes, and suggestions div IDs, and call `htmx.process()` on the new item.

Added an `htmx:configRequest` event listener on `document.body` that intercepts requests to `/browser/tag-suggestions` and replaces the parameters with `{q: triggerEl.value}`. This was necessary because `hx-vals='js:{"q": this.value}'` did not reliably pass the `q` query parameter on htmx GET requests — the initial implementation sent requests without the `q` param, returning all tags unfiltered.

## Verification

- **Unit tests:** `backend/.venv/bin/pytest backend/tests/test_tag_suggestions.py -v` — 22/22 passed
- **Browser: tag field renders autocomplete** — opened SemPKM Development project edit form → Tags field shows `.tag-autocomplete-field` wrapper with `hx-get`, `hx-trigger`, `hx-target` attributes ✅
- **Browser: typing triggers filtered suggestions** — typed "plant" → dropdown showed "garden/plant (13)" (only matching tag) ✅
- **Browser: clicking suggestion fills input** — clicked "garden/plant" → input value set to "garden/plant", dropdown cleared ✅
- **Browser: new tags work** — typed "my-brand-new-tag" → no suggestions shown, value accepted as normal text ✅
- **Browser: cloned input has working autocomplete** — clicked "+ Add Tags" → new input created with correct IDs, typed "build" → showed "architect/build (7)" ✅
- **Browser: save works** — saved object with mix of autocompleted ("garden/plant") and new ("my-brand-new-tag") tags → "Changes saved successfully" ✅

**Slice-level verification:**
- ✅ `backend/.venv/bin/pytest tests/test_tag_suggestions.py -v` — 22/22 passed
- ✅ Browser: edit object with tags → type partial tag → see suggestion dropdown → click suggestion → input filled
- ✅ Browser: type new tag value → no suggestion selected → tag saved normally
- ✅ Browser: click "+ Add Tags" → new input has working autocomplete (addMultiValue cloning)

All slice verification checks pass. This is the final task of the slice — all checks pass.

## Diagnostics

- Type in any tag field in an edit form → network tab shows `GET /browser/tag-suggestions?q=<typed_value>`
- `document.querySelectorAll('.tag-autocomplete-field').length` — count of active tag autocomplete inputs on the page
- Server log: `Tag suggestions for q='...': N results` on every request
- If filtering doesn't work: check that `htmx:configRequest` listener is active on `document.body` (look in object_form.html script block)

## Deviations

- **hx-vals approach replaced with htmx:configRequest listener** — the plan specified `hx-vals='js:{"q": this.value}'` with `hx-params="none"`. Testing revealed that `hx-params="none"` blocked all params including hx-vals, and even without it, `hx-vals` with `js:` prefix did not reliably pass the `q` parameter on GET requests. Replaced with a `htmx:configRequest` event listener that intercepts tag-suggestions requests and injects `{q: input.value}` — this is more robust and follows htmx's recommended event-driven approach.

## Known Issues

None.

## Files Created/Modified

- `backend/app/templates/forms/_field.html` — Added tag autocomplete branch in `_render_input` macro (between anyURI and default text input)
- `frontend/static/css/forms.css` — Added `.tag-autocomplete-field` and `.tag-count` CSS rules
- `backend/app/templates/forms/object_form.html` — Updated `addMultiValue()` with tag autocomplete cloning branch; added `htmx:configRequest` listener for q parameter injection
- `.gsd/milestones/M005/slices/S04/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
