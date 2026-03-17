---
id: T01
parent: S05
milestone: M011
provides:
  - 6 CRM model files committed to models/crm/
  - Cross-model offline validation test covering all 4 M011 models
key_files:
  - models/crm/ (6 files — manifest, ontology, shapes, views, rules, seed)
  - backend/tests/test_cross_model_validation.py
key_decisions:
  - Used _run_pyshacl helper instead of parametrize for pyshacl tests to keep expected counts explicit per test
patterns_established:
  - Cross-model validation pattern: module-scoped fixtures for manifests/archives dict, parametrized individual validation, helper function for pyshacl execution
observability_surfaces:
  - "cd backend && .venv/bin/python -m pytest tests/test_cross_model_validation.py -v — 10 tests covering parse/validate, namespace, graph merge, pyshacl counts"
duration: ~12min
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T01: Commit CRM model files and write cross-model offline validation test

**Copied 6 CRM model files from worktree to main tree and wrote 10-test cross-model validation suite proving all 4 M011 models coexist without conflicts.**

## What Happened

1. Copied 6 CRM model files from `.gsd/worktrees/M011/models/crm/` to `models/crm/` — verified binary-identical with `diff`.
2. Validated CRM archive via `parse_manifest → load_archive → validate_archive` — `Valid=True Errors=0`.
3. Ran pyshacl against all 4 models to confirm expected warning/info counts before writing tests.
4. Wrote `backend/tests/test_cross_model_validation.py` with 10 tests:
   - 4 parametrized `test_model_parses_and_validates` (one per model)
   - `test_no_namespace_collisions` — all 4 namespaces distinct
   - `test_combined_graph_merge` — no silent triple drops
   - `test_pyshacl_basic_pkm_warnings` — 1W 0I ✓
   - `test_pyshacl_crm_warnings` — 2W 0I ✓
   - `test_pyshacl_zettelkasten_warnings` — 2W 1I ✓
   - `test_pyshacl_research_warnings` — 2W 2I ✓
5. All 10 tests pass. LSP diagnostics clean — no import errors.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_cross_model_validation.py -v` — **10 passed** in 0.69s
- `find models/crm -type f | wc -l` — **6**
- `diff models/crm/manifest.yaml .gsd/worktrees/M011/models/crm/manifest.yaml` — **no differences** (verified all 6 files)
- LSP diagnostics on test file — **no errors**

### Slice-level verification status (T01 is task 1 of 3):
- ✅ `pytest tests/test_cross_model_validation.py -v` — all tests pass
- ⏳ E2E Playwright tests — not yet created (T02)
- ⏳ Chapter 29 docs — not yet created (T03)
- ⏳ TOC/nav updates — not yet done (T03)

## Diagnostics

- Run `cd backend && .venv/bin/python -m pytest tests/test_cross_model_validation.py -v` to see per-model results
- On pyshacl assertion failure, full `results_text` is printed showing focus nodes, severity, and messages
- Parametrized test names include model name for easy filtering: `pytest -k crm`

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `models/crm/manifest.yaml` — CRM manifest (copied from worktree)
- `models/crm/ontology/crm.jsonld` — CRM ontology (copied from worktree)
- `models/crm/shapes/crm.jsonld` — CRM shapes (copied from worktree)
- `models/crm/views/crm.jsonld` — CRM views (copied from worktree)
- `models/crm/rules/crm.ttl` — CRM rules (copied from worktree)
- `models/crm/seed/crm.jsonld` — CRM seed data (copied from worktree)
- `backend/tests/test_cross_model_validation.py` — 10-test cross-model validation suite
- `.gsd/milestones/M011/slices/S05/tasks/T01-PLAN.md` — added Observability Impact section
