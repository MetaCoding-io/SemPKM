# S04: Create-New-Object Tab Fix

**Goal:** Clicking "New Object" always opens a fresh dockview tab, preserving the user's current view.
**Demo:** User has an object tab open → presses Alt+N or uses command palette → type picker loads in a new tab → old tab is untouched → object is created → temporary tab is cleaned up and real object tab opens.

## Must-Haves

- `showTypePicker()` always creates a new dockview panel with `component: 'empty'` before loading the type picker
- Existing tab content is never overwritten by the type picker
- `objectCreated` event handler closes the temporary `__new-object-*` panel after opening the real object tab
- Tutorial (`startCreateObjectTour`) continues to work — tour's `afterSwapHandler` picks up the new panel's editor area
- E2E test proves tab preservation: open object → trigger new object → verify old tab still exists → complete creation → verify cleanup

## Proof Level

- This slice proves: integration
- Real runtime required: yes (browser + dockview + htmx)
- Human/UAT required: no (E2E test covers the full flow)

## Verification

- `cd e2e && npx playwright test tests/12-bug-fixes/new-object-tab.spec.ts` — passes with tab preservation assertions
- Manual check: open workspace, click an object, press Alt+N, verify old tab is still in the tab bar, create an object, verify temp tab closes

## Observability / Diagnostics

- Runtime signals: `console.debug('[workspace] showTypePicker: created temp panel', panelId)` for debugging temp panel lifecycle
- Inspection surfaces: `window._dockview.panels` in browser console shows all panels; temp panels identifiable by `__new-object-` prefix
- Failure visibility: if temp panel not cleaned up, it remains as a visible empty "New Object" tab — obvious to user and test
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `dockview.api.addPanel()`, `window.getActiveEditorArea()`, `window._tabMeta` sidecar, `closeTab()`, htmx swap pattern with `hx-target="closest .group-editor-area"`
- New wiring introduced in this slice: temp panel creation in `showTypePicker()`, temp panel cleanup in `objectCreated` handler
- What remains before the milestone is truly usable end-to-end: S05 (docs & test coverage)

## Tasks

- [x] **T01: Fix showTypePicker to always create a fresh panel and clean up on object creation** `est:45m`
  - Why: This is the core bug fix — `showTypePicker()` currently overwrites the active tab's content instead of creating a new panel. The `objectCreated` handler needs to close the temp panel after the real tab opens.
  - Files: `frontend/static/js/workspace.js`
  - Do: Refactor `showTypePicker()` to always create a new `__new-object-{timestamp}` panel via `dv.api.addPanel()` (remove the `if (!editorArea)` conditional — the addPanel block runs unconditionally). Track the temp panel ID in a module-level variable (`_newObjectPanelId`). In `objectCreated` handler, close the temp panel via `closeTab(_newObjectPanelId)` after `openTab()`, then clear the tracker.
  - Verify: Start Docker stack, open workspace in browser, open an existing object tab, press Alt+N, confirm old tab survives in tab bar, create an object, confirm temp tab closes and real tab opens.
  - Done when: type picker always opens in a fresh tab; old tab content is never destroyed; temp panel is cleaned up on object creation.

- [x] **T02: Add E2E test for new-object tab preservation** `est:30m`
  - Why: Proves the fix works and prevents regression. No existing E2E test covers the create-object flow's tab behavior.
  - Files: `e2e/tests/12-bug-fixes/new-object-tab.spec.ts`
  - Do: Write a Playwright spec that: (1) opens the workspace, (2) opens a seed object tab, (3) calls `window.showTypePicker()`, (4) asserts the seed object's tab still exists in the tab bar, (5) verifies a new "New Object" tab appeared, (6) optionally completes the full create flow to verify temp tab cleanup. Use existing fixtures (`ownerPage`, `SEED`, `waitForWorkspace`, `waitForIdle`).
  - Verify: `cd e2e && npx playwright test tests/12-bug-fixes/new-object-tab.spec.ts` passes.
  - Done when: E2E test passes proving tab preservation and (at minimum) new-panel creation.

## Files Likely Touched

- `frontend/static/js/workspace.js` — `showTypePicker()` and `objectCreated` handler
- `e2e/tests/12-bug-fixes/new-object-tab.spec.ts` — new E2E test
