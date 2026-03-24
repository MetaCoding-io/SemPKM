---
id: T03
parent: S01
milestone: M041
provides:
  - Type Safety, SPARQL Construction, Async Patterns, and FastAPI Patterns sections in S01-BACKEND-FINDINGS.md (15 findings: TS-01 through TS-03, SQ-01 through SQ-04, AP-01 through AP-04, FP-01 through FP-04)
  - Complete 8-dimension backend audit with 40 findings across 40 subsections
key_files:
  - .gsd/milestones/M041/S01-BACKEND-FINDINGS.md
key_decisions: []
patterns_established:
  - Layer-stratified annotation coverage measurement (routers vs services vs utilities) for accurate type safety assessment
observability_surfaces:
  - Every finding includes a reproducible Detection command that future agents can re-run to verify whether the issue persists
duration: 20m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T03: Type safety, SPARQL construction, async patterns, and FastAPI audit

**Audited 669 functions for type annotations (74% covered, routers worst at 17%), cataloged 131 f-string SPARQL construction sites with no parameterization utility, identified 6 blocking I/O calls in async handlers, and documented inconsistent DI patterns (254 direct `app.state` accesses vs 9 `Depends()` factories).**

## What Happened

Executed all 8 plan steps using `rg`, `fd`, and shell pipelines across all 233 backend Python modules:

1. **Type safety (TS-01 through TS-03):** 496 of 669 functions have return type annotations (74%). The router layer is the weakest at 17% (62/368). Services average 67%, utilities ~70%. Nine routers have zero annotations. Only 45 of ~260 route decorators specify `response_model`. Positive: zero deprecated `.dict()` calls — all Pydantic v2.

2. **SPARQL construction (SQ-01 through SQ-04):** 131 f-string SPARQL construction sites across 25 files with no parameterized query builder. `views/service.py` is the largest contributor (~30 sites). The `scope_filter` parameter is injected raw into 11 WHERE clause positions. Only one escaping utility exists (`escape_sparql_regex`) and it handles only REGEX metacharacters, not IRIs or literals. Three independent IRI validation functions exist across the codebase.

3. **Async patterns (AP-01 through AP-04):** 6 blocking `open()` calls in async handlers (manifest reads and zip writes). Zero `time.sleep()` calls (positive). 3 sync helpers in async routers are all appropriate (pure computation, Depends factories). The 254 direct `request.app.state` accesses create an inconsistent DI pattern.

4. **FastAPI patterns (FP-01 through FP-04):** Inconsistent router prefix conventions (18 with prefix, 12 without). `dependencies.py` has factories for only 9 of ~20+ app.state services. No middleware ordering documentation for the 5 middleware layers. All routers have tags (positive).

5. **SQL injection check:** The one raw SQL f-string found (`browser/comments.py:318`) uses parameterized queries (`:uid_N` placeholders via SQLAlchemy `text()`), so it's safe.

## Verification

- `test -f .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` — file exists ✅
- `grep -c "^### " .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` → 40 (≥ 8 required) ✅
- `grep -c "Severity:" .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` → 40 (≥ 15 required) ✅
- `grep -c "Detection:" .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` → 40 (≥ 15 required) ✅
- Detection command re-runs verified: TS-01 (669 total, 173 unannotated), SQ-01 (131 sites), AP-01 (6 files) ✅

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` | 0 | ✅ pass | <1s |
| 2 | `grep -c "^### " .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` (= 40, ≥ 8) | 0 | ✅ pass | <1s |
| 3 | `grep -c "Severity:" .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` (= 40, ≥ 15) | 0 | ✅ pass | <1s |
| 4 | `grep -c "Detection:" .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` (= 40, ≥ 15) | 0 | ✅ pass | <1s |
| 5 | TS-01 detection re-run: `rg "^\s*def " backend/app/ | wc -l` (= 669) | 0 | ✅ pass | <1s |
| 6 | SQ-01 detection re-run: f-string SPARQL count (= 131) | 0 | ✅ pass | 1s |
| 7 | AP-01 detection re-run: blocking open() in async (= 6) | 0 | ✅ pass | 1s |

## Diagnostics

Re-run any finding's Detection command to check current state. Key commands:
- `rg "^\s*def " backend/app/ -n | rg -v "\->" | wc -l` — count functions without return annotations
- `{ rg -n 'f"[^"]*(?:SELECT|INSERT|DELETE|CONSTRUCT|ASK)' backend/app/; rg -n 'f"""[^"]*(?:SELECT|INSERT|DELETE|CONSTRUCT|ASK)' backend/app/; } | sort -u | wc -l` — count f-string SPARQL sites
- `rg "request\.app\.state\." backend/app/ | wc -l` — count direct app.state accesses
- `rg "response_model=" backend/app/ | wc -l` — count response_model declarations

## Deviations

- The plan's SQL injection check (step 3) found only SPARQL queries matching the pattern, not actual SQL — the one real SQL query in `browser/comments.py` uses parameterized queries. Documented as a positive finding rather than a separate finding section.
- Added SQ-02 (scope_filter injection risk) and SQ-03 (duplicated IRI validation) beyond the plan's scope because they emerged naturally from the SPARQL construction audit.
- Added FP-03 (incomplete dependencies.py) and FP-04 (middleware ordering) beyond the plan's FastAPI scope based on data from the Depends() consistency analysis.

## Known Issues

None.

## Files Created/Modified

- `.gsd/milestones/M041/S01-BACKEND-FINDINGS.md` — Appended Type Safety (3 findings), SPARQL Construction (4 findings), Async Patterns (4 findings), and FastAPI Patterns (4 findings) sections
