---
id: S02
parent: M014
milestone: M014
provides:
  - SHACL form renderer module (renderForm, renderField, getFormValues) for converting shape JSON to Chrome MV3 CSP-compliant HTML forms
  - Dynamic type selector → shape fetch → form render pipeline in popup
  - All 10 standard SHACL property types rendered (string, date, dateTime, boolean, integer, decimal, anyURI, enum, object reference, tags)
  - Multi-value field support (add/remove) with correct array extraction
  - Collapsible group sections matching Jinja2 _group.html pattern
  - Skip paths (dcterms:created, dcterms:modified, body), required markers, helptext toggle, default values
  - Backend multi-value property support (list → separate triples) in object_create handler
  - CSS for 380px popup viewport with groups, multi-value, helptext, loading states
requires:
  - slice: S01
    provides: extension scaffold (popup.html, popup.js, popup.css, api-client.js, storage.js), type selector, save flow, SemPKMClient.getShape()
affects:
  - S04 — object reference fields have data-target-class attribute for search-as-you-type enhancement
  - S05 — E2E tests exercise the dynamic form rendering
key_files:
  - extension/shared/shacl-renderer.js
  - extension/popup/popup.html
  - extension/popup/popup.js
  - extension/popup/popup.css
  - backend/app/commands/handlers/object_create.py
key_decisions:
  - D189 — Backend object_create handler patched to iterate list values for multi-value fields
  - D190 — Title extraction uses 4-priority cascade to handle types without dcterms:title
  - data-target-class placed on both .reference-field wrapper and visible search input for S04 flexibility
patterns_established:
  - el() helper for imperative DOM creation without inline handlers
  - createInput() dispatch matching Jinja2 _field.html macro dispatch order exactly
  - handleTypeChange() as single orchestrator for type selector → shape fetch → render → DOM insertion
  - extractTitle() cascade for handling varying title conventions across Mental Models
observability_surfaces:
  - "[SemPKM] Shape loaded for {typeIri}: N properties, M groups" in popup DevTools console
  - "[SemPKM] Saving object — type: {typeIri}, properties: [keys]" before API call
  - Shape fetch errors → red toast + console.warn with full error
  - "#dynamic-form" container in DevTools Elements panel shows rendered DOM with data-path attributes
drill_down_paths:
  - .gsd/milestones/M014/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M014/slices/S02/tasks/T02-SUMMARY.md
duration: 1h10m
verification_result: passed
completed_at: 2026-03-18
---

# S02: SHACL Form Renderer + Type Selector

**Dynamic SHACL-driven form rendering in the browser extension popup — type selector change fetches shape JSON and renders correct fields for all 10 property types with groups, multi-value, and validation indicators.**

## What Happened

**T01 (25m):** Built `extension/shared/shacl-renderer.js` — a 588-line ES module exporting three functions: `renderForm(shapeResponse)` returns a DocumentFragment, `renderField(prop)` returns DOM for one property, and `getFormValues(container)` returns `{path: value|[values]}` pairs. The dispatch order matches the Jinja2 `_field.html` macro exactly across 10 property types: enum select, object reference (text + hidden IRI), date, dateTime, boolean (Yes/No select), integer, decimal, anyURI, tags, and default text. Multi-value fields use `.multi-value-list` with add/remove buttons. Groups render as collapsible `<details>` elements (first open, rest collapsed). Skip paths filter created/modified/body. An `el()` helper does all DOM creation with zero inline handlers — Chrome MV3 CSP-safe throughout.

**T02 (45m):** Wired the renderer into the popup lifecycle. Restructured `popup.html` replacing hardcoded title/body fields with `#dynamic-form` container, `#form-loading` spinner, and `#form-fallback` title-only input. `popup.js` imports `renderForm`/`getFormValues` and orchestrates via `handleTypeChange()`: on type selector change, fetch shape, render fragment, insert into DOM. `handleSave()` uses `getFormValues()` with a 4-priority `extractTitle()` cascade (title path → name parts → first required → any value) to handle types like CRM Contact that lack a dcterms:title field. Added 300+ lines of CSS for groups, multi-value, helptext, required markers, loading states in the 380px popup. Patched `backend/app/commands/handlers/object_create.py` to iterate list values — each item becomes a separate triple, enabling multi-value fields like tags.

## Verification

- `node --check` passes on shacl-renderer.js and popup.js (syntax valid, zero inline handlers)
- `python3 ast.parse` passes on object_create.py
- Node.js rendering test against live API: all 4 types render correctly — Contact (12 fields/6 groups), Deal (decimal + USD default), Note (6 fields), Task (18 fields/4 groups) — 15/15 checks passed
- API integration: Contact created with multi-value tags via POST /api/commands — visible in Object Browser with all properties
- 16/16 must-have grep checks pass (data-path, data-target-class, multi-value, form-group-section, etc.)
- Zero inline event handlers (grep for onclick/onchange/onsubmit returns empty)
- 10 addEventListener calls across both files

## Requirements Advanced

- EXT-02 (SHACL forms) — Dynamic form renderer handles all standard property types with groups, multi-value, validation indicators. Renders CRM Contact (widest type variety), basic-pkm Note/Task, and CRM Deal correctly.

## Requirements Validated

- None moved to validated — EXT-02 requires sideloaded extension visual verification which is pending S05 E2E tests.

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- Backend patch to `object_create.py` for list-value support was not in the original plan — discovered as necessary when multi-value fields (tags) submitted arrays that the handler serialized as literal "[tag1, tag2]" strings instead of separate triples.
- Title extraction expanded from simple dcterms:title lookup to 4-priority cascade — CRM Contact has firstName/lastName but no title field.
- Chrome extension sideload not automatable via Playwright — substituted Node.js rendering tests against live API + direct curl API integration tests.
- shacl-renderer.js is 588 lines vs estimated 200-350 — includes comprehensive JSDoc, el() DOM helper, and cloneEmptyInput() for multi-value. Functional code is proportional to the 10 property types.

## Known Limitations

- Extension popup cannot be tested via Playwright (Chrome extension popups are outside page context) — manual sideload required for visual verification.
- Object reference fields render as text + hidden IRI input placeholders — S04 will enhance these with search-as-you-type.
- Contact objects display as IRI fragments in explorer (pre-existing label resolution issue, not caused by S02).

## Follow-ups

- S04: Object reference fields marked with `data-target-class` are ready for search-as-you-type enhancement.
- S05: E2E tests should verify form rendering for all 4 types (Note, Contact, Deal, Task) and multi-value save round-trip.

## Files Created/Modified

- `extension/shared/shacl-renderer.js` — New: 588-line SHACL form renderer module with renderForm, renderField, getFormValues exports
- `extension/popup/popup.html` — Modified: replaced hardcoded fields with #dynamic-form container, loading spinner, fallback, type icon
- `extension/popup/popup.js` — Modified: rewritten with shacl-renderer integration, handleTypeChange(), extractTitle()
- `extension/popup/popup.css` — Modified: added 300+ lines for dynamic form elements (groups, multi-value, helptext, etc.)
- `backend/app/commands/handlers/object_create.py` — Modified: patched list-value iteration for multi-value properties

## Forward Intelligence

### What the next slice should know
- The SHACL renderer produces DOM with `data-path` on all value-bearing inputs and `data-target-class` on object reference fields — S04's relationship picker should query these attributes.
- `getFormValues()` returns `{path: value|[values]}` where multi-value fields produce arrays — the backend now handles these correctly.
- The popup has a fixed Notes textarea (`#notes-input`) below the dynamic form that saves as `sempkm:body` — this is separate from the SHACL form's body field (which is skipped by the renderer).

### What's fragile
- `extractTitle()` cascade relies on string matching ("title" in path, "name" in path) — new Mental Model types with unconventional title fields may fall through to the "first required field" heuristic.
- CSS for 380px popup assumes groups stack vertically with 8px padding — deeply nested multi-value fields with long labels may overflow horizontally.

### Authoritative diagnostics
- Chrome DevTools console shows `[SemPKM] Shape loaded for {typeIri}` with property/group counts — this confirms the shape fetch and render pipeline is working.
- `#dynamic-form` container in Elements panel shows the full rendered DOM tree — inspect `data-path` attributes to verify correct property IRI binding.

### What assumptions changed
- Assumed object_create handler already supported list values — it didn't. Required a backend patch.
- Assumed all types have dcterms:title — CRM Contact doesn't. Required the extractTitle cascade.
