---
id: T01
parent: S06
milestone: M044
key_files:
  - frontend/static/js/api-fetch.js
  - frontend/static/js/copilot.js
  - frontend/static/js/calendar.js
  - frontend/static/js/workspace.js
  - frontend/static/js/graph.js
  - frontend/static/js/tutorials.js
  - frontend/static/js/bmc.js
  - frontend/static/js/decision-matrix.js
  - frontend/static/js/kanban.js
  - frontend/static/js/okr.js
  - frontend/static/js/quadrant.js
  - frontend/static/js/recurrence-editor.js
  - backend/app/templates/browser/timeline_view.html
  - backend/app/templates/browser/workspace.html
key_decisions:
  - SemPKM.debug() placed in api-fetch.js on window.SemPKM namespace — loads in base.html before all page-specific JS, guaranteeing availability everywhere
  - localStorage flag key is 'sempkm_debug' — truthy check means any non-empty value enables debug logging
  - try/catch around localStorage access for private browsing / sandboxed iframe resilience
duration: ""
verification_result: passed
completed_at: 2026-03-25T22:14:29.996Z
blocker_discovered: false
---

# T01: Add SemPKM.debug() utility gated by localStorage flag and migrate all 37 console.log calls across 14 files

**Add SemPKM.debug() utility gated by localStorage flag and migrate all 37 console.log calls across 14 files**

## What Happened

Created `SemPKM.debug(tag, ...args)` in `api-fetch.js` — a simple localStorage-gated wrapper around `console.log`. When `localStorage.getItem('sempkm_debug')` is truthy, it forwards to `console.log('[tag]', ...args)`. Otherwise it's a no-op. Wrapped in try/catch for environments where localStorage is unavailable (private browsing, sandboxed iframes).

Migrated all 37 `console.log` calls across 14 files:
- **JS files (32 calls, 11 files):** copilot.js (10), calendar.js (7), workspace.js (5), graph.js (2), tutorials.js (2), bmc.js (1), decision-matrix.js (1), kanban.js (1), okr.js (1), quadrant.js (1), recurrence-editor.js (1)
- **Template inline scripts (5 calls, 2 files):** timeline_view.html (4), workspace.html (1)

All `console.warn` (48) and `console.error` (49) calls left untouched — they're legitimate operational signals. The existing `console.debug` call in workspace.js also left unchanged per plan.

Tags used: 'copilot', 'calendar', 'SemPKM', 'scope', 'graph', 'timeline', 'bmc', 'decision-matrix', 'kanban', 'okr', 'quadrant', 'recurrence-editor'.

First attempted the edit tool for all replacements, but discovered partial application in multi-call files (copilot, calendar, workspace, graph, tutorials, timeline). Switched to `sed -i` for reliable in-place replacement of remaining calls. Final verification confirmed zero stray `console.log` calls outside the debug utility implementation.

## Verification

Ran `grep -rn 'console.log' frontend/static/js/ backend/app/templates/ --include='*.js' --include='*.html' | grep -v node_modules` — only 2 hits remain, both inside the `SemPKM.debug()` implementation in api-fetch.js (the JSDoc comment and the gated console.log call). Excluding api-fetch.js: 0 hits. Confirmed 38 `SemPKM.debug` calls present (37 migrated + 1 definition). Confirmed console.warn (48) and console.error (49) counts unchanged. Spot-checked multi-line calls in calendar.js, copilot.js, workspace.js, and timeline_view.html for syntactic correctness.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -rn 'console.log' frontend/static/js/ backend/app/templates/ --include='*.js' --include='*.html' | grep -v node_modules | grep -v 'api-fetch.js' | wc -l` | 0 | ✅ pass | 150ms |
| 2 | `grep -rn 'SemPKM.debug' frontend/static/js/ backend/app/templates/ --include='*.js' --include='*.html' | wc -l` | 0 | ✅ pass (38 = 37 migrated + 1 definition) | 120ms |
| 3 | `grep -rn 'console.warn' frontend/static/js/ --include='*.js' | grep -v node_modules | wc -l` | 0 | ✅ pass (48 unchanged) | 100ms |
| 4 | `grep -rn 'console.error' frontend/static/js/ --include='*.js' | grep -v node_modules | wc -l` | 0 | ✅ pass (49 unchanged) | 100ms |


## Deviations

Used sed -i for bulk replacement after the edit tool showed partial application on multi-call files. Same result, different mechanism. No semantic deviation from plan.

## Known Issues

The slice verification command `grep ... | wc -l # must be 0` returns 2 (not 0) because api-fetch.js itself contains `console.log` inside the debug utility implementation. This is expected — the utility must call console.log to function. Excluding api-fetch.js yields 0.

## Files Created/Modified

- `frontend/static/js/api-fetch.js`
- `frontend/static/js/copilot.js`
- `frontend/static/js/calendar.js`
- `frontend/static/js/workspace.js`
- `frontend/static/js/graph.js`
- `frontend/static/js/tutorials.js`
- `frontend/static/js/bmc.js`
- `frontend/static/js/decision-matrix.js`
- `frontend/static/js/kanban.js`
- `frontend/static/js/okr.js`
- `frontend/static/js/quadrant.js`
- `frontend/static/js/recurrence-editor.js`
- `backend/app/templates/browser/timeline_view.html`
- `backend/app/templates/browser/workspace.html`
