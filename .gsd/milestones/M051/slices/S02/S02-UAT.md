# S02: Explorer & Nav Cleanup + Object Tab Refresh — UAT

**Milestone:** M051
**Written:** 2026-04-06T01:18:52.165Z

## UAT: S02 — Explorer & Nav Cleanup + Object Tab Refresh

### Preconditions
- SemPKM workspace running (Docker dev stack or local)
- At least one Mental Model installed (e.g., basic-pkm)
- At least one object created

### Test Cases

#### TC1: Explorer type labels show clean names
1. Open workspace at `/browser/`
2. Expand the OBJECTS section in the explorer sidebar
3. Observe the type labels listed (e.g., for basic-pkm types)
4. **Expected:** Labels show 'Project', 'Task', 'Note' — NOT 'Project Shape', 'Task Shape', 'Note Shape'

#### TC2: Event log placeholder shows loading text
1. Open workspace at `/browser/`
2. Click the Event Log panel tab (if not already visible)
3. Observe the placeholder text before content loads
4. **Expected:** Shows 'Loading event log...' — NOT 'Event Log Explorer — coming in Phase 16'
5. After htmx load completes, actual event content replaces the placeholder

#### TC3: VFS mount dropdown shows human-readable model names
1. Navigate to VFS browser or any UI that shows the mount dropdown
2. Observe the model mount entries
3. **Expected:** Mounts show the model's dcterms:title (e.g., 'Basic PKM') instead of raw modelId (e.g., 'basic-pkm'). If a model has no dcterms:title, the modelId is shown as fallback.

#### TC4: Object tab has refresh button
1. Open any object in a workspace tab
2. Observe the object toolbar (top-right area with star, delete buttons)
3. **Expected:** A refresh button with a refresh-cw icon appears between the star and delete buttons
4. Click the refresh button
5. **Expected:** Object content reloads (the tab content refreshes via loadObjectContent)

#### TC5: Object tab (app variant) has refresh button
1. Open an object that uses the app-variant tab template (object_tab_app.html)
2. Observe the object toolbar
3. **Expected:** Same refresh button appears with refresh-cw icon
4. Click it
5. **Expected:** Content reloads

#### TC6: Refresh button hover state
1. Open any object tab
2. Hover over the refresh button
3. **Expected:** Icon color transitions from muted to primary color (smooth 0.2s transition)
4. Move mouse away
5. **Expected:** Color transitions back to muted

### Edge Cases

#### EC1: Type with no ' Shape' suffix is unaffected
1. If a model defines a type with label 'Contact' (no ' Shape' suffix)
2. **Expected:** Label shows 'Contact' unchanged — removesuffix is a no-op

#### EC2: Model with no dcterms:title
1. If a model's RDF metadata in urn:sempkm:models has no dcterms:title triple
2. **Expected:** VFS mount shows modelId as fallback name
