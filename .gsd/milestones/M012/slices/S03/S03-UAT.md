# S03: Workspace Personas — UAT

**Milestone:** M012
**Written:** 2026-03-17

## UAT Type

- UAT mode: mixed (artifact-driven for API + live-runtime for frontend)
- Why this mode is sufficient: Backend CRUD validated by 20 unit tests + curl. Frontend requires live browser interaction to verify layout restore, command palette, and sidebar UI.

## Preconditions

- Docker stack running: `docker compose up -d` with all 3 services healthy
- At least one Mental Model installed (basic-pkm) so workspace has objects to arrange
- Browser opened to `http://localhost:3000/browser/`
- User logged in (session cookie active)

## Smoke Test

Open the Object Browser → click user avatar in bottom-left → verify "PERSONAS" section appears in the popover with at least "Default" persona listed.

## Test Cases

### 1. Default Persona Auto-Creation

1. Clear all personas: `sqlite3 backend/data/sempkm.db "DELETE FROM personas"` (or use fresh DB)
2. Navigate to `http://localhost:3000/browser/`
3. Wait for workspace to load fully (dockview panels visible)
4. Open browser console → search for "SemPKM: persona"
5. **Expected:** Console shows "SemPKM: persona init — created Default"
6. Click user avatar → check PERSONAS section
7. **Expected:** "Default" persona listed with check-circle (active) indicator
8. Verify via API: `curl -b "sempkm_session=$TOKEN" http://localhost:8001/api/personas`
9. **Expected:** JSON array with one persona: `{"name": "Default", "is_active": true, ...}`

### 2. Create Second Persona

1. Click user avatar → PERSONAS section → click "+" button
2. Enter name "Research Mode" when prompted
3. **Expected:** Toast "Persona 'Research Mode' created"
4. **Expected:** PERSONAS section refreshes showing "Research Mode" with active indicator, "Default" now inactive
5. Verify via API: `curl -b "sempkm_session=$TOKEN" http://localhost:8001/api/personas`
6. **Expected:** Two personas, "Research Mode" is_active: true, "Default" is_active: false

### 3. Arrange Layout and Save

1. With "Research Mode" active, rearrange workspace: drag a panel to a different position, close SPARQL panel, resize explorer
2. Click user avatar → PERSONAS → "Save Current"
3. **Expected:** Toast "Persona saved"
4. Verify via API: `curl -b "sempkm_session=$TOKEN" http://localhost:8001/api/personas/{research-id}`
5. **Expected:** layout_json field contains the current dockview layout (non-empty JSON string)

### 4. Switch Between Personas

1. Click user avatar → PERSONAS → click "Default"
2. **Expected:** Toast "Switched to persona: Default"
3. **Expected:** Workspace layout changes to Default's saved layout (SPARQL panel reappears if it was visible in Default, panel positions change)
4. **Expected:** "Default" now shows check-circle, "Research Mode" shows circle
5. Click "Research Mode" again
6. **Expected:** Layout restores to Research Mode's saved arrangement (SPARQL panel closed, panels in rearranged positions)

### 5. Command Palette Persona Access

1. Press F1 (or Ctrl+K) to open command palette
2. Type "Persona"
3. **Expected:** Three commands visible:
   - "Persona: Switch To..."
   - "Persona: Save Current"
   - "Persona: Create New..."
4. Click "Persona: Switch To..."
5. **Expected:** Submenu shows persona list with active checkmark (e.g., "✓ Research Mode", "Default")
6. Click a non-active persona
7. **Expected:** Persona switches, toast appears, layout changes

### 6. Command Palette Create New

1. Press F1 → type "Persona" → select "Persona: Create New..."
2. Type a name (e.g., "Writing") and press Enter
3. **Expected:** Toast "Persona 'Writing' created"
4. Click user avatar → verify 3 personas listed, "Writing" is active

### 7. Persona Persistence Across Reload

1. Ensure a non-Default persona is active (e.g., "Research Mode")
2. Rearrange layout distinctively (e.g., close a panel, resize explorer wider)
3. Save current state (user avatar → Save Current)
4. Reload the page (F5 or browser refresh)
5. **Expected:** Same persona remains active after reload
6. **Expected:** Layout matches the saved state (panel arrangement preserved)
7. Verify via API: active persona unchanged

### 8. API Error Handling

1. `curl -b "sempkm_session=$TOKEN" http://localhost:8001/api/personas/00000000-0000-0000-0000-000000000000`
2. **Expected:** HTTP 404 with `{"detail": "Persona not found"}`
3. `curl -X DELETE -b "sempkm_session=$TOKEN" http://localhost:8001/api/personas/00000000-0000-0000-0000-000000000000`
4. **Expected:** HTTP 404 with `{"detail": "Persona not found"}`

### 9. Delete Persona

1. Currently have 3 personas, "Writing" is active
2. Via API: `curl -X DELETE -b "sempkm_session=$TOKEN" http://localhost:8001/api/personas/{writing-id}`
3. **Expected:** HTTP 204 No Content
4. Check API list: only 2 personas remain
5. **Expected:** One of the remaining personas auto-activated (since the active one was deleted)

## Edge Cases

### Layout Restore Failure Handling

1. Save a persona with layout_json
2. Manually corrupt the layout_json in SQLite: `UPDATE personas SET layout_json='invalid json' WHERE name='Test'`
3. Switch to that persona
4. **Expected:** Toast "Layout couldn't be fully restored" (or similar warning)
5. **Expected:** Workspace doesn't crash — falls back to default layout or stays on current layout

### beforeunload Save

1. Ensure a persona is active and rearrange the layout
2. Close the browser tab
3. Reopen `http://localhost:3000/browser/`
4. **Expected:** State saved via sendBeacon before close (check layout_json via API)

### Guard Flag During Switch

1. Open browser console
2. Call `switchPersona('some-id')` from console
3. During the switch, observe `window._switchingPersona` is `true`
4. After switch completes, verify `window._switchingPersona` is `false`
5. **Expected:** Guard prevents onDidLayoutChange from writing to localStorage during fromJSON()

## Failure Signals

- PERSONAS section missing from user popover → sidebar template not updated or browser route failing
- "Default" not auto-created on fresh load → initPersonas() not called or API create failing
- Layout doesn't change on persona switch → dv.fromJSON() failing silently (check console)
- Command palette shows no persona entries → initCommandPalette() not registering persona items
- API returns 500 → PersonaService not wired into app.state or migration not applied
- Console error "switchPersona is not defined" → function not exported from IIFE to global scope

## Requirements Proved By This UAT

- PERSONA-01 — Create, rename, delete personas with proper constraint enforcement
- PERSONA-02 — Persona switch restores dockview layout + sidebar positions + explorer mode
- PERSONA-03 — Persona selector visible in user popover with active indicator
- PERSONA-04 — All three command palette entries work with dynamic submenu
- PERSONA-05 — Default persona auto-created on first workspace load

## Not Proven By This UAT

- Playwright E2E automation (deferred to S04)
- User guide documentation (deferred to S04)
- Multi-user isolation (not tested — would need two separate user sessions)
- Docker restart persistence (requires `docker compose down && docker compose up` cycle)

## Notes for Tester

- The persona selector loads eagerly when the popover opens. If it doesn't appear, check network tab for `/browser/personas/selector` response.
- Explorer mode changes may not be visually obvious unless you switch between different modes (By Type, By Tag, etc.) when saving different personas.
- The "Research Mode" persona in the existing database was created during development. Delete all personas and start fresh for a clean test run.
- Layout_json can be large (5-50KB). Don't panic if the GET-by-ID response is verbose.
