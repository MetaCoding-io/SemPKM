# S02: Closed Tab Recovery — UAT

**Milestone:** M055
**Written:** 2026-04-06T06:58:26.110Z

# S02 UAT: Closed Tab Recovery

## Preconditions
- Workspace loaded at `/browser/` with at least one Mental Model installed (basic-pkm)
- At least 3 objects exist to open as tabs

---

## Test 1: Single Tab Close and Reopen
1. Open an object tab by clicking an object in the explorer
2. Note the tab label and IRI
3. Close the tab via the X button
4. Press **Ctrl+Shift+T**
5. **Expected:** The same object tab reopens with the same label and content

## Test 2: Multi-Tab LIFO Stack
1. Open 3 different object tabs (A, B, C)
2. Close tab C, then tab B, then tab A
3. Press **Ctrl+Shift+T**
4. **Expected:** Tab A reopens (last closed = first reopened)
5. Press **Ctrl+Shift+T** again
6. **Expected:** Tab B reopens
7. Press **Ctrl+Shift+T** again
8. **Expected:** Tab C reopens

## Test 3: Empty Stack — No-Op
1. Ensure no tabs have been closed (or reopen all closed tabs)
2. Press **Ctrl+Shift+T**
3. **Expected:** Nothing happens. No new tab opens. No error in browser console.

## Test 4: Skip Already-Open Tab
1. Open 2 object tabs (A, B)
2. Close both tabs
3. Manually reopen tab B by clicking it in the explorer
4. Press **Ctrl+Shift+T**
5. **Expected:** Tab A reopens (tab B is skipped because it's already open)

## Test 5: Command Palette Entry
1. Press **F1** to open the command palette
2. Type "Reopen"
3. **Expected:** "Reopen Closed Tab" entry appears with Ctrl+Shift+T hotkey badge
4. Close an object tab, press F1, select "Reopen Closed Tab"
5. **Expected:** The closed tab reopens

## Test 6: View Tab Recovery
1. Open a view tab (e.g., Table view for a type)
2. Close the view tab
3. Press **Ctrl+Shift+T**
4. **Expected:** The same view tab reopens with the correct view type

## Edge Cases
- Stack is capped at 20 entries — closing 21+ tabs only retains the 20 most recent
- Special tabs (Docs, Canvas, Settings) can also be recovered via Ctrl+Shift+T
