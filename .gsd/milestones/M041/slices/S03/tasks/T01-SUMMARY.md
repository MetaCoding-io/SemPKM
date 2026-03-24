---
id: T01
parent: S03
milestone: M041
provides:
  - Cross-cutting analysis data: dead code, duplication, test gaps, tech debt
  - `.gsd/milestones/M041/S03-CROSS-CUTTING-FINDINGS.md` — working data for T02 assembly
key_files:
  - .gsd/milestones/M041/S03-CROSS-CUTTING-FINDINGS.md
key_decisions: []
patterns_established: []
observability_surfaces:
  - none (analysis-only task, no runtime artifacts)
duration: 20m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T01: Dead code, duplication, and test coverage gap analysis

**Analyzed all four cross-cutting quality dimensions (dead code, duplication, test gaps, tech debt) across 193 backend modules and frontend sources, producing structured working data with 7 duplication patterns, 165 untested modules (including all 7 auth modules), and 7 confirmed tech debt items for T02 report assembly.**

## What Happened

Ran pattern-based analysis across all backend Python (193 modules) and frontend JS/CSS sources covering four dimensions:

1. **Dead code markers:** Zero TODO/FIXME/HACK/XXX markers found (case-insensitive). No genuine commented-out code blocks — all 3+ consecutive comment runs are documentation. 3 unused imports found in 10-module sample. One dead function (`register_renderer()` in `views/registry.py` — defined but never called).

2. **Code duplication:** Found 7 distinct duplication patterns: PersonMatcher across 9 sync apps (largest), ISO 8601 Z-replacement (8 instances in 4 files), `datetime.now(timezone.utc)` proliferation (46 call sites), label resolution SPARQL (4+ copies), hard-coded `FROM <urn:sempkm:current>` graph URIs (20+ instances), IRI pill rendering (3 frontend implementations), and `escapeHtml` (2 independent definitions).

3. **Test coverage gaps:** 165 of 193 modules have no dedicated test file. Critical gaps: auth (7/7 untested), commands (9/10 untested), triplestore (3/3 untested), views core (3/3 untested), copilot (6/7 untested). The entire VFS subsystem (13 modules) has only 2 test files.

4. **Tech debt:** Cross-referenced KNOWLEDGE.md items — 7 items confirmed still present (K001 rdflib workaround, K002 seed data type mismatch, extract_scope_where_body LIMIT bug, register_renderer dead code, SPARQL API no UPDATE, PersonMatcher duplication, Z-replacement pattern). 2 items resolved (worktree isolation mode, nginx /static/ path). Identified 6 additional accumulated debt items not previously documented.

## Verification

All four cross-cutting dimensions have structured data in `S03-CROSS-CUTTING-FINDINGS.md`:
- Dead code marker count: 0 formal markers (documented)
- Untested module list: 165 modules enumerated with risk ratings
- Duplication instances: 7 patterns documented (exceeds 5 minimum)
- Tech debt items: 7 still present, 2 resolved (verified against codebase)

Slice-level checks (intermediate — T02 creates the final report):
- `M041-RECOMMENDATIONS.md`: expected not to exist yet (T02 deliverable)
- Working data file exists: PASS
- All 4 dimensions present in working data: PASS

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f .gsd/milestones/M041/S03-CROSS-CUTTING-FINDINGS.md` | 0 | ✅ pass | <1s |
| 2 | `grep -q "Dead Code" .gsd/milestones/M041/S03-CROSS-CUTTING-FINDINGS.md` | 0 | ✅ pass | <1s |
| 3 | `grep -q "Duplication" .gsd/milestones/M041/S03-CROSS-CUTTING-FINDINGS.md` | 0 | ✅ pass | <1s |
| 4 | `grep -q "Test Coverage" .gsd/milestones/M041/S03-CROSS-CUTTING-FINDINGS.md` | 0 | ✅ pass | <1s |
| 5 | `grep -q "Tech Debt" .gsd/milestones/M041/S03-CROSS-CUTTING-FINDINGS.md` | 0 | ✅ pass | <1s |
| 6 | `grep -c "^### 2\." .gsd/milestones/M041/S03-CROSS-CUTTING-FINDINGS.md` = 7 | 0 | ✅ pass | <1s |
| 7 | `grep -q "Still present" .gsd/milestones/M041/S03-CROSS-CUTTING-FINDINGS.md` | 0 | ✅ pass | <1s |

## Diagnostics

None — this is an analysis-only task producing a markdown working-data file. No runtime surfaces, logs, or persisted state.

## Deviations

None. All six planned analysis steps executed as specified.

## Known Issues

None.

## Files Created/Modified

- `.gsd/milestones/M041/S03-CROSS-CUTTING-FINDINGS.md` — Working data covering all 4 cross-cutting dimensions with structured findings, severity ratings, and reproducible detection commands
