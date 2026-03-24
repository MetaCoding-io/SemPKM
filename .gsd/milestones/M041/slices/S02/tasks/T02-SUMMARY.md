---
id: T02
parent: S02
milestone: M041
provides:
  - CSS Architecture & Theming section of S02-FRONTEND-FINDINGS.md
key_files:
  - .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md
key_decisions: []
patterns_established:
  - "Three-tier hex classification: variable definitions (theme.css), var() fallback values, and standalone hardcoded — only the third tier is a real finding"
observability_surfaces:
  - "Detection commands in each finding block — re-run to verify finding status"
duration: 20m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T02: CSS architecture and theme consistency audit

**Audited 20,495 LOC across 16 CSS files, producing 5 findings covering hardcoded colors, rgba values, !important usage, breakpoint consistency, and property duplication.**

## What Happened

Ran systematic pattern-based detection across all `frontend/static/css/` files covering:

1. **CSS-01: 84 standalone hardcoded hex colors bypass the theme system** (Medium) — Of 499 hex instances, 360 are var() fallbacks (acceptable), 55 are theme.css definitions (expected), and 84 are truly standalone. Top offenders: `#fff` in 10 files, `#1e1e1e` in 5 files. Variable adoption rate: 89.7%.

2. **CSS-02: 202 standalone hardcoded rgba() values bypass theme system** (Medium) — Raw RGB values in rgba() calls that won't respond to theme changes. workspace.css has 101, bmc.css has 61. The `color-mix()` pattern is already used in some places but not consistently adopted.

3. **CSS-03: 61 !important declarations — 30 necessary, 31 avoidable** (Low) — 30 are driver.js (tour library) vendor overrides, which is standard practice. 31 are avoidable specificity workarounds across 7 files (workspace.css:10, views.css:9, style.css:6, etc.).

4. **CSS-04: Inconsistent responsive breakpoints — 4 values, no tokens** (Low) — 12 @media queries use 600px, 640px, 768px, and 800px with no documented standard set. The 640px/600px overlap causes jarring intermediate states.

5. **CSS-05: Repeated property patterns suggest missing utilities** (Low) — `display: flex` appears 165 times in workspace.css alone; the flex+align-items+flex-shrink triplet appears ~130 times.

Key insight: the hex color classification required distinguishing three tiers — theme definitions, var() fallbacks, and true standalone values. Without this separation, the hardcoded color count appears 6x worse (499 vs 84).

## Verification

- `test -f .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` → exists ✅
- `grep -c "^### " .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` → 13 (need ≥3 for T02) ✅
- `grep -c "Severity:" .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` → 13 (need ≥12 by slice end, already met) ✅
- Hardcoded color count per file: documented in file summary table and CSS-01 ✅
- CSS variable adoption percentage: 89.7% calculated and documented ✅
- !important usage quantified and categorized: 61 total, split into necessary/avoidable ✅

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` | 0 | ✅ pass | <1s |
| 2 | `grep -c "^### " .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` | 0 (returns 13, ≥3) | ✅ pass | <1s |
| 3 | `grep -c "Severity:" .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` | 0 (returns 13, ≥12) | ✅ pass | <1s |
| 4 | `grep -q "89.7%" .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` | 0 | ✅ pass | <1s |
| 5 | `grep -q "61.*important" .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` | 0 | ✅ pass | <1s |

## Diagnostics

Each finding in the output document includes a "Detection command" block that can be re-run at any time to verify the finding still applies. For example:
- `rg "#[0-9a-fA-F]{3,8}\b" frontend/static/css/ -n | grep -v "var(--" | grep -v "theme.css"` — should return 84 lines if no standalone hex colors have been migrated to variables.
- `rg "!important" frontend/static/css/ -n --count` — total should be 61; reduction indicates cleanup progress.

## Deviations

Added CSS-02 (hardcoded rgba) as a separate finding beyond the plan's scope. The plan only mentioned hex colors, but rgba values are a larger untokenized color surface (202 instances vs 84 hex) and represent the same theming gap. This was a natural extension of step 2.

## Known Issues

None.

## Files Created/Modified

- `.gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` — appended CSS Architecture & Theming section with 5 findings (CSS-01 through CSS-05), updated header with CSS stats
