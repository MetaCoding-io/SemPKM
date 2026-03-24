---
estimated_steps: 6
estimated_files: 1
skills_used: []
---

# T01: Dead code, duplication, and test coverage gap analysis

**Slice:** S03 — Cross-Cutting Analysis & Report Assembly
**Milestone:** M041

## Description

Analyze cross-cutting quality dimensions that span both backend and frontend: dead code, code duplication, test coverage gaps, and accumulated tech debt. Collect data for the final report assembly.

## Steps

1. Dead code markers: `rg "# TODO|# FIXME|# HACK|# XXX" backend/ frontend/ -n --count` — catalog all marked debt.
2. Commented-out code: find blocks of 3+ consecutive comment lines that look like disabled code (not docstrings).
3. Unused imports: sample 10 backend modules for imports that aren't referenced in the file body.
4. Backend test coverage gaps: list all `backend/app/**/*.py` modules, cross-reference against `backend/tests/test_*.py` files. Identify untested modules. Flag critical untested paths (auth, commands, triplestore client).
5. Code duplication: `rg` for repeated SPARQL query fragments, repeated utility patterns across backend modules (e.g., IRI encoding, date formatting). Note the PersonMatcher duplication in apps/ as a known example (out of scope for fixing but worth documenting).
6. Tech debt cross-reference: read `.gsd/KNOWLEDGE.md` Lessons Learned + `.gsd/PROJECT.md` tech debt section. Check which items are still present in the codebase.

## Must-Haves

- [ ] Dead code marker count (TODO/FIXME/HACK/XXX)
- [ ] List of modules with zero test coverage
- [ ] At least 5 duplication instances documented
- [ ] Tech debt items from KNOWLEDGE.md verified as still present or resolved

## Verification

- Working notes or intermediate data exist covering all 4 cross-cutting dimensions
- Manual review — data collected and ready for T02 assembly

## Inputs

- `backend/app/` — all Python source modules
- `frontend/static/` — all JS/CSS source files
- `backend/tests/` — test files for coverage gap analysis
- `.gsd/KNOWLEDGE.md` — known tech debt
- `.gsd/PROJECT.md` — project tech debt section

## Expected Output

- Working data for dead code, duplication, test gaps, and tech debt (used by T02 for report assembly)
