# S01: Composable Explorer with Config Builder — UAT

**Milestone:** M054
**Written:** 2026-04-06T04:47:35.820Z

## UAT: Composable Explorer with Config Builder

### Preconditions
- SemPKM running at localhost:3901 with at least one Mental Model installed (basic-pkm recommended — it has Tasks with status/priority/dueDate fields)
- At least 3-5 objects of mixed types exist (tasks, notes, contacts)
- At least 2 tasks with different status values (e.g., "To Do", "In Progress")

---

### TC-01: Config Panel Toggle
1. Navigate to `/browser/`
2. Locate the OBJECTS section in the explorer sidebar
3. **Expected:** A gear icon button (⚙) appears in the OBJECTS header — no dropdown selector
4. Click the gear icon
5. **Expected:** Config panel expands below the header showing three rows: Filter (Type), Group By, Sort By
6. Click the gear icon again
7. **Expected:** Config panel collapses, summary bar shows current config state

### TC-02: Type Filter
1. Open the config panel (gear icon)
2. Select a type from the Filter dropdown (e.g., "Task")
3. Click Apply
4. **Expected:** Explorer tree shows only objects of the selected type — no other types visible
5. Select "All Types" from the Filter dropdown
6. Click Apply
7. **Expected:** All object types reappear in the tree

### TC-03: Group By Type
1. Open the config panel
2. Set Group By to "By Type"
3. Click Apply
4. **Expected:** Explorer tree shows folder nodes for each type (e.g., "Task (3)", "Note (2)") with item counts
5. Click a folder node
6. **Expected:** Folder expands to show sorted objects of that type

### TC-04: Group By Property (Status)
1. Open the config panel
2. Select type filter = "Task" (so type-specific properties appear)
3. Set Group By to a status property (e.g., "Task Status" or equivalent)
4. Click Apply
5. **Expected:** Explorer tree shows folder nodes for each status value (e.g., "To Do (2)", "In Progress (1)")
6. Click a status folder
7. **Expected:** Tasks within that status group appear as leaf nodes

### TC-05: Group By Tag
1. Open the config panel
2. Set Group By to "By Tag"
3. Click Apply
4. **Expected:** Explorer tree shows folder nodes for each tag value. Objects without tags appear under an "Untagged" or similar group.

### TC-06: Sort By Label (Default)
1. Open the config panel
2. Ensure Sort By is "Label" and order is ascending (↑)
3. Click Apply
4. **Expected:** Objects within any group or flat list are sorted alphabetically A→Z
5. Toggle sort order to descending (↓)
6. Click Apply
7. **Expected:** Objects sorted Z→A

### TC-07: Sort By Date Created
1. Open the config panel
2. Set Sort By to "Date Created"
3. Set sort order to descending
4. Click Apply
5. **Expected:** Most recently created objects appear first

### TC-08: Combined Filter + Group + Sort
1. Open the config panel
2. Set Filter = Task, Group By = Status, Sort By = Due Date, Order = Ascending
3. Click Apply
4. **Expected:** Tree shows only tasks, grouped by status folders, items within each folder sorted by due date (earliest first)

### TC-09: Reset
1. With an active config (from TC-08)
2. Click Reset in the config panel
3. **Expected:** All dropdowns return to defaults (All Types, None, Label, Ascending)
4. Tree reverts to the default by-type view

### TC-10: Dynamic Property Loading
1. Open the config panel
2. Change the type filter from "All Types" to a specific type (e.g., "Task")
3. **Expected:** Group By and Sort By dropdowns update to show type-specific properties (e.g., "Task Status", "Due Date", "Priority")
4. Change type filter to a different type
5. **Expected:** Property dropdowns update again for the new type's SHACL properties

### TC-11: Empty State
1. Open the config panel
2. Set type filter to a type with no instances (or filter + group combination yielding zero results)
3. Click Apply
4. **Expected:** Tree shows "No objects match this configuration" empty state message

### TC-12: Object Click-to-Open
1. With any config active showing objects in the tree
2. Click an object leaf node
3. **Expected:** Object opens in a workspace tab (same behavior as the old explorer tree)

### TC-13: Clean Type Labels (R009)
1. With Group By = "By Type" active
2. **Expected:** Folder labels show clean names like "Task", "Contact", "Note" — NOT "Task Shape" or "basic-pkm:Task"

### TC-14: Backward Compatibility
1. Navigate to `/browser/explorer/tree?mode=by-type`
2. **Expected:** Legacy endpoint still returns HTML tree (backward compat for any external consumers)

---

### Edge Cases

**EC-01: No Models Installed**
- With no Mental Models installed, open the config panel
- Type filter dropdown should show "All Types" only (no type-specific options)
- Group By should show only built-in options (By Type, By Tag)
- Apply with defaults should show "No objects match" empty state

**EC-02: Rapid Apply**
- Click Apply multiple times in quick succession
- Tree should update correctly without duplicate renders or stale state

**EC-03: Page Refresh**
- Configure a custom filter/group/sort, click Apply, refresh the page
- Config panel should reset to defaults (persistence is S02 scope)
- Tree should show default by-type view
