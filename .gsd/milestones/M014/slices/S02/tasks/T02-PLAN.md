---
estimated_steps: 9
estimated_files: 3
---

# T02: Wire Renderer into Popup, Restructure HTML, Add CSS, and Verify

**Slice:** S02 — SHACL Form Renderer + Type Selector
**Milestone:** M014

## Description

Connect `shacl-renderer.js` to the popup lifecycle. Restructure `popup.html` to replace hardcoded form fields with a `#dynamic-form` container. Update `popup.js` so the type selector `change` event fetches the shape and re-renders via `renderForm()`, and `handleSave()` extracts values via `getFormValues()`. Add CSS for form groups, multi-value lists, helptext, and required markers in the 380px popup viewport. Verify against all 4 test types in a running Docker stack.

**Relevant skill:** None required — vanilla JS + CSS.

## Steps

1. **Restructure popup.html.** Replace the hardcoded `title-input`, `body-input` form groups with a `<div id="dynamic-form" class="dynamic-form"></div>` container. Inside, add a `<div id="form-loading" class="form-loading hidden">` with a spinner for shape-loading state, and a `<div id="form-fallback" class="form-fallback hidden">` containing a simple title input for the no-shape case. Keep the Notes textarea (`body-input`) as a fixed field below `#dynamic-form` — body is always available for free-text capture (the renderer skips body fields from the shape, but the popup always offers a notes area). Keep Source URL field (`url-input`) below notes. Keep the save button. Add a `<div id="selected-type-icon" class="selected-type-icon hidden"></div>` next to the type selector for icon display.

2. **Update popup.js imports and module state.** Add `import { renderForm, getFormValues } from '../shared/shacl-renderer.js';`. Add module-scope variables: `let loadedTypes = []` (to store type info including icons), `let currentShape = null` (the active shape response). Update DOM references: add `$dynamicForm`, `$formLoading`, `$formFallback`, `$typeIcon`, `$notesInput` (the body textarea, renamed for clarity). Remove direct references to the old `$titleInput` (title is now inside the dynamic form or fallback).

3. **Update `init()` function.** After fetching types, store them in `loadedTypes`. After populating type selector, if `defaultType` is set and matches a loaded type, trigger `handleTypeChange()` to auto-render the shape. If no default type, show the fallback (simple title input).

4. **Implement `handleTypeChange()` async function.** On type selector `change`:
   - If value is empty: clear `#dynamic-form`, show fallback, set `currentShape = null`, return.
   - Show loading spinner, hide fallback.
   - Call `client.getShape(typeIri)` — wrap in try/catch.
   - On success: call `renderForm(shape)`, clear `#dynamic-form`, append fragment, store `currentShape = shape`. Log: `[SemPKM] Shape loaded for {typeIri}: {N} properties, {M} groups`. Update type icon display from `loadedTypes` matching the IRI.
   - On failure: show toast error, show fallback, log warning.
   - Hide loading spinner.
   - Bind this to `$typeSelect`'s `change` event.

5. **Update `handleSave()` function.** When `currentShape` is active:
   - Call `getFormValues($dynamicForm)` → `properties` object.
   - Find the title value: look for a property key containing `title` (case-insensitive path match). If not found or empty, show validation error and return.
   - Add body: if `$notesInput.value.trim()` is non-empty, add `'sempkm:body': body` to properties (using the compact IRI — the backend's `_resolve_predicate()` also handles compact IRIs).
   - Add URL: if `$urlInput.value.trim()` is non-empty, add `'schema:url': url` to properties.
   - Call `client.createObject({ type: typeIri, properties })`.
   - On success: show toast, reset form (clear dynamic form inputs, clear notes, keep type selector).
   - On failure: show toast error.
   
   When `currentShape` is null (fallback mode):
   - Read title from fallback input. Validate non-empty.
   - Build properties with `'dcterms:title'`, optional body, optional URL.
   - Same createObject call.

6. **Update `populateTypeSelector()` to store type metadata.** Modify the function (or add a separate step) so that `loadedTypes` retains the full type objects including `icon` and `icon_color`. When a type is selected, update the `$typeIcon` element to show a small colored indicator or icon name next to the selector. Since we can't render Lucide SVGs inside `<option>` elements, show the icon as a label badge next to the `<select>` using CSS — e.g., a small colored dot or the icon name as text.

7. **Add CSS for dynamic form elements.** In `popup.css`, add styles for:
   - `.dynamic-form` — container with same padding/gap as `.capture-form`
   - `details.form-group-section` — collapsible group with styled summary: `font-weight: 600`, `font-size: 12px`, `text-transform: uppercase`, `color: #64748b`, `cursor: pointer`, padding, border-bottom. `details[open] > summary` with different state. Match the group aesthetic from the web app but compact for popup.
   - `.form-group-section .form-group-content` — inner content with vertical gap
   - `.form-field` — each field wrapper with bottom margin
   - `.form-field > label` — match existing `.form-group > label` style (11px, uppercase, slate)
   - `.required-marker` — `color: #ef4444; font-weight: 700`
   - `.field-help` — `font-size: 11px; color: #94a3b8; margin-top: 2px`
   - `.btn-helptext-toggle` — small inline button, subtle
   - `.field-helptext` — expandable box with light background, border, small text
   - `.multi-value-list` — flex column with small gap
   - `.multi-value-item` — flex row: input takes `flex:1`, remove button compact
   - `.btn-remove-value` — small red-ish × button, `flex-shrink: 0`
   - `.btn-add-value` — small text button: `+ Add {name}`, muted color, hover accent
   - `.reference-field` — wrapper for text + hidden input
   - `.form-loading` — centered small spinner (reuse `.btn-spinner` animation)
   - `.default-value` — subtle border color indication (e.g. `border-color: #a5b4fc`)
   - `.form-fallback` — same styles as existing form-group
   - `.selected-type-icon` — small colored dot next to type selector
   - Ensure popup scrolls when content exceeds viewport: `.popup-container { max-height: 600px; overflow-y: auto; }` or similar

8. **Validate JS syntax.** Run `node --check extension/popup/popup.js` — must pass.

9. **Live verification.** Start the Docker stack (`docker compose up -d`). Sideload the extension in Chrome (chrome://extensions → Developer mode → Load unpacked → select `extension/` directory). Open the popup on any page. Test:
   - Select "Note" (basic-pkm) → verify simple string fields render, no groups (or single group)
   - Select "Contact" (CRM) → verify 12 fields across 6 groups: string fields (firstName, lastName, email, phone, jobTitle), enum select (relationship), date (followUpDate), boolean select (followUpDone), object reference placeholders (worksAt, knows), multi-value (tags, knows). Groups are collapsible `<details>`.
   - Select "Deal" (CRM) → verify decimal (dealValue), enum selects (dealStage, currency), default "USD" in currency
   - Select "Task" (basic-pkm) → verify enum selects (status, priority), date (dueDate), object reference (assignedTo)
   - Fill a Contact form and save → verify object created in SemPKM workspace with all properties
   - Test multi-value: add 3 tags → save → verify 3 separate tag triples
   - Switch between types → form re-renders cleanly without stale fields

## Must-Haves

- [ ] `#dynamic-form` container replaces hardcoded fields in popup.html
- [ ] Type selector `change` triggers shape fetch → `renderForm()` → DOM insertion
- [ ] Default type auto-fetches shape on popup load
- [ ] Loading spinner shows during shape fetch
- [ ] Fallback title input when no shape loaded
- [ ] `handleSave()` uses `getFormValues()` for dynamic form, validates title presence
- [ ] Notes textarea remains as fixed field below dynamic form
- [ ] Source URL field remains fixed and read-only
- [ ] Body value from notes textarea sent as `sempkm:body`
- [ ] Property keys use full IRI paths from the shape (not compact IRIs)
- [ ] CSS fits all form elements in 380px popup width
- [ ] Groups, multi-value, helptext, required markers all styled
- [ ] Popup scrolls when content exceeds viewport height
- [ ] All 4 test types render correctly (Note, Contact, Deal, Task)
- [ ] Saved Contact object appears in workspace with all populated properties
- [ ] `node --check` passes on popup.js

## Verification

- `node --check extension/popup/popup.js` — exit code 0
- Extension sideloaded in Chrome → popup renders 4 different type forms correctly
- CRM Contact save → object visible in SemPKM workspace with properties
- Multi-value tags save → 3 tags appear as separate values
- Type switching re-renders form without stale DOM
- No JS errors in popup DevTools console during normal operation

## Inputs

- `extension/shared/shacl-renderer.js` from T01 — provides `renderForm()` and `getFormValues()` exports
- `extension/popup/popup.html` — current popup shell with hardcoded fields (to be restructured)
- `extension/popup/popup.js` — current popup logic with `init()`, `handleSave()`, `populateTypeSelector()` (to be updated)
- `extension/popup/popup.css` — current base styles (to be extended)
- `extension/shared/api-client.js` — `SemPKMClient.getShape(typeIri)` returns `ShapeResponse` JSON
- S01 Summary: popup uses ES modules, `showToast(msg, type)` for feedback, `setConnectionDot()` for health, `setSaving()` for button state. `getSettings()` returns `{instanceUrl, apiKey, defaultType, autoFillTitle, ...}`.

## Expected Output

- `extension/popup/popup.html` — restructured with `#dynamic-form` container, notes textarea, URL field, type icon display
- `extension/popup/popup.js` — updated with shape fetch on type change, `renderForm()` integration, `getFormValues()` in save flow
- `extension/popup/popup.css` — extended with styles for groups, multi-value, helptext, required markers, loading state, scrollable popup
