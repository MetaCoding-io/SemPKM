---
estimated_steps: 7
estimated_files: 1
skills_used: []
---

# T02: Error handling and logging audit

**Slice:** S01 — Backend Code Quality Audit
**Milestone:** M041

## Description

Audit error handling patterns (broad catches, swallowed exceptions, missing context) and logging consistency (structured vs unstructured, level appropriateness, coverage gaps) across all backend modules.

## Steps

1. `rg "except Exception" -n backend/app/` — catalog all broad exception catches with file:line.
2. `rg "except.*:\s*pass$" -n backend/app/` and `rg "except.*:\s*$" -A2 -n backend/app/` — find swallowed exceptions.
3. For each broad catch, classify: (a) genuinely needs broad catch + logs, (b) should be narrowed, (c) swallowed and dangerous.
4. `rg "logger = |logging\.getLogger" backend/app/ --count` — check which modules have loggers. Cross-reference against all modules to find logging gaps.
5. `rg "logger\.\w+\(f\"" backend/app/ --count` — find f-string logging (should use % or extra= for structured logging).
6. Sample 5 modules for log level appropriateness — are errors logged as info? Are debug messages logged as warning?
7. Append Error Handling and Logging sections to S01-BACKEND-FINDINGS.md.

## Must-Haves

- [ ] All swallowed exceptions identified with file:line
- [ ] All broad `except Exception` classified by risk
- [ ] Modules with zero logging identified

## Verification

- `grep -c "^### " .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` returns >= 4

## Inputs

- `.gsd/milestones/M041/S01-BACKEND-FINDINGS.md` — append to existing findings doc
- `backend/app/` — all Python source modules

## Expected Output

- `.gsd/milestones/M041/S01-BACKEND-FINDINGS.md` — updated with Error Handling and Logging sections
