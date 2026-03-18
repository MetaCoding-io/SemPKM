---
id: T01
parent: S02
milestone: M014
provides:
  - SHACL form renderer module (renderForm, renderField, getFormValues)
key_files:
  - extension/shared/shacl-renderer.js
key_decisions:
  - data-target-class placed on both .reference-field wrapper and visible search input for S04 flexibility
patterns_established:
  - el() helper for imperative DOM creation without inline handlers
  - createInput() dispatch matching Jinja2 _field.html macro order exactly
observability_surfaces:
  - Chrome DevTools Elements panel — inspect #dynamic-form container for rendered DOM with data-path attributes
duration: 25m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: Build SHACL form renderer module

**Created `extension/shared/shacl-renderer.js` — ES module exporting `renderForm()`, `renderField()`, and `getFormValues()` for converting SHACL shape JSON into Chrome MV3 CSP-compliant HTML form elements.**

## What Happened

Built the core SHACL form renderer as a pure function module that takes a `ShapeResponse` JSON object (from `GET /api/shapes/{type_iri}`) and produces a `DocumentFragment` via imperative DOM manipulation. The dispatch order matches the Jinja2 `_field.html` macro exactly:

1. `in_values` → `<select>` with options
2. `target_class` → `.reference-field` with visible search input + hidden IRI input
3. `xsd:date` → `<input type="date">`
4. `xsd:dateTime` → `<input type="datetime-local">`
5. `xsd:boolean` → Yes/No `<select>` returning `"true"`/`"false"` strings
6. `xsd:integer` → `<input type="number" step="1">`
7. `xsd:decimal/float/double` → `<input type="number" step="0.01">`
8. `xsd:anyURI` → `<input type="url">`
9. Tags/keywords path → `<input type="text">`
10. Default → `<input type="text">`

Multi-value fields wrap inputs in `.multi-value-list` with add/remove buttons using `addEventListener()`. Groups render as `<details class="form-group-section">` with first group open. Skip paths filter `dcterms:created`, `dcterms:modified`, and body properties. Ungrouped required fields render directly; ungrouped optional fields go in a collapsed "Additional Fields" section.

`getFormValues(container)` walks all `[data-path]` elements, groups same-path inputs into arrays for multi-value, and omits empty values.

## Verification

- `node --check extension/shared/shacl-renderer.js` — exit 0, syntax valid
- `node --check extension/popup/popup.js` — exit 0, unmodified, still valid
- Grep for inline handlers (`onclick`, `onchange`, etc.) — zero matches
- Three exports confirmed: `renderForm`, `renderField`, `getFormValues`
- All 10 XSD type dispatches present with full IRIs via `XSD` constant prefix
- `data-target-class` present on both `.reference-field` wrapper and visible search input
- `data-path` on all value-bearing inputs; NOT on visible reference search input (hidden input only)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `node --check extension/shared/shacl-renderer.js` | 0 | ✅ pass | <1s |
| 2 | `node --check extension/popup/popup.js` | 0 | ✅ pass | <1s |
| 3 | `grep -n 'onclick\|onchange' extension/shared/shacl-renderer.js` | 1 (no match) | ✅ pass | <1s |
| 4 | `grep -c 'export function' extension/shared/shacl-renderer.js` | 0 (3 matches) | ✅ pass | <1s |

## Diagnostics

- **Inspection:** Chrome DevTools → Elements panel on popup → `#dynamic-form` container shows rendered DOM tree after T02 wires it in
- **Field tracing:** Every value-bearing input has `data-path` matching the full SHACL property IRI
- **Reference fields:** `.reference-field[data-target-class]` wrapper enables S04 search-as-you-type enhancement
- **Failure mode:** Malformed shape data produces empty/partial fragment — no exceptions thrown, falls through to default text inputs

## Deviations

- File is 588 lines vs estimated 200-350 — includes comprehensive JSDoc, `el()` DOM helper, and `cloneEmptyInput()` for multi-value. Functional code is proportional.
- Added `data-target-class` to both the `.reference-field` wrapper div AND the visible search input (plan was ambiguous — step 3 says visible input, must-have says wrapper). Both present for S04 flexibility.

## Known Issues

None.

## Files Created/Modified

- `extension/shared/shacl-renderer.js` — New module: SHACL form renderer with 3 exports
- `.gsd/milestones/M014/slices/S02/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
