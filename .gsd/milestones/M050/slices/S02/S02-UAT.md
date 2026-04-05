# S02: Toolbar Cleanup + View Polish — UAT

**Milestone:** M050
**Written:** 2026-04-05T21:46:25.679Z

## UAT: S02 — Toolbar Cleanup + View Polish

### Preconditions
- SemPKM running with at least one Mental Model installed (basic-pkm recommended)
- At least one type with date fields (e.g., Task with dueDate/scheduledStart) for calendar/timeline views
- Dark mode and light mode both available via theme toggle

---

### Test 1: Calendar dark mode nav icon visibility
1. Open workspace, switch to **dark mode** via theme toggle
2. Open a Calendar view (any type with date fields)
3. Observe the prev/next navigation buttons in the calendar toolbar header
4. **Expected:** Arrow icons are clearly visible (light text on dark button background)
5. Click prev and next buttons
6. **Expected:** Buttons respond to clicks, calendar navigates months. Hover state shows distinct background change. Active/today button shows accent color.
7. Switch to **light mode**
8. **Expected:** Calendar nav buttons still render correctly (no regression)

### Test 2: Timeline popup Escape dismiss
1. Open a Timeline view for a type with date-bearing instances (e.g., Tasks)
2. Click a Gantt bar to open the popup detail card
3. **Expected:** `.popup-wrapper` appears near the clicked bar
4. Press **Escape**
5. **Expected:** Popup dismisses immediately
6. Click another bar to reopen a popup
7. Press Escape again
8. **Expected:** Popup dismisses again (handler survives multiple uses)

### Test 3: Timeline popup click-outside dismiss
1. Open a Timeline view, click a Gantt bar to open popup
2. Click on empty space in the timeline (not on any bar, not inside the popup)
3. **Expected:** Popup dismisses
4. Click a bar again to reopen popup
5. Click inside the popup text area
6. **Expected:** Popup stays open (click is inside .popup-wrapper)
7. Click on a different Gantt bar
8. **Expected:** Previous popup closes, new bar's popup opens (Frappe Gantt native behavior)

### Test 4: Timeline panel cleanup on close
1. Open a Timeline view tab
2. Click a Gantt bar to confirm popup works
3. Close the Timeline tab (click X on the dockview tab)
4. Open a new Timeline tab
5. Click a bar, press Escape
6. **Expected:** Dismiss still works — no stale listeners from previous panel. No console errors about removed elements.

### Edge Cases
- **No date data:** Open timeline for a type with no date-bearing instances → Gantt renders empty, no popup to dismiss, no errors
- **Rapid Escape:** Press Escape when no popup is open → no error, no-op
- **Multiple timeline tabs:** Open two timeline tabs side by side, open popups in both, press Escape → only the focused tab's popup dismisses
