# S02: SHACL Form Renderer + Type Selector — Research

**Date:** 2026-03-18
**Status:** Complete

## Summary

S02 replaces the popup's hardcoded title/body/URL form with a dynamic SHACL-driven form that changes when the user selects a different type. The work is entirely in the extension — no backend changes. The `GET /api/shapes/{type_iri}` endpoint already returns structured JSON with all the metadata the renderer needs (properties with datatypes, constraints, groups, helptext, default values). The popup's type selector already loads types from `GET /api/types` (S01). What's missing is: (1) a JS module that converts shape JSON into HTML form elements, (2) wiring the type selector `change` event to fetch the shape and re-render, and (3) updating the save handler to extract values from the dynamic form instead of the hardcoded fields.

The CRM Contact shape exercises the widest variety of field types: string, date, boolean, enum (sh:in), object reference (sh:class), multi-value (tags with no maxCount), and 6 property groups. This is the validation target per the roadmap. Object reference fields get a placeholder input in S02 (text input with `data-target-class` attribute) — the full search-as-you-type picker is S04's scope.

## Recommendation

**Build the renderer as a pure function module**, `extension/shared/shacl-renderer.js`, that takes shape JSON and returns a `DocumentFragment`. No global state, no DOM queries, no side effects. This makes it testable (pass JSON, assert on the returned DOM) and isolates the rendering concern from popup lifecycle. The popup wires it into the form container on type change.

**Keep the existing title/body/URL fields as fallback** when no shape is loaded (unselected type or failed fetch). The dynamic form replaces the form container interior only when a shape is successfully fetched.

**Skip the body/notes field from shape rendering.** The Jinja2 template skips `sempkm:body` and `dcterms:created/modified` from the form fields — the extension should do the same. The body field has its own dedicated textarea outside the SHACL form.

## Implementation Landscape

### Key Files

- `extension/shared/shacl-renderer.js` — **New.** The SHACL form renderer module. Pure function: `renderForm(shapeResponse) → DocumentFragment`. Contains `renderField(prop)`, `renderGroup(group, props)`, `getFormValues(container) → {path: value}` exports.
- `extension/popup/popup.js` — **Modify.** Wire type selector `change` → `client.getShape(typeIri)` → `renderForm()` → insert into form container. Update `handleSave()` to call `getFormValues()` instead of reading hardcoded field IDs. Keep title input outside the dynamic form (always required). Retain body textarea and URL input as fixed fields.
- `extension/popup/popup.html` — **Modify.** Replace the hardcoded title/body/URL form fields with: (1) a `#dynamic-form` container div where the renderer inserts shape-driven fields, (2) keep the fixed source URL field below, (3) keep the save button. The title field moves into the dynamic form (rendered by the shape's dcterms:title property if present, or always present as a fixed input when the shape lacks it).
- `extension/popup/popup.css` — **Modify.** Add styles for form groups (`<details>` elements), multi-value lists (add/remove buttons), field helptext, required indicators, validation feedback, and the compact layout for the 380px popup viewport.

### Existing Infrastructure (no changes needed)

- `extension/shared/api-client.js` — `client.getShape(typeIri)` already exists and returns `ShapeResponse` JSON.
- `extension/shared/storage.js` — Settings already wired, `getClient()` returns configured client.
- `backend/app/api/router.py` — `GET /api/shapes/{type_iri}` returns `ShapeResponse` Pydantic model via `asdict()` from `NodeShapeForm` dataclass. Fields: `shape_iri`, `target_class`, `label`, `groups[]`, `properties[]`, `helptext`.
- `backend/app/commands/handlers/object_create.py` — `_resolve_predicate()` accepts full IRIs from shape `path` fields directly.

### Shape JSON → HTML Mapping

The renderer dispatches on property attributes in this order (matching `_field.html`):

| Condition | HTML Widget | Notes |
|---|---|---|
| `in_values.length > 0` | `<select>` with options | Enum constraint (sh:in) — e.g. relationship: colleague/client/friend |
| `target_class != null` | `<input type="text">` + `<input type="hidden">` | Object reference placeholder. S02 renders the visible text input with `data-target-class` attr + hidden IRI input. S04 adds search-as-you-type. |
| `datatype == xsd:date` | `<input type="date">` | |
| `datatype == xsd:dateTime` | `<input type="datetime-local">` | Strip timezone for value |
| `datatype == xsd:boolean` | `<select>` Yes/No | Matches Jinja2 — not a checkbox |
| `datatype == xsd:integer` | `<input type="number" step="1">` | |
| `datatype == xsd:decimal/float/double` | `<input type="number" step="0.01">` | |
| `datatype == xsd:anyURI` | `<input type="url">` | |
| path contains `tags` or `keywords` | `<input type="text">` | Tag field — simplified, no autocomplete (no htmx in extension) |
| default | `<input type="text">` | xsd:string or unknown datatype |

Multi-value: when `max_count == null` or `max_count > 1`, render a `.multi-value-list` container with one input + "× Remove" button + "+ Add" button below. Clone the input type for new items.

Groups: render as `<details open>` with `<summary>` label, matching the Jinja2 `_group.html` pattern. Properties without a group are rendered outside any details element — required ones first, optional ones in a collapsed "Advanced" details.

### Skip Paths

The renderer should skip these property paths (matching `object_form.html` logic):
- `http://purl.org/dc/terms/created`
- `http://purl.org/dc/terms/modified`
- Properties where path contains `body` (the body has its own dedicated editor/textarea)

### Form Value Extraction

`getFormValues(container)` walks all `[data-path]` inputs/selects inside the container and returns a flat `{path: value}` object. Multi-value fields produce `{path: [value1, value2, ...]}`. Empty values are omitted. Boolean selects return `"true"` / `"false"` strings (matching `_to_rdf_value` in the object_create handler).

For object references, the hidden input's value (an IRI) is what gets sent in properties. If empty, skip it — S04 will handle population.

### Popup HTML Restructure

Current popup HTML has hardcoded `title-input`, `body-input`, `url-input`. The new structure:

```
<form id="capture-form">
  <div class="form-group">Type selector (unchanged)</div>
  <div id="dynamic-form" class="dynamic-form">
    <!-- SHACL renderer inserts form groups + fields here -->
    <!-- Falls back to simple title/body fields when no shape loaded -->
  </div>
  <div class="form-group">Source URL (always visible, read-only)</div>
  <button type="submit">Save</button>
</form>
```

The dynamic form container is emptied and repopulated on every type change. A loading spinner shows during shape fetch.

### Type Selector Enhancement

The type selector already groups by model via `<optgroup>` (S01). S02 adds:
- Icon display: each `<option>` gets a data attribute with the Lucide icon name from `TypeInfo.icon`. CSS can't render icons inside `<option>` elements, but the selected type's icon can be shown as a label next to the select.
- The type selector fires `change` → fetch shape → render form. On initial load, if `defaultType` is set, auto-fetch its shape.

### Build Order

1. **shacl-renderer.js** — Pure renderer module. Start with string/date/boolean/select, then add multi-value, groups, reference placeholder, helptext. Testable in isolation via `node --check` for syntax + manual Chrome DevTools for DOM output.
2. **popup.html restructure** — Replace hardcoded fields with `#dynamic-form` container. Keep URL input and save button.
3. **popup.js wiring** — Type selector change handler fetches shape, calls renderer, inserts into container. Update `handleSave()` to use `getFormValues()`.
4. **popup.css additions** — Compact form group styles, multi-value layout, helptext toggle, required markers, validation states. Must fit in 380px width.
5. **Verification** — Load extension in Chrome, select CRM Contact, verify all 12 fields render correctly across 6 groups with correct input types. Save a Contact with populated fields, check object in SemPKM workspace.

### Verification Approach

1. `node --check extension/shared/shacl-renderer.js` — syntax validation
2. `node --check extension/popup/popup.js` — syntax validation
3. Load extension in Chrome (sideload) → open popup → select type → verify:
   - "Note" (basic-pkm): simple string fields, no groups
   - "Contact" (CRM): 12 fields, 6 groups, enum (relationship), date (followUpDate), boolean (followUpDone), object reference (worksAt, knows), multi-value (tags, knows)
   - "Deal" (CRM): decimal (dealValue), enum (dealStage, currency), default value (currency = USD)
   - "Task" (basic-pkm): enum (status, priority), date (dueDate), object reference (assignedTo)
4. Save a CRM Contact with filled fields → verify properties appear in SemPKM workspace object view
5. Verify multi-value: add 3 tags, save, verify all 3 appear as separate triples
6. Verify groups render as collapsible `<details>` elements
7. Verify required fields show asterisk indicator
8. Verify form helptext toggle shows/hides markdown content

## Constraints

- **380px popup width** — Form groups must stack vertically, no side-by-side columns. Labels above inputs. Multi-value add/remove buttons must be compact.
- **No htmx in extension** — The Jinja2 form template's reference search uses `hx-get="/browser/search"`. The extension renderer must use vanilla JS event listeners + `fetch()`. For S02, reference fields are placeholder only (S04 adds search).
- **No build step** — Vanilla JS, ES modules. No JSX, no template literals with syntax highlighting. The renderer builds DOM imperatively with `document.createElement()`.
- **Chrome MV3 CSP** — No inline event handlers (`onclick`). Must use `addEventListener()` exclusively.

## Common Pitfalls

- **Property `path` is a full IRI, not a compact IRI.** The shape response returns `"path": "urn:sempkm:model:crm:firstName"`, not `"path": "crm:firstName"`. The `_resolve_predicate()` handler in `object_create.py` accepts full IRIs (checks for `://` or `urn:` prefix). The extension should pass the `path` value as-is in the properties object.

- **Boolean select values must be strings `"true"`/`"false"`.** The backend's `_to_rdf_value()` converts these to `xsd:boolean` literals. A checkbox would send empty string or `"on"` which wouldn't round-trip. Using `<select>` with explicit string values matches the Jinja2 template.

- **Multi-value extraction must handle multiple inputs with the same `data-path`.** `getFormValues()` should collect all inputs sharing a `data-path` into an array when the property's `max_count != 1`.

- **Tags path detection.** The Jinja2 template checks `'tags' in prop.path or 'keywords' in prop.path` for tag-specific rendering. The JS renderer should replicate this check on the `path` string. In the CRM model, tags use `urn:sempkm:model:basic-pkm:tags` (bpkm:tags) which contains "tags".

- **Empty groups after skip-path filtering.** If all properties in a group are skipped (e.g. the Notes group's only property is `sempkm:body`), the group `<details>` should not be rendered. Filter group membership after applying skip paths.

- **Default values.** Properties with `default_value` (e.g. CRM Deal currency = "USD") should pre-populate the input. The Jinja2 template adds a `default-value` CSS class for visual indication.

## Open Risks

- **Form height in popup viewport.** The CRM Contact shape has 12 fields across 6 groups. If all groups are expanded, the popup content exceeds the viewport. Collapsible groups mitigate this (only first group expanded by default, rest collapsed). The popup body should scroll.
- **Multi-value DOM cloning.** The Jinja2 template clones DOM nodes for new multi-value items. The JS equivalent must correctly duplicate the input type (text, select, reference wrapper) and reset values. Off-by-one in index generation could cause duplicate IDs.
