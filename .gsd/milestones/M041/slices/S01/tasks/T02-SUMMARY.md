---
id: T02
parent: S01
milestone: M041
provides:
  - Error Handling and Logging sections in S01-BACKEND-FINDINGS.md (12 findings: EH-01 through EH-06, LG-01 through LG-06)
  - Classification of all 312 except Exception handlers by risk category
  - Identification of 26 substantial modules missing logging
key_files:
  - .gsd/milestones/M041/S01-BACKEND-FINDINGS.md
key_decisions: []
patterns_established:
  - AST-based exception handler classification (silent pass, silent return, logged+reraise, logged+degrade) for accurate categorization beyond regex grep
observability_surfaces:
  - Each finding's Detection command is re-runnable to check if the issue still exists
duration: 25m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T02: Error handling and logging audit

**Audited 312 broad exception handlers and 233 modules for logging coverage — identified 26 silent `except Exception: pass` blocks, 19 silent returns, 26 substantial modules without loggers, and zero structured logging usage across 743 log calls.**

## What Happened

Executed systematic pattern-based detection across all 233 backend Python files:

1. **Broad exception catches:** Found 312 `except Exception` handlers total. Classified by behavior: 70% catch-and-degrade (log + return default), 8% completely silent (`pass`), 6% silent returns, 5% properly logged-and-reraised, 11% mixed patterns.

2. **Silent exceptions:** Identified 26 `except Exception: pass` blocks and 19 `except Exception: return <default>` with no logging. The worst cluster is `admin/router.py` with 7 consecutive silent catches in `_query_entailment_examples()`. The most dangerous are in `services/models.py` (4 silent catches in model install/refresh), `inference/service.py` (user override loading), and `models/registry.py` (model scan).

3. **Logging coverage:** 115 of 233 modules (49%) have loggers. After filtering `__init__.py`, models, and schemas, 26 substantial modules (>100 LOC) lack any logging. The highest-risk gaps: `auth/service.py` (333 LOC, authentication with zero logging), `vfs/mount_service.py` (597 LOC, largest unlogged module), `sparql/client.py` (242 LOC, SPARQL communication), and `triplestore/client.py` (151 LOC).

4. **Logging quality:** Zero f-string logging (positive — %-style used consistently). Zero `extra={}` structured logging (all 743 log calls embed context in format strings). 105 `exc_info=True` usages (good stack trace preservation). Two log level misclassifications found: `inference/service.py` logs triplestore errors at `debug`, `federation/signatures.py` logs signature verification failure at `info`.

## Verification

- `grep -c "^### " .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` → 25 (T02 target: >= 4) ✅
- `grep -c "Severity:" .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` → 25 (target: >= 15) ✅
- `grep -c "Detection:" .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` → 25 (target: >= 15) ✅
- EH-01 detection command re-run → 312 (matches documented count) ✅
- LG-02 detection command re-run → 0 f-string log calls (matches documented count) ✅

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` | 0 | ✅ pass | <1s |
| 2 | `grep -c "^### " .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` (= 25, >= 4) | 0 | ✅ pass | <1s |
| 3 | `grep -c "Severity:" .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` (= 25, >= 15) | 0 | ✅ pass | <1s |
| 4 | `grep -c "Detection:" .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` (= 25, >= 15) | 0 | ✅ pass | <1s |

## Diagnostics

Re-run any finding's Detection command to check current state. Key commands:
- `python3 -c "import ast,os; ..."` (EH-01) — recount total broad catches
- `rg "except Exception" -c backend/app/views/service.py` — check views/service.py catch count
- `comm -23 <(fd -e py . backend/app/ | sort) <(rg "logger\s*=\s*|logging\.getLogger" -l backend/app/ | sort)` — list modules without loggers
- `rg "logger\.\w+\(f\"" -c backend/app/` — verify zero f-string logging

## Deviations

- The plan's step 2 (`rg "except.*:\s*pass$"`) found zero matches because Python formatting places `pass` on the next line. Used AST-based analysis instead, which correctly identifies all single-statement `pass`/`continue` exception handlers regardless of formatting.
- Added risk classification tiers (acceptable/should-add-logging/dangerous) beyond the plan's simple catalog, providing actionable triage for remediation.

## Known Issues

None.

## Files Created/Modified

- `.gsd/milestones/M041/S01-BACKEND-FINDINGS.md` — appended Error Handling (6 findings: EH-01 through EH-06) and Logging (6 findings: LG-01 through LG-06) sections
