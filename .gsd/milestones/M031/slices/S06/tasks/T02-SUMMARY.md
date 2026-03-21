---
id: T02
parent: S06
milestone: M031
provides:
  - /browser/class-search JSON endpoint for ontology class autocomplete
  - /browser/object-search JSON endpoint for object instance autocomplete
  - Dashboard builder create-form block has class IRI autocomplete
  - Dashboard builder object-embed block has object IRI autocomplete
  - Workflow builder form step has class IRI autocomplete
key_files:
  - backend/app/browser/search.py
  - backend/app/templates/browser/dashboard_builder.html
  - backend/app/templates/browser/workflow_builder.html
  - frontend/static/css/workspace.css
key_decisions:
  - Used shared _builderAutocomplete/_wfBuilderAutocomplete helper functions with endpoint parameter rather than duplicating fetch logic per field
  - Selected IRI is shown directly in the text input (not a separate label span) for simpler state management
  - Object search uses SPARQL REGEX across rdfs:label, dcterms:title, skos:prefLabel, schema:name in the current state graph
patterns_established:
  - Builder autocomplete pattern: reference-field wrapper with visible search input + hidden data-key input + suggestions-dropdown, debounced fetch, click-outside dismiss
observability_surfaces:
  - Endpoint health: curl '/browser/class-search?q=test' returns JSON array (empty or populated)
  - Endpoint health: curl '/browser/object-search?q=test' returns JSON array (empty or populated)
  - Errors logged with logger.warning() including exc_info; graceful degradation returns empty array
  - Autocomplete shows "No results" in dropdown on empty/error response
  - Hidden input value: document.querySelector('[data-key="target_class"]').value shows selected IRI
duration: 12m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T02: Add autocomplete for Target Class IRI and Object IRI fields

**Added `/browser/class-search` and `/browser/object-search` JSON endpoints and wired search-as-you-type autocomplete into dashboard builder (create-form, object-embed) and workflow builder (form step) IRI fields.**

## What Happened

1. Added two new JSON endpoints to `backend/app/browser/search.py`:
   - `/browser/class-search?q=...` wraps `OntologyService.search_classes()` and returns `[{iri, label}]` from ontology graphs. Errors gracefully degrade to empty array with a warning log.
   - `/browser/object-search?q=...` runs a SPARQL query against the current state graph to find instances matching a label regex across `rdfs:label`, `dcterms:title`, `skos:prefLabel`, and `schema:name`. Returns `[{iri, label}]`, limited to 15 results.

2. In the dashboard builder template, replaced the plain text `<input>` for the `create-form` Target Class IRI field with a `.reference-field` autocomplete wrapper: a visible search input, a hidden `data-key="target_class"` input, and a `.suggestions-dropdown`. Connected to `window._builderClassSearch()` via `oninput`.

3. Same pattern applied to the `object-embed` Object IRI field, connected to `window._builderObjectSearch()` which hits `/browser/object-search`.

4. Added shared `_builderAutocomplete(inputEl, endpoint)` helper function in the dashboard builder that handles 300ms debounce, fetch, rendering suggestion items (label + IRI), click-to-select (sets hidden input + text input), and error handling ("No results" on empty/error).

5. In the workflow builder template, replaced the `form` step's Target Class IRI field with the same autocomplete pattern, using a parallel `_wfBuilderAutocomplete` helper connected to `/browser/class-search`.

6. Added click-outside dismissal in both builders via a `document.addEventListener('click')` handler.

7. Added CSS in `workspace.css` for `.block-config-fields .reference-field` to ensure proper positioning and max-width alignment with other builder inputs.

## Verification

All 6 task-level checks pass. All relevant slice-level checks also pass.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -q 'class-search' backend/app/browser/search.py` | 0 | ✅ pass | <1s |
| 2 | `grep -q 'object-search' backend/app/browser/search.py` | 0 | ✅ pass | <1s |
| 3 | `grep -q 'class-search' backend/app/templates/browser/dashboard_builder.html` | 0 | ✅ pass | <1s |
| 4 | `grep -q 'class-search' backend/app/templates/browser/workflow_builder.html` | 0 | ✅ pass | <1s |
| 5 | `grep -q 'object-search' backend/app/templates/browser/dashboard_builder.html` | 0 | ✅ pass | <1s |
| 6 | `python3 -c "import ast; ast.parse(open('backend/app/browser/search.py').read())"` | 0 | ✅ pass | <1s |
| 7 | `grep -c 'field-help' backend/app/templates/browser/dashboard_builder.html` (result: 13) | 0 | ✅ pass (slice) | <1s |
| 8 | `grep -c 'field-help' backend/app/templates/browser/workflow_builder.html` (result: 6) | 0 | ✅ pass (slice) | <1s |
| 9 | `grep -c 'step-config-renderer' backend/app/templates/browser/workflow_builder.html` (result: 0) | 0 | ✅ pass (slice) | <1s |
| 10 | `grep -q 'builder-error' ...dashboard_builder.html && ...workflow_builder.html` | 0 | ✅ pass (slice) | <1s |

## Diagnostics

- **Endpoint health:** `curl '/browser/class-search?q=Person'` should return `[{iri, label}]` or `[]`. Same for `/browser/object-search?q=test`.
- **Error logging:** Both endpoints log `logger.warning()` with `exc_info=True` on exceptions, then return `[]`.
- **Dropdown behavior:** Typing in a Target Class IRI or Object IRI field triggers a 300ms debounced fetch. Suggestions show label + IRI. Click selects and sets hidden input. "No results" shows on empty response or error.
- **Click-outside dismiss:** Clicking anywhere outside `.reference-field` clears all `.builder-suggestions` dropdowns.
- **Save compatibility:** Hidden inputs retain `data-key` attributes so the existing `querySelectorAll('[data-key]')` save collector continues to work.

## Deviations

- Did not create a `selected-reference-label` CSS class or separate chip/badge for selected IRIs. Instead, the selected IRI is written directly into the visible text input. This is simpler and avoids extra DOM manipulation while still showing the user what was selected.
- CSS additions went into `workspace.css` (builder context) rather than `forms.css` since the existing `.reference-field` base styles in `forms.css` already provide everything needed. The builder additions are scoped under `.block-config-fields` for specificity.
- Used separate `_wfBuilderAutocomplete` helper in workflow builder rather than sharing code across templates, since each template is a standalone page with its own `<script>` block.

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/search.py` — Added `/browser/class-search` and `/browser/object-search` JSON endpoints with graceful error handling
- `backend/app/templates/browser/dashboard_builder.html` — Replaced create-form and object-embed text inputs with autocomplete widgets; added `_builderClassSearch`, `_builderObjectSearch`, and shared `_builderAutocomplete` JS functions
- `backend/app/templates/browser/workflow_builder.html` — Replaced form step target_class text input with autocomplete widget; added `_wfBuilderClassSearch` and `_wfBuilderAutocomplete` JS functions
- `frontend/static/css/workspace.css` — Added `.block-config-fields .reference-field` and `.suggestions-dropdown` scoped styles for builder context
- `.gsd/milestones/M031/slices/S06/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
