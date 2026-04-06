# S03: Version Checking + Update Notifications — UAT

**Milestone:** M053
**Written:** 2026-04-06T03:49:52.503Z

## UAT: Version Checking + Update Notifications

### Preconditions
- SemPKM running with marketplace configured (`MARKETPLACE_REGISTRY_URL` set to a valid registry.json URL)
- At least one model installed from the marketplace (not bundled)
- Registry contains a newer version of at least one installed model

### Test 1: Up-to-date badge displays correctly
1. Navigate to Admin → Mental Models
2. Observe the installed models table
3. **Expected:** Models whose installed version matches the registry version show a green "Up to date" badge in the Status column
4. **Expected:** No Update button appears for up-to-date models

### Test 2: Update available badge and button
1. Navigate to Admin → Mental Models with an outdated model installed
2. **Expected:** The outdated model shows an amber "Update available: vX.Y.Z" badge with the latest version number
3. **Expected:** An "Update" button appears next to the badge

### Test 3: Update button triggers confirmation dialog
1. Click the Update button on an outdated model
2. **Expected:** Browser confirmation dialog appears: "Update {model name} to vX.Y.Z?"
3. Click Cancel
4. **Expected:** No update occurs, page unchanged

### Test 4: Successful model update
1. Click Update on an outdated model, confirm the dialog
2. **Expected:** Loading indicator appears while update is in progress
3. **Expected:** After completion, the model table refreshes via htmx
4. **Expected:** The updated model now shows the new version number and "Up to date" badge
5. **Expected:** Model types still appear in the workspace explorer

### Test 5: Marketplace cards show update status
1. Navigate to Admin → Mental Models, scroll to Browse Marketplace section
2. **Expected:** Marketplace cards for installed-but-outdated models show "Update available" badge instead of "✓ Installed"
3. **Expected:** Marketplace cards for up-to-date installed models still show "✓ Installed"

### Test 6: Graceful degradation — marketplace unreachable
1. Set `MARKETPLACE_REGISTRY_URL` to an invalid URL or disconnect network
2. Navigate to Admin → Mental Models
3. **Expected:** No version badges appear (no Status column content for marketplace models)
4. **Expected:** Page loads normally without errors or crashes
5. **Expected:** Bundled models still display and function correctly

### Test 7: Graceful degradation — marketplace disabled
1. Unset `MARKETPLACE_REGISTRY_URL` entirely
2. Navigate to Admin → Mental Models
3. **Expected:** No Browse Marketplace section appears
4. **Expected:** No version badges appear on installed models
5. **Expected:** Page loads normally

### Edge Cases
- **Model not in registry:** Bundled-only models (not in marketplace registry) show no badge — no crash
- **Malformed version in registry:** If a registry entry has an unparseable version string, it is silently skipped — no crash, other models still show badges
- **Installed version newer than registry:** Shows "Up to date" (not "downgrade available")
- **Update download failure:** Old model version is preserved — the update endpoint downloads and verifies BEFORE removing the old version
