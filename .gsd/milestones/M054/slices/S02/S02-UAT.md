# S02: Config Persistence, Multi-Panel & Presets — UAT

**Milestone:** M054
**Written:** 2026-04-06T05:32:18.574Z

## UAT: S02 — Config Persistence, Multi-Panel & Presets

### Preconditions
- SemPKM running with at least one Mental Model installed (e.g., basic-pkm with Tasks)
- User logged in to workspace at /browser/
- S01 composable explorer config panel working (gear icon toggle)

---

### TC-01: Preset availability on first load
1. Open workspace at /browser/
2. Locate the OBJECTS section in the sidebar
3. Open the config selector dropdown (above the config builder)
4. **Expected:** Dropdown shows "Presets" optgroup containing "By Type" and "By Tag" options, plus "Hierarchy" option
5. **Expected:** No saved configs shown (Presets optgroup only for fresh user)

### TC-02: By Type preset renders type-grouped tree
1. Select "By Type" from the config selector dropdown
2. **Expected:** Config builder panel shows (gear icon area) with Type filter, Group-by, and Sort dropdowns
3. **Expected:** Explorer tree renders objects grouped by type folders with sorted items

### TC-03: By Tag preset renders tag-grouped tree
1. Select "By Tag" from the config selector dropdown
2. **Expected:** Explorer tree renders objects grouped by tag folders

### TC-04: Hierarchy preset hides config panel and uses legacy endpoint
1. Select "Hierarchy" from the config selector dropdown
2. **Expected:** Config builder panel hides (filter/group/sort dropdowns not visible)
3. **Expected:** Explorer tree renders the traditional hierarchy mode (types → objects)

### TC-05: Save a named config
1. Select "By Type" preset
2. Set Type filter to a specific type (e.g., "Task")
3. Set Group-by to "Status" (if available)
4. Type a name in the config name input (e.g., "My Tasks by Status")
5. Click Save button
6. **Expected:** Config selector dropdown refreshes and shows "My Tasks by Status" under "Saved Configs" optgroup
7. **Expected:** The newly saved config is now selected in the dropdown

### TC-06: Load a saved config
1. After TC-05, select a different preset (e.g., "By Tag")
2. Tree changes to tag-grouped view
3. Select "My Tasks by Status" from the Saved Configs section of the dropdown
4. **Expected:** Config builder panel shows with the saved filter/group/sort values restored
5. **Expected:** Tree renders with the saved configuration applied

### TC-07: Config persists across page reload
1. After TC-05/TC-06, note the active config name in the selector
2. Reload the browser page (F5)
3. **Expected:** After page loads, the config selector shows the previously active config selected
4. **Expected:** Tree renders with the persisted configuration

### TC-08: Delete a saved config
1. Select a saved config (not a preset) from the dropdown
2. Click Delete button
3. **Expected:** Config is removed from the dropdown
4. **Expected:** Tree resets to default navigation tree
5. **Expected:** Delete button is disabled/hidden when no saved config is selected

### TC-09: Cannot delete presets
1. Select "By Type" preset from the dropdown
2. **Expected:** Delete button is disabled or hidden (presets cannot be deleted)

### TC-10: Duplicate OBJECTS section
1. Click the Duplicate button (copy icon) in the OBJECTS section header
2. **Expected:** A second OBJECTS section appears below the original in the sidebar
3. **Expected:** The duplicate has its own config selector, config panel, and tree body
4. **Expected:** The duplicate has a Close (×) button in its header

### TC-11: Independent configs across sections
1. In the original OBJECTS section, select "By Type" preset
2. In the duplicate OBJECTS section, select "By Tag" preset
3. **Expected:** Original shows type-grouped tree; duplicate shows tag-grouped tree
4. **Expected:** Changing the config in one section does NOT affect the other

### TC-12: Close duplicate section
1. Click the Close (×) button on the duplicate OBJECTS section
2. **Expected:** Duplicate section is removed from the sidebar
3. **Expected:** Original OBJECTS section is unaffected and continues rendering

### TC-13: refreshExplorerTree() backward compatibility
1. Open browser dev console
2. Run: `window.SemPKM.refreshExplorerTree()`
3. **Expected:** Primary OBJECTS section tree refreshes without errors
4. **Expected:** No console errors

### Edge Cases

### TC-14: Save config with empty name
1. Clear the config name input
2. Click Save
3. **Expected:** Save is rejected or a default name is assigned (no crash)

### TC-15: Multiple duplicates
1. Click Duplicate twice
2. **Expected:** Three OBJECTS sections visible (original + 2 duplicates)
3. Configure each with a different preset
4. **Expected:** All three render independently
5. Close both duplicates
6. **Expected:** Only original remains, functioning normally
