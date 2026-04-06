---
id: T02
parent: S01
milestone: M051
key_files:
  - frontend/static/js/dropdown-dismiss.js
  - .gsd/KNOWLEDGE.md
key_decisions:
  - Used _getFixedContainingBlockRect() to detect CSS contain:layout ancestors that create new containing blocks for position:fixed — coordinates computed relative to containing block, not viewport
  - MutationObserver on document.body with subtree:true to detect dropdown population from htmx swaps and multi-value field cloning
  - Scroll listener uses capture phase to catch scroll events on any ancestor element
duration: 
verification_result: passed
completed_at: 2026-04-06T01:01:32.977Z
blocker_discovered: false
---

# T02: Added position:fixed repositioning with containing-block correction and flip-above logic to suggestion dropdowns, escaping overflow clipping in dockview panels

**Added position:fixed repositioning with containing-block correction and flip-above logic to suggestion dropdowns, escaping overflow clipping in dockview panels**

## What Happened

Extended dropdown-dismiss.js with repositioning logic that switches suggestion dropdowns to position:fixed when populated (via MutationObserver), flips above the input when insufficient viewport space below (MIN_SPACE_BELOW=220px), and corrects for dockview's CSS contain:layout which creates a new containing block for fixed-position elements. Added scroll (capture phase) and resize dismiss listeners to prevent orphaned fixed dropdowns. Builder dropdowns are explicitly skipped via the .builder-suggestions class check.

## Verification

All 7 must-haves verified in-browser inside dockview panels: tag field near bottom flips above correctly, reference field with space below renders below normally, dropdown width/left matches input, dismiss (click-outside/Escape/scroll) resets inline styles, works for both reference and tag fields, builder dropdowns skipped. JS syntax check passes. File serves 200 from nginx.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `node -c frontend/static/js/dropdown-dismiss.js` | 0 | ✅ pass | 100ms |
| 2 | `curl -s -o /dev/null -w '%{http_code}' http://localhost:3901/js/dropdown-dismiss.js` | 0 | ✅ pass | 100ms |
| 3 | `rg '_repositionDropdown' frontend/static/js/dropdown-dismiss.js` | 0 | ✅ pass | 50ms |
| 4 | `Browser: tag field near bottom → dropdown flips above, fully visible` | 0 | ✅ pass | 5000ms |
| 5 | `Browser: reference field with space below → dropdown renders below` | 0 | ✅ pass | 3000ms |
| 6 | `Browser: scroll panel → dropdown dismissed, styles reset` | 0 | ✅ pass | 2000ms |
| 7 | `Browser: Escape + click-outside → dismissed, styles reset` | 0 | ✅ pass | 1000ms |

## Deviations

Added _getFixedContainingBlockRect() to handle dockview's contain:layout creating a new containing block for position:fixed — not anticipated by the plan. Added style.right='auto' override for CSS right:0 conflict. No CSS changes to forms.css were needed.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/dropdown-dismiss.js`
- `.gsd/KNOWLEDGE.md`
