# S01: URL Sync & History Navigation — UAT

**Milestone:** M055
**Written:** 2026-04-06T06:31:37.410Z

# UAT: S01 — URL Sync & History Navigation

## Preconditions
- Dev stack running at localhost (or test stack at localhost:3901)
- At least 2 objects exist in the knowledge base (e.g., seed data from an installed Mental Model)
- User is authenticated and on the workspace page (/browser/)

## Test Cases

### TC1: URL updates when opening an object tab
1. Navigate to `/browser/`
2. Verify URL has no `?tab=` parameter
3. Open any object (e.g., click a seed data item in the explorer)
4. **Expected:** URL updates to include `?tab=<object-IRI>` where `<object-IRI>` is the full IRI of the opened object

### TC2: URL updates when switching between tabs
1. Open object A — note URL shows `?tab=<A-IRI>`
2. Open object B
3. **Expected:** URL now shows `?tab=<B-IRI>`
4. Click back on object A's tab header
5. **Expected:** URL updates back to `?tab=<A-IRI>`

### TC3: Browser back/forward navigates between tabs
1. Open object A, then open object B (two entries in history)
2. Press browser Back button
3. **Expected:** Object A's tab is now active, URL shows `?tab=<A-IRI>`
4. Press browser Forward button
5. **Expected:** Object B's tab is now active, URL shows `?tab=<B-IRI>`

### TC4: Deep-link via ?tab= opens correct tab
1. Copy the URL from TC1 (should be `/browser/?tab=<object-IRI>`)
2. Open a new browser tab and paste the URL
3. **Expected:** Workspace loads, and the referenced object tab opens and is focused
4. Reload the page (F5)
5. **Expected:** Same object tab remains open and focused after reload

### TC5: Deep-link to special tab
1. Navigate to `/browser/?tab=special:docs`
2. **Expected:** The Docs & Tutorials tab opens and is focused

### TC6: Stale history entry cleanup after closing a tab
1. Open object A, then open object B (URL shows B)
2. Close object B's tab (click the X on the tab)
3. Press browser Back button
4. **Expected:** No error occurs. URL updates — either shows object A's tab (if A is still the active entry) or removes the stale `?tab=` parameter

### TC7: Ephemeral tabs excluded from history
1. Click "New Object" to create a new object (opens an ephemeral `__new-object-` tab)
2. Check the URL
3. **Expected:** URL does NOT contain `?tab=__new-object-*`. The ephemeral tab is excluded from history pushState.

### TC8: ?panel=sparql coexists with ?tab=
1. Open an object (URL shows `?tab=<IRI>`)
2. Open the SPARQL console via the command palette or keyboard shortcut
3. **Expected:** Both `?tab=` and `?panel=sparql` can coexist in the URL, or ?panel=sparql is handled independently without breaking ?tab=

## Edge Cases
- Opening 5+ tabs and navigating back through all of them should work without loops or duplicate entries
- Closing all tabs then pressing Back should not produce JavaScript errors
- The deep-link handler does not open duplicate tabs if the panel was already restored from saved layout
