---
estimated_steps: 6
estimated_files: 7
---

# T01: Commit CRM model files and write cross-model offline validation test

**Slice:** S05 — Cross-Model Verification, E2E Tests & User Guide
**Milestone:** M011

## Description

The CRM model files (6 files built in S02) exist only in `.gsd/worktrees/M011/models/crm/` — the main `models/crm/` directory has empty subdirectories but no actual files. This task copies the files over and then writes a cross-model offline validation pytest that proves all 4 M011 models (basic-pkm v2, CRM, Zettelkasten+, Research Workflow) coexist without namespace conflicts.

The test follows the established pattern in `backend/tests/test_basic_pkm_v2.py` — module-scoped fixtures for manifest/archive loading, individual model validation, plus cross-model coexistence checks.

## Steps

1. **Copy CRM model files from worktree to main tree.** Copy these 6 files:
   - `.gsd/worktrees/M011/models/crm/manifest.yaml` → `models/crm/manifest.yaml`
   - `.gsd/worktrees/M011/models/crm/ontology/crm.jsonld` → `models/crm/ontology/crm.jsonld`
   - `.gsd/worktrees/M011/models/crm/shapes/crm.jsonld` → `models/crm/shapes/crm.jsonld`
   - `.gsd/worktrees/M011/models/crm/views/crm.jsonld` → `models/crm/views/crm.jsonld`
   - `.gsd/worktrees/M011/models/crm/rules/crm.ttl` → `models/crm/rules/crm.ttl`
   - `.gsd/worktrees/M011/models/crm/seed/crm.jsonld` → `models/crm/seed/crm.jsonld`

2. **Verify CRM files parse correctly.** Run a quick validation:
   ```bash
   cd backend && .venv/bin/python3 -c "
   from pathlib import Path
   from app.models.manifest import parse_manifest
   from app.models.loader import load_archive
   from app.models.validator import validate_archive
   m = parse_manifest(Path('../models/crm'))
   a = load_archive(Path('../models/crm'), m)
   r = validate_archive(a)
   print(f'CRM: Valid={r.is_valid} Errors={len(r.errors)} Warnings={len(r.warnings)}')
   "
   ```
   Must print `Valid=True Errors=0`.

3. **Write `backend/tests/test_cross_model_validation.py`.** Structure:

   **Module-scoped fixtures** (one per model):
   ```python
   MODEL_DIRS = {
       'basic-pkm': Path(__file__).resolve().parents[2] / 'models' / 'basic-pkm',
       'crm': Path(__file__).resolve().parents[2] / 'models' / 'crm',
       'zettelkasten': Path(__file__).resolve().parents[2] / 'models' / 'zettelkasten',
       'research': Path(__file__).resolve().parents[2] / 'models' / 'research',
   }
   ```
   For each model, create `@pytest.fixture(scope="module")` for manifest and archive.

   **Test cases:**

   a. `test_{model}_parses_and_validates` (parametrized over 4 models) — each model passes `parse_manifest()` + `load_archive()` + `validate_archive()` with `is_valid=True` and 0 errors.

   b. `test_no_namespace_collisions` — extract namespace from each model's manifest, verify all 4 are distinct (`urn:sempkm:model:basic-pkm:`, `urn:sempkm:model:crm:`, `urn:sempkm:model:zettelkasten:`, `urn:sempkm:model:research:`).

   c. `test_combined_graph_merge` — merge all 4 ontology graphs into one `rdflib.Graph()`, check no parse errors and total triples > sum check (no silent drops).

   d. `test_pyshacl_basic_pkm_warnings` — pyshacl fires exactly 1 Warning (overdue task) against basic-pkm seed data. Pattern: `data_graph = seed + ontology`, `shapes_graph = shapes + rules`, `pyshacl.validate(..., advanced=True)`. Check `conforms=False` (has warnings).

   e. `test_pyshacl_crm_warnings` — pyshacl fires exactly 2 Warnings against CRM seed data (stale contact Marcus, overdue follow-up).

   f. `test_pyshacl_zettelkasten_warnings` — pyshacl fires 2 Warning + 1 Info against zettelkasten seed data.

   g. `test_pyshacl_research_warnings` — pyshacl fires 2 Warning + 2 Info against research seed data.

   **Important pyshacl validation pattern** (from S01 test):
   ```python
   data_graph = Graph()
   data_graph.parse(seed_path, format='json-ld')
   data_graph.parse(ontology_path, format='json-ld')
   
   shapes_graph = Graph()
   shapes_graph.parse(shapes_path, format='json-ld')
   shapes_graph.parse(rules_path, format='turtle')
   
   conforms, results_graph, results_text = pyshacl.validate(
       data_graph,
       shacl_graph=shapes_graph,
       ont_graph=data_graph,  # ontology also in data graph
       advanced=True,
       allow_infos=True,
       allow_warnings=True,
   )
   ```

   For counting violations by severity, query `results_graph`:
   ```python
   SH = Namespace("http://www.w3.org/ns/shacl#")
   warnings = list(results_graph.subjects(SH.resultSeverity, SH.Warning))
   infos = list(results_graph.subjects(SH.resultSeverity, SH.Info))
   ```

4. **Run the tests:**
   ```bash
   cd backend && .venv/bin/python -m pytest tests/test_cross_model_validation.py -v
   ```

5. **Verify all 4 models also still pass their individual validation inline** (the parametrized test covers this).

6. **Check LSP diagnostics** on the test file to ensure no import errors.

## Must-Haves

- [ ] All 6 CRM files copied from worktree and match the originals (binary identical)
- [ ] `parse_manifest()` + `load_archive()` + `validate_archive()` passes for all 4 models with 0 errors
- [ ] No namespace prefix collisions across all 4 models
- [ ] pyshacl fires correct number of warnings/infos per model: basic-pkm 1W, CRM 2W, zettelkasten 2W+1I, research 2W+2I
- [ ] Combined ontology graph merge produces no parse errors

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_cross_model_validation.py -v` — all tests pass
- `find models/crm -type f | wc -l` — returns 6
- `diff models/crm/manifest.yaml .gsd/worktrees/M011/models/crm/manifest.yaml` — no differences

## Inputs

- `.gsd/worktrees/M011/models/crm/` — 6 CRM model files built in S02
- `models/basic-pkm/` — basic-pkm v2.0 archive from S01
- `models/zettelkasten/` — zettelkasten archive from S03
- `models/research/` — research archive from S04
- `backend/tests/test_basic_pkm_v2.py` — reference pattern for module-scoped fixtures and pyshacl validation. Key pattern: `pyshacl.validate(data_graph, shacl_graph=shapes_graph, ont_graph=data_graph, advanced=True, allow_infos=True, allow_warnings=True)`
- `backend/app/models/manifest.py` — `parse_manifest()` function
- `backend/app/models/loader.py` — `load_archive()` function
- `backend/app/models/validator.py` — `validate_archive()` function

## Observability Impact

- **New test file:** `backend/tests/test_cross_model_validation.py` — 10 tests covering all 4 models. `pytest -v` output shows per-model validation, namespace checks, graph merge, and pyshacl warning/info counts.
- **Inspection surface:** Run `cd backend && .venv/bin/python -m pytest tests/test_cross_model_validation.py -v` to verify all models coexist. Each test prints specific counts on failure.
- **Failure visibility:** Parametrized test names include the model name (e.g. `test_model_parses_and_validates[crm]`). pyshacl tests print full `results_text` on assertion failure for root-cause diagnosis.
- **No runtime signals changed:** This is offline-only validation; no Docker or API impact.

## Expected Output

- `models/crm/manifest.yaml` — CRM manifest (copied from worktree)
- `models/crm/ontology/crm.jsonld` — CRM ontology (copied from worktree)
- `models/crm/shapes/crm.jsonld` — CRM shapes (copied from worktree)
- `models/crm/views/crm.jsonld` — CRM views (copied from worktree)
- `models/crm/rules/crm.ttl` — CRM rules (copied from worktree)
- `models/crm/seed/crm.jsonld` — CRM seed data (copied from worktree)
- `backend/tests/test_cross_model_validation.py` — Cross-model validation test with ~7-10 test functions all passing
