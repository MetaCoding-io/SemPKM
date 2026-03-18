# S02: SHACL Form Renderer + Type Selector — UAT

**Milestone:** M014
**Written:** 2026-03-18

## UAT Type

- UAT mode: mixed (artifact-driven syntax checks + live-runtime API tests + manual sideload visual verification)
- Why this mode is sufficient: The renderer module is testable via syntax checks and Node.js rendering against live API. Visual verification requires manual Chrome sideload since Playwright cannot interact with extension popups.

## Preconditions

- Docker stack running (`docker compose up -d` from project root)
- At least two Mental Models installed: basic-pkm and crm (for type variety)
- API key configured in extension options (from S01)
- Extension sideloaded in Chrome via `chrome://extensions` → Load unpacked → `extension/` directory
- User logged in to SemPKM web app (for workspace verification)

## Smoke Test

Open the extension popup on any page → type selector shows types from both basic-pkm and crm models → select "Contact" → form renders with multiple grouped fields → fill firstName/lastName/email → click Save → object created (no error toast).

## Test Cases

### 1. Note type renders simple fields

1. Open the extension popup on any page
2. Select "Note" from the type selector
3. **Expected:** Form renders with ~6 fields (title, tags, etc.), no groups (or one group), all text inputs. No date/boolean/enum fields visible.

### 2. CRM Contact renders all property types with groups

1. Open the extension popup on any page
2. Select "Contact" from the type selector
3. **Expected:** Form renders 12 fields across 6 collapsible groups:
   - String fields: firstName, lastName, email, phone, jobTitle (text inputs)
   - Enum select: relationship (dropdown with options)
   - Date: followUpDate (`<input type="date">`)
   - Boolean: followUpDone (Yes/No `<select>`)
   - Object reference: worksAt, knows (text input + hidden IRI input, marked with data-target-class)
   - Multi-value: tags (text input with Add button), knows (multiple reference slots)
4. First group should be open (`<details open>`), others collapsed

### 3. CRM Deal renders default values

1. Open the extension popup
2. Select "Deal" from the type selector
3. **Expected:** Form shows decimal field (dealValue, `<input type="number" step="0.01">`), enum selects (dealStage, currency), and currency field pre-populated with "USD"

### 4. Task type renders enum selects and date

1. Open the extension popup
2. Select "Task" from the type selector
3. **Expected:** Form shows enum selects (status, priority), date field (dueDate), and object reference (assignedTo). ~18 fields across 4 groups.

### 5. Type switching clears and re-renders form

1. Open popup, select "Contact" — form renders
2. Switch to "Note" — form re-renders with Note fields
3. Switch back to "Contact" — form re-renders with Contact fields
4. **Expected:** Each switch fully replaces the form content. No leftover fields from previous type. Loading spinner appears briefly during each fetch.

### 6. Save CRM Contact with multi-value tags

1. Open popup, select "Contact"
2. Fill in: firstName = "Alice", lastName = "Test", email = "alice@example.com"
3. In tags field, type "vip", click Add, type "partner", click Add
4. Click Save
5. **Expected:** Success toast shown. Object created in SemPKM. Navigate to the workspace Object Browser → find the new Contact → verify firstName, lastName, email properties exist, and both tags ("vip", "partner") appear as separate values.

### 7. Source URL field persists across type changes

1. Open popup on a page with a URL (e.g., `http://localhost:3000/browser/`)
2. Note the Source URL field shows the current page URL (read-only)
3. Switch between types (Note → Contact → Deal)
4. **Expected:** Source URL field remains visible and unchanged across all type switches. It stays below the dynamic form area.

### 8. Notes textarea preserves content across type changes

1. Open popup, type "Some notes here" in the Notes textarea
2. Switch from "Note" to "Contact"
3. **Expected:** Notes textarea content preserved ("Some notes here" still visible)

### 9. Loading spinner during shape fetch

1. Open popup on a page
2. Select a type from the dropdown
3. **Expected:** Brief loading spinner visible in the form area while shape loads. Spinner disappears when form renders. If network is slow, spinner remains until response arrives.

### 10. Form fallback on shape fetch failure

1. Disconnect from the SemPKM instance (stop Docker or change API URL to invalid)
2. Open popup and select a type
3. **Expected:** Error toast appears. Form falls back to simple title-only input. Save still possible with just a title.

## Edge Cases

### Empty groups not rendered

1. If a type has a SHACL group where all properties are in the skip list (created, modified, body)
2. **Expected:** That group's `<details>` element should not appear in the form at all

### Skip paths excluded

1. Select any type (e.g., Contact)
2. Inspect the rendered form in DevTools (`#dynamic-form`)
3. **Expected:** No input with `data-path` containing "dcterms/created", "dcterms/modified", or where field name is "body"

### Multi-value add and remove

1. Select Contact, find the tags field
2. Click "Add" 3 times — should create 3 tag input rows
3. Click the remove (×) button on the middle row
4. **Expected:** Middle row removed, 2 rows remain. Click Save → only 2 tag values submitted.

### Required field validation

1. Select Contact
2. Leave firstName empty (if it's marked required)
3. Click Save
4. **Expected:** Title extraction cascade finds another field or shows validation error. Required fields have red asterisk (*) indicator.

### Helptext toggle

1. Select a type that has helptext on a property (CRM Contact has help descriptions)
2. Look for a small "?" or info icon button next to a field label
3. Click it
4. **Expected:** Helptext description text appears/disappears below the field label

## Failure Signals

- Type selector shows no types or shows error → API connection issue or getTypes() failure
- Selecting a type shows no form fields → shacl-renderer.js not loaded or renderForm() returning empty fragment
- Form renders but Save fails → getFormValues() returning wrong structure, or object_create.py rejecting list values
- Multi-value tags save as single "[tag1, tag2]" string → object_create.py list iteration patch missing
- Console shows CSP violation → inline event handler present (onclick/onchange in HTML or JS strings)
- `#dynamic-form` container is empty after type selection → handleTypeChange() or renderForm() failing silently

## Requirements Proved By This UAT

- EXT-02 (SHACL forms) — Dynamic form rendering for all standard property types, groups, multi-value, validation indicators across 4 type families (Note, Contact, Deal, Task)

## Not Proven By This UAT

- EXT-01 (popup capture) — Full end-to-end capture flow is S01 territory, though Save from dynamic form is exercised here
- Object reference field search-as-you-type — S04 scope
- Auto-population from page metadata — S03 scope
- Cross-browser (Firefox) rendering — S05 scope

## Notes for Tester

- Chrome extension popups cannot be automated via Playwright. All popup tests require manual sideload via `chrome://extensions` → Developer mode → Load unpacked → select the `extension/` directory.
- After loading the extension, click the extension icon in the Chrome toolbar (or pin it) to open the popup. The popup closes if you click outside it — use DevTools on the popup by right-clicking the popup → Inspect.
- The type icon (colored dot) next to the type selector should reflect the Lucide icon color from the model configuration.
- Contact objects may display as IRI fragments (e.g., `urn:sempkm:...`) in the Object Browser explorer tree — this is a pre-existing label resolution issue, not an S02 bug. The object detail page should show all properties correctly.
