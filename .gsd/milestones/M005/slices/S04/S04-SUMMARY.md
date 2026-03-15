---
id: S04
parent: M005
milestone: M005
provides:
  - GET /browser/tag-suggestions endpoint with SPARQL-backed tag autocomplete
  - Tag autocomplete UI wired into edit forms for bpkm:tags and schema:keywords properties
  - addMultiValue() cloning support for tag autocomplete fields
requires:
  - slice: S03
    provides: Tag query infrastructure (existing tag values endpoint) reusable for autocomplete
affects:
  - S09
key_files:
  - backend/app/browser/search.py
  - backend/app/templates/browser/tag_suggestions.html
  - backend/tests/test_tag_suggestions.py
  - backend/app/templates/forms/_field.html
  - frontend/static/css/forms.css
  - backend/app/templates/forms/object_form.html
key_decisions:
  - D087: Tag autocomplete q parameter via htmx:configRequest, not hx-vals — hx-vals with js: prefix did not reliably pass query params on GET requests
patterns_established:
  - Tag suggestion SPARQL — UNION across bpkm:tags and schema:keywords, GROUP BY + COUNT for frequency, CONTAINS/LCASE for filtering, LIMIT 30
  - Tag autocomplete htmx wiring — input triggers hx-get to /browser/tag-suggestions, htmx:configRequest rewrites params, suggestion dropdown positioned via relative/absolute wrapper
  - addMultiValue tag cloning — detect .tag-autocomplete-field, clone wrapper, update input ID + hx-target + suggestions div ID, call htmx.process()
observability_surfaces:
  - GET /browser/tag-suggestions?q=<term> — directly inspectable via curl
  - logger.debug("Tag suggestions for q='%s': %d results", ...) on every request
  - SPARQL failures logged at WARNING with exc_info; endpoint returns empty HTML gracefully
  - document.querySelectorAll('.tag-autocomplete-field').length — count of active autocomplete inputs
drill_down_paths:
  - .gsd/milestones/M005/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M005/slices/S04/tasks/T02-SUMMARY.md
duration: 40m
verification_result: passed
completed_at: 2026-03-14
---

# S04: Tag Autocomplete

**Tag input fields in edit forms suggest existing tag values from the graph as the user types, with frequency-ordered dropdown and free-entry for new tags**

## What Happened

T01 added the backend endpoint `GET /browser/tag-suggestions?q=<prefix>` to `search.py` with three extracted pure functions (`_sparql_escape`, `build_tag_suggestions_sparql`, `parse_tag_bindings`). The SPARQL query UNIONs across `bpkm:tags` and `schema:keywords`, applies case-insensitive CONTAINS filtering when q is non-empty, and returns up to 30 results ordered by frequency DESC then alphabetically. The `tag_suggestions.html` template renders each result as a `.suggestion-item` div with an onclick handler that sets the input value and clears the dropdown. 22 unit tests cover query generation, escaping, result parsing, and escaping integration.

T02 wired the autocomplete UI into edit forms. A new branch in the `_render_input` macro in `_field.html` detects tag properties (`'tags' in prop.path or 'keywords' in prop.path`) and renders a `.tag-autocomplete-field` wrapper with htmx attributes for debounced fetching. CSS rules in `forms.css` handle dropdown positioning (relative/absolute pattern matching reference fields). The `addMultiValue()` function in `object_form.html` was updated to detect and clone tag autocomplete fields with correct ID/target updates and `htmx.process()` calls. An `htmx:configRequest` event listener on `document.body` intercepts tag-suggestions requests and injects `{q: input.value}` — this replaced the planned `hx-vals` approach which did not reliably pass the q parameter on GET requests.

## Verification

- `backend/.venv/bin/pytest backend/tests/test_tag_suggestions.py -v` — **22/22 passed**
- Browser: tag field renders `.tag-autocomplete-field` wrapper with htmx attributes ✅
- Browser: typing "plant" → dropdown shows "garden/plant (13)" ✅
- Browser: clicking suggestion fills input value, clears dropdown ✅
- Browser: typing new tag "my-brand-new-tag" → no suggestions, value accepted ✅
- Browser: "+ Add Tags" creates cloned input with working autocomplete ✅
- Browser: save with mix of autocompleted and new tags → "Changes saved successfully" ✅

## Requirements Advanced

- TAG-05 (Tag autocomplete in edit forms) — new requirement, fully implemented

## Requirements Validated

- TAG-05 — Tag autocomplete in edit forms: endpoint returns frequency-ordered suggestions, UI wired into _field.html for tag/keyword properties, multi-value cloning works, both existing and new tags accepted

## New Requirements Surfaced

- TAG-05 — Tag input fields in edit forms offer autocomplete with existing tag values from the graph

## Requirements Invalidated or Re-scoped

- none

## Deviations

- **hx-vals replaced with htmx:configRequest** — the T02 plan specified `hx-vals='js:{"q": this.value}'`. Testing revealed this did not reliably pass the q parameter on htmx GET requests. Replaced with an `htmx:configRequest` event listener that intercepts tag-suggestions requests and injects `{q: input.value}`. This is more robust and follows htmx's recommended event-driven approach (D087).

## Known Limitations

- Tag suggestions endpoint queries the full triplestore without graph scoping — acceptable for single-user/small-team use; may need optimization for very large tag sets
- Suggestion dropdown does not handle keyboard navigation (arrow keys to select) — mouse/touch only

## Follow-ups

- S09: E2E Playwright tests for tag autocomplete flow
- S09: User guide documentation for tag autocomplete feature

## Files Created/Modified

- `backend/app/browser/search.py` — Added `_sparql_escape`, `build_tag_suggestions_sparql`, `parse_tag_bindings` helpers and `tag_suggestions` endpoint
- `backend/app/templates/browser/tag_suggestions.html` — New template rendering tag suggestion items with onclick handlers
- `backend/tests/test_tag_suggestions.py` — 22 unit tests covering query generation, escaping, parsing, and integration
- `backend/app/templates/forms/_field.html` — Added tag autocomplete branch in `_render_input` macro
- `frontend/static/css/forms.css` — Added `.tag-autocomplete-field` and `.tag-count` CSS rules
- `backend/app/templates/forms/object_form.html` — Updated `addMultiValue()` with tag autocomplete cloning; added `htmx:configRequest` listener

## Forward Intelligence

### What the next slice should know
- The tag-suggestions endpoint pattern (pure function extraction, SPARQL UNION, frequency ordering) can be reused for any similar autocomplete feature
- The `htmx:configRequest` listener pattern for injecting query params is more reliable than `hx-vals` with `js:` prefix on GET requests

### What's fragile
- The `htmx:configRequest` listener matches on `detail.path.includes('/browser/tag-suggestions')` — if the endpoint URL changes, the listener silently stops working and all suggestions return unfiltered
- Tag property detection uses substring matching (`'tags' in prop.path or 'keywords' in prop.path`) — adding a third tag-like property requires updating this check in `_field.html`, `object_patch.py`, and the SPARQL query

### Authoritative diagnostics
- `GET /browser/tag-suggestions?q=test` — returns HTML directly, curl-inspectable without auth in dev
- Server log `Tag suggestions for q='...': N results` — confirms SPARQL execution and result count
- `document.querySelectorAll('.tag-autocomplete-field').length` in browser console — confirms autocomplete inputs are rendered

### What assumptions changed
- Assumed `hx-vals` with `js:` prefix would work for dynamic GET parameters — it did not; `htmx:configRequest` is the reliable approach
