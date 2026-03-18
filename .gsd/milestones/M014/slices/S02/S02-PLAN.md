# S02: SHACL Form Renderer + Type Selector

**Goal:** Replace the popup's hardcoded title/body/URL form with a dynamic SHACL-driven form that renders the correct fields when the user selects a type.
**Demo:** User opens the popup, selects "Contact" (CRM) from the type dropdown, and sees 12 fields across 6 collapsible groups with correct input types (string, date, boolean, enum select, object reference placeholder, multi-value tags). Selecting "Note" shows simple string fields. Saving a Contact with populated fields creates the object in SemPKM with all properties intact.

## Must-Haves

- `shacl-renderer.js` pure function module: `renderForm(shapeResponse) → DocumentFragment` and `getFormValues(container) → {path: value|[values]}`
- All standard property types rendered: string, date, dateTime, boolean (Yes/No select), integer, decimal, anyURI, enum (sh:in select), object reference placeholder (text + hidden IRI input with `data-target-class`), multi-value (add/remove), tags
- Groups rendered as collapsible `<details>` elements matching Jinja2 `_group.html` pattern
- Skip paths: `dcterms:created`, `dcterms:modified`, and properties with `name.toLowerCase() === "body"` 
- Empty groups (all properties skipped) not rendered
- Required field indicators (asterisk) and helptext toggle
- Type selector `change` event fetches shape via `client.getShape(typeIri)` and re-renders form
- Default type auto-fetches shape on popup load
- `handleSave()` uses `getFormValues()` to build properties object with full IRI paths
- Multi-value extraction collects all same-`data-path` inputs into arrays
- Boolean select values are strings `"true"` / `"false"`
- Object reference hidden inputs pass IRI values (empty = omitted)
- Default values pre-populate inputs (e.g. CRM Deal currency = USD)
- Form fits 380px popup width — groups stack vertically, labels above inputs
- Source URL field remains fixed outside the dynamic form
- Fallback to simple title field when no shape loaded or shape fetch fails
- No inline event handlers — `addEventListener()` only (Chrome MV3 CSP)
- Vanilla JS, ES modules, no build step

## Proof Level

- This slice proves: integration — extension renders SHACL shapes correctly and saves objects with all property types
- Real runtime required: yes (live shape data from `/api/shapes/{type_iri}`, save via `/api/commands`)
- Human/UAT required: no (agent verification via Chrome sideload + browser tools)

## Verification

- `node --check extension/shared/shacl-renderer.js` — syntax valid
- `node --check extension/popup/popup.js` — syntax valid
- Load extension in Chrome → open popup → select "Note" → renders simple string fields, no groups
- Select "Contact" (CRM) → renders 12 fields across 6 groups with correct input types: string (firstName, lastName, email, phone, jobTitle), enum select (relationship), date (followUpDate), boolean select (followUpDone), object reference placeholder (worksAt, knows), multi-value (tags, knows)
- Select "Deal" (CRM) → renders decimal (dealValue), enum selects (dealStage, currency), default value "USD" pre-populated in currency
- Select "Task" (basic-pkm) → renders enum selects (status, priority), date (dueDate), object reference (assignedTo)
- Save a CRM Contact with filled fields → verify object appears in SemPKM workspace with all properties
- Multi-value: add 3 tags, save, verify all 3 appear as separate triples
- Groups render as collapsible `<details>` elements — first group open, others collapsed
- Required fields show asterisk indicator
- Source URL field always visible, read-only, outside dynamic form

## Observability / Diagnostics

- Runtime signals: `[SemPKM] Shape loaded for {typeIri}: {N} properties, {M} groups` in popup DevTools console
- Inspection surfaces: Chrome DevTools → Elements panel on popup → `#dynamic-form` container shows rendered DOM; Console shows `[SemPKM]` lifecycle messages
- Failure visibility: Shape fetch errors show red toast with detail message; console.warn with full error object
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `extension/shared/api-client.js` (`SemPKMClient.getShape()`), `extension/shared/storage.js` (`getSettings()`), `extension/popup/popup.html` (popup shell), `extension/popup/popup.js` (type selector, save flow), `extension/popup/popup.css` (base styles)
- New wiring introduced in this slice: type selector `change` → shape fetch → `renderForm()` → DOM insertion; `handleSave()` → `getFormValues()` → property extraction from dynamic form
- What remains before the milestone is truly usable end-to-end: S03 (auto-population from page metadata + context menu), S04 (relationship picker replacing object reference placeholders), S05 (cross-browser, E2E tests, user guide)

## Tasks

- [x] **T01: Build SHACL form renderer module** `est:1h30m`
  - Why: The core S02 deliverable — a pure function module that converts shape JSON to HTML form elements. All ~10 property types, multi-value support, groups, skip paths, helptext. Must be testable in isolation and produce DOM that S04 can enhance for relationship search.
  - Files: `extension/shared/shacl-renderer.js`
  - Do: Create `shacl-renderer.js` with three exports: `renderForm(shapeResponse)` returns a DocumentFragment, `renderField(prop)` returns DOM for one property, `getFormValues(container)` returns `{path: value}` pairs. Dispatch on property attributes matching the Jinja2 `_field.html` macro: `in_values.length > 0` → `<select>`, `target_class` → text + hidden IRI input with `data-target-class`, `xsd:date` → `<input type="date">`, `xsd:dateTime` → `<input type="datetime-local">`, `xsd:boolean` → Yes/No `<select>`, `xsd:integer` → `<input type="number" step="1">`, `xsd:decimal/float/double` → `<input type="number" step="0.01">`, `xsd:anyURI` → `<input type="url">`, tags path → `<input type="text">`, default → `<input type="text">`. Multi-value: when `max_count == null || max_count > 1`, render `.multi-value-list` container with add/remove buttons, clone input type for new items. Groups: `<details>` with `<summary>` label, first group `open`, rest collapsed. Skip paths: `dcterms:created`, `dcterms:modified`, and properties where `name.toLowerCase() === "body"`. Required asterisk. Default values. Helptext toggle. All event listeners via `addEventListener()`. All inputs get `data-path` attribute. Object reference inputs get `data-target-class`. `getFormValues()` collects all `[data-path]` inputs, groups same-path multi-value into arrays, omits empty, returns `{path: value|[values]}`.
  - Verify: `node --check extension/shared/shacl-renderer.js` passes
  - Done when: Module exports `renderForm`, `renderField`, `getFormValues` and handles all 10 property types with correct HTML output per the dispatch table

- [x] **T02: Wire renderer into popup, restructure HTML, add CSS, and verify** `est:1h30m`
  - Why: Connects the renderer module to the popup lifecycle — type selector change fetches shape and re-renders the form container. Updates save flow to extract values from the dynamic form. Adds CSS for groups, multi-value, helptext in the 380px popup. Verifies against real types in a running Docker stack.
  - Files: `extension/popup/popup.html`, `extension/popup/popup.js`, `extension/popup/popup.css`
  - Do: (1) **popup.html**: Replace hardcoded title/body/URL form fields with `<div id="dynamic-form" class="dynamic-form"></div>` container. Keep Source URL field below the dynamic form (always visible, read-only). Keep the save button. Remove `title-input`, `body-input` elements (they move into the dynamic form or are generated by the renderer). Keep `title-error` for fallback validation. Add a loading spinner div `#form-loading` inside the dynamic form area. (2) **popup.js**: Import `renderForm`, `getFormValues` from `../shared/shacl-renderer.js`. Store loaded types array in module scope so type icon/info is accessible. Add `handleTypeChange()` async function: on type selector `change`, if value is empty show fallback (title-only input), otherwise call `client.getShape(typeIri)`, call `renderForm(shape)`, clear `#dynamic-form` and append the fragment. Show loading spinner during fetch. Log shape load details. On init, if `defaultType` is set, trigger `handleTypeChange` after types load. Update `handleSave()`: read type IRI from selector; if dynamic form is active, call `getFormValues($dynamicForm)` to build properties; find title from properties (key containing `title` or `dcterms:title`) and validate it's non-empty; merge source URL into properties as `schema:url` if non-empty; call `client.createObject({type: typeIri, properties})`. Handle body field: if a body-like value exists in properties, extract it separately (the popup's dedicated body textarea is gone — body comes from the shape's body field, but that's skipped by the renderer; instead, keep a Notes textarea always visible below the dynamic form for free-text capture → save as `sempkm:body`). (3) **popup.css**: Add styles for `.dynamic-form`, `details.form-group-section` (collapsible groups with summary styling), `.multi-value-list` and `.multi-value-item` (inline layout with remove button), `.btn-add-value` and `.btn-remove-value` (compact), `.field-help` (muted description text), `.btn-helptext-toggle` (small icon button), `.field-helptext` (expandable markdown content), `.required-marker` (red asterisk), `.reference-field` (text + hidden input wrapper), `.form-loading` (centered spinner), `.default-value` (subtle visual indication). All must fit in 380px width with proper vertical stacking. (4) **Verify**: Start Docker stack, sideload extension in Chrome, open popup on any page, test all 4 types (Note, Contact, Deal, Task), save a Contact with populated fields, verify object in workspace.
  - Verify: `node --check extension/popup/popup.js` passes; sideloaded extension popup renders correct fields for Note, Contact, Deal, and Task types; saved Contact appears in SemPKM workspace with all properties
  - Done when: Type selector change renders dynamic SHACL form, save flow extracts values correctly, CSS is compact and usable, all 4 test types verified

## Files Likely Touched

- `extension/shared/shacl-renderer.js` (new)
- `extension/popup/popup.html` (modify)
- `extension/popup/popup.js` (modify)
- `extension/popup/popup.css` (modify)
