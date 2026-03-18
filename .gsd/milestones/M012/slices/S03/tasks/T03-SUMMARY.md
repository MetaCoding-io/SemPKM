---
id: T03
parent: S03
milestone: M012
provides:
  - Frontend persona lifecycle: init, save, switch, create, command palette integration, and beforeunload auto-save
  - _switchingPersona guard flag preventing localStorage overwrite during dv.fromJSON()
key_files:
  - frontend/static/js/workspace.js
  - frontend/static/js/workspace-layout.js
key_decisions:
  - Use window._switchingPersona to bridge guard flag across workspace.js and workspace-layout.js IIFE boundaries
  - ninja-keys children array must list child IDs (not just rely on parent property) for drill-down navigation to work
patterns_established:
  - _refreshPersonaPaletteItems follows _refreshLayoutPaletteItems pattern with async fetch + parent children array update
observability_surfaces:
  - Console logs: "SemPKM: persona init — created Default", "SemPKM: switched to persona: <name>"
  - Console warnings: "SemPKM: persona layout restore failed: ...", "SemPKM: persona save failed: ..."
  - Toast notifications: "Persona saved", "Switched to persona: <name>", "Persona '<name>' created", failure toasts
  - navigator.sendBeacon on beforeunload for fire-and-forget save
duration: 35min
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T03: Frontend persona switching, command palette, and default persona

**Added full frontend persona lifecycle: auto-create Default on first load, save/switch/create personas with dockview layout + sidebar positions + explorer mode restore, command palette entries with dynamic submenu, and beforeunload auto-save via sendBeacon**

## What Happened

Implemented all 7 steps from the task plan in `workspace.js`:

1. **State variables and initPersonas()**: Added `_activePersonaId` and `_switchingPersona` guard flag near the top of the IIFE. `initPersonas()` fetches persona list on workspace load — if empty, auto-creates "Default" persona with current workspace state; if personas exist, finds and tracks the active one. Called from `init()` after dockview and explorer mode are ready.

2. **saveCurrentPersonaState()**: Captures dockview layout JSON, sidebar positions from localStorage, and explorer mode, then POSTs to `/api/personas/{id}/save-state`. Returns a Promise for chaining. Shows toast on success, warning toast on failure.

3. **switchPersona(id)**: Full save-fetch-activate-apply pipeline. Sets `_switchingPersona = true` (also on `window` for cross-IIFE access), saves current state, fetches full persona payload, activates on server, then applies layout via `dv.fromJSON()` (wrapped in try/catch with toast on failure), sidebar positions via `restorePanelPositions()`, and explorer mode via localStorage + dropdown value + htmx trigger. Always clears guard flag in `.finally()`.

4. **createNewPersona(name)**: Accepts optional name parameter (for command palette) or prompts user. Saves current persona first, then POSTs new persona with current state. API auto-activates, so updates `_activePersonaId`.

5. **Command palette entries**: Added "Persona: Switch To...", "Persona: Save Current", "Persona: Create New..." to `initCommandPalette()`. The Create New entry uses the ninja-keys search field input pattern (same as layout-save-as).

6. **_refreshPersonaPaletteItems(ninja)**: Async fetch of persona list, builds child commands under `persona-switch` parent with active checkmark indicator. Updates parent's `children` array with child IDs (required for ninja-keys drill-down navigation).

7. **beforeunload + guard flag**: `navigator.sendBeacon` fires on tab close for reliable fire-and-forget save. `window._switchingPersona` guard added to `workspace-layout.js` `onDidLayoutChange` handler to prevent localStorage overwrite during `fromJSON()`.

## Verification

- **Default persona auto-creation**: Opened workspace with no personas → console logged "SemPKM: persona init — created Default" → API confirmed persona exists with `is_active: true`
- **Save current state**: Called `saveCurrentPersonaState()` → API confirmed layout_json, sidebar_positions_json, explorer_mode saved
- **Create persona**: Called `createNewPersona('Research')` → API confirmed two personas, Research now active
- **Switch persona**: Called `switchPersona()` back to Default → API confirmed Default active, Research inactive
- **Command palette**: F1 → typed "Persona" → saw all three commands → Enter on "Switch To..." → saw submenu with "Default ✓" and "Research"
- **Sidebar popover**: Clicked user avatar → PERSONAS section shows persona list with active indicator, Save Current button, + button
- **Reload persistence**: Reloaded page → Research still active via API
- **Unit tests**: All 20 `test_persona_service.py` tests pass
- **404 diagnostic**: `GET /api/personas/00000000-...` returns `{"detail":"Persona not found"}`

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && python -m pytest tests/test_persona_service.py -v` | 0 | ✅ pass | 4.0s |
| 2 | `node -c frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |
| 3 | `node -c frontend/static/js/workspace-layout.js` | 0 | ✅ pass | <1s |
| 4 | Browser: Default persona auto-created on first load | — | ✅ pass | — |
| 5 | Browser: Command palette shows Persona commands with drill-down | — | ✅ pass | — |
| 6 | Browser: Sidebar popover shows persona selector | — | ✅ pass | — |
| 7 | Browser: Persona switch via command palette works | — | ✅ pass | — |
| 8 | Browser: Active persona persists across page reload | — | ✅ pass | — |
| 9 | Browser: API 404 returns proper error body | — | ✅ pass | — |

## Diagnostics

- **Console logs**: `initPersonas()` logs creation or active persona on load; `switchPersona()` logs switch with name and ID
- **Console warnings**: Layout restore failure, save failure, and init failure all logged with error details
- **Toast notifications**: User-visible feedback for save, switch, create, and error states
- **API inspection**: `GET /api/personas` returns persona list with `is_active` indicator; `GET /api/personas/{id}` returns full payload including layout_json
- **Guard flag**: `window._switchingPersona` can be checked in browser console during debugging

## Deviations

- **ninja-keys children array**: The plan specified `children: []` (empty array) on the persona-switch parent. This doesn't work — ninja-keys requires child IDs in the array for drill-down navigation. Fixed `_refreshPersonaPaletteItems` to update `parentItem.children = childIds` after populating children.
- **window._switchingPersona bridge**: The guard flag `_switchingPersona` is scoped inside the workspace.js IIFE. Since `workspace-layout.js` is a separate IIFE, the guard is exposed via `window._switchingPersona` and checked there. This was an implementation detail not called out in the plan.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/workspace.js` — Added persona state variables, `initPersonas()`, `saveCurrentPersonaState()`, `switchPersona()`, `createNewPersona()`, `_refreshPersonaPaletteItems()`, command palette entries, beforeunload handler, and window exports
- `frontend/static/js/workspace-layout.js` — Added `_switchingPersona` guard in `onDidLayoutChange` handler
- `.gsd/milestones/M012/slices/S03/tasks/T03-PLAN.md` — Added Observability Impact section (pre-flight fix)
