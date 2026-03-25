# S02: Event Listener & Timer Leak Fixes — UAT

**Milestone:** M044
**Written:** 2026-03-25T17:13:31.762Z

# S02 UAT: Event Listener & Timer Leak Fixes

## Preconditions
- SemPKM running in Docker (`docker compose up`)
- At least one Mental Model installed with objects (for view tabs)
- Browser DevTools available (Chrome/Firefox)

## Test 1: Dockview panel dispose fires cleanup

**Steps:**
1. Open the workspace at `/browser/`
2. Open browser DevTools → Console
3. Open a Graph view tab (click any graph ViewSpec in the explorer)
4. Close the Graph view tab (click the X on the dockview tab)
5. Reopen the same Graph view tab

**Expected:** No console errors. Graph renders correctly on reopen. No duplicate event handlers visible in DevTools → Elements → Event Listeners on `document`.

## Test 2: Calendar panel open/close cycle

**Steps:**
1. Install basic-pkm model (if not already installed) — it has bpkm:Event with calendar ViewSpec
2. Open a Calendar view tab from the explorer
3. Wait for FullCalendar to render (CDN lazy-load)
4. Close the Calendar tab
5. Run in DevTools console: `getEventListeners(document)` (Chrome) — check for `sempkm:command-executed` and `sempkm:scope-changed`
6. Reopen the Calendar tab

**Expected:**
- Step 4: No stale `sempkm:command-executed` or `sempkm:scope-changed` listeners on document after close
- Step 6: Calendar renders correctly; no duplicate listeners; no console errors

## Test 3: Calendar panel double-open does not stack listeners

**Steps:**
1. Open a Calendar view tab
2. Close the Calendar tab
3. Open the Calendar tab again
4. Close it again
5. In DevTools console, check `getEventListeners(document)` for `sempkm:command-executed`

**Expected:** Zero `sempkm:command-executed` listeners remaining (they should have been removed on close). If any remain, the named-handler removal path failed.

## Test 4: Canvas (spatial) panel open/close cycle

**Steps:**
1. Open the spatial canvas view (if available — requires canvas-enabled type)
2. Interact with the canvas (drag, zoom)
3. Close the canvas tab
4. Check `getEventListeners(window)` for `pointermove`, `pointerup`
5. Check `getEventListeners(document)` for `dragover`, `dragleave`, `drop`, `dragend`, `keydown`

**Expected:** No stale window/document listeners from canvas after panel close. Canvas-viewport-scoped listeners (wheel, pointerdown) are expected to GC with the DOM element.

## Test 5: Federation badge polling clears on page unload

**Steps:**
1. Open the workspace at `/browser/`
2. Open DevTools → Sources → find federation.js or add a breakpoint on `setInterval`
3. Confirm the badge polling interval is running (network tab shows periodic `/federation/inbox/count` requests every ~60s)
4. Navigate away from the page (e.g., go to `/admin/`) or close the tab
5. (If navigating away) Return to `/browser/` and check that a new interval starts fresh

**Expected:** The interval does not persist across page navigations. The `beforeunload` handler clears it.

## Test 6: Rapid panel open/close stress test

**Steps:**
1. Open a Graph view tab
2. Immediately close it (within 1 second)
3. Immediately reopen it
4. Repeat 5 times rapidly
5. Check for console errors or visual glitches

**Expected:** No errors, no listener stacking, graph renders correctly each time. The dispose() → runCleanup() path handles rapid teardown gracefully.

## Edge Cases

- **No models installed:** Panel disposal should not error when there are no cleanup functions registered for the panel ID
- **Multiple panels open simultaneously:** Closing one panel should not affect cleanup registrations for other open panels
- **Browser back/forward:** Navigating away and back should start fresh (beforeunload clears federation interval; panels re-initialize via htmx)
