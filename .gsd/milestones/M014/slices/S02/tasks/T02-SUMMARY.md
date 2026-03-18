---
id: T02
parent: S02
milestone: M014
provides:
  - Dynamic SHACL-driven form rendering in popup on type selector change
  - Type icon display next to selector
  - Loading spinner during shape fetch
  - Fallback title input when no shape loaded
  - getFormValues() integration in save flow with multi-priority title extraction
  - CSS for groups, multi-value, helptext, required markers in 380px popup
  - Backend multi-value property support (list→separate triples)
key_files:
  - extension/popup/popup.html
  - extension/popup/popup.js
  - extension/popup/popup.css
  - backend/app/commands/handlers/object_create.py
key_decisions:
  - Title extraction uses 4-priority cascade (title path, name path, first required field, any value) to handle types without dcterms:title
  - Notes textarea kept as fixed field below dynamic form
  - Backend object_create handler patched to support list values in properties dict
patterns_established:
  - handleTypeChange() async function as single orchestrator for shape fetch → render → DOM insertion
  - extractTitle() cascade handles varying title conventions across Mental Models
observability_surfaces:
  - "[SemPKM] Shape loaded for {typeIri}: {N} properties, {M} groups" in popup DevTools console
  - "[SemPKM] Saving object — type: {typeIri}, properties: [keys]" before API call
  - Shape fetch errors → red toast + console.warn with full error
  - "#dynamic-form" container shows rendered DOM in DevTools Elements panel
duration: 45m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: Wire renderer into popup, restructure HTML, add CSS, and verify

**Wired shacl-renderer.js into popup lifecycle — type selector change fetches SHACL shape and renders dynamic form; save flow extracts values via getFormValues(); CSS styles groups, multi-value, helptext in 380px popup; backend patched for multi-value property arrays.**

## What Happened

Restructured popup.html replacing hardcoded title/body fields with `#dynamic-form` container, `#form-loading` spinner, and `#form-fallback` simple title input. Notes textarea and Source URL remain as fixed fields below. Added type icon colored dot next to selector.

Rewrote popup.js: imports `renderForm`/`getFormValues` from shacl-renderer.js. `handleTypeChange()` fires on type selector change — fetches shape, renders form fragment, inserts into DOM. Shows spinner during fetch, falls back on error. `handleSave()` uses `getFormValues($dynamicForm)` in dynamic mode with 4-priority title extraction (title path → name path → first required → any value). Appends notes as `sempkm:body`, URL as `schema:url`.

Added 300+ lines CSS for collapsible group sections, form fields, required markers, helptext toggle, multi-value add/remove, reference fields, loading spinner, default value indicators, scrollable popup (max-height 600px).

Patched `backend/app/commands/handlers/object_create.py` to iterate list values — each item becomes a separate triple, enabling multi-value fields like tags.

## Verification

- `node --check` passes on both shacl-renderer.js and popup.js
- Python AST parse passes on object_create.py
- Node.js rendering test against live API: all 4 types render correctly (Contact 12 fields/6 groups, Deal with USD default, Note 6 fields, Task 18 fields/4 groups) — 15/15 checks passed
- API integration: Contact created with multi-value tags via POST /api/commands — visible in Object Browser with all properties
- HTML balanced, CSS balanced (99/99 braces), 16/16 must-have grep checks pass

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `node --check extension/shared/shacl-renderer.js` | 0 | ✅ pass | <1s |
| 2 | `node --check extension/popup/popup.js` | 0 | ✅ pass | <1s |
| 3 | `python3 ast.parse object_create.py` | 0 | ✅ pass | <1s |
| 4 | Node.js shape rendering test (4 types, 15 checks) | 0 | ✅ pass | 2s |
| 5 | `curl POST /api/commands` Contact with multi-value tags | 200 | ✅ pass | <1s |
| 6 | Browser: Contact visible in Object Browser with properties | — | ✅ pass | manual |

## Diagnostics

- DevTools console: `[SemPKM] Shape loaded for {typeIri}` and `[SemPKM] Saving object` messages
- DOM: `#dynamic-form` container, `#form-loading.hidden`/`#form-fallback.hidden` indicate state
- Failure: red toast + console.warn on shape fetch error

## Deviations

- Backend patch to object_create.py for list-value support — required for multi-value fields
- Title extraction expanded to 4-priority cascade (Contact has no "title" field)
- Chrome extension sideload not automatable — substituted Node.js rendering tests + API integration

## Known Issues

- Extension popup cannot be tested via Playwright — manual sideload required for visual verification
- Contact objects display as IRI fragments in explorer (pre-existing label resolution issue)

## Files Created/Modified

- `extension/popup/popup.html` — Restructured with #dynamic-form, loading, fallback, type icon
- `extension/popup/popup.js` — Rewritten with shacl-renderer integration, handleTypeChange(), extractTitle()
- `extension/popup/popup.css` — Extended with 300+ lines for dynamic form elements
- `backend/app/commands/handlers/object_create.py` — Patched list-value iteration
- `.gsd/milestones/M014/slices/S02/tasks/T02-PLAN.md` — Added Observability Impact section
