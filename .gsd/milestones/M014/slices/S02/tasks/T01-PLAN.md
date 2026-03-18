---
estimated_steps: 8
estimated_files: 1
---

# T01: Build SHACL Form Renderer Module

**Slice:** S02 — SHACL Form Renderer + Type Selector
**Milestone:** M014

## Description

Create `extension/shared/shacl-renderer.js` — a pure function module that converts SHACL shape JSON (from `GET /api/shapes/{type_iri}`) into HTML form elements via imperative DOM manipulation. This is the core S02 deliverable and the highest-risk piece. The module must handle all ~10 property types the web app supports, multi-value fields, collapsible groups, skip paths, required indicators, helptext, and default values — all without htmx, without a build step, and using `addEventListener()` exclusively (Chrome MV3 CSP).

The module produces a `DocumentFragment` that the popup inserts into a container div. It also exports `getFormValues(container)` for extracting form data as `{path: value}` pairs. S04 will later enhance object reference fields (which this task renders as placeholder text + hidden IRI inputs) with search-as-you-type.

**Relevant skill:** None required — this is vanilla JS DOM manipulation.

## Steps

1. **Create the module file** `extension/shared/shacl-renderer.js` with ES module exports.

2. **Define constants and skip-path logic.** Create `SKIP_PATHS` set containing `http://purl.org/dc/terms/created` and `http://purl.org/dc/terms/modified`. Create `isBodyProperty(prop)` that returns true when `prop.name && prop.name.toLowerCase() === 'body'`. Create `isTagProperty(prop)` that checks `prop.path.includes('tags') || prop.path.includes('keywords')`. Create `isMultiValue(prop)` that returns `prop.max_count === null || prop.max_count === undefined || prop.max_count > 1`.

3. **Build `renderField(prop)` function.** Takes a single property object (matching `PropertyShapeInfo` schema: `{path, name, datatype, target_class, order, group, min_count, max_count, in_values, default_value, description, helptext}`). Returns a `<div class="form-field">` element. Dispatch order (matching `_field.html` exactly):
   - `prop.in_values && prop.in_values.length > 0` → `<select>` with `<option value="">-- Select --</option>` + one option per value. Pre-select `default_value` if present.
   - `prop.target_class` → `.reference-field` wrapper with visible `<input type="text" placeholder="Search {name}...">` with `data-target-class` attribute + `<input type="hidden" data-path="{path}">`. The visible input does NOT have `data-path` — only the hidden one does.
   - `prop.datatype === 'http://www.w3.org/2001/XMLSchema#date'` → `<input type="date">`
   - `prop.datatype === 'http://www.w3.org/2001/XMLSchema#dateTime'` → `<input type="datetime-local">`
   - `prop.datatype === 'http://www.w3.org/2001/XMLSchema#boolean'` → `<select>` with options: `""` (-- Select --), `"true"` (Yes), `"false"` (No)
   - `prop.datatype === 'http://www.w3.org/2001/XMLSchema#integer'` → `<input type="number" step="1">`
   - `prop.datatype` ends with `decimal` or `float` or `double` → `<input type="number" step="0.01">`
   - `prop.datatype === 'http://www.w3.org/2001/XMLSchema#anyURI'` → `<input type="url" placeholder="https://...">`
   - `isTagProperty(prop)` → `<input type="text" placeholder="Type to add tags...">`
   - default → `<input type="text">`
   
   For all non-reference single inputs: set `data-path` attribute to `prop.path`. Set `value` to `prop.default_value` if present (add class `default-value`). Set `required` attribute if `prop.min_count > 0`.
   
   Add label row: `<label>` with `prop.name`, plus `<span class="required-marker">*</span>` if `min_count > 0`.
   
   Add description if `prop.description` is non-empty: `<small class="field-help">{description}</small>`.
   
   Add helptext toggle button + hidden helptext div if `prop.helptext` is non-empty. Use `addEventListener('click', ...)` to toggle visibility.

4. **Build multi-value wrapper.** When `isMultiValue(prop)` is true, wrap the input in a `.multi-value-list` container. Render one initial input + "× Remove" button. Add a "+ Add {name}" button below that clones the input (same type, empty value) and appends to the list. Remove button removes its `.multi-value-item` parent (but keep at least one input). Use `addEventListener` for add/remove buttons — no inline handlers.

5. **Build `renderGroup(group, properties)` function.** Takes a group object `{iri, label, order}` and array of properties. Returns a `<details class="form-group-section">` element with `<summary>{label}</summary>` and a content div containing `renderField()` output for each property. The group is only rendered if it has at least one property after skip-path filtering.

6. **Build `renderForm(shapeResponse)` function.** Takes the full shape response `{shape_iri, target_class, label, groups, properties, helptext}`. Returns a `DocumentFragment`. Processing:
   - Filter out skip-path and body properties from `properties`
   - Group properties by `group` IRI: properties where `prop.group` matches a group's `iri`
   - Ungrouped properties (where `prop.group` is null/undefined) split into: required ones first, then optional ones in a collapsible "Additional Fields" details
   - Sort groups by `order`, render each via `renderGroup()`
   - First group gets `open` attribute on `<details>`, rest are collapsed
   - Append ungrouped required fields directly (no wrapping details)
   - Append ungrouped optional fields in a collapsed "Additional Fields" details if any exist

7. **Build `getFormValues(container)` function.** Walks all elements with `[data-path]` inside `container`. For each unique path, if only one input has that path, return `{path: value}`. If multiple inputs share the same path (multi-value), return `{path: [value1, value2, ...]}`. Omit entries where all values are empty strings. For `<select>` elements, use `.value`. For `<input>` elements, use `.value`. Boolean selects naturally return `"true"` / `"false"` strings.

8. **Validate syntax.** Run `node --check extension/shared/shacl-renderer.js` — must pass with no errors.

## Must-Haves

- [ ] `renderForm(shapeResponse)` returns a DocumentFragment with correct DOM structure
- [ ] All 10 property types dispatch correctly (string, date, dateTime, boolean, integer, decimal, anyURI, enum, object reference, tags)
- [ ] Multi-value fields render with add/remove buttons and clone the correct input type
- [ ] Groups render as `<details>` elements with first group open, rest collapsed
- [ ] Skip paths filter out `dcterms:created`, `dcterms:modified`, and body properties
- [ ] Empty groups (all properties skipped) are not rendered
- [ ] Required fields show asterisk indicator
- [ ] Default values pre-populate inputs
- [ ] Object reference fields have `data-target-class` on the hidden input wrapper for S04
- [ ] `getFormValues()` correctly extracts single and multi-value properties, omitting empty values
- [ ] Boolean select returns `"true"` / `"false"` strings
- [ ] No inline event handlers — `addEventListener()` only
- [ ] `node --check` passes

## Verification

- `node --check extension/shared/shacl-renderer.js` — exit code 0
- Module exports: `renderForm`, `getFormValues` (and optionally `renderField` for unit-testing convenience)
- All constants use full XSD IRIs matching the backend `PropertyShapeInfo` schema (e.g. `http://www.w3.org/2001/XMLSchema#date`)
- No `onclick`, `onchange`, or other inline handlers in generated DOM

## Inputs

- `backend/app/api/router.py` lines 88-121 — `PropertyShapeInfo` and `ShapeResponse` Pydantic models define the exact JSON schema the renderer consumes. Fields: `path` (full IRI string), `name` (human label), `datatype` (full XSD IRI or null), `target_class` (IRI or null), `order` (float), `group` (group IRI or null), `min_count` (int, 0 = optional), `max_count` (int or null, null = unbounded), `in_values` (string array), `default_value` (string or null), `description` (string or null), `helptext` (string or null).
- `backend/app/templates/forms/_field.html` — The 205-line Jinja2 reference implementation. Dispatch order and HTML widget choices must match this macro.
- `backend/app/templates/forms/_group.html` — Group rendering as `<details open>` with `<summary>`.
- S01 Summary: the popup uses ES modules (`import` / `export`). Follow the same pattern.

## Expected Output

- `extension/shared/shacl-renderer.js` — New file exporting `renderForm(shapeResponse)`, `getFormValues(container)`, and `renderField(prop)`. ~200-350 lines of vanilla JS.
