# S02 Research: Copilot Bottom Panel — Z-Index Fix

## Summary

The 5 copilot E2E tests all fail on the first action: clicking the AI COPILOT tab button. The root cause is that the bottom panel starts collapsed (`height: 0; overflow: hidden`) and the test's `openCopilotTab()` helper tries to click the tab button directly without opening the panel first. Playwright finds the button in the DOM but can't deliver the click because: (1) the button is clipped by `overflow: hidden`, and (2) the dockview watermark (`.editor-empty` inside `.dv-watermark-container`) sits at the click coordinates and intercepts pointer events.

This is a straightforward fix requiring changes to one JS file and one test file.

## Recommendation

Apply a two-part fix:

1. **App-level JS fix** — Make panel tab clicks auto-open the panel when it's closed. In `initPanelTabs()` in `workspace.js`, add `if (!panelState.open) { panelState.open = true; }` before calling `_applyPanelState()`. This is also a UX improvement — clicking a hidden tab should reveal the panel.

2. **E2E test fix** — In `openCopilotTab()` in `copilot.spec.ts`, call `page.evaluate(() => { if (!document.getElementById('bottom-panel').style.height || document.getElementById('bottom-panel').style.height === '0px') { window.SemPKM.toggleBottomPanel(); } })` before clicking the tab button. Belt-and-suspenders approach.

Optional CSS hardening: add `pointer-events: none` to `.editor-empty` since it contains no interactive elements (just instructional text + kbd hint). This prevents the watermark from ever intercepting clicks intended for sibling elements.

## Implementation Landscape

### Files to Change

| File | Change | Why |
|------|--------|-----|
| `frontend/static/js/workspace.js` | Add auto-open logic in `initPanelTabs()` tab click handler (~line 523) | Panel tab clicks should open the panel when collapsed |
| `e2e/tests/46-copilot/copilot.spec.ts` | Update `openCopilotTab()` to open panel before clicking tab | Ensure test works regardless of initial panel state |
| `frontend/static/css/workspace.css` | (optional) Add `pointer-events: none` to `.editor-empty` (~line 1933) | Defensive — watermark has no interactive content |

### Key DOM Structure

```
.editor-column (flex column)
├── .editor-groups-container (flex: 1, contains dockview)
│   └── .dv-dockview (position: relative, contain: layout)
│       └── .dv-watermark-container (position: absolute, inset 0, z-index: 1)
│           └── .editor-empty (position: relative, height: 100%)
├── .panel-resize-handle
└── .bottom-panel#bottom-panel (height: 0, overflow: hidden — collapsed by default)
    ├── .panel-header
    │   ├── .panel-tab-bar
    │   │   ├── button.panel-tab[data-panel="event-log"] (default active)
    │   │   ├── button.panel-tab[data-panel="inference"]
    │   │   ├── button.panel-tab[data-panel="ai-copilot"]  ← the target
    │   │   ├── button.panel-tab[data-panel="lint-dashboard"]
    │   │   └── button.panel-tab[data-panel="sparql"]
    │   └── .panel-controls
    └── .panel-content
        └── .panel-pane#panel-ai-copilot
```

### The Failure Mechanism

1. Test navigates to `/browser/`, waits for workspace
2. Panel starts collapsed: `height: 0; overflow: hidden`
3. Tab button exists in DOM but is clipped — Playwright sees it as "visible" (has dimensions) but can't deliver click
4. Playwright tries to click at button's center coordinates (y ≈ 813)
5. `.editor-empty` inside `.dv-watermark-container` (position: absolute, covering full editor height) intercepts the click at those coordinates
6. Error: `<div class="editor-empty">…</div> from <div id="editor-groups-container">…</div> subtree intercepts pointer events`
7. Test times out after 10s of retries

### Verified Fix

When the panel is opened first (via `window.SemPKM.toggleBottomPanel()`), the tab button moves to y≈560 and the watermark ends at y≈556. No overlap, clicks succeed.

### The JS Change (workspace.js ~line 522-525)

Current:
```javascript
btn.addEventListener('click', function () {
    panelState.activeTab = btn.dataset.panel;
    savePanelState();
    _applyPanelState();
```

Fixed:
```javascript
btn.addEventListener('click', function () {
    panelState.activeTab = btn.dataset.panel;
    if (!panelState.open) { panelState.open = true; }
    savePanelState();
    _applyPanelState();
```

### Test Verification

```bash
cd e2e && npx playwright test tests/46-copilot/copilot.spec.ts --project=chromium --reporter=list
```

All 5 tests should pass:
- basic chat flow
- SPARQL generation and approval flow
- conversation persistence across page reload
- persona switching
- object creation from chat

### Notes on Running Tests

Tests must be run from the `e2e/` directory, not the project root. Running from root causes `test.describe() not expected here` error due to Playwright config resolution.

### Copilot Test Dependencies

- Mock LLM server must be running (`mock-llm` Docker service)
- Tests use `test.beforeAll` to configure LLM to point at `http://mock-llm:8080`
- Tests use serial mode — they build on shared copilot state
- Auth fixture provides `ownerPage` and `ownerRequest`
