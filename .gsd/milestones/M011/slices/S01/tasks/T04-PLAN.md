---
estimated_steps: 7
estimated_files: 1
---

# T04: Write offline validation test proving archive correctness and overdue-task rule

**Slice:** S01 — basic-pkm v2 — Task & Milestone Types
**Milestone:** M011

## Description

Write the slice's acceptance test: a pytest file that exercises the full validation pipeline (parse_manifest → load_archive → validate_archive) and proves the overdue-task SPARQLConstraint fires a sh:Warning via pyshacl. This task retires the three key risks from the M011 roadmap:

1. **SPARQL-based validation rules with date arithmetic** — proven by pyshacl firing warning on seed data
2. **refresh_artifacts upgrade path** — proven by archive passing offline validation (additive types)
3. **sh:severity placement** — proven by warning (not error) appearing in pyshacl output

The test uses existing backend infrastructure (`parse_manifest`, `load_archive`, `validate_archive` from `backend/app/models/`) and `pyshacl` (already in pyproject.toml as `~=0.31.0`).

## Steps

1. **Create `backend/tests/test_basic_pkm_v2.py`** with these test functions:

2. **Test: `test_manifest_parses_v2`** — Call `parse_manifest(Path("models/basic-pkm"))`. Assert version == "2.0.0", modelId == "basic-pkm", len(icons) == 6. Assert icon types include "bpkm:Task" and "bpkm:Milestone".

3. **Test: `test_archive_loads_all_graphs`** — Call `parse_manifest` then `load_archive`. Assert ontology, shapes, views, seed, rules are all non-None and non-empty (len(graph) > 0 for each).

4. **Test: `test_archive_validates_zero_errors`** — Call `validate_archive(archive)`. Assert `report.is_valid` is True (zero errors). Warnings are acceptable.

5. **Test: `test_ontology_has_six_classes`** — Parse ontology graph, count subjects with `rdf:type owl:Class` within the `bpkm:` namespace. Assert count == 6 (Project, Person, Note, Concept, Task, Milestone).

6. **Test: `test_shapes_has_six_nodeshapes`** — Parse shapes graph, count subjects with `rdf:type sh:NodeShape` within the `bpkm:` namespace. Assert count >= 6 (4 existing + 2 new — may be more if PropertyGroups counted differently). Also verify TaskShape targets bpkm:Task and MilestoneShape targets bpkm:Milestone.

7. **Test: `test_views_has_all_viewspecs_and_queries`** — Count ViewSpec instances (expect 18: 6 types × 3 renderers). Count SavedQuery instances (expect 6: 3 original + 3 new).

8. **Test: `test_seed_has_task_and_milestone_instances`** — Assert seed graph contains subjects typed as bpkm:Task (expect 4) and bpkm:Milestone (expect 2). Assert the overdue task `bpkm:seed-task-fix-validation` has `bpkm:dueDate` with a past date and `bpkm:taskStatus` "todo".

9. **Test: `test_seed_has_inverse_pairs`** — Verify D154: assert `bpkm:seed-project-sempkm` has `bpkm:hasProjectTasks` edges, assert `bpkm:seed-person-alice` has `bpkm:hasAssignedTask` edges.

10. **Test: `test_pyshacl_overdue_task_warning`** — This is the key risk-retirement test:
    ```python
    import pyshacl
    from rdflib import Graph
    
    # Build data graph from seed + ontology (need type declarations)
    data_graph = archive.seed + archive.ontology
    
    # Build shapes graph from shapes + rules (validation rules in rules file)
    shapes_graph = archive.shapes + archive.rules
    
    conforms, results_graph, results_text = pyshacl.validate(
        data_graph,
        shacl_graph=shapes_graph,
        advanced=True,  # enable SPARQL-based constraints
        allow_infos=True,
        allow_warnings=True,
    )
    
    # conforms should be True because sh:Warning doesn't cause non-conformance
    # (unless pyshacl treats warnings as failures — check behavior)
    # Parse results_graph for sh:Warning violations
    SH = Namespace("http://www.w3.org/ns/shacl#")
    warnings = list(results_graph.triples((None, SH.resultSeverity, SH.Warning)))
    assert len(warnings) >= 1, "Expected at least one overdue-task warning"
    
    # Verify the warning references the overdue task
    # Check resultMessage contains "overdue"
    ```
    **Important pyshacl behavior note:** With `allow_warnings=True`, pyshacl returns `conforms=True` even when warnings exist. If we don't pass `allow_warnings=True`, warnings cause `conforms=False`. Test both scenarios or just use `allow_warnings=True` and check the results graph.

11. **Test: `test_pyshacl_no_warning_for_done_or_future_tasks`** — Construct a minimal data graph with a done task (past dueDate + status "done") and a future task (future dueDate + status "todo"). Run pyshacl validate. Assert zero warnings for these tasks.

All test functions should use a shared fixture that loads the archive once:
```python
import pytest
from pathlib import Path
from app.models.manifest import parse_manifest
from app.models.loader import load_archive

@pytest.fixture(scope="module")
def archive():
    model_dir = Path(__file__).resolve().parents[2] / "models" / "basic-pkm"
    manifest = parse_manifest(model_dir)
    return load_archive(model_dir, manifest)
```

## Must-Haves

- [ ] All tests pass: `python -m pytest backend/tests/test_basic_pkm_v2.py -v`
- [ ] Manifest parses as v2.0.0 with 6 icons
- [ ] Archive validates with zero errors
- [ ] Ontology has exactly 6 OWL classes in bpkm namespace
- [ ] pyshacl fires at least one sh:Warning for overdue task
- [ ] pyshacl does NOT fire warning for done/future tasks
- [ ] Test uses existing parse_manifest/load_archive/validate_archive (no mocking)

## Verification

- `cd /home/james/Code/SemPKM && python -m pytest backend/tests/test_basic_pkm_v2.py -v` — all tests pass
- Test output shows pyshacl warning containing "overdue" in message

## Inputs

- All model files from T01 (ontology, shapes), T02 (rules), T03 (views, seed, manifest)
- `backend/app/models/manifest.py` — `parse_manifest()` function
- `backend/app/models/loader.py` — `load_archive()` function, `ModelArchive` dataclass
- `backend/app/models/validator.py` — `validate_archive()` function
- `pyshacl` package (v0.31.0, already in pyproject.toml)

## Expected Output

- `backend/tests/test_basic_pkm_v2.py` — new test file with ~10 test functions covering manifest parsing, archive loading, validation, class/shape/view counting, seed data verification, and pyshacl overdue-task warning
