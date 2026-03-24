# M041: Code Quality Audit — Backend & Frontend

**Vision:** A prioritized recommendation report covering every quality dimension of the SemPKM codebase — categorized, severity-rated, effort-estimated, and anchored to specific files. The report feeds a follow-up execution milestone.

## Success Criteria

- The recommendation report exists at `.gsd/milestones/M041/M041-RECOMMENDATIONS.md`
- Every stated dimension is covered: readability, module structure, logging, error handling, type safety, SPARQL/SQL patterns, CSS architecture, JS structure, test gaps, duplication, dead code, tech debt
- Every recommendation has: category, severity (critical/high/medium/low), effort estimate (small/medium/large), and specific file:line references
- The report includes a Top 10 highest-impact recommendations summary
- Backend and frontend are both covered substantively — not one at the expense of the other
- Pattern-detection commands (rg, ast-grep, fd) are included so findings are reproducible

## Key Risks / Unknowns

- **Context window pressure** — 117k LOC can't be read in a single pass. Pattern-based detection (rg, ast-grep) must substitute for line-by-line review. Risk of missing isolated issues. Acceptable — the goal is systematic patterns.
- **Severity subjectivity** — Mitigated by anchoring to concrete impact: runtime errors > contributor confusion > style inconsistency.

## Verification Classes

- Contract verification: file existence, section count, grep-based structure validation of the report
- Integration verification: none — pure analysis
- Operational verification: none — no runtime
- UAT / human verification: the user reads the report and judges whether it's actionable

## Milestone Definition of Done

This milestone is complete only when all are true:

- M041-RECOMMENDATIONS.md exists with all 12+ quality dimensions covered
- Every finding has category + severity + effort + file references
- Top 10 prioritized summary section exists
- Backend findings and frontend findings are both substantive (not placeholder)
- Pattern-detection commands are documented for reproducibility

## Requirement Coverage

- Covers: none — this milestone creates no requirements; it produces input for a future execution milestone
- Partially covers: none
- Leaves for later: all existing requirements are unaffected
- Orphan risks: none

## Slices

- [ ] **S01: Backend Code Quality Audit** `risk:high` `depends:[]`
  > After this: the user can read a structured findings section covering backend Python across 8 dimensions (readability, module structure, logging, error handling, type safety, SPARQL patterns, async hygiene, FastAPI patterns) with severity-rated, effort-estimated entries anchored to specific files
- [ ] **S02: Frontend Code Quality Audit** `risk:medium` `depends:[]`
  > After this: the user can read a structured findings section covering frontend JS, CSS, and Jinja2 templates across 5 dimensions (JS structure, CSS architecture, template hygiene, DOM/event patterns, htmx consistency) with severity-rated, effort-estimated entries anchored to specific files
- [ ] **S03: Cross-Cutting Analysis & Report Assembly** `risk:low` `depends:[S01,S02]`
  > After this: the user can read the complete M041-RECOMMENDATIONS.md report with cross-cutting findings (dead code, duplication, test gaps, tech debt), the Top 10 prioritized summary, and a linting tool recommendation section — all dimensions consolidated into a single deliverable

## Boundary Map

### S01 → S03

Produces:
- Backend findings written to `.gsd/milestones/M041/S01-BACKEND-FINDINGS.md` — structured per-dimension sections with severity/effort/file annotations

Consumes:
- nothing (first slice, reads source code directly)

### S02 → S03

Produces:
- Frontend findings written to `.gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` — structured per-dimension sections with severity/effort/file annotations

Consumes:
- nothing (independent slice, reads source code directly)

### S03

Produces:
- `.gsd/milestones/M041/M041-RECOMMENDATIONS.md` — the final consolidated report with all dimensions, Top 10 summary, and linting recommendations

Consumes:
- `S01-BACKEND-FINDINGS.md` and `S02-FRONTEND-FINDINGS.md` from S01 and S02
