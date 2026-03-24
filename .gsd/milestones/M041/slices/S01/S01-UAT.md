# S01: Backend Code Quality Audit — UAT

**Milestone:** M041
**Written:** 2026-03-23

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S01 produces a static analysis document, not runtime behavior. Verification is structural (file exists, sections present, findings formatted correctly) and content-quality (findings are actionable, detection commands work).

## Preconditions

- The SemPKM repository is checked out at the commit containing S01 work
- `S01-BACKEND-FINDINGS.md` exists at `.gsd/milestones/M041/S01-BACKEND-FINDINGS.md`
- `rg`, `fd`, and `python3` are available in the shell

## Smoke Test

Run `grep -c "^### " .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` — should return ≥ 40. If it returns < 8, the findings document is incomplete.

## Test Cases

### 1. All 8 quality dimensions are covered

1. Run: `grep "^## " .gsd/milestones/M041/S01-BACKEND-FINDINGS.md`
2. **Expected:** Output includes all 8 dimension headers: Module Structure, Readability & Naming, Error Handling, Logging, Type Safety, SPARQL Construction, Async Patterns, FastAPI Patterns (plus Summary Statistics).

### 2. Every finding has required metadata fields

1. Run: `grep -c "Severity:" .gsd/milestones/M041/S01-BACKEND-FINDINGS.md`
2. Run: `grep -c "Effort:" .gsd/milestones/M041/S01-BACKEND-FINDINGS.md`
3. Run: `grep -c "Location:" .gsd/milestones/M041/S01-BACKEND-FINDINGS.md`
4. Run: `grep -c "Detection:" .gsd/milestones/M041/S01-BACKEND-FINDINGS.md`
5. **Expected:** All four counts are equal and ≥ 40 (one per finding).

### 3. Detection commands are re-runnable

1. Pick finding MS-01. Read its Detection command from the document.
2. Run the command verbatim in the shell from the project root.
3. **Expected:** The command succeeds (exit 0) and produces output consistent with the finding's description (e.g., `wc -l backend/app/views/service.py` returns ~3663).

### 4. Severity levels use the defined scale

1. Run: `grep "Severity:" .gsd/milestones/M041/S01-BACKEND-FINDINGS.md | sort -u`
2. **Expected:** All values are one of: Critical, High, Medium, Low, Positive (informational).

### 5. File:line references point to real locations

1. Pick finding EH-02 (silent `except Exception: pass` blocks). Read the Location field.
2. Open the referenced file at the referenced line.
3. **Expected:** The code at that location matches the finding's description (e.g., an `except Exception` block with `pass`).

### 6. God module finding includes decomposition recommendation

1. Read finding MS-01 (`views/service.py`).
2. **Expected:** The finding includes a specific decomposition recommendation naming proposed output files or module structure.

### 7. SPARQL construction findings identify specific injection risks

1. Read finding SQ-01 and SQ-02.
2. **Expected:** SQ-01 counts f-string SPARQL sites with file-level breakdown. SQ-02 identifies `scope_filter` raw injection with specific WHERE clause locations.

### 8. Positive findings are included for balanced assessment

1. Run: `grep -c 'Severity: Positive' .gsd/milestones/M041/S01-BACKEND-FINDINGS.md`
2. **Expected:** Count ≥ 4 (RN-01 naming, LG-02 no f-string logging, TS-03 no deprecated Pydantic, AP-02 no sleep calls, LG-04 good exc_info).

## Edge Cases

### Empty detection command output

1. Pick finding AP-02 (zero `time.sleep()` calls — positive finding).
2. Run its detection command.
3. **Expected:** The command returns 0 matches, confirming the positive finding still holds.

### Large finding count in a single dimension

1. Count findings under Module Structure: `grep -c "^### Finding MS-" .gsd/milestones/M041/S01-BACKEND-FINDINGS.md`
2. **Expected:** Returns 8 (MS-01 through MS-08). Each has unique content and file references.

### Finding IDs are unique and sequential within each dimension

1. Run: `grep "^### Finding " .gsd/milestones/M041/S01-BACKEND-FINDINGS.md | sort | uniq -d`
2. **Expected:** No output (zero duplicate finding IDs).

## Failure Signals

- `grep -c "^### "` returns < 8 — missing quality dimensions
- A Detection command fails with a nonzero exit or produces wildly different counts — finding may be based on stale data or a broken command
- A Location reference points to a nonexistent file — file was moved/renamed after the audit
- Severity field contains values outside the defined scale — formatting error

## Requirements Proved By This UAT

None — M041 is a pure analysis milestone with no requirement coverage.

## Not Proven By This UAT

- Whether the findings are *complete* (pattern-based detection may miss isolated issues)
- Whether effort estimates are accurate (these are informed guesses, not measured)
- Frontend quality dimensions (covered by S02)
- Cross-cutting analysis and Top 10 prioritization (covered by S03)

## Notes for Tester

- The findings document is 681 lines. Skim the Summary Statistics section first for aggregate numbers, then drill into specific dimensions of interest.
- Detection commands use `rg` (ripgrep), `fd` (fd-find), and Python AST parsing. All are available in the dev environment.
- Positive findings (Severity: Positive) are intentionally included to highlight areas where the codebase is already strong — they're not padding.
- The highest-impact findings for a future execution milestone are likely MS-01 (views/service.py decomposition), SQ-01 (SPARQL parameterization), EH-02/EH-03 (silent exceptions), and TS-01 (router type annotations).
