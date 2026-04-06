---
estimated_steps: 7
estimated_files: 2
skills_used: []
---

# T01: pushState on tab switch + popstate handler with guard flag

Wire URL updates to dockview panel activation and back/forward navigation.

1. In workspace-layout.js, extend the onDidActivePanelChange handler to call history.pushState with ?tab=<panelId> (skip ephemeral __new-object- tabs)
2. Add a _navigatingFromHistory guard flag that suppresses pushState when a panel activation is triggered by popstate
3. Add a window popstate listener that reads state.tabId and activates the corresponding panel via panel.api.setActive() (with guard flag set)
4. If the panel referenced by popstate no longer exists (was closed), update URL with replaceState to remove stale ?tab=
5. Use replaceState (not pushState) for the initial page load state to avoid double-entry in history
6. Ensure existing ?panel=sparql handling in initBottomPanel is unaffected

## Inputs

- `frontend/static/js/workspace-layout.js (onDidActivePanelChange handler)`
- `frontend/static/js/workspace.js (existing pushState/replaceState patterns)`

## Expected Output

- `frontend/static/js/workspace-layout.js (modified — pushState + popstate handler)`

## Verification

Start dev stack. Open /browser/. Open object A → check URL has ?tab= with A's IRI. Open object B → URL updates. Press back → A is focused, URL shows A. Press forward → B focused. Open 5 tabs, navigate back through all of them — no loop, no duplicate entries. Verify ?panel=sparql still works.
