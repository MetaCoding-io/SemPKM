# S02 UAT: Multiple View Instances + Saved Views Fix

**Preconditions:**
- Docker stack running (`docker compose up -d`)
- At least one Mental Model installed (basic-pkm)
- At least 2–3 objects exist (any type)
- At least one saved query exists (create via SPARQL console → Save if needed)
- Browser open to workspace (`http://localhost:3000/browser/workspace`)

---

## TC-01: Open two unscoped table views from explorer

**Steps:**
1. In the explorer sidebar, click "Table View"
2. Observe: a tab labeled "Table View" appears with table content
3. Click "Table View" in the explorer sidebar again
4. Observe: a **second** tab appears, labeled "Table View (2)"
5. Both tabs are independently scrollable and show their own content
6. Close one tab — the other remains unaffected

**Expected:** Two separate dockview panels with distinct tab labels. No console errors about duplicate panel IDs.

---

## TC-02: Open two scoped views with different saved queries

**Steps:**
1. Open "Table View" from the explorer
2. In the view toolbar, select a saved query from the scope dropdown (e.g., "Upcoming Tasks")
3. Note the tab label changes to include the query name (e.g., "Table View — Upcoming Tasks")
4. Open "Table View" from the explorer again
5. Select a **different** saved query from the scope dropdown (e.g., "All Projects")
6. Observe: two table view tabs exist with different scope labels and different filtered data

**Expected:** Both tabs coexist. Each shows data filtered by its respective saved query.

---

## TC-03: Scoped tab deduplication

**Steps:**
1. Open "Table View" from the explorer
2. Select saved query "Upcoming Tasks" from scope dropdown
3. Open "Table View" from explorer again
4. Select the **same** saved query "Upcoming Tasks" from scope dropdown
5. Observe: the existing scoped tab is activated — no new tab is created

**Expected:** Only one tab with "Table View — Upcoming Tasks" exists. The system deduplicates by `renderer:scope:queryId` composite key.

---

## TC-04: Save current view configuration

**Steps:**
1. Open "Table View" from the explorer
2. Optionally select a type filter pill (e.g., "Project")
3. Optionally select a scope query from the dropdown
4. Click the "Save View" button (bookmark-plus icon) in the view toolbar
5. A browser prompt appears asking for a name
6. Enter "My Project Table" and confirm
7. Observe: success feedback (no error), saved views tree refreshes

**Expected:** The view is saved. No console errors. A POST to `/browser/views/save` returns 200.

---

## TC-05: Saved view appears in Saved Views folder

**Steps:**
1. After TC-04, navigate to the Saved Views section in the explorer
2. Observe: "My Project Table" appears in the list
3. The entry shows a renderer-type icon (table icon for table views)
4. The entry has an unpin action (x button or similar)

**Expected:** Saved view entry is visible with correct label and icon.

---

## TC-06: Open a saved generic view from Saved Views folder

**Steps:**
1. Click "My Project Table" in the Saved Views folder
2. Observe: a new tab opens with the correct renderer (table)
3. If a type filter was active when saved, it should be restored
4. If a scope query was active when saved, data should be filtered accordingly

**Expected:** The saved view reopens with the exact configuration that was saved — renderer, type filter, and scope query all match.

---

## TC-07: Unpin (delete) a saved generic view

**Steps:**
1. In the Saved Views folder, click the unpin/delete action on "My Project Table"
2. Observe: the entry disappears from the Saved Views list
3. Refresh the page — the entry should not reappear

**Expected:** DELETE request to `/browser/views/saved/{view_id}` returns 200. Entry removed from UI and from the triplestore.

---

## TC-08: Query-based promoted views still work

**Steps:**
1. Go to SPARQL console, run a query, save it
2. Click "Pin as Saved View" on the saved query
3. Navigate to Saved Views folder
4. Observe: the query-based saved view appears alongside any generic saved views
5. Click it — opens via `openViewTab()` (dedicated view, not generic view tab)
6. Unpin it — uses `demoteView()` path

**Expected:** Backward compatibility with query-based promoted views is maintained. The two-path pattern (generic vs. query-based) works without conflict.

---

## TC-09: Multiple renderer types as simultaneous tabs

**Steps:**
1. Open "Table View" from explorer
2. Open "Cards View" from explorer
3. Open "Graph View" from explorer
4. Open "Table View" again from explorer

**Expected:** Four tabs coexist: Table View, Cards View, Graph View, Table View (2). All independently functional.

---

## TC-10: Save View button visibility

**Steps:**
1. Open a generic view (Table/Cards/Graph from explorer sidebar)
2. Observe: "Save View" button (bookmark-plus icon) is visible in the view toolbar
3. Open a model-declared view (e.g., select a type filter, then pick a model variant from the toolbar dropdown)
4. Observe: "Save View" button behavior — it should be present only for generic views (guarded by `is_generic` flag)

**Expected:** The Save View button appears on generic views. Its visibility is controlled by the `is_generic` template variable.

---

## Edge Cases

### EC-01: Save view with empty name
1. Click "Save View" button
2. Leave the name prompt empty or cancel
3. **Expected:** No save occurs, no error thrown

### EC-02: Invalid renderer type in API
1. Send `POST /browser/views/save` with `renderer_type: "nonexistent"`
2. **Expected:** HTTP 400 with error message about invalid renderer

### EC-03: Rapid double-click on explorer view entry
1. Double-click "Table View" very quickly in the explorer
2. **Expected:** Two tabs may appear (Date.now() gives different millisecond timestamps). No crash, no duplicate ID errors from dockview.
