# S01: Fix Table & Cards Views + Creation Timestamps — UAT

**Milestone:** M048
**Written:** 2026-04-05T18:13:32.866Z

## UAT: Fix Table & Cards Views + Creation Timestamps

### Preconditions
- SemPKM running via Docker Compose with at least one Mental Model installed (e.g., basic-pkm)
- At least 2–3 objects already exist in the system

---

### Test Case 1: Table View Renders Objects

**Steps:**
1. Open the workspace
2. In the explorer pane, expand "Views" or navigate to a Table View
3. Click on any Table View entry (e.g., "All Objects" or a type-specific table)

**Expected:**
- Table renders with rows — NOT "No objects found" empty state
- Each row shows: Label, Type, Created date, Modified date columns
- Label column shows human-readable labels (not raw IRIs)
- Type column shows the object's rdf:type

**Failure indicator:** "No objects found" message, empty table, or browser console showing SPARQL parse errors with "undefined prefix"

---

### Test Case 2: Cards View Renders Cards

**Steps:**
1. Open the workspace
2. Navigate to a Cards View in the explorer (or switch an existing view to Cards renderer)

**Expected:**
- Cards render with object data — NOT empty grid
- Each card shows at minimum a label/title

**Failure indicator:** Empty cards area, "No objects found", or SPARQL errors in backend logs

---

### Test Case 3: New Object Gets Creation Timestamp

**Steps:**
1. Open the workspace
2. Create a new object via the "+" button or command palette (Ctrl+K → "Create Object")
3. Select a type (e.g., "Note" from basic-pkm)
4. Fill in a title and save
5. Open a Table View that includes this object type

**Expected:**
- The newly created object appears in the table
- The "Created" column shows a valid datetime (today's date, UTC)
- The "Modified" column shows the same datetime as Created

---

### Test Case 4: User-Supplied Created Date Takes Precedence

**Steps:**
1. Create a new object via the API or form where you can explicitly set `dcterms:created` as a property
2. Set it to a past date (e.g., "2020-01-01T00:00:00+00:00")
3. Save the object
4. Check the object in Table View

**Expected:**
- The "Created" column shows 2020-01-01, NOT today's date
- The "Modified" column shows today's date (auto-injected since user only supplied created)

---

### Test Case 5: Existing Objects Still Render in Views

**Steps:**
1. Verify that objects created BEFORE this fix (which lack dcterms:created) still appear in Table and Cards views

**Expected:**
- All existing objects render in views
- Created/Modified columns are blank for pre-fix objects (expected — no timestamp was stored)
- No errors or missing rows

---

### Edge Cases

- **Empty triplestore:** Table/Cards views show "No objects found" gracefully (not SPARQL errors)
- **Multiple types:** Table View with mixed types renders all matching objects
- **Rapid creation:** Create 3 objects quickly — all get distinct timestamps and appear in views
