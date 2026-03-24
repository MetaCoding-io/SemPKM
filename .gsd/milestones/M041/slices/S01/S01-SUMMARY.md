---
id: S01
parent: M041
milestone: M041
provides:
  - S01-BACKEND-FINDINGS.md — 40 findings across 8 quality dimensions with severity/effort/file:line references and reproducible detection commands
requires: []
affects:
  - S03
key_files:
  - .gsd/milestones/M041/S01-BACKEND-FINDINGS.md
key_decisions:
  - AST parsing over regex for function counts, exception handler classification, and annotation coverage — regex misses multiline patterns
  - Layer-stratified type annotation measurement (routers vs services vs utilities) for actionable triage
patterns_established:
  - Findings format — each finding has ID (dimension prefix + number), Severity, Effort, Location (file:line), Detection (re-runnable shell command), narrative, and decomposition/fix recommendation
  - AST-based exception handler classification (silent pass, silent return, logged+reraise, logged+degrade) — more accurate than grep-based detection
observability_surfaces:
  - Every finding includes a Detection command re-runnable by any future agent to verify whether the issue persists
drill_down_paths:
  - .gsd/milestones/M041/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M041/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M041/slices/S01/tasks/T03-SUMMARY.md
duration: 70m
verification_result: passed
completed_at: 2026-03-23
---

# S01: Backend Code Quality Audit

**Systematic audit of 233 backend Python modules (60k LOC) across 8 quality dimensions, producing 40 categorized findings with severity ratings, effort estimates, file:line references, and reproducible detection commands.**

## What Happened

Three tasks executed sequentially, each appending findings sections to `S01-BACKEND-FINDINGS.md`:

**T01 — Module structure and readability (13 findings).** Identified 9 modules exceeding 1,000 LOC. Top god module: `views/service.py` (3,663 LOC, 56 functions, 12 renderer types in one class). Top god function: `generic_view()` at 1,020 lines — a giant if/elif dispatcher. 280 functions exceed 50 lines. Naming conventions are clean (zero violations). Docstring coverage is 98%+. Each god module got specific decomposition recommendations.

**T02 — Error handling and logging (12 findings).** Found 312 `except Exception` handlers. Classified by risk: 26 completely silent (`pass`), 19 silent returns, the rest logged-and-degraded. Worst cluster: `admin/router.py` with 7 sequential silent catches. 26 substantial modules (>100 LOC) lack any logging — most critically `auth/service.py` (333 LOC, authentication, zero logging). Zero structured logging across 743 log calls. Two log level misclassifications found.

**T03 — Type safety, SPARQL, async, FastAPI patterns (15 findings).** 74% return type annotation coverage overall, but routers average only 17%. 131 f-string SPARQL construction sites with no parameterized query builder. `scope_filter` injected raw into 11 WHERE clauses. 6 blocking `open()` calls in async handlers. 254 direct `request.app.state` accesses vs only 9 `Depends()` factories. Inconsistent router prefix conventions.

The findings document totals 681 lines with a summary statistics section, 8 dimension sections, and 40 individually-numbered findings.

## Verification

All 4 slice-level checks pass:

| # | Check | Result | Pass? |
|---|-------|--------|-------|
| 1 | `test -f .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` | exists | ✅ |
| 2 | `grep -c "^### " S01-BACKEND-FINDINGS.md` ≥ 8 | 40 | ✅ |
| 3 | `grep -c "Severity:" S01-BACKEND-FINDINGS.md` ≥ 15 | 40 | ✅ |
| 4 | `grep -c "Detection:" S01-BACKEND-FINDINGS.md` ≥ 15 | 40 | ✅ |

## Requirements Advanced

None — M041 is a pure analysis milestone that produces input for a future execution milestone.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

- T02 plan step 2 (`rg "except.*:\s*pass$"`) found zero matches because Python formatting places `pass` on the next line. AST-based analysis was substituted, which correctly identifies all silent handlers regardless of formatting.
- T03 added 4 additional findings beyond the plan's scope (SQ-02 scope_filter injection, SQ-03 duplicated IRI validation, FP-03 incomplete dependencies.py, FP-04 middleware ordering) — emerged naturally from the audit data.

## Known Limitations

- The audit uses pattern-based detection (rg, AST, fd+wc). Isolated one-off issues that don't match searchable patterns may be missed. Acceptable — the goal is systematic patterns, not line-by-line review.
- Severity ratings are anchored to impact heuristics (runtime errors > contributor confusion > style inconsistency) but are inherently judgment calls.

## Follow-ups

None — S02 (frontend) and S03 (cross-cutting + assembly) are already planned in the roadmap.

## Files Created/Modified

- `.gsd/milestones/M041/S01-BACKEND-FINDINGS.md` — 681-line findings document with 8 dimension sections and 40 findings

## Forward Intelligence

### What the next slice should know
- The backend findings are structured as `## Dimension` → `### Finding XX-NN` with consistent Severity/Effort/Location/Detection fields. S03 can grep/parse this structure mechanically.
- The summary statistics section at the top of the findings file provides aggregate numbers for each dimension — useful for the Top 10 prioritization in S03.
- The highest-impact backend findings are: `views/service.py` decomposition (MS-01), missing SPARQL parameterization (SQ-01), silent exception blocks (EH-02/EH-03), and router type annotation gaps (TS-01).

### What's fragile
- Detection commands that count lines (`wc -l`) or matches (`rg -c`) will drift as the codebase evolves. The commands are accurate as of the audit date; S03 should not re-run them but instead reference the documented counts.

### Authoritative diagnostics
- Any finding's Detection command can be re-run to check whether the issue still exists — this is the primary reproducibility mechanism.

### What assumptions changed
- Expected ~20-25 findings across 8 dimensions. Actual: 40 findings. The error handling and SPARQL construction dimensions were richer than anticipated. 5 positive findings (clean naming, no f-string logging, no deprecated Pydantic, no sleep calls, good exc_info usage) were included to give a balanced picture.
