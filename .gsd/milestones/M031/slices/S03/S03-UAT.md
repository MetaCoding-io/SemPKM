# S03: Saved Queries Everywhere — UAT Script

## Preconditions

- Docker dev stack running (`docker compose up`)
- At least one user account logged in
- At least one saved SPARQL query exists (user-created via SPARQL console "Save Query")
- At least one Mental Model with saved queries loaded (e.g., basic-pkm has model queries)

---

## Test Case 1: QUERIES section appears in explorer sidebar

**Steps:**
1. Open the workspace at `/browser/workspace`
2. Look at the explorer sidebar (left panel)

**Expected:**
- A "QUERIES" section appears between VIEWS and DASHBOARDS
- Section auto-loads via htmx on page load (no user action needed)

---

## Test Case 2: Saved queries listed with correct grouping

**Steps:**
1. Expand the QUERIES section in the explorer sidebar
2. Observe the listed entries

**Expected:**
- User-created queries appear under a "My Queries" header with a `database` Lucide icon
- Model-bundled queries appear under a "Model Queries" header with a `book-open` Lucide icon
- If only one group has queries, only that group's header appears
- Each entry shows the query name as its label
- Hovering an entry shows the query description (or name if no description) in a tooltip

---

## Test Case 3: Empty state when no saved queries exist

**Steps:**
1. Ensure no saved queries exist (delete all user queries, unload models with queries)
2. Reload the workspace
3. Look at the QUERIES section

**Expected:**
- The section shows "No saved queries" text
- No group headers ("My Queries" / "Model Queries") appear

---

## Test Case 4: Click a saved query opens a scoped Table View tab

**Steps:**
1. Click on any saved query entry in the QUERIES section
2. Observe the tab bar and the view that opens

**Expected:**
- A new Table View tab opens in the workspace
- The tab is scoped to the clicked query (shows results matching the query)
- The tab label includes the query name
- The table view toolbar shows the query as the active scope

---

## Test Case 5: Drag a saved query onto the spatial canvas

**Steps:**
1. Open the Spatial Canvas view
2. Drag a saved query entry from the QUERIES section onto the canvas

**Expected:**
- A new embedded view widget appears on the canvas
- The widget displays the query results (loaded via iframe from `/browser/sparql-result/{id}?embed=1`)
- The widget label shows the query name

**Debug:** Open browser console during drag and check `window.__canvasDragPayload` — should be `{type:'query', id:'<uuid>', url:'/browser/sparql-result/<uuid>?embed=1', label:'<name>'}`

---

## Test Case 6: Queries section refreshes after saving a new query

**Steps:**
1. Open the SPARQL console
2. Write and execute a simple query (e.g., `SELECT ?s WHERE { ?s a ?t } LIMIT 5`)
3. Save the query with a name (e.g., "Test Query UAT")
4. Switch to the workspace and observe the QUERIES section

**Expected:**
- The QUERIES section includes the newly saved "Test Query UAT" entry
- If `htmx.trigger(document.body, 'queriesRefreshed')` is fired after save, the update is automatic
- If not auto-refreshed, manually reload the workspace and verify the query appears

---

## Test Case 7: Error handling — endpoint failure gracefully degrades

**Steps:**
1. Simulate a backend error in `list_all_queries()` (e.g., stop the triplestore)
2. Reload the workspace
3. Observe the QUERIES section

**Expected:**
- The section renders "No saved queries" (empty state), not a broken/error UI
- Backend logs contain `saved_queries_explorer: failed to load queries` with full traceback
- The rest of the workspace remains functional

---

## Test Case 8: VFS mount scope works with saved queries (SQ-03)

**Steps:**
1. Open VFS settings (admin or workspace VFS panel)
2. Create or edit a VFS mount
3. Set the scope to a saved query from the scope dropdown
4. Browse the mounted VFS path

**Expected:**
- The VFS mount shows only objects matching the saved query's scope
- `build_scope_filter()` generates a sub-select from the resolved query text
- Objects outside the query scope are not visible in the mount

---

## Edge Cases

### EC-1: Query with special characters in name
- Save a query with characters like `"Queries: <special> & 'fun'"`
- The QUERIES section should render the name correctly (HTML-escaped)
- Click and drag should work without JS errors

### EC-2: Many saved queries (20+)
- Create 20+ saved queries
- All should render in the QUERIES section without truncation
- The section should be scrollable if needed

### EC-3: Concurrent query deletion
- Have the QUERIES section open in one tab
- Delete a query via the SPARQL console in another tab
- Fire `queriesRefreshed` or reload — the deleted query should disappear
