# S04: Relationship Picker + Edge Creation — UAT

**Milestone:** M014
**Written:** 2026-03-18

## UAT Type

- UAT mode: mixed (artifact-driven for module structure + live-runtime for API integration)
- Why this mode is sufficient: The reference picker module is verifiable via syntax/export checks and DOM inspection. The edge creation flow requires a running Docker stack with objects to search against. Full in-browser extension testing is deferred to S05 E2E tests.

## Preconditions

- Docker test stack running (`docker compose -f docker-compose.test.yml up -d`) with API healthy on port 8901
- At least one Mental Model installed (CRM model preferred — has object reference fields like "Works At")
- At least one Company object created in the triplestore (for reference search results)
- Chrome browser available for extension sideloading

## Smoke Test

Open `extension/popup/popup.html` in a browser (or sideload the extension), select a type with object reference fields (e.g. CRM Contact), and verify that typing in a reference field triggers a dropdown with search results.

## Test Cases

### 1. Reference picker initialization on form render

1. Sideload the extension in Chrome
2. Configure the options page with `http://localhost:8901` and a valid API key
3. Click the extension icon to open the popup
4. Select "Contact" (CRM) from the type dropdown
5. Open DevTools console for the popup
6. **Expected:** Console shows `[SemPKM] Reference picker initialized: N fields` where N > 0 (at least the "Works At" reference field)

### 2. Search-as-you-type with debounce

1. With the Contact form open, locate the "Works At" reference field
2. Type a query that matches an existing Company (e.g. first 3 characters of a Company name)
3. **Expected:** After ~300ms pause, a dropdown appears below the field with matching suggestions. Each suggestion shows the object label and a type badge.
4. **Expected:** Console shows `[SemPKM] Search: "query" → M results (K after type filter)`

### 3. Type filtering restricts results

1. With the Contact form open, type a query in the "Works At" field that would match objects of multiple types
2. **Expected:** Only Company-type objects appear in the dropdown (the field's `data-target-class` filters results)
3. **Expected:** Console search log shows `M results (K after type filter)` where K ≤ M

### 4. Selection and clear

1. From the search results dropdown, click a suggestion
2. **Expected:** The search field shows the selected object's label, becomes read-only, and a × clear button appears
3. **Expected:** The dropdown closes and the field wrapper has class `.has-selection`
4. **Expected:** Console shows `[SemPKM] Reference selected: {label} ({iri})`
5. Click the × clear button
6. **Expected:** The selection is removed, the field becomes editable again, and the field is focused for a new search

### 5. Two-step save creates object and edges

1. Fill in the Contact form (at least a name/title)
2. Select a Company in the "Works At" reference field
3. Click Save
4. **Expected:** Toast shows "✓ Object created!" (or similar success message)
5. **Expected:** Console shows `[SemPKM] Edge created: {contactIri} → {worksAtPath} → {companyIri}`
6. Open the SemPKM workspace and find the newly created Contact
7. **Expected:** The Contact's Relations panel shows an edge to the selected Company

### 6. Edge failure shows warning toast without blocking object

1. Fill in the Contact form with a reference selection
2. Temporarily break the API (e.g. stop the Docker stack after the first save succeeds but before edges)
3. **Expected:** Object creation succeeds, but edge creation fails
4. **Expected:** Toast shows "✓ Object created, but N relationship(s) failed to save"
5. **Expected:** Console shows `[SemPKM] Edge creation failed: ...` warning

### 7. Multi-value reference field gets picker behavior

1. Open a type form that has a multi-value object reference field
2. Click the "+" add button to add a new reference field entry
3. **Expected:** The newly added field has search-as-you-type behavior (type in it and see dropdown)
4. **Expected:** The `sempkm:reference-field-added` custom event was dispatched (check console or Elements panel)

### 8. Stale query response discarded

1. In a reference field, type a query quickly, then immediately clear and type a different query
2. **Expected:** Only results for the second (current) query appear in the dropdown
3. **Expected:** No results from the first query flash briefly then get replaced

## Edge Cases

### Empty search results

1. Type a query that matches no objects (e.g. "zzzznonexistent")
2. **Expected:** Dropdown shows an empty/no-match state message (not just an invisible empty container)

### Short query (less than 2 characters)

1. Type a single character in a reference field
2. **Expected:** No search is triggered, no dropdown appears

### Outside click closes dropdown

1. Type a query to open the dropdown
2. Click anywhere outside the reference field wrapper
3. **Expected:** Dropdown closes

### Form reset after save preserves picker behavior

1. Save an object with a reference selection
2. After the save success, the form resets to create another object
3. Select a type again
4. **Expected:** Reference fields in the new form have working search-as-you-type (pickers re-initialized)

## Failure Signals

- No `[SemPKM] Reference picker initialized` log after selecting a type with reference fields → picker not wired into form render
- Dropdown never appears after typing → searchObjects API call failing or debounce not firing
- Edge created log missing after save with reference selection → two-step save not executing edge creation loop
- Inline event handlers found (`grep -rn "onclick" extension/shared/reference-picker.js` returns matches) → MV3 CSP violation
- `node --check` fails on any of the three JS files → syntax error introduced

## Requirements Proved By This UAT

- EXT-04 (relationship picker) — tests 1-8 prove search-as-you-type, type filtering, selection/clear, edge creation, multi-value support, and error handling

## Not Proven By This UAT

- Firefox compatibility (deferred to S05)
- Full automated E2E test coverage (deferred to S05 Playwright tests)
- Keyboard navigation within the dropdown (not implemented — mouse-only selection in v1)

## Notes for Tester

- The Docker test stack setup token may already be consumed. Use the magic-link auth flow to log in, then create an API key from the Admin page for extension configuration.
- CRM model must be installed for the "Works At" reference field to appear. If not installed, use Admin > Mental Models > Install and select the CRM model archive.
- Create at least one Company object before testing the reference picker, so search has something to find.
- The reference picker's search hits `POST /api/context-query` which searches across all object types — the type filter on the frontend narrows results after the API response. If the API returns no results at all, there may be no objects in the triplestore.
