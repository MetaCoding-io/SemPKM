# S01: Smart Type Dropdown — UAT

**Milestone:** M050
**Written:** 2026-04-05T21:35:44.286Z

## UAT: S01 — Smart Type Dropdown

### Preconditions
- At least one Mental Model installed (e.g., Basic PKM) that provides types with SHACL shapes
- Basic PKM Task type has a status field (bpkm:taskStatus with sh:in constraint)
- At least one type exists without status/date/geo fields (e.g., Concept)
- Docker dev stack running with backend + triplestore accessible

### Test Case 1: Table View Shows All Types
1. Open the workspace
2. Open a Table View tab (via explorer sidebar → VIEWS → Table)
3. **Expected:** A `<select>` dropdown appears in the toolbar area (not a row of 37 type pill buttons)
4. Click the dropdown
5. **Expected:** "All Types" is the default option. All installed types appear as options regardless of their SHACL shape fields.

### Test Case 2: Kanban View Shows Only Status-Field Types
1. Open a Kanban View tab
2. Click the type dropdown
3. **Expected:** Only types whose SHACL shape includes a property with `sh:in` constraint appear (e.g., Task). Types without status fields (e.g., Concept, Person) are absent.
4. **Expected:** The dropdown has fewer options than the Table View dropdown.

### Test Case 3: Calendar/Timeline View Shows Only Date-Field Types
1. Open a Calendar View tab
2. Click the type dropdown
3. **Expected:** Only types whose SHACL shape includes date/dateTime properties appear (e.g., Task with bpkm:dueDate or bpkm:scheduledStart). Types without any date field are absent.
4. Repeat for Timeline View — same filtering expected.

### Test Case 4: Map View Shows Only Geo-Field Types
1. Open a Map View tab
2. Click the type dropdown
3. **Expected:** Only types whose SHACL shape includes geo-coordinate properties (wgs84:lat/long or similar) appear. If no types have geo fields, the dropdown shows only "All Types".

### Test Case 5: Type Selection Triggers View Reload
1. Open a Table View tab
2. Select a specific type from the dropdown (e.g., "Task")
3. **Expected:** The view reloads via htmx showing only objects of the selected type
4. **Expected:** The dropdown retains the selected type after reload

### Test Case 6: Type Selection Persists in localStorage
1. Open a Table View, select a type (e.g., "Project")
2. Close the tab
3. Open a new Table View tab
4. **Expected:** The dropdown remembers the previously selected type (restored from localStorage key `sempkm_generic_type_table`)

### Test Case 7: Scope Query Preserved on Type Change
1. Open a Table View with a scope query active (e.g., via a saved view with scope)
2. Change the type in the dropdown
3. **Expected:** The htmx reload URL includes the scope_query parameter — the scope filter is not lost

### Test Case 8: View Variants Dropdown Removed
1. Open any view tab (Table, Kanban, Cards, etc.)
2. Inspect the toolbar area
3. **Expected:** No "View Variants" dropdown is present anywhere in the toolbar. Only the type filter dropdown and scope select remain.

### Test Case 9: Pill Bar Fully Removed
1. Open any of the 11 view types
2. **Expected:** No row of type pill buttons appears. The toolbar uses the compact select dropdown instead.
3. Inspect page source — no `.type-filter-pills` or `.type-pill` CSS classes in the rendered HTML.

### Test Case 10: Compatible Types JSON Endpoint
1. `curl http://localhost:8000/browser/views/compatible-types?renderer=kanban` (with auth cookie)
2. **Expected:** JSON response `{"types": [...]}` containing only types with status fields
3. `curl http://localhost:8000/browser/views/compatible-types?renderer=table`
4. **Expected:** JSON response containing all types (table is unfiltered)

### Edge Cases
- **No models installed:** All dropdowns show only "All Types" with no type options
- **Unknown renderer in URL:** Falls back to showing all types (safe default)
- **Specialized views (OKR, BMC, Quadrant, Decision Matrix):** Also use the dropdown, not pills
