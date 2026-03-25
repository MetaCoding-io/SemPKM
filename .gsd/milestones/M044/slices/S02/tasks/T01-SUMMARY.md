---
id: T01
parent: S02
milestone: M044
key_files:
  - frontend/static/js/cleanup.js
  - frontend/static/js/workspace-layout.js
key_decisions:
  - Removed entire onDidVisibilityChange handler from view-panel renderer since it only contained dead _cytoscapeInstances code — no live resize/fit logic to preserve
duration: ""
verification_result: passed
completed_at: 2026-03-25T17:07:03.399Z
blocker_discovered: false
---

# T01: Wire dockview panel dispose() to cleanup registry and remove dead _cytoscapeInstances code

**Wire dockview panel dispose() to cleanup registry and remove dead _cytoscapeInstances code**

## What Happened

Exported `runCleanup` to `window.runCleanup` in cleanup.js so dockview content renderers can invoke it from their dispose() hooks.

Added `dispose()` methods to all three content renderers in workspace-layout.js (object-editor, view-panel, special-panel). Each dispose function calls `window.runCleanup(el.id)` on the panel root element and iterates all child elements with IDs to run their cleanup functions too. This mirrors the existing htmx:beforeCleanupElement listener pattern — when dockview closes a panel, the same teardown functions fire that would fire during an htmx swap.

Removed the dead `_cytoscapeInstances` reference from the view-panel renderer's `onDidVisibilityChange` handler. The `window._cytoscapeInstances` object is never populated anywhere in the codebase — graph views use the cleanup registry instead. The entire `onDidVisibilityChange` handler on view-panel was removed since it only contained the dead code.

## Verification

All 5 task-plan verification checks pass:
1. `rg 'window.runCleanup' cleanup.js` — shows the export line
2. `rg 'dispose' workspace-layout.js` — shows dispose on all 3 content renderers plus the existing tab dispose (4 matches of `dispose: function`)
3. `rg '_cytoscapeInstances' frontend/static/js/` — returns zero results (dead code removed)
4. Node check for `window.runCleanup` in cleanup.js — exits 0
5. Node check for 3+ `dispose: function` matches in workspace-layout.js — exits 0 (found 4)
Both files pass `node --check` syntax validation.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg 'window.runCleanup' frontend/static/js/cleanup.js` | 0 | ✅ pass | 45ms |
| 2 | `rg 'dispose' frontend/static/js/workspace-layout.js` | 0 | ✅ pass | 40ms |
| 3 | `rg '_cytoscapeInstances' frontend/static/js/` | 1 | ✅ pass (no matches = dead code removed) | 42ms |
| 4 | `node -e "...cleanup.js window.runCleanup check..."` | 0 | ✅ pass | 55ms |
| 5 | `node -e "...workspace-layout.js dispose count check..."` | 0 | ✅ pass (found 4) | 52ms |


## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/cleanup.js`
- `frontend/static/js/workspace-layout.js`
