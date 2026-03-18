---
id: T03
parent: S02
milestone: M013
provides:
  - 8 unit tests for GET /api/types endpoint covering schema, auth, icons, model attribution, and empty state
  - 11 unit tests for GET /api/shapes/{type_iri} endpoint covering property fields, constraints, groups, helptext, target_class, 404, and auth
key_files:
  - backend/tests/test_api_surface.py
key_decisions:
  - Enhanced test_types_entries_have_required_fields to assert all 6 TypeInfo fields (iri, label, icon, icon_color, model_id, model_name) not just iri and label
  - Enhanced test_shapes_property_fields to assert all 6 key fields (path, name, order, datatype, min_count, max_count) with type checks
patterns_established:
  - Test coverage for dataclass → asdict() → Pydantic → JSON serialization roundtrip verified via asserting every field key exists and has correct type
observability_surfaces:
  - pytest test count: 19 types/shapes tests, 990 total suite; regression detectable via `pytest tests/ -q`
duration: 10m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T03: Unit tests for types and shapes endpoints

**Enhanced existing types/shapes tests to verify all response model fields round-trip correctly from SHACL dataclass through Pydantic to JSON**

## What Happened

Tests for both endpoints were largely written during T01 and T02 execution. T03 hardened them to match the plan's field-completeness requirements:

1. `test_types_entries_have_required_fields` — expanded from checking only iri/label to asserting all 6 TypeInfo fields (iri, label, icon, icon_color, model_id, model_name) are present in every response entry.
2. `test_shapes_property_fields` — expanded from checking path/name/order to asserting all 6 key fields (path, name, order, datatype, min_count, max_count) with type validation (int for counts, float/int for order, str for path/name).

Final test counts: 8 types endpoint tests + 11 shapes endpoint tests = 19 total, exceeding the plan's ≥4 + ≥6 requirements.

## Verification

- `pytest tests/test_api_surface.py -v -k "types or shapes"` — 19 passed
- `pytest tests/ --tb=short -q` — 990 passed, 0 failures, no regressions
- Slice-level curl checks: shapes endpoint returns correct JSON with 9 properties for Note type; 404 returns structured error; 401 enforced without credentials
- Runtime note: `/api/types` returns 500 at runtime because `icon_service` and `model_service` are not wired to `app.state` in the main app startup — this is a wiring gap from T01/T02, not a T03 test issue. Tests correctly mock these services.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_api_surface.py -v -k "types or shapes"` | 0 | ✅ pass | 0.84s |
| 2 | `pytest tests/ --tb=short -q` | 0 | ✅ pass | 6.88s |
| 3 | `curl /api/types` (no auth) → 401 | 0 | ✅ pass | <1s |
| 4 | `curl /api/shapes/urn:sempkm:model:basic-pkm:Note` → 200, 9 properties | 0 | ✅ pass | <1s |
| 5 | `curl /api/shapes/urn:nonexistent:Type` → 404 with structured detail | 0 | ✅ pass | <1s |
| 6 | `curl /api/types` (authenticated) → 500 (icon_service not wired) | 0 | ❌ fail | <1s |

## Diagnostics

- Run `pytest tests/test_api_surface.py -v -k "types or shapes"` to see all 19 test names and pass/fail status
- Run `pytest tests/test_api_surface.py -v -k "shapes_preserves"` to specifically check constraint serialization fidelity
- The 500 on `/api/types` at runtime is caused by `AttributeError: 'State' object has no attribute 'icon_service'` — needs `icon_service` and `model_service` registered on `app.state` during startup (likely a follow-up wiring task)

## Deviations

- Tests were mostly written during T01/T02 execution rather than T03. T03 enhanced field-completeness assertions rather than writing tests from scratch.
- `/api/types` runtime 500 error discovered — `icon_service` and `model_service` not registered on app.state. Unit tests pass (mocked), but runtime fails. Not a T03 blocker since this task is specifically about unit tests.

## Known Issues

- `/api/types` returns 500 at runtime: `icon_service` not registered on `app.state` during app startup. The endpoint works in tests because services are mocked. Fix requires wiring `IconService` and `ModelService` instances in the app lifespan handler.

## Files Created/Modified

- `backend/tests/test_api_surface.py` — enhanced `test_types_entries_have_required_fields` and `test_shapes_property_fields` for full field coverage
- `.gsd/milestones/M013/slices/S02/tasks/T03-PLAN.md` — added Observability Impact section
