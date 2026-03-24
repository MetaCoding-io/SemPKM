---
estimated_steps: 8
estimated_files: 1
skills_used: []
---

# T02: CSS architecture and theme consistency audit

**Slice:** S02 — Frontend Code Quality Audit
**Milestone:** M041

## Description

Audit CSS architecture: hardcoded colors vs CSS variables, specificity issues (!important usage), selector complexity, duplication patterns, and responsive breakpoint consistency.

## Steps

1. `fd -e css . frontend/static/css/ | xargs wc -l | sort -rn` — rank CSS files by size.
2. `rg "#[0-9a-fA-F]{3,8}\b" frontend/static/css/ -on --count` — count hardcoded colors per file. Sample 20 to categorize: should-be-variable vs legitimate one-off.
3. `rg "var\(--" frontend/static/css/ --count` — count variable usage per file. Compute variable adoption percentage.
4. `rg "!important" frontend/static/css/ -n --count` — find all specificity overrides. Categorize as necessary (vendor override) vs avoidable.
5. Check for deep nesting / complex selectors: `rg "^\s{8,}\S" frontend/static/css/ -n` as proxy for >4-level nesting.
6. Check for duplicated property blocks: look for identical multi-line declarations that could be shared classes.
7. `rg "@media" frontend/static/css/ -n` — audit responsive breakpoints for consistency (are the same breakpoints used everywhere?).
8. Append CSS Architecture & Theming section to S02-FRONTEND-FINDINGS.md.

## Must-Haves

- [ ] Hardcoded color count per file documented
- [ ] CSS variable adoption percentage calculated
- [ ] !important usage quantified and categorized

## Verification

- `grep -c "^### " .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` returns >= 3

## Inputs

- `.gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` — append to existing findings doc
- `frontend/static/css/` — all CSS source files

## Expected Output

- `.gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` — updated with CSS Architecture section
