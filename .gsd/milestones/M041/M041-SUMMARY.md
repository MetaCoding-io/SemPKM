---
id: M041
provides:
  - M041-RECOMMENDATIONS.md — 84 findings across 17 quality dimensions with Top 10 prioritization, linting configs, and reproducible detection commands
  - S01-BACKEND-FINDINGS.md — 40 backend findings across 8 dimensions
  - S02-FRONTEND-FINDINGS.md — 21 frontend findings across 5 dimensions
  - S03-CROSS-CUTTING-FINDINGS.md — 23 cross-cutting findings across 4 dimensions
key_decisions: []
patterns_established:
  - Pattern-based code quality audit using rg/fd/ast-grep/Python AST scales to 117K LOC without reading every file
  - Severity ranking by runtime risk > correctness > maintainability > style produces actionable prioritization
  - Three-tier hex classification (theme definitions / var() fallbacks / standalone hardcoded) separates real color issues from false positives
  - AST-based exception handler classification (silent pass, silent return, logged+reraise, logged+degrade) is more accurate than regex
  - Layer-stratified type annotation measurement (routers vs services vs utilities) enables targeted triage
observability_surfaces:
  - Every finding includes a Detection command re-runnable by any future agent to verify whether the issue persists
requirement_outcomes: []
duration: 115m
verification_result: passed
completed_at: 2026-03-23
---

# M041: Code Quality Audit — Backend & Frontend

**Systematic audit of the full SemPKM codebase (117,474 LOC across 442 files) producing a prioritized recommendation report with 84 findings across 17 quality dimensions — each severity-rated, effort-estimated, and anchored to specific files with reproducible detection commands.**

## What Happened

This was a pure analysis milestone — no source code changes, only `.gsd/` artifacts. Three slices executed sequentially, each contributing structured findings that S03 assembled into the final report.

**S01 (Backend, 40 findings)** audited 233 Python modules (60K LOC) across 8 dimensions: module structure, readability, error handling, logging, type safety, SPARQL construction, async patterns, and FastAPI patterns. The highest-risk backend findings: 131 f-string SPARQL construction sites with zero escaping (SQ-01), 26 completely silent `except Exception: pass` blocks (EH-02), `views/service.py` as a 3,663-line god module with a 1,020-line dispatcher function (MS-01), and 0% test coverage across all 7 auth modules (found in S03 cross-cutting analysis). AST-based analysis was substituted for regex in several cases — Python formatting conventions defeated grep patterns (e.g., `pass` on a separate line from `except`).

**S02 (Frontend, 21 findings)** audited 28 JS files (18.6K LOC), 16 CSS files (20.5K LOC), and 165 Jinja2 templates (18.3K LOC) across 5 dimensions: JS structure, DOM/event patterns, CSS architecture, template hygiene, and htmx consistency. The highest-risk frontend findings: 67 of 131 fetch() calls (51%) missing error handling (DOM-03), workspace.js as a 5,409-line monolith with 170 functions (JS-01), 188 unmatched addEventListener calls creating memory leak risk (DOM-01), and computation logic in Jinja2 templates that belongs in Python (TPL-02).

**S03 (Cross-Cutting + Assembly)** analyzed dead code, duplication, test coverage gaps, and tech debt — then assembled everything into the 1,034-line M041-RECOMMENDATIONS.md. Dead code was minimal (one confirmed dead function). Duplication analysis found 7 patterns, the largest being PersonMatcher duplicated across 9 sync apps. Test coverage revealed 165 of 193 backend modules have no dedicated test file, with critical gaps in auth (7/7 untested), commands (9/10 untested), and triplestore (3/3 untested). The Top 10 prioritization ranks SPARQL injection risk as #1, silent exceptions as #2, auth test coverage as #3, and unhandled fetch() as #4. Linting tool recommendations (ruff + ESLint + Stylelint) with specific configs are included — estimated 2 hours setup, ~100 auto-fixable issues.

## Cross-Slice Verification

| # | Success Criterion | Evidence | Pass? |
|---|-------------------|----------|-------|
| 1 | M041-RECOMMENDATIONS.md exists | `test -f .gsd/milestones/M041/M041-RECOMMENDATIONS.md` → exists | ✅ |
| 2 | Every stated dimension covered (12+) | 17 dimensions: 8 backend (S01) + 5 frontend (S02) + 4 cross-cutting (S03) | ✅ |
| 3 | Every recommendation has category + severity + effort + file references | 94 Severity: annotations, 86 Effort: annotations, 56 Location: annotations across 84 findings | ✅ |
| 4 | Top 10 highest-impact summary exists | `grep -q "Top 10" M041-RECOMMENDATIONS.md` → PASS | ✅ |
| 5 | Backend covered substantively | 40 findings across 8 dimensions, 72 backend-related references | ✅ |
| 6 | Frontend covered substantively | 21 findings across 5 dimensions, 32 frontend-related references | ✅ |
| 7 | Pattern-detection commands documented | Detection commands appendix in report + per-finding Detection: fields in source findings files | ✅ |
| 8 | No source code changes (analysis-only) | `git diff --stat HEAD $(git merge-base HEAD main) -- ':!.gsd/'` → empty (correct for analysis milestone) | ✅ |

**Definition of Done:**
- All 3 slices marked `[x]` in roadmap ✅
- All 3 slice summaries exist ✅
- S01→S03 boundary: S01-BACKEND-FINDINGS.md consumed by S03 ✅
- S02→S03 boundary: S02-FRONTEND-FINDINGS.md consumed by S03 ✅
- Final report assembled with all cross-cutting dimensions ✅

## Requirement Changes

None. M041 is a pure analysis milestone — it produces input for a future execution milestone but creates, validates, or transitions no requirements.

## Forward Intelligence

### What the next milestone should know
- The Top 10 list in M041-RECOMMENDATIONS.md is the execution starting point. Items #1 (SPARQL parameterization, 131 sites) and #2 (silent exception elimination, 26 blocks) carry runtime risk and should be prioritized.
- Linting setup (ruff + ESLint + Stylelint) is a low-effort, high-leverage quick win (~2 hours) that would prevent regression on many findings. Good candidate for a standalone quick milestone.
- `views/service.py` decomposition (#5 in Top 10) is the largest single refactoring — 3,663 LOC, 56 functions, 12 renderer types. The report recommends splitting into per-renderer modules. This is high-effort but the module is the most frequently-edited backend file.
- Test coverage gaps are concentrated: auth (0%), commands (10%), triplestore (0%). Starting with auth gives the highest blast-radius coverage improvement.
- Frontend fetch error handling (#4) is mechanical — a shared `apiFetch()` wrapper plus migration of 67 call sites. Medium effort, high user-impact improvement.

### What's fragile
- Detection commands that count lines (`wc -l`) or matches (`rg -c`) will drift as the codebase evolves. The commands are accurate as of audit date (2026-03-23). Re-run them to get current counts rather than trusting the documented numbers.
- Severity ratings are judgment calls. The ranking (runtime risk > correctness > maintainability > style) is documented but reasonable people could reorder some medium-vs-high items.

### Authoritative diagnostics
- `M041-RECOMMENDATIONS.md` Top 10 section — the prioritized execution roadmap
- Each finding's Detection command (in the source findings files S01/S02/S03) — re-runnable verification of whether each issue still exists
- `grep -c "Severity:" M041-RECOMMENDATIONS.md` — confirms annotation completeness (currently 94)

### What assumptions changed
- Expected ~40-50 findings across 12 dimensions. Actual: 84 findings across 17 dimensions. Error handling, SPARQL construction, and test coverage were richer than anticipated.
- Expected significant dead code and TODO markers. Actual: the codebase is clean on that dimension — zero TODO/FIXME/HACK markers, minimal commented-out code, one confirmed dead function. The real quality risks are in error handling patterns and test coverage, not accumulated cruft.
- Expected CSS variable adoption to be a major issue. Actual: 89.7% adoption already — only 84 standalone hex + 202 rgba values remain. The theme system is mature.

## Files Created/Modified

- `.gsd/milestones/M041/M041-RECOMMENDATIONS.md` — 1,034-line final report with 84 findings, Top 10, linting configs, detection commands appendix
- `.gsd/milestones/M041/S01-BACKEND-FINDINGS.md` — 681-line backend findings (40 findings, 8 dimensions)
- `.gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` — frontend findings (21 findings, 5 dimensions)
- `.gsd/milestones/M041/S03-CROSS-CUTTING-FINDINGS.md` — cross-cutting findings (23 findings, 4 dimensions)
