# S06 UAT: Dashboard & Workflow Builder UX

## Preconditions

- Docker stack running (`docker compose up -d`)
- At least one user account exists
- At least one Mental Model installed (basic-pkm) with types that have classes
- Browser open to SemPKM workspace

---

## Test 1: Dashboard Builder Help Text

**Goal:** Verify every field in the dashboard builder has contextual help text.

1. Navigate to `/browser/dashboard/new`
2. Verify the Name, Description, and Layout fields each have a `<small class="field-help">` hint below them
3. Click "Add Block" and select "View Embed"
4. Verify the View Spec and Renderer fields have help text
5. Click "Add Block" and select "Markdown"
6. Verify the Content field has help text
7. Click "Add Block" and select "Create Form"
8. Verify the Target Class IRI field has help text
9. Click "Add Block" and select "Object Embed"
10. Verify the Object IRI field has help text
11. Click "Add Block" and select "SPARQL Result"
12. Verify the SPARQL Query and Label fields have help text

**Expected:** All fields have descriptive help text visible beneath them. Total count ≥ 13.

---

## Test 2: Workflow Builder Help Text

**Goal:** Verify every field in the workflow builder has contextual help text.

1. Navigate to `/browser/workflow/new`
2. Verify the Name and Description fields have help text
3. Click "Add Step"
4. Verify the step Label field has help text
5. Select step type "View" — verify the View dropdown has help text
6. Select step type "Dashboard" — verify the Dashboard dropdown has help text
7. Select step type "Form" — verify the Target Class IRI field has help text

**Expected:** All fields have help text. Total count ≥ 6.

---

## Test 3: Workflow View Step — No Renderer Dropdown

**Goal:** Verify the workflow "view" step uses a single view picker with auto-set renderer.

1. Navigate to `/browser/workflow/new`
2. Click "Add Step" and select step type "View"
3. Verify there is ONE dropdown (View selector) — NOT a second "Renderer" dropdown
4. Select a view from the dropdown (e.g., a table view)
5. Verify a renderer badge appears (e.g., "(table)") next to the view dropdown
6. Inspect DOM: `document.querySelector('[data-key="renderer_type"]')` should be a hidden input with the correct value (e.g., "table")
7. Change the view selection to a different renderer type (e.g., a graph view)
8. Verify the badge updates to reflect the new renderer type

**Expected:** Single view dropdown, auto-set renderer badge, hidden input value matches selected view's renderer.

---

## Test 4: Dashboard Builder — Class IRI Autocomplete

**Goal:** Verify Target Class IRI field offers search-as-you-type autocomplete.

1. Navigate to `/browser/dashboard/new`
2. Click "Add Block" and select "Create Form"
3. Click into the Target Class IRI search field
4. Type "Per" (partial match for "Person" or similar class)
5. Wait ~300ms for debounce
6. Verify a suggestions dropdown appears with matching class labels and IRIs
7. Click a suggestion
8. Verify the hidden input (`data-key="target_class"`) is set to the full IRI
9. Verify the visible input shows the selected value

**Expected:** Typing triggers autocomplete from `/browser/class-search`, selecting sets the hidden IRI value.

**Edge case:** Type a string that matches nothing (e.g., "xyzzynonexistent") — verify "No results" appears in the dropdown rather than an error or empty state.

---

## Test 5: Dashboard Builder — Object IRI Autocomplete

**Goal:** Verify Object IRI field offers search-as-you-type autocomplete.

1. Navigate to `/browser/dashboard/new`
2. Click "Add Block" and select "Object Embed"
3. Click into the Object IRI search field
4. Type the beginning of a known object label (e.g., first few chars of an existing Note or Project title)
5. Wait ~300ms for debounce
6. Verify suggestions dropdown shows matching objects with labels and IRIs
7. Click a suggestion
8. Verify the hidden input (`data-key="object_iri"`) is set to the selected object's IRI

**Expected:** Typing triggers autocomplete from `/browser/object-search`, selecting sets the hidden IRI value.

---

## Test 6: Workflow Builder — Class IRI Autocomplete

**Goal:** Verify the workflow form step's Target Class IRI has autocomplete.

1. Navigate to `/browser/workflow/new`
2. Click "Add Step" and select step type "Form"
3. Click into the Target Class IRI search field
4. Type a partial class name
5. Verify suggestions dropdown appears from `/browser/class-search`
6. Select a suggestion and verify the hidden input is set

**Expected:** Same autocomplete behavior as dashboard builder's create-form block.

---

## Test 7: Seed Data — Fresh User Gets Sample Data

**Goal:** Verify seed data creates sample dashboard and workflow for new users.

1. With no dashboards or workflows for the test user, restart the backend: `docker compose restart api`
2. Check logs: `docker compose logs api | grep -i seed`
3. Verify log shows seed data was created (e.g., `dashboard_created: True, workflow_created: True`)
4. Navigate to the dashboard list — verify "Getting Started" dashboard appears
5. Open it — verify it has a markdown welcome block and a view-embed block
6. Navigate to the workflow list — verify "Create & Review" workflow appears

**Expected:** Sample data created automatically on first startup with a user who has no dashboards/workflows.

---

## Test 8: Seed Data — Idempotency

**Goal:** Verify seed data doesn't duplicate on subsequent startups.

1. After Test 7, restart the backend again: `docker compose restart api`
2. Check logs: `docker compose logs api --since 1m | grep -i seed`
3. Verify no new seed data was created (seed was skipped because data already exists)
4. Verify there is still only ONE "Getting Started" dashboard and ONE "Create & Review" workflow

**Expected:** Seed function detects existing data and skips creation.

---

## Test 9: Autocomplete Error Handling

**Goal:** Verify autocomplete degrades gracefully when search fails.

1. Navigate to `/browser/dashboard/new`
2. Add a "Create Form" block
3. Open browser dev tools Network tab
4. Block requests to `/browser/class-search` (or disconnect backend temporarily)
5. Type in the Target Class IRI field
6. Verify the dropdown shows "No results" rather than throwing a JS error or hanging

**Expected:** Graceful degradation — no console errors, "No results" message shown.

---

## Test 10: Builder Error Display

**Goal:** Verify the `#builder-error` div surfaces save failures.

1. Navigate to `/browser/dashboard/new`
2. Leave the Name field empty
3. Attempt to save the dashboard
4. Verify the `#builder-error` div becomes visible with an appropriate error message

**Expected:** Error message is visible — no silent failures.
