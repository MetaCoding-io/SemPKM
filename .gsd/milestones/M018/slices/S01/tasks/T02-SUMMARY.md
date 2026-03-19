---
id: T02
parent: S01
milestone: M018
provides:
  - 22 offline validation tests for bpkm:Event type (manifest, ontology, shapes, views, seed, pyshacl, enum constraints)
  - Three named enum constraint tests proving D212 cross-provider superset
key_files:
  - backend/tests/test_basic_pkm_event.py
key_decisions: []
patterns_established:
  - _get_enum_values helper extracts sh:in values from a property shape for targeted enum assertions
observability_surfaces:
  - cd backend && .venv/bin/python -m pytest tests/test_basic_pkm_event.py -v — 22 tests covering all Event type invariants
duration: 8m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: Write offline validation tests for bpkm:Event type

**Added 3 plan-named enum constraint tests to the Event test suite (22 total), confirming all structural invariants and D212 cross-provider enum values pass.**

## What Happened

T01 had already created `test_basic_pkm_event.py` with 19 tests as a deviation (noted in T01 summary). The T02 plan specified three individual enum tests by name (`test_event_shape_has_status_enum`, `test_event_shape_has_show_as_enum`, `test_event_shape_has_response_status_enum`) that didn't exist as standalone tests — the enum checks were combined in `test_event_shape_enum_constraints`.

Added a `_get_enum_values()` helper to reduce duplication, then wrote the three named tests. Each directly asserts the expected enum value set for its property. Total suite is now 22 tests.

Verified both the event test suite (22/22) and the v2 regression suite (10/10) pass cleanly.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_basic_pkm_event.py -v` — 22/22 passed in 0.36s
- `cd backend && .venv/bin/python -m pytest tests/test_basic_pkm_v2.py -v` — 10/10 passed in 0.38s
- pyshacl validation fires zero sh:Violation results (overdue-task sh:Warning expected and allowed)
- All T02 must-haves verified:
  - ✅ Follows test_basic_pkm_v2.py pattern (same fixtures, imports)
  - ✅ ≥8 tests (22 tests)
  - ✅ Enum constraint tests prove D212 cross-provider superset
  - ✅ pyshacl passes (zero Violations)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_basic_pkm_event.py -v` | 0 | ✅ pass (22/22) | 0.36s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_basic_pkm_v2.py -v` | 0 | ✅ pass (10/10) | 0.38s |

## Diagnostics

- **Full suite:** `cd backend && .venv/bin/python -m pytest tests/test_basic_pkm_event.py -v` — 22 tests.
- **Enum-only:** `cd backend && .venv/bin/python -m pytest tests/test_basic_pkm_event.py -v -k "enum or show_as or status_enum or response_status"` — runs just the enum constraint tests.
- **pyshacl diagnostics:** On failure, `test_pyshacl_zero_errors_on_events` prints full results text with focus node, path, and message.

## Deviations

- T01 had already created the test file with 19 tests. T02 extended it with 3 additional plan-named enum tests rather than writing from scratch.
- Added Observability Impact section to T02-PLAN.md per pre-flight requirement.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_basic_pkm_event.py` — added `_get_enum_values` helper and 3 named enum tests (19 → 22 tests)
- `.gsd/milestones/M018/slices/S01/tasks/T02-PLAN.md` — added Observability Impact section
