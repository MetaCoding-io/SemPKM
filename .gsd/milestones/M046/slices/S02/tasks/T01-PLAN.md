---
estimated_steps: 5
estimated_files: 3
skills_used: []
---

# T01: Fix panel auto-open on tab click, harden watermark pointer-events, and update E2E helper

Three targeted edits to fix the copilot E2E test failures:

1. **workspace.js** — In `initPanelTabs()`, add `if (!panelState.open) { panelState.open = true; }` before `savePanelState()` in the tab click handler (~line 523). This makes clicking any bottom-panel tab auto-open the panel when it's collapsed, which is both the E2E fix and a UX improvement.

2. **workspace.css** — Add `pointer-events: none` to the `.editor-empty` rule (~line 1933). The watermark overlay contains no interactive elements (just instructional text and kbd hints), so it should never intercept pointer events. This prevents the watermark from blocking clicks on sibling elements like the bottom panel tabs.

3. **copilot.spec.ts** — In `openCopilotTab()`, add a `page.evaluate()` call before clicking the tab button that checks if the bottom panel is collapsed and opens it via `window.SemPKM.toggleBottomPanel()`. Belt-and-suspenders — the JS fix handles it app-side, this handles it test-side.

The root cause is that when the bottom panel starts collapsed (height: 0, overflow: hidden), the tab buttons exist in the DOM but are clipped. Playwright finds the button but can't deliver the click because the `.editor-empty` watermark (position: absolute, covering the full editor area) sits at the click coordinates and intercepts pointer events.

## Inputs

- ``frontend/static/js/workspace.js` — contains `initPanelTabs()` tab click handler at ~line 522`
- ``frontend/static/css/workspace.css` — contains `.editor-empty` rule at ~line 1933`
- ``e2e/tests/46-copilot/copilot.spec.ts` — contains `openCopilotTab()` helper at line 25`
- ``e2e/helpers/selectors.ts` — contains `SEL.copilot.tabBtn` selector definition`

## Expected Output

- ``frontend/static/js/workspace.js` — panel tab click handler auto-opens collapsed panel`
- ``frontend/static/css/workspace.css` — `.editor-empty` has `pointer-events: none``
- ``e2e/tests/46-copilot/copilot.spec.ts` — `openCopilotTab()` opens bottom panel before clicking tab`

## Verification

cd e2e && npx playwright test tests/46-copilot/copilot.spec.ts --project=chromium --reporter=list 2>&1 | tail -20
