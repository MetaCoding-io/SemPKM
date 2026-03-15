# S04: Tag Autocomplete

**Goal:** Tag input fields in edit forms suggest existing tag values as the user types; new tags can still be entered freely.
**Demo:** Open an object edit form → type in a tag field → dropdown shows matching existing tags from the graph → click a suggestion to fill the input → typing a new tag that doesn't exist works normally.

## Must-Haves

- New `GET /browser/tag-suggestions?q=<prefix>` endpoint returns HTML partial with matching tags
- SPARQL queries both `bpkm:tags` and `schema:keywords` via UNION
- Case-insensitive matching with CONTAINS
- Results capped at 30, ordered by frequency DESC then alphabetically
- Empty query returns top tags by frequency (discoverability)
- `_field.html` renders autocomplete-enabled input for tag properties (detected by `'tags' in prop.path or 'keywords' in prop.path`)
- `addMultiValue()` correctly clones tag autocomplete inputs with updated IDs/targets
- User input is SPARQL-escaped to prevent injection
- Clicking a suggestion fills the input value and clears the dropdown
- New tags (not in suggestions) can still be typed freely

## Proof Level

- This slice proves: integration
- Real runtime required: yes (SPARQL + browser)
- Human/UAT required: no

## Verification

- `backend/.venv/bin/pytest tests/test_tag_suggestions.py -v` — unit tests for tag suggestions endpoint logic
- Browser: edit an object with tags → type partial tag → see suggestion dropdown → click suggestion → input filled
- Browser: type a new tag value → no suggestion selected → tag saved normally
- Browser: click "+ Add Tags" → new input has working autocomplete (addMultiValue cloning)

## Observability / Diagnostics

- Runtime signals: `logger.debug("Tag suggestions for q='%s': %d results", ...)` in endpoint
- Inspection surfaces: `GET /browser/tag-suggestions?q=test` returns HTML partial directly
- Failure visibility: Empty query returns all tags; malformed query returns empty list (no crash)

## Integration Closure

- Upstream surfaces consumed: `_execute_sparql_select()` and `_sparql_escape()` from `workspace.py`; `.suggestions-dropdown` CSS from `forms.css`; `addMultiValue()` from `object_form.html`
- New wiring introduced in this slice: `tag_suggestions` endpoint in `search.py`; tag branch in `_field.html` macro; tag-autocomplete CSS in `forms.css`
- What remains before the milestone is truly usable end-to-end: S09 E2E tests + docs

## Tasks

- [x] **T01: Backend tag-suggestions endpoint with template and tests** `est:30m`
  - Why: The frontend needs a server endpoint to query existing tags. This is independently testable.
  - Files: `backend/app/browser/search.py`, `backend/app/templates/browser/tag_suggestions.html`, `backend/tests/test_tag_suggestions.py`
  - Do: Add `GET /tag-suggestions?q=<query>` to `search_router`. SPARQL UNION across `bpkm:tags` and `schema:keywords` with case-insensitive CONTAINS filter. LIMIT 30, ORDER BY count DESC then alpha. Escape user input with same pattern as `_sparql_escape`. Return HTML partial via new `tag_suggestions.html` template. Template renders suggestion items with `onclick` that sets parent input value and clears dropdown. Unit tests cover: empty query returns all tags, prefix match filters correctly, special characters are escaped, result limit works.
  - Verify: `backend/.venv/bin/pytest tests/test_tag_suggestions.py -v`
  - Done when: Endpoint returns correct HTML suggestions for tag queries, unit tests pass

- [x] **T02: Wire tag autocomplete into edit forms and verify in browser** `est:30m`
  - Why: The endpoint exists but tag fields still render as plain text inputs. This task wires the autocomplete UI.
  - Files: `backend/app/templates/forms/_field.html`, `frontend/static/css/forms.css`, `backend/app/templates/forms/object_form.html`
  - Do: Add new branch in `_render_input` macro for tag properties (`'tags' in prop.path or 'keywords' in prop.path`) before the default text input case. Render a `.tag-autocomplete-field` wrapper with the text input (carrying `hx-get="/browser/tag-suggestions"`, `hx-trigger="input changed delay:200ms, focus"`, `hx-target` pointing to suggestions div) and a suggestions dropdown div. Add `.tag-autocomplete-field` CSS rules inheriting from `.reference-field` pattern. Update `addMultiValue()` to detect and clone tag autocomplete fields (same pattern as reference field cloning — update input IDs, `hx-target`, suggestions div ID, call `htmx.process`). Verify in browser: edit an object with tags, type, see suggestions, click to select, add new value and verify cloned input has working autocomplete.
  - Verify: Browser test — open object edit → type in tag field → suggestions appear → click fills input → "+ Add" creates working clone
  - Done when: Tag autocomplete works in edit forms with multi-value support, both existing and new tags accepted

## Files Likely Touched

- `backend/app/browser/search.py`
- `backend/app/templates/browser/tag_suggestions.html`
- `backend/tests/test_tag_suggestions.py`
- `backend/app/templates/forms/_field.html`
- `frontend/static/css/forms.css`
- `backend/app/templates/forms/object_form.html`
