---
id: T04
parent: S02
milestone: M037
provides:
  - persona_switched SSE event handler in context-indicator.js
  - Auto-switch toast notification with 3-second auto-dismiss
  - Graceful fallback when window.switchPersona is unavailable
key_files:
  - frontend/static/js/context-indicator.js
  - frontend/static/css/context-indicator.css
key_decisions:
  - Toast appended to document.body with position:fixed for z-index independence from dockview panels — consistent with the stacking context escape pattern (D293/KNOWLEDGE)
  - Rule name "auto" (from backend integration hook) is suppressed in toast display since it's a generic label, not a user-created rule name
patterns_established:
  - SSE event handlers in context-indicator.js follow try/catch-per-event pattern with console.error on parse failure
  - Toast notification uses CSS transition for enter + CSS @keyframes for exit, with JS setTimeout fallback removal
observability_surfaces:
  - Console warning: "[context-indicator] window.switchPersona not available" when workspace.js hasn't loaded
  - Console error: "[context-indicator] persona_switched parse error" when SSE payload is malformed
  - DOM inspection: document.querySelector('.context-auto-switch-toast') returns element while toast is visible
  - Visual: toast at top-right corner confirms SSE→switchPersona→UI loop completed
duration: 20m
verification_result: passed
completed_at: 2026-03-24
blocker_discovered: false
---

# T04: Frontend auto-switch handler — SSE persona_switched event

**Added persona_switched SSE handler to context-indicator.js with auto-switch toast notification — end-to-end flow from context update → rule match → persona switch → UI update verified in browser.**

## What Happened

Two changes to two files:

1. **context-indicator.js** — Added `persona_switched` event listener to the existing EventSource in `_connectSSE()`. On receiving the event, parses `{persona_id, persona_name, rule_name}` from the SSE data, calls `window.switchPersona(persona_id)` to apply the workspace layout change, and shows a brief toast notification via `_showAutoSwitchNotice()`. Graceful fallback: if `switchPersona` is undefined, logs a console warning and skips. JSON parse errors caught and logged.

2. **context-indicator.css** — Added ~50 lines of toast styles: `.context-auto-switch-toast` with fixed positioning at top-right, z-index 9000 (above workspace, below modals), CSS transition for fade-in, and `@keyframes context-toast-fadeout` for exit animation. Toast auto-removes from DOM after the exit animation completes (3s display + 0.4s fadeout). Uses theme CSS variables with fallbacks.

## Verification

- `grep -q "persona_switched" frontend/static/js/context-indicator.js` — handler exists
- `grep -q "switchPersona" frontend/static/js/context-indicator.js` — calls the switch function
- `grep -q "context-auto-switch-toast" frontend/static/css/context-indicator.css` — toast CSS exists
- `cd backend && .venv/bin/python -m pytest tests/test_rules_engine.py -v` — 19/19 passed (no regression)
- `cd backend && .venv/bin/python -m pytest tests/test_rules_router.py -v` — 26/26 passed (no regression)
- Browser end-to-end: Created Work persona + "Office Work" rule → activated Default persona → set home context → POST office context → persona_switched SSE event received → window.switchPersona called → toast appeared showing "Auto-switched to Work" → toast auto-dismissed after 3 seconds
- Toast CSS verified via manual DOM injection: dark rounded card at top-right with bold persona name and subtle rule name subtitle
- SSE event payload confirmed via debug EventSource: `{persona_id, persona_name: "Work", rule_name: "auto"}`

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -q "persona_switched" frontend/static/js/context-indicator.js` | 0 | ✅ pass | <1s |
| 2 | `grep -q "switchPersona" frontend/static/js/context-indicator.js` | 0 | ✅ pass | <1s |
| 3 | `grep -q "context-auto-switch-toast" frontend/static/css/context-indicator.css` | 0 | ✅ pass | <1s |
| 4 | `cd backend && .venv/bin/python -m pytest tests/test_rules_engine.py -v` | 0 | ✅ pass | 0.44s |
| 5 | `cd backend && .venv/bin/python -m pytest tests/test_rules_router.py -v` | 0 | ✅ pass | 0.75s |
| 6 | Browser: SSE persona_switched event received + handler fired + toast shown | — | ✅ pass | manual |

## Diagnostics

- **SSE delivery:** Open browser Network tab → filter EventStream → look for `persona_switched` events on `/api/context/stream`. If missing, check backend logs for `context.persona_switched` structured log.
- **Handler execution:** Console logs `[context-indicator] window.switchPersona not available` if workspace.js hasn't loaded. `[context-indicator] persona_switched parse error: <err>` if SSE payload is malformed.
- **Toast visibility:** `document.querySelector('.context-auto-switch-toast')` returns the element while visible (null after auto-dismiss). The toast has `pointer-events: none` so it doesn't block workspace interaction.
- **Persona state:** `GET /api/personas/` shows `is_active: true` on the persona that was auto-switched to.

## Deviations

- The toast suppresses the rule name display when `rule_name === "auto"` — the backend integration hook currently hardcodes `"auto"` as the rule_name instead of passing the actual rule name from the matched ContextRule. A future improvement in the backend would pass `matched_rule.name` through the SSE event for display.

## Known Issues

- The backend integration hook sends `rule_name: "auto"` instead of the actual rule name. This means the toast only shows "Auto-switched to {persona}" without the rule name subtitle. This is a backend data issue (in `router.py` line ~119), not a frontend problem — the frontend correctly displays the rule name when it's provided and not "auto".

## Files Created/Modified

- `frontend/static/js/context-indicator.js` — Added persona_switched SSE handler and _showAutoSwitchNotice toast function (modified)
- `frontend/static/css/context-indicator.css` — Added auto-switch toast styles with enter/exit animations (modified)
- `.gsd/milestones/M037/slices/S02/tasks/T04-PLAN.md` — Added Observability Impact section (modified)
