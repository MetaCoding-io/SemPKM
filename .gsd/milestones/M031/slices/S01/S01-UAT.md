# S01 UAT: Carousel Removal + View Scope Binding

## Preconditions

- Docker stack running (`docker compose up -d`)
- At least one Mental Model installed (e.g., basic-pkm) with some objects created
- At least one saved SPARQL query exists (create one via SPARQL console > Save Query if needed)
- At least one type has model-declared ViewSpecs (e.g., a type with a dedicated table view)

---

## Test Case 1: Carousel Is Completely Gone

**Goal:** Verify no carousel UI appears anywhere in the application.

1. Open the workspace in a browser
2. Click "Table View" in the explorer sidebar → table view opens in a dockview tab
3. **Expected:** No carousel tab bar visible above or within the table view. Content renders directly with type filter pills and view toolbar.
4. Click "Cards View" in the explorer sidebar → cards view opens
5. **Expected:** No carousel tab bar visible. Cards render directly.
6. Click "Graph View" in the explorer sidebar → graph view opens
7. **Expected:** No carousel tab bar visible. Graph renders directly.
8. Open browser DevTools console, run: `document.querySelector('.carousel-tab-bar')`
9. **Expected:** Returns `null`
10. Run: `typeof window.switchCarouselView`
11. **Expected:** Returns `"undefined"`
12. Run: `localStorage.getItem('sempkm_carousel_view')`
13. **Expected:** Returns `null`

---

## Test Case 2: Model-Declared Variant Dropdown Appears When Type Selected

**Goal:** Verify the variant dropdown shows model-declared ViewSpecs for the active type.

1. Open Table View from the explorer
2. **Expected:** No "View Variant" dropdown visible in the toolbar (no type selected yet)
3. Click a type filter pill for a type that HAS model-declared ViewSpecs (e.g., "Project" if a "Projects Table" spec exists)
4. **Expected:** A `<select>` dropdown labeled with view variant names appears in the view toolbar
5. The dropdown lists model-declared view labels (e.g., "Projects Table")
6. Select a variant from the dropdown
7. **Expected:** The workspace navigates to the dedicated view endpoint for that spec. The correct view renders in a new or updated tab.
8. Verify the URL changed to something like `/browser/views/table/{spec_iri}`

---

## Test Case 3: Variant Dropdown Does NOT Appear for Types Without Specs

**Goal:** Verify no empty/broken dropdown for types without model-declared views.

1. Open Table View from the explorer
2. Click a type filter pill for a type that has NO model-declared ViewSpecs (e.g., "Note" if no custom Note views exist)
3. **Expected:** No "View Variant" dropdown appears in the toolbar
4. Open DevTools, run: `document.querySelector('.view-variant-select')`
5. **Expected:** Returns `null`
6. Check console for errors — **Expected:** Zero JS errors related to variant dropdown

---

## Test Case 4: Scope Dropdown Lists Saved Queries

**Goal:** Verify the scope dropdown appears and is populated with saved queries.

1. Ensure at least one saved SPARQL query exists (create via SPARQL console if needed)
2. Open Table View from the explorer
3. **Expected:** A "Scope" dropdown (`<select class="view-scope-select">`) appears in the view toolbar
4. Click the dropdown
5. **Expected:** Lists saved queries in optgroups ("My Queries" and/or "Model Queries")
6. The first option is "All Objects" (default/no scope)

---

## Test Case 5: Scope Selection Filters View Results

**Goal:** Verify selecting a saved query scope actually filters the displayed objects.

1. Open Table View with some objects visible (e.g., 10+ objects)
2. Note the total count of objects displayed
3. Select a saved query from the Scope dropdown that would match a subset of objects (e.g., a query that returns only Projects)
4. **Expected:** The table re-fetches via htmx and displays only objects matching the saved query
5. The displayed count is less than the original unfiltered count
6. Open DevTools Network tab — verify the request URL contains `scope_query=<uuid>` parameter
7. Select "All Objects" from the Scope dropdown
8. **Expected:** The table re-fetches and shows all objects again (full unfiltered set)

---

## Test Case 6: Scope Persists Across Pagination

**Goal:** Verify scope_query is preserved when paginating.

1. Open Table View with a scope query selected that returns enough objects to paginate (or lower the page size)
2. Click "Next Page" (or page 2) in the pagination controls
3. **Expected:** The scope is preserved — still showing only scoped objects on page 2
4. Check the pagination URL in Network tab — should contain `scope_query=<uuid>` alongside page params
5. Click back to page 1
6. **Expected:** Scope still active, same filtered results

---

## Test Case 7: Scope Works on Cards View

**Goal:** Verify scope_query filters cards view.

1. Open Cards View from the explorer
2. Select a saved query from the Scope dropdown
3. **Expected:** Cards re-render showing only objects matching the query
4. Open DevTools Network tab — confirm `scope_query=<uuid>` in the request URL

---

## Test Case 8: Scope Works on Graph View

**Goal:** Verify scope_query filters graph view data.

1. Open Graph View from the explorer
2. Note the number of nodes visible
3. Select a saved query from the Scope dropdown
4. **Expected:** Graph re-renders with fewer nodes — only objects matching the query
5. Open DevTools Network tab — verify the graph data API request contains `scope_query=<uuid>`

---

## Test Case 9: Scope Dropdown Not Shown on Dedicated Model Views

**Goal:** Verify the scope dropdown is hidden on dedicated (non-generic) model views.

1. Open a model-declared view (e.g., navigate to a variant via the variant dropdown, or via Saved Views)
2. **Expected:** The scope dropdown does NOT appear in the toolbar (dedicated views have fixed queries)
3. Open DevTools, run: `document.querySelector('.view-scope-select')`
4. **Expected:** Returns `null` (or the element has `display: none`)

---

## Test Case 10: Graceful Degradation for Invalid Scope

**Goal:** Verify the view handles a nonexistent scope query gracefully.

1. Open Table View
2. In the browser address bar, manually append `?scope_query=00000000-0000-0000-0000-000000000000` (a nonexistent UUID) to the generic view URL and load it
3. **Expected:** The table renders normally with all objects (unfiltered — graceful fallback)
4. No user-facing error message
5. Check the server logs (Docker container): should see a warning like `generic_view: scope_query=... not found — rendering unfiltered`

---

## Test Case 11: Type Filter Pills Still Work Without Carousel

**Goal:** Verify type filter pills continue to work after carousel removal.

1. Open Table View from the explorer
2. Click a type filter pill (e.g., "Project")
3. **Expected:** Table filters to show only objects of that type
4. Click "All" or deselect the pill
5. **Expected:** Table shows all objects again
6. No JS errors in console related to carousel or view switching

---

## Test Case 12: Combined Type + Scope Filtering

**Goal:** Verify type filter and scope query work together.

1. Open Table View
2. Click a type filter pill (e.g., "Project")
3. Select a saved query from the Scope dropdown
4. **Expected:** Table shows only objects that match BOTH the type AND the scope query
5. The result count should be ≤ the type-only filtered count
6. Remove the scope (select "All Objects")
7. **Expected:** Shows all objects of the selected type again

---

## Edge Cases

### E1: No Saved Queries Exist
1. Delete all saved queries (or test with a fresh instance with none)
2. Open Table View
3. **Expected:** No scope dropdown appears (no empty dropdown visible)

### E2: Scope Query with Non-UUID Value
1. Manually set `?scope_query=not-a-uuid` in the URL
2. **Expected:** View renders unfiltered, server logs a warning, no 500 error

### E3: Rapid Scope Switching
1. Open Table View
2. Quickly change the scope dropdown selection 3–4 times in rapid succession
3. **Expected:** Final render matches the last selected scope, no stale data or race condition errors
