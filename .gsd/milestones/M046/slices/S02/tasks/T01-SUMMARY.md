---
id: T01
parent: S02
milestone: M046
key_files:
  - frontend/static/js/workspace.js
  - frontend/static/css/workspace.css
  - e2e/tests/46-copilot/copilot.spec.ts
key_decisions:
  - pointer-events:none on .editor-empty is safe because it contains no interactive elements
duration: 
verification_result: passed
completed_at: 2026-03-29T01:47:41.558Z
blocker_discovered: false
---

# T01: Fix copilot E2E test failures by auto-opening collapsed bottom panel on tab click, blocking pointer events on editor-empty watermark, and hardening the E2E helper

**Fix copilot E2E test failures by auto-opening collapsed bottom panel on tab click, blocking pointer events on editor-empty watermark, and hardening the E2E helper**

## What Happened

Three surgical edits fixed the root cause of all 5 copilot E2E failures. workspace.js now auto-opens the bottom panel when a tab button is clicked while collapsed. workspace.css adds pointer-events:none to .editor-empty so the watermark overlay doesn't intercept clicks on sibling elements. copilot.spec.ts openCopilotTab() helper now ensures the bottom panel is open before clicking the tab button.

## Verification

All 5 copilot E2E tests pass on chromium: basic chat flow, SPARQL generation and approval, conversation persistence, persona switching, and object creation from chat.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd e2e && npx playwright test tests/46-copilot/copilot.spec.ts --project=chromium --reporter=list` | 0 | ✅ pass | 28300ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/workspace.js`
- `frontend/static/css/workspace.css`
- `e2e/tests/46-copilot/copilot.spec.ts`
