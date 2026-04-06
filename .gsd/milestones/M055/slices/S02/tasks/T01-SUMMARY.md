---
id: T01
parent: S02
milestone: M055
key_files:
  - frontend/static/js/workspace-layout.js
  - frontend/static/js/workspace.js
key_decisions:
  - Module-private _closedTabStack — not exposed on window, accessed via closure by reopenClosedTab()
  - Component type inferred from params flags as fallback during panel disposal
  - Skip-and-try-next when closed tab already manually reopened
duration: 
verification_result: passed
completed_at: 2026-04-06T06:46:21.955Z
blocker_discovered: false
---

# T01: Added closed-tab recovery stack with Ctrl+Shift+T reopen and command palette entry

**Added closed-tab recovery stack with Ctrl+Shift+T reopen and command palette entry**

## What Happened

Implemented closed-tab recovery in workspace-layout.js (module-private _closedTabStack array, onDidRemovePanel captures panel metadata, reopenClosedTab() dispatches to correct opener for all 18+ tab types) and workspace.js (Ctrl+Shift+T keyboard shortcut, "Reopen Closed Tab" command palette entry). Stack is LIFO with 20-entry max. Skip-and-try-next when a tab was manually reopened.

## Verification

Verified in browser: (1) Close object tab → Ctrl+Shift+T reopens with full content, (2) Close view tab → Ctrl+Shift+T reopens, (3) Empty stack → no action, no errors, (4) F1 → "Reopen" shows command entry with hotkey badge.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `Browser: Open 3 tabs, close last, Ctrl+Shift+T reopens` | 0 | ✅ pass | 3000ms |
| 2 | `Browser: Close view tab, Ctrl+Shift+T reopens` | 0 | ✅ pass | 2000ms |
| 3 | `Browser: Ctrl+Shift+T with empty stack, no errors` | 0 | ✅ pass | 1000ms |
| 4 | `Browser: F1 → Reopen shows command palette entry` | 0 | ✅ pass | 1000ms |

## Deviations

Required rebuilding frontend assets via node build.js since production manifest was active.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/workspace-layout.js`
- `frontend/static/js/workspace.js`
