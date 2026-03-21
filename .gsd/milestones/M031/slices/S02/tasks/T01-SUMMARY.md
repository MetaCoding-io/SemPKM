---
id: T01
parent: S02
milestone: M031
provides:
  - unique tab IDs for generic view instances so multiple tabs of the same renderer coexist
  - scopeLabel parameter for caller-controlled tab differentiation
key_files:
  - frontend/static/js/workspace.js
key_decisions:
  - Unscoped generic view tabs use Date.now() for uniqueness — no deduplication on repeat clicks from explorer sidebar
  - Scoped tabs deduplicate by renderer+scopeQuery composite key
  - Tab label numbering for unscoped duplicates counts existing same-renderer panels at creation time
patterns_established:
  - Tab ID scheme: generic-view:{renderer}:{timestamp} (unscoped) or generic-view:{renderer}:scope:{queryId} (scoped)
  - Optional scopeLabel third parameter for callers to set a human-readable tab title suffix
observability_surfaces:
  - Dockview panel IDs visible in browser DevTools showing tab scheme
  - Tab labels in dockview tab bar differentiate instances visually
duration: 15m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T01: Enable multiple generic view instances as separate dockview tabs

**Changed openGenericViewTab() tab ID from fixed `generic-view:{renderer}` to unique `generic-view:{renderer}:{timestamp}` (unscoped) or `generic-view:{renderer}:scope:{queryId}` (scoped), enabling multiple independent dockview tabs per renderer type.**

## What Happened

Rewrote `openGenericViewTab()` in `workspace.js` (line 3217) to replace the fixed tab ID scheme with a dual strategy:

1. **Scoped tabs** (caller passes `scopeQuery`): tab key is `generic-view:{renderer}:scope:{scopeQuery}`. If a tab with that key already exists, it's activated instead of creating a duplicate — this is the correct deduplication behavior for saved views.

2. **Unscoped tabs** (explorer sidebar clicks, no scopeQuery): tab key is `generic-view:{renderer}:{Date.now()}`. Each click creates a fresh independent tab instance — no deduplication, per the VIEW-10 requirement.

Tab labels differentiate instances: scoped tabs append the query name via the new `scopeLabel` parameter ("Table View — My Projects"), and unscoped duplicates get a numeric suffix ("Table View (2)") based on existing same-renderer panel count.

The function signature now accepts an optional third parameter `scopeLabel`, maintaining backward compatibility with all existing callers (explorer sidebar with 1 arg, tutorials.js with 1 arg).

Verified that `workspace-layout.js` special-panel init (line 237) reads from `params.params.renderer/selectedType/scopeQuery` which is unchanged in the addPanel params — no modification needed.

## Verification

- Old fixed tab key pattern removed: `grep -c "var tabKey = 'generic-view:' + renderer;"` returns 0
- New scope pattern present: `grep -q "generic-view:.*scope:"` confirms match
- Date.now pattern present: `node -e` inline check prints "OK"
- Function signature has 3 params: `grep -c "openGenericViewTab(renderer, scopeQuery, scopeLabel)"` returns 1
- `workspace-layout.js` confirmed unaffected — reads `params.params.*` fields which remain unchanged

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -c "var tabKey = 'generic-view:' + renderer;" frontend/static/js/workspace.js` | 1 (count=0) | ✅ pass | <1s |
| 2 | `grep -q "generic-view:.*scope:" frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |
| 3 | `node -e "...Date.now check..."` | 0 (prints OK) | ✅ pass | <1s |
| 4 | `grep -c "openGenericViewTab(renderer, scopeQuery, scopeLabel)" frontend/static/js/workspace.js` | 0 (count=1) | ✅ pass | <1s |
| 5 | `grep -c "generic-view:" frontend/static/js/workspace.js` (slice check) | 0 (count=3) | ⚠️ expected 0, see note | <1s |

**Note on check 5:** The slice verification `grep -c "generic-view:"` expects 0, but the new code intentionally uses `generic-view:` as a prefix in the dynamic tab ID generation (3 occurrences). The intent of the check was to confirm the old *fixed* pattern `var tabKey = 'generic-view:' + renderer;` is gone — which check 1 confirms. This is a spec false-negative, not a code defect. T02 should update the slice verification to check for the old fixed pattern specifically rather than any occurrence of the prefix string.

## Diagnostics

- **Panel IDs:** Open browser DevTools → Elements → inspect dockview panel containers. Each generic view tab has a unique ID like `generic-view:table:1711036800000`.
- **Tab labels:** Visible in the dockview tab bar. Unscoped duplicates show numeric suffix; scoped tabs show scope label.
- **Failure mode:** If Date.now() somehow collided (same-millisecond clicks), dockview would log a console error about duplicate panel IDs. This is astronomically unlikely from user interaction.

## Deviations

None — implementation follows the task plan exactly.

## Known Issues

- Slice verification check `grep -c "generic-view:" frontend/static/js/workspace.js` returns 3 instead of expected 0. The check needs to be refined to target the old fixed pattern specifically (e.g., `grep -c "var tabKey = 'generic-view:' + renderer;"` which correctly returns 0).

## Files Created/Modified

- `frontend/static/js/workspace.js` — Rewrote `openGenericViewTab()` with unique tab ID scheme and optional `scopeLabel` parameter
- `.gsd/milestones/M031/slices/S02/tasks/T01-PLAN.md` — Added Observability Impact section per pre-flight requirement
