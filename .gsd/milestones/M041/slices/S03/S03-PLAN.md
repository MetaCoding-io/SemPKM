# S03: Cross-Cutting Analysis & Report Assembly

**Goal:** Complete the cross-cutting quality dimensions (dead code, duplication, test gaps, tech debt) and assemble all findings into the final M041-RECOMMENDATIONS.md with a prioritized Top 10 summary.
**Demo:** The user reads the complete M041-RECOMMENDATIONS.md and sees every quality dimension covered, a Top 10 highest-impact list, and linting tool recommendations — ready to scope an execution milestone.

## Must-Haves

- Cross-cutting findings: dead code, duplication, test coverage gaps, tech debt
- All S01 + S02 findings consolidated into M041-RECOMMENDATIONS.md
- Top 10 prioritized summary section
- Linting tool recommendations (ruff, eslint, stylelint)
- Every finding has: category, severity, effort, file references

## Verification

- `test -f .gsd/milestones/M041/M041-RECOMMENDATIONS.md`
- `grep -c "^## " .gsd/milestones/M041/M041-RECOMMENDATIONS.md` returns >= 5 (major sections)
- `grep -q "Top 10" .gsd/milestones/M041/M041-RECOMMENDATIONS.md` (prioritized summary exists)
- `grep -q "Linting" .gsd/milestones/M041/M041-RECOMMENDATIONS.md` (tool recommendations exist)
- `grep -c "Severity:" .gsd/milestones/M041/M041-RECOMMENDATIONS.md` returns >= 30 (all findings consolidated)

## Tasks

- [x] **T01: Dead code, duplication, and test coverage gap analysis** `est:45m`
  - Why: These cross-cutting dimensions span both backend and frontend and weren't covered in S01/S02.
  - Files: all backend and frontend source files, `backend/tests/`
  - Do: (1) Dead code: `rg "# TODO|# FIXME|# HACK|# XXX" backend/ frontend/` for marked debt. Search for unused imports via ast-grep or grep patterns. Look for commented-out code blocks (>3 consecutive commented lines). (2) Duplication: identify copy-pasted utility functions (PersonMatcher is out of scope in apps/, but look for backend/ internal duplication). Check for duplicated SPARQL query fragments. (3) Test gaps: `fd -e py . backend/app/ -x basename {} .py` cross-referenced against `fd -e py . backend/tests/ -x basename {} .py` to find modules with zero test coverage. Identify critical paths (auth, commands, triplestore) and their coverage status. (4) Tech debt: cross-reference KNOWLEDGE.md and PROJECT.md tech debt sections. Check for items that have accumulated since those were written.
  - Verify: working notes exist with dead code count, duplication instances, and test gap list
  - Done when: cross-cutting analysis data is collected and ready for assembly

- [ ] **T02: Report assembly, Top 10 prioritization, and linting recommendations** `est:40m`
  - Why: The final deliverable. Consolidates all findings into one actionable report.
  - Files: `.gsd/milestones/M041/S01-BACKEND-FINDINGS.md`, `.gsd/milestones/M041/S02-FRONTEND-FINDINGS.md`, `.gsd/milestones/M041/M041-RECOMMENDATIONS.md`
  - Do: (1) Create M041-RECOMMENDATIONS.md with preamble (scope, methodology, metrics summary). (2) Consolidate backend findings from S01. (3) Consolidate frontend findings from S02. (4) Add cross-cutting section (dead code, duplication, test gaps, tech debt from T01). (5) Write Top 10 section by selecting highest-impact findings across all dimensions — prioritize by: runtime risk > correctness > maintainability > style. (6) Write linting recommendations section: recommend ruff for Python (with specific rule sets), eslint for JS, stylelint for CSS. Estimate setup effort. (7) Add appendix with all detection commands used for reproducibility. (8) Final verification: every dimension present, every finding annotated, Top 10 complete.
  - Verify: `test -f .gsd/milestones/M041/M041-RECOMMENDATIONS.md && grep -c "^## " .gsd/milestones/M041/M041-RECOMMENDATIONS.md` returns >= 5 && `grep -q "Top 10" .gsd/milestones/M041/M041-RECOMMENDATIONS.md`
  - Done when: M041-RECOMMENDATIONS.md is complete with all dimensions, Top 10, linting recommendations, and reproducible detection commands

## Files Likely Touched

- `.gsd/milestones/M041/M041-RECOMMENDATIONS.md` (created — the primary deliverable)
