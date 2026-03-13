---
id: T03
parent: S08
milestone: M003
provides:
  - Class creation form UI with icon picker, parent class search, property editor
  - GET /browser/ontology/tbox/search endpoint for parent class picker
  - GET /browser/ontology/create-class-form endpoint for lazy form loading
  - search_classes() method on OntologyService
  - classCreated/classDeleted event-driven TBox tree refresh
key_files:
  - backend/app/templates/browser/ontology/create_class_form.html
  - backend/app/templates/browser/ontology/ontology_page.html
  - backend/app/ontology/router.py
  - backend/app/ontology/service.py
  - frontend/static/css/workspace.css
  - frontend/static/js/workspace.js
key_decisions:
  - Form loads lazily via htmx (hx-trigger="loadForm") to avoid loading icon grid on every TBox view
  - ccf-container sits between ontology-tabs and ontology-tab-content (sibling, not child) to avoid overflow:hidden clipping
  - Properties serialized via hx-on::before-request="serializeProperties()" for reliable pre-submission serialization
  - Parent class search uses case-insensitive CONTAINS filter on class labels across all ontology graphs
patterns_established:
  - Icon picker pattern: curated grid of Lucide icons with data-icon attributes, search filter via JS, hidden input for form submission
  - Parent class picker pattern: hx-get search-as-you-type with dropdown results, click-to-select stores IRI in hidden input
  - Property editor pattern: dynamic rows with add/remove, predicate dropdown + custom IRI option, JSON serialization to hidden input
  - Color swatch picker: button grid with data-color attributes, selected state via CSS class
observability_surfaces:
  - POST /browser/ontology/create-class returns descriptive HTML error/success in #ccf-result
  - htmx events (classCreated, classDeleted) visible in browser console
  - Network tab shows POST to /browser/ontology/create-class and subsequent TBox refresh GET
duration: 1.5h
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T03: Class creation form UI with icon picker and property editor

**Built the complete class creation form with searchable icon picker, htmx-powered parent class search, dynamic property editor, and event-driven TBox tree refresh.**

## What Happened

Built the user-facing form for creating new RDF classes in the ontology viewer. The form includes:

1. **Class Name field** — required text input with placeholder
2. **Icon Picker** — grid of 40 curated Lucide icons (file-text, book, lightbulb, etc.) with text search filter. Selected icon gets visual highlight and value stored in hidden input.
3. **Icon Color picker** — row of 9 color swatches (default, indigo, purple, pink, red, amber, emerald, blue, cyan) with selected state
4. **Parent Class selector** — search-as-you-type input that queries `GET /browser/ontology/tbox/search?q={query}`. Results render as a dropdown showing class label + IRI. Default is owl:Thing. Selected class stored in hidden input.
5. **Property Editor** — dynamic list of property rows. Each row has: name (text), predicate (dropdown of 9 common predicates + custom IRI), datatype (dropdown of 7 XSD types). Add/Remove buttons. Properties serialized as JSON array before form submission.
6. **Submit** — htmx POST to `/browser/ontology/create-class` with loading indicator. Success/error feedback shown inline.

Added `search_classes()` method to OntologyService with case-insensitive CONTAINS filter and SPARQL injection protection.

Modified `ontology_page.html` to add "Create Class" button in the tab bar and `hx-trigger="classCreated from:body, classDeleted from:body"` on the TBox pane for auto-refresh.

Added comprehensive CSS for all form components following existing workspace patterns (Lucide SVG sizing with flex-shrink:0, CSS variables for theming).

## Verification

- **Unit tests**: `cd backend && .venv/bin/pytest tests/test_class_creation.py -v` — 34 tests pass (28 existing + 6 new: search_classes matching, empty query, quote escaping, tbox_search endpoint results/empty/no-results)
- **Browser verification**: Opened ontology viewer → clicked "Create Class" → form rendered with all fields → typed "Research Paper" as name → selected "book" icon → selected indigo color → searched "cont" in parent class picker → dropdown showed gist Content/Content Expression/Contemporary Event → selected Content → added two properties (Title/dcterms:title/xsd:string, Description/dcterms:description/xsd:string) → submitted → success message "Created class Research Paper" with IRI displayed → TBox tree auto-refreshed → expanded Content node → "Research Paper" visible with "user" badge → Research Paper Shape appeared in explorer sidebar type picker
- **Slice-level checks**: `cd backend && .venv/bin/pytest tests/test_class_creation.py -v` passes (34/34). E2E test not yet written (T04).

## Diagnostics

- POST endpoint returns descriptive HTML in `<div class="error-message">` on 422 / `<div class="success-message">` on 200
- Network tab shows POST to /browser/ontology/create-class and subsequent GET /browser/ontology/tbox on classCreated event
- Icon picker state: `document.getElementById('ccf-icon').value` returns selected icon name
- Parent IRI state: `document.getElementById('ccf-parent-iri').value` returns selected parent IRI
- Properties state: `document.getElementById('ccf-properties').value` returns serialized JSON array

## Deviations

- Moved `ccf-container` from inside `ontology-tab-content` (child) to between `ontology-tabs` and `ontology-tab-content` (sibling) because the parent had `overflow: hidden` which clipped the scrollable form
- Added `hx-on::before-request="serializeProperties()"` directly on the form element instead of using JS event listener for more reliable property serialization across htmx dynamic loading
- Replaced "tool" icon with "wrench" — "tool" icon name not found in the Lucide bundle

## Known Issues

- The icon picker "tool" Lucide icon name was not found in the loaded Lucide bundle — replaced with "wrench"
- When submitting the form multiple times without clearing, duplicate classes are created (each with unique IRI). This is by design (UUID-based IRI minting) but UX could be improved by clearing/resetting form on success.

## Files Created/Modified

- `backend/app/templates/browser/ontology/create_class_form.html` — **new** — complete class creation form template with icon picker, color picker, parent class search, property editor
- `backend/app/templates/browser/ontology/ontology_page.html` — **modified** — added "Create Class" button in tab bar, classCreated/classDeleted htmx triggers on TBox pane, lazy form loading container
- `backend/app/ontology/router.py` — **modified** — added GET /ontology/tbox/search and GET /ontology/create-class-form endpoints
- `backend/app/ontology/service.py` — **modified** — added search_classes() method with case-insensitive CONTAINS filter
- `frontend/static/css/workspace.css` — **modified** — added ~350 lines of CSS for class creation form, icon picker grid, color picker, parent class picker, property editor, form messages
- `frontend/static/js/workspace.js` — **modified** — added ~200 lines of JS for icon selection/filtering, color selection, parent class picker, property editor add/remove/serialize
- `backend/tests/test_class_creation.py` — **modified** — added 6 new tests for search_classes and tbox_search endpoint (34 total)
