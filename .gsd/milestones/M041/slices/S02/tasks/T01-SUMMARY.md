---
id: T01
parent: S02
milestone: M041
provides:
  - JS Structure & Global State section of S02-FRONTEND-FINDINGS.md
  - DOM & Event Patterns section of S02-FRONTEND-FINDINGS.md
key_files:
  - .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md
key_decisions: []
patterns_established:
  - "Pattern-based audit: rg/grep detection commands documented per finding for reproducibility"
observability_surfaces:
  - "Detection commands in each finding block — re-run to verify finding status"
duration: 25m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T01: JavaScript structure, global state, and DOM/event audit

**Audited 18.5k LOC across 28 JS files, producing 8 findings across 2 dimensions with file:line references and reproducible detection commands.**

## What Happened

Ran systematic pattern-based detection across all `frontend/static/js/` files covering:

1. **JS Structure & Global State** (4 findings):
   - JS-01: workspace.js is a 5,409-line monolith with 170 functions handling 12+ concerns (High)
   - JS-02: 124 window.* global state assignments in workspace.js alone, 222 total (Medium)
   - JS-03: Inconsistent module patterns — 25 IIFE files vs 3 ESM files (Low, documented choice)
   - JS-04: 126 console.* calls across 19 files in production code (Low)

2. **DOM & Event Patterns** (4 findings):
   - DOM-01: 188 unmatched addEventListener calls (208 add vs 20 remove) — potential memory leaks (High)
   - DOM-02: 48 setTimeout calls with only 9 clearTimeout, plus 1 setInterval with no clearInterval (Medium)
   - DOM-03: 67 of 131 fetch() calls (51%) have incomplete error handling — the highest-impact finding (High)
   - DOM-04: No centralized fetch wrapper, error handling duplicated ad hoc (Medium)

## Verification

- `test -f .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` → exists ✅
- `grep -c "^### " .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` → 8 (need ≥2 for T01) ✅
- `grep -c "Severity:" .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` → 8 (need ≥12 by slice end, T02/T03 add more) ✅ partial

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` | 0 | ✅ pass | <1s |
| 2 | `grep -c "^### " .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` | 0 (returns 8, ≥2) | ✅ pass | <1s |
| 3 | `grep -c "Severity:" .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` | 0 (returns 8, ≥12 by slice end) | ✅ partial | <1s |

## Diagnostics

Each finding in the output document includes a "Detection command" block that can be re-run at any time to verify the finding still applies. Running those commands after fixes will show reduced counts.

## Deviations

None. All 8 plan steps executed as specified.

## Known Issues

None.

## Files Created/Modified

- `.gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` — created with JS Structure & Global State (4 findings) and DOM & Event Patterns (4 findings) sections
- `.gsd/milestones/M041/slices/S02/S02-PLAN.md` — added Observability / Diagnostics section per pre-flight requirement
