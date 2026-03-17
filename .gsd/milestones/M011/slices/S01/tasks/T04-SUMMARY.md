---
id: T04
parent: S01
milestone: M011
provides:
  - 10-function pytest acceptance suite for basic-pkm v2.0.0 covering manifest, archive, validation, ontology, shapes, views, seed, and pyshacl overdue-task warning
key_files:
  - backend/tests/test_basic_pkm_v2.py
key_decisions:
  - Used allow_warnings=True with pyshacl.validate() so conforms=True despite sh:Warning results; warning presence verified by querying results_graph directly
  - Negative test (done/future tasks) uses only rules file as shapes graph, avoiding interference from SHACL property constraints in the main shapes file
patterns_established:
  - Module-scoped pytest fixtures for manifest+archive loading to avoid repeated I/O across 10 tests
  - pyshacl validation pattern: data_graph = seed + ontology, shapes_graph = shapes + rules, advanced=True
observability_surfaces:
  - pytest -v output shows 10 named tests with pass/fail; pyshacl results_text included in assertion messages on failure
duration: 15m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T04: Write offline validation test proving archive correctness and overdue-task rule

**Added 10-function pytest acceptance suite proving basic-pkm v2.0.0 archive correctness and pyshacl overdue-task warning**

## What Happened

Created `backend/tests/test_basic_pkm_v2.py` with 10 test functions that exercise the full validation pipeline using real `parse_manifest`, `load_archive`, and `validate_archive` infrastructure (no mocking). Tests cover:

1. **test_manifest_parses_v2** — version 2.0.0, 6 icons including Task and Milestone
2. **test_archive_loads_all_graphs** — all 5 graphs (ontology, shapes, views, seed, rules) non-empty
3. **test_archive_validates_zero_errors** — zero validation errors via `validate_archive`
4. **test_ontology_has_six_classes** — exactly 6 OWL classes: Project, Person, Note, Concept, Task, Milestone
5. **test_shapes_has_six_nodeshapes** — 6 NodeShapes, TaskShape→Task, MilestoneShape→Milestone
6. **test_views_has_all_viewspecs_and_queries** — 18 ViewSpecs, 6 SavedQueries
7. **test_seed_has_task_and_milestone_instances** — 4 Tasks, 2 Milestones, overdue task has past dueDate + "todo" status
8. **test_seed_has_inverse_pairs** — D154 verified: Project.hasProjectTasks and Person.hasAssignedTask edges present
9. **test_pyshacl_overdue_task_warning** — key risk-retirement: pyshacl fires sh:Warning for seed-task-fix-validation with "overdue" in message
10. **test_pyshacl_no_warning_for_done_or_future_tasks** — negative test: done tasks and future-due tasks produce zero warnings

This retires the three key M011 risks:
- SPARQL-based validation rules with date arithmetic → proven by pyshacl firing warning
- refresh_artifacts upgrade path → proven by archive passing offline validation
- sh:severity placement → proven by warning (not error) in pyshacl output

## Verification

```
$ cd /home/james/Code/SemPKM && backend/.venv/bin/python -m pytest backend/tests/test_basic_pkm_v2.py -v
10 passed in 0.36s
```

All 10 tests pass. pyshacl output shows:
- Conforms: True (with allow_warnings=True)
- 1 sh:Warning for seed-task-fix-validation with message "Task is overdue: due date has passed but task is not done or cancelled."

### Slice-level verification (final task — all must pass):
- ✅ `parse_manifest()` succeeds on updated manifest.yaml (v2.0.0)
- ✅ `load_archive()` loads all 5 files without errors
- ✅ `validate_archive()` returns zero errors
- ✅ Ontology has 6 OWL classes
- ✅ Shapes has 6 NodeShapes with correct targetClass
- ✅ Views has 18 ViewSpecs + 6 SavedQueries
- ✅ Seed data has 4 Task + 2 Milestone instances
- ✅ Seed data has both sides of inverseOf pairs
- ✅ pyshacl fires sh:Warning for overdue task
- ✅ pyshacl does NOT fire warning for done/future tasks

## Diagnostics

```bash
# Run the full acceptance suite
cd /home/james/Code/SemPKM && backend/.venv/bin/python -m pytest backend/tests/test_basic_pkm_v2.py -v

# Run only pyshacl tests
backend/.venv/bin/python -m pytest backend/tests/test_basic_pkm_v2.py -v -k pyshacl

# Quick pyshacl probe
backend/.venv/bin/python -c "
import pyshacl; from rdflib import Graph, Namespace
d=Graph(); d.parse('models/basic-pkm/seed/basic-pkm.jsonld',format='json-ld'); d.parse('models/basic-pkm/ontology/basic-pkm.jsonld',format='json-ld')
s=Graph(); s.parse('models/basic-pkm/shapes/basic-pkm.jsonld',format='json-ld'); s.parse('models/basic-pkm/rules/basic-pkm.ttl',format='turtle')
c,_,t=pyshacl.validate(d,shacl_graph=s,advanced=True,allow_warnings=True); print(t)
"
```

## Deviations

None. All 10 tests match the plan specification exactly.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_basic_pkm_v2.py` — new: 10-function acceptance test suite for basic-pkm v2.0.0
- `.gsd/milestones/M011/slices/S01/tasks/T04-PLAN.md` — added Observability Impact section (pre-flight fix)
