---
id: T02
parent: S03
milestone: M051
key_files:
  - backend/app/templates/admin/model_ontology_diagram.html
key_decisions:
  - Fixed both node and edge hover popovers since both had identical panel-relative positioning bug
duration: 
verification_result: passed
completed_at: 2026-04-06T01:30:08.521Z
blocker_discovered: false
---

# T02: Fixed admin ontology diagram popover positioning by removing panel-relative offset subtraction from both node and edge hover handlers, using viewport coordinates to match position:fixed CSS

**Fixed admin ontology diagram popover positioning by removing panel-relative offset subtraction from both node and edge hover handlers, using viewport coordinates to match position:fixed CSS**

## What Happened

The .graph-popover element uses position:fixed but the positioning JS subtracted panelRect offsets, double-transforming coordinates and misplacing the popover. Removed panelRect subtraction from all coordinate calculations in both node hover (showPopover) and edge hover (setTimeout callback), switched overflow boundary checks from panel bounds to window.innerWidth/innerHeight.

## Verification

All grep checks pass: zero panelRect references remain, containerRect.left + pos confirms viewport-relative coords, window.innerWidth/innerHeight confirms viewport overflow checks.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -c panelRect | grep '^0$' && grep -q containerRect.left+pos && grep -q window.innerWidth` | 0 | ✅ pass | 100ms |

## Deviations

Fixed edge hover popover in addition to node hover — plan only mentioned showPopover but identical bug was in edge hover callback.

## Known Issues

None.

## Files Created/Modified

- `backend/app/templates/admin/model_ontology_diagram.html`
