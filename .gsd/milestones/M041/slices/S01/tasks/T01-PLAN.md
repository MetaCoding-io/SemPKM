---
estimated_steps: 6
estimated_files: 1
skills_used: []
---

# T01: Module structure, readability, and god-module analysis

**Slice:** S01 — Backend Code Quality Audit
**Milestone:** M041

## Description

Identify all oversized backend modules, assess function length distribution, check naming conventions and docstring coverage. Establish the findings document format and write the first two dimension sections.

## Steps

1. Run `fd -e py . backend/app/ | xargs wc -l | sort -rn | head -30` to rank modules by size. Flag everything >300 LOC.
2. For the top 5 largest modules, count functions via `rg "^    def |^def " <file> | wc -l`. Assess cohesion (how many distinct responsibilities).
3. Find long functions: `rg "^    def |^def " backend/app/ -n` then check line spans for functions >50 lines.
4. Check naming conventions: `rg "def [A-Z]" backend/app/` for non-snake_case functions. `rg "class [a-z]" backend/app/` for non-PascalCase classes.
5. Sample docstring coverage: for 10 representative modules, check whether public functions have docstrings.
6. Write Module Structure and Readability sections to S01-BACKEND-FINDINGS.md with severity/effort/file:line per finding.

## Must-Haves

- [ ] All modules >300 LOC identified with line counts
- [ ] God modules (>500 LOC with >15 functions) have specific decomposition recommendations
- [ ] Detection commands documented for each finding

## Verification

- `test -f .gsd/milestones/M041/S01-BACKEND-FINDINGS.md && grep -c "^### " .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` returns >= 2

## Inputs

- `backend/app/` — all Python source modules to analyze

## Expected Output

- `.gsd/milestones/M041/S01-BACKEND-FINDINGS.md` — created with Module Structure and Readability sections
