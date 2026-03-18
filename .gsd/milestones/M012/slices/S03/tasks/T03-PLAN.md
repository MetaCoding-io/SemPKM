---
estimated_steps: 7
estimated_files: 2
---

# T03: Frontend persona switching, command palette, and default persona

**Slice:** S03 — Workspace Personas
**Milestone:** M012

## Description

Implement all frontend JavaScript logic for the persona system: switching between personas (with dockview layout restore, sidebar panel position restore, and explorer mode restore), command palette entries for keyboard-driven persona management, default persona auto-creation on first workspace load, and beforeunload state saving. This is the integration task that makes the backend service (T01) and API routes (T02) into a usable feature.

Key risks this task must handle:
- `dv.fromJSON()` can fail on stale/incompatible layout JSON — must wrap in try/catch with fallback
- `onDidLayoutChange` fires when `dv.fromJSON()` is called during persona switch — must use a guard flag to prevent localStorage overwrite during switch
- Explorer mode change requires both localStorage + dropdown value + htmx trigger to fully apply
- `beforeunload` is unreliable for async requests — use `navigator.sendBeacon()` for the save

## Steps

1. **Add persona state variables and init function.** Near the top of `workspace.js` (after `PANEL_POSITIONS_KEY` / `EXPLORER_MODE_KEY` declarations around line 17), add:
   - `var _activePersonaId = null;` — tracks current active persona ID
   - `var _switchingPersona = false;` — guard flag to prevent auto-save during persona switch
   
   Create `initPersonas()` function:
   - Fetch `GET /api/personas` (needs auth cookie, use `fetch` with `credentials: 'same-origin'`)
   - If response is empty array (no personas exist): auto-create "Default" persona by capturing current state (`window._dockview ? JSON.stringify(window._dockview.toJSON()) : '{}'`, `localStorage.getItem(PANEL_POSITIONS_KEY) || '{}'`, `localStorage.getItem(EXPLORER_MODE_KEY) || 'by-type'`) and POSTing to `POST /api/personas` with name "Default" and all three state fields. Set `_activePersonaId` to the returned persona ID.
   - If personas exist: find the one with `is_active === true`, set `_activePersonaId` to its ID. Do NOT apply layout on initial load (workspace-layout.js already restores from localStorage; persona state is the server-side backup).
   - Wrap everything in try/catch — persona init failure must not block workspace startup.

2. **Add `saveCurrentPersonaState()` function:**
   - If `_activePersonaId` is null, return (no active persona to save to)
   - Capture: `layout_json = window._dockview ? JSON.stringify(window._dockview.toJSON()) : null`, `sidebar_positions_json = localStorage.getItem(PANEL_POSITIONS_KEY)`, `explorer_mode = localStorage.getItem(EXPLORER_MODE_KEY)`
   - POST to `/api/personas/${_activePersonaId}/save-state` with JSON body `{layout_json, sidebar_positions_json, explorer_mode}`
   - Show toast "Persona saved" on success
   - Wrap in try/catch — save failure should show warning toast but not crash

3. **Add `switchPersona(id)` function:**
   - If `id === _activePersonaId`, return (already on this persona)
   - Set `_switchingPersona = true` (guard flag)
   - Step 1: Save current persona state (await `saveCurrentPersonaState()` — but make it return a Promise)
   - Step 2: Fetch `GET /api/personas/${id}` for full payload
   - Step 3: POST `/api/personas/${id}/activate`
   - Step 4: Apply layout — `dv.fromJSON(JSON.parse(persona.layout_json))` wrapped in try/catch. On failure, show toast "Layout couldn't be fully restored" and do NOT fall back to `buildDefaultLayout()` (keep whatever is currently on screen — less disruptive). Check if `window._dockview` exists first.
   - Step 5: Apply sidebar positions — write `persona.sidebar_positions_json` to `localStorage.setItem(PANEL_POSITIONS_KEY, ...)` then call `restorePanelPositions()`
   - Step 6: Apply explorer mode — write `persona.explorer_mode` to `localStorage.setItem(EXPLORER_MODE_KEY, ...)`, then set `document.getElementById('explorer-mode-select').value = persona.explorer_mode`, then trigger htmx: `htmx.trigger(document.getElementById('explorer-mode-select'), 'change')`
   - Step 7: Update `_activePersonaId = id`
   - Step 8: Set `_switchingPersona = false`
   - Step 9: Show toast "Switched to persona: {name}"
   - Step 10: Refresh persona selector if visible: `htmx.ajax('GET', '/browser/personas/selector', {target: '#persona-selector-container', swap: 'innerHTML'})`
   - Step 11: Refresh command palette persona items: `_refreshPersonaPaletteItems(document.querySelector('ninja-keys'))`
   - Wrap entire function in try/catch, always set `_switchingPersona = false` in finally block.

4. **Add `createNewPersona()` function:**
   - Prompt user for name via `window.prompt('New persona name:')` (simple for v1)
   - If cancelled or empty, return
   - Save current persona state first (so current persona doesn't lose unsaved changes)
   - POST to `/api/personas` with name + current state (layout_json, sidebar_positions_json, explorer_mode)
   - The API auto-activates new persona (per T02), so update `_activePersonaId`
   - Show toast "Persona '{name}' created"
   - Refresh persona selector and palette items

5. **Add command palette entries in `initCommandPalette()`:**
   - After the layout-related entries (around line 1470), add persona entries to the `commands` array:
     ```javascript
     {
       id: 'persona-switch',
       title: 'Persona: Switch To...',
       section: 'Persona',
       children: []  // populated by _refreshPersonaPaletteItems
     },
     {
       id: 'persona-save',
       title: 'Persona: Save Current',
       section: 'Persona',
       handler: function() { saveCurrentPersonaState(); }
     },
     {
       id: 'persona-create',
       title: 'Persona: Create New...',
       section: 'Persona',
       children: ['persona-create-confirm']
     },
     {
       id: 'persona-create-confirm',
       title: 'Type a persona name above, then select this item to save',
       parent: 'persona-create',
       handler: function() {
         // Same ninja-keys search field pattern as layout-save-confirm
         var ninjaEl = document.querySelector('ninja-keys');
         var name = '';
         if (ninjaEl) {
           try {
             var input = ninjaEl.shadowRoot.querySelector('input[type="text"]');
             if (input) name = input.value;
           } catch(e) {}
           if (!name && ninjaEl._search) name = ninjaEl._search;
         }
         name = name ? name.trim() : '';
         if (!name) {
           showToast('Please type a persona name in the search field first', 3000);
           return;
         }
         createNewPersona(name);  // overload to accept optional name param
       }
     }
     ```
   - After `_refreshLayoutPaletteItems(ninja)` call, add `_refreshPersonaPaletteItems(ninja)`.

6. **Add `_refreshPersonaPaletteItems(ninja)` function** (following `_refreshLayoutPaletteItems` pattern):
   - Filter out existing persona-switch- prefixed items from `ninja.data`
   - Fetch `GET /api/personas` to get current list
   - For each persona, add a child command:
     ```javascript
     {
       id: 'persona-switch-' + persona.id,
       title: persona.name + (persona.is_active ? ' ✓' : ''),
       parent: 'persona-switch',
       handler: function() { switchPersona(persona.id); }
     }
     ```
   - Set `ninja.data = baseData` (triggers ninja-keys re-render)
   - Since this requires an async fetch, wrap the fetch in `.then()` and update ninja.data in the callback.

7. **Add `beforeunload` handler and wire `initPersonas()` into workspace init:**
   - Add `window.addEventListener('beforeunload', function() { ... })`:
     - If `_activePersonaId && !_switchingPersona`: use `navigator.sendBeacon('/api/personas/' + _activePersonaId + '/save-state', new Blob([JSON.stringify({layout_json: ..., sidebar_positions_json: ..., explorer_mode: ...})], {type: 'application/json'}))` for reliable fire-and-forget save
   - In the existing workspace initialization sequence (look for where `initExplorerMode()`, `restorePanelPositions()`, `initCommandPalette()` are called), add `initPersonas()` after those calls. It must run after dockview is initialized (`window._dockview` must exist).
   - If the existing `onDidLayoutChange` handler writes to localStorage, add a check: `if (_switchingPersona) return;` at the top to prevent auto-save during persona switch.

## Must-Haves

- [ ] `initPersonas()` auto-creates "Default" persona on first load when none exist
- [ ] `switchPersona(id)` saves current state → fetches new → activates → applies layout + positions + mode
- [ ] `dv.fromJSON()` wrapped in try/catch with toast on failure
- [ ] `_switchingPersona` guard flag prevents localStorage overwrite during switch
- [ ] `saveCurrentPersonaState()` captures and persists all three state pieces
- [ ] `beforeunload` saves current persona via `navigator.sendBeacon`
- [ ] Command palette has "Persona: Switch To...", "Persona: Save Current", "Persona: Create New..."
- [ ] `_refreshPersonaPaletteItems()` dynamically populates switch children from API
- [ ] `createNewPersona()` works from both sidebar button and command palette
- [ ] Explorer mode restore triggers htmx change on dropdown (not just localStorage write)

## Verification

- Open workspace → no personas exist → "Default" persona auto-created (check via `curl /api/personas`)
- Rearrange layout (move panels, change explorer mode) → click "Save Current" in popover → state saved to server
- Create second persona "Research" → layout/positions captured → switched automatically
- Rearrange differently → save → switch back to "Default" → verify original layout restores
- Ctrl+K → type "Persona" → see "Switch To...", "Save Current", "Create New..." commands
- Ctrl+K → "Persona: Switch To..." → see persona list with ✓ on active one
- Reload page → active persona ID persists, workspace state matches
- Close browser tab → reopen → persona state was saved via beforeunload

## Inputs

- `backend/app/persona/router.py` — API endpoints (from T02): `GET/POST /api/personas`, `GET /api/personas/{id}`, `POST /api/personas/{id}/activate`, `POST /api/personas/{id}/save-state`
- `backend/app/templates/components/_persona_selector.html` — partial buttons call `switchPersona()`, `saveCurrentPersonaState()`, `createNewPersona()` (from T02)
- `frontend/static/js/workspace.js` — existing patterns: `PANEL_POSITIONS_KEY` (line 17), `EXPLORER_MODE_KEY` (line 2183), `savePanelPositions()` (line 2099), `restorePanelPositions()` (line 2117), `initExplorerMode()` (line 2184), `window._dockview` (global), `_refreshLayoutPaletteItems()` (line 1674), `initCommandPalette()` (line 1285), `showToast()` utility
- `frontend/static/js/workspace-layout.js` — `dv.fromJSON()` and `dv.toJSON()` via `window._dockview` (lines 289-316)

## Observability Impact

- **Browser console logs:** `console.log('SemPKM: persona init — created Default')` on first load, `console.log('SemPKM: switched to persona: <name>')` on switch, `console.warn('SemPKM: persona layout restore failed: ...')` on fromJSON failure
- **Inspection:** `_activePersonaId` accessible via browser console (closure-scoped but observable through API calls); `GET /api/personas` shows active persona with `is_active: true`
- **Failure visibility:** `dv.fromJSON()` failure shows toast "Layout couldn't be fully restored" + console warning; `saveCurrentPersonaState()` failure shows warning toast; `initPersonas()` failure logged to console but doesn't block workspace startup
- **beforeunload:** `navigator.sendBeacon` fires on tab close — verify via server logs showing save-state POST for active persona
- **Guard flag:** `_switchingPersona` prevents localStorage layout overwrite during persona switch; observable if you add a breakpoint in the `onDidLayoutChange` handler

## Expected Output

- `frontend/static/js/workspace.js` — modified with: `initPersonas()`, `saveCurrentPersonaState()`, `switchPersona(id)`, `createNewPersona()`, `_refreshPersonaPaletteItems()`, beforeunload handler, command palette entries, `_switchingPersona` guard flag
- `frontend/static/css/workspace.css` — minor additions if any persona-related styling needed beyond T02
