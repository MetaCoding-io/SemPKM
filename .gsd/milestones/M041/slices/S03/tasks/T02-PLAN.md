---
estimated_steps: 8
estimated_files: 1
skills_used: []
---

# T02: Report assembly, Top 10 prioritization, and linting recommendations

**Slice:** S03 — Cross-Cutting Analysis & Report Assembly
**Milestone:** M041

## Description

Assemble the final M041-RECOMMENDATIONS.md by consolidating S01 backend findings, S02 frontend findings, and T01 cross-cutting analysis. Add Top 10 prioritized summary and linting tool recommendations.

## Steps

1. Create M041-RECOMMENDATIONS.md with preamble: scope, methodology, codebase metrics summary (from M041-RESEARCH.md).
2. Add "## Backend Findings" section — consolidate from S01-BACKEND-FINDINGS.md (8 dimensions).
3. Add "## Frontend Findings" section — consolidate from S02-FRONTEND-FINDINGS.md (5 dimensions).
4. Add "## Cross-Cutting Findings" section — dead code, duplication, test gaps, tech debt from T01 data.
5. Write "## Top 10 Highest-Impact Recommendations" — select from all findings, prioritized by: runtime risk > correctness > maintainability > style. Each entry: rank, title, category, severity, effort, brief rationale, file references.
6. Write "## Linting Tool Recommendations" — recommend ruff (Python), eslint (JS), stylelint (CSS) with specific rule sets and estimated setup effort.
7. Add "## Appendix: Detection Commands" — reproducible rg/ast-grep/fd commands used for each finding category.
8. Final validation: every dimension present, every finding annotated, Top 10 complete.

## Must-Haves

- [ ] All 12+ quality dimensions present in the report
- [ ] Every finding has category, severity, effort, file references
- [ ] Top 10 section exists with ranked recommendations
- [ ] Linting tool recommendations with specific rule sets
- [ ] Detection commands appendix for reproducibility

## Verification

- `test -f .gsd/milestones/M041/M041-RECOMMENDATIONS.md`
- `grep -c "^## " .gsd/milestones/M041/M041-RECOMMENDATIONS.md` returns >= 5
- `grep -q "Top 10" .gsd/milestones/M041/M041-RECOMMENDATIONS.md`
- `grep -q "Linting" .gsd/milestones/M041/M041-RECOMMENDATIONS.md`
- `grep -c "Severity:" .gsd/milestones/M041/M041-RECOMMENDATIONS.md` returns >= 30

## Inputs

- `.gsd/milestones/M041/S01-BACKEND-FINDINGS.md` — backend audit findings from S01
- `.gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` — frontend audit findings from S02
- `.gsd/milestones/M041/M041-RESEARCH.md` — codebase metrics for preamble

## Expected Output

- `.gsd/milestones/M041/M041-RECOMMENDATIONS.md` — the complete, final deliverable
