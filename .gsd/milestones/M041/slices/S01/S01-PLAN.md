# S01: Backend Code Quality Audit

**Goal:** Systematically audit 60k LOC of backend Python across 8 quality dimensions using pattern-based detection, producing a structured findings document.
**Demo:** The user reads S01-BACKEND-FINDINGS.md and sees categorized, severity-rated findings with file:line references and reproducible detection commands.

## Must-Haves

- Findings for all 8 backend dimensions: readability, module structure, logging, error handling, type safety, SPARQL construction, async patterns, FastAPI patterns
- Every finding has: category, severity, effort, file:line reference
- Detection commands are documented for each finding category

## Verification

- `test -f .gsd/milestones/M041/S01-BACKEND-FINDINGS.md`
- `grep -c "^### " .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` returns >= 8 (8+ dimension sections)
- `grep -c "Severity:" .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` returns >= 15 (15+ individual findings)
- Each finding's detection command is re-runnable: `grep -c "Detection:" .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` returns >= 15

## Tasks

- [x] **T01: Module structure, readability, and god-module analysis** `est:45m`
  - Why: The largest files (views/service.py 3663 LOC, admin/router.py 1400 LOC, main.py 750 LOC) are the highest-impact structural findings. This task also establishes the findings document format.
  - Files: `backend/app/views/service.py`, `backend/app/main.py`, `backend/app/admin/router.py`, `backend/app/views/router.py`, all backend modules
  - Do: (1) Use `fd -e py` + `wc -l` to identify all modules >300 LOC. (2) For each god-module, count functions and classes via ast-grep or grep. (3) Assess function length distribution (functions >50 lines). (4) Check naming conventions (snake_case compliance, `_private` prefix consistency). (5) Check docstring coverage via ast-grep for def without docstring. (6) Write findings to S01-BACKEND-FINDINGS.md with the dimension sections for "Module Structure" and "Readability & Naming". Each finding gets severity/effort/file:line and the detection command used.
  - Verify: `test -f .gsd/milestones/M041/S01-BACKEND-FINDINGS.md && grep -c "^### " .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` returns >= 2
  - Done when: Module Structure and Readability sections exist with specific findings

- [x] **T02: Error handling and logging audit** `est:40m`
  - Why: Research found 15 swallowed exceptions and 7 broad `except Exception` blocks in admin/router.py alone. Error handling is a runtime reliability concern.
  - Files: all backend `.py` files
  - Do: (1) `rg "except Exception" --count` across backend/ to find all broad catches. (2) `rg "except.*:[\s]*pass" -n` to find swallowed exceptions. (3) `rg "except.*:\s*$" -A2` to find empty except blocks. (4) Audit logging patterns: `rg "logger\." --count` vs modules with no logging. (5) Check structured vs unstructured logging (f-string in log calls vs %s or extra={}). (6) Check log level appropriateness (logger.info for errors, logger.debug for important events). (7) Append "Error Handling" and "Logging" sections to findings doc.
  - Verify: `grep -c "^### " .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` returns >= 4
  - Done when: Error Handling and Logging sections exist with categorized findings

- [ ] **T03: Type safety, SPARQL construction, async patterns, and FastAPI audit** `est:50m`
  - Why: Completes the backend dimension coverage. SPARQL f-string injection is a correctness risk. Type annotation gaps affect maintainability. Async boundary violations cause runtime bugs.
  - Files: all backend `.py` files, especially `backend/app/views/service.py`, `backend/app/triplestore/`, `backend/app/sparql/`, `backend/app/dependencies.py`
  - Do: (1) Type safety: count functions without return annotations via grep/ast-grep. Sample annotation coverage across routers vs services vs utilities. (2) SPARQL construction: `rg 'f".*SELECT|f".*INSERT|f".*DELETE|f".*CONSTRUCT' backend/` to find f-string SPARQL. Check for the absence of a shared escaping utility. (3) Async: `rg "def [a-z]" backend/app/` in async router files to find sync functions in async contexts. Check for `time.sleep`, `open()`, other blocking calls in async code. (4) FastAPI: Check dependency injection patterns, router organization (flat vs nested), middleware layering. (5) Append "Type Safety", "SPARQL Construction", "Async Patterns", and "FastAPI Patterns" sections.
  - Verify: `grep -c "^### " .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` returns >= 8
  - Done when: All 8 backend dimension sections exist with specific, actionable findings

## Files Likely Touched

- `.gsd/milestones/M041/S01-BACKEND-FINDINGS.md` (created)
 any future agent can re-run
- Severity ratings enable triage (Critical > High > Medium > Low)
- File:line references enable direct navigation to each finding
- If a detection command produces zero results on a future run, the finding has been fixed

**Failure visibility:** If the findings document is incomplete (fewer than 8 sections or fewer than 15 findings), the slice verification checks will fail with specific counts, indicating which dimension coverage is missing.

## Files Likely Touched

- `.gsd/milestones/M041/S01-BACKEND-FINDINGS.md` (created)
