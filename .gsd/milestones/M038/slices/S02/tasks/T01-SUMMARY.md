---
id: T01
parent: S02
milestone: M038
provides:
  - rules_service.py with CRUD + evaluate_rules for schedule rules
  - DailyMediaPlan and PlanEntry OWL classes + SHACL shapes
  - generate-plan task in manifest
  - 48 new rule-related unit tests
key_files:
  - apps/media-scheduler/services/rules_service.py
  - models/media-scheduler/ontology/media-scheduler.jsonld
  - models/media-scheduler/shapes/media-scheduler.jsonld
  - apps/media-scheduler/manifest.yaml
  - backend/tests/test_media_scheduler.py
key_decisions:
  - Time range with missing current_time in context → no match (fail-closed rather than wildcard)
  - Midnight-wrapping time ranges supported via start > end comparison
patterns_established:
  - Rules stored as JSON array in StateClient, keyed by RULES_STATE_KEY
  - evaluate_rules is pure-function (no I/O) — takes rules list + context dict, returns matched sorted list
  - _matches_condition uses AND logic with null=wildcard for simple conditions, dict-based time_range
observability_surfaces:
  - validate_rule raises ValueError with descriptive message on invalid input
  - load_rules logs warning on invalid JSON or non-list state
  - add_rule/update_rule/delete_rule/toggle_rule log info on successful mutations
  - evaluate_rules returns full matched rule dicts for caller to log/inspect
duration: 25m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T01: Rules service + ontology extension

**Created rules_service.py with CRUD + AND-matching evaluation logic, extended ontology with DailyMediaPlan/PlanEntry classes and SHACL shapes, added generate-plan task to manifest, and wrote 48 passing rule tests.**

## What Happened

Created `rules_service.py` with the full rule lifecycle: `validate_rule` (normalisation + UUID generation), async CRUD via StateClient (`load_rules`, `save_rules`, `add_rule`, `update_rule`, `delete_rule`, `toggle_rule`), and the pure-function `evaluate_rules` which AND-matches conditions against context and sorts by priority descending. Time range conditions support midnight-wrapping (start > end).

Extended the media-scheduler ontology with `ms:DailyMediaPlan` and `ms:PlanEntry` OWL classes plus 8 new properties (planStatus, plan, mediaItem, slotStart, slotEnd, slotOrder, entryStatus, ruleId). Extended shapes with `DailyMediaPlanShape` and `PlanEntryShape` including `sh:in` constraints for status enums and PropertyGroups.

Added `generate-plan` task to the manifest with 6h interval. Updated the existing `test_manifest_has_one_task` to `test_manifest_has_tasks` asserting 2 tasks.

Wrote 48 new tests across 3 classes: `TestRuleValidation` (12 tests), `TestRuleCRUD` (15 tests), `TestRuleEvaluation` (21 tests) covering wildcards, priority ordering, time ranges, boundary conditions, midnight wrapping, disabled rules, empty inputs, and error cases.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v -k "rule or Rule"` — 48 passed
- `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py --tb=short -q` — 112 passed (all existing + new)
- Ontology check: DailyMediaPlan and PlanEntry classes present
- Manifest check: generate-plan task present
- Test count: 112 total (≥100 threshold met)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v -k "rule or Rule"` | 0 | ✅ pass | 0.27s |
| 2 | `python3 -c "import json; ... assert 'ms:DailyMediaPlan' in types and 'ms:PlanEntry' in types"` | 0 | ✅ pass | <1s |
| 3 | `python3 -c "import yaml; ... assert 'generate-plan' in ids"` | 0 | ✅ pass | <1s |
| 4 | `grep -c "async def test_\|def test_" backend/tests/test_media_scheduler.py` → 112 | 0 | ✅ pass | <1s |
| 5 | `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py --tb=short -q` — 112 passed | 0 | ✅ pass | 0.38s |
| 6 | `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v -k "invalid or error or empty"` — 20 passed | 0 | ✅ pass | 0.25s |

## Diagnostics

- **Rule evaluation:** Call `evaluate_rules(rules, context)` with any rules list + context dict. Returns full matched rule dicts sorted by priority — log `len(result)` and `[r['id'] for r in result]` for tracing.
- **State inspection:** `load_rules(state_client)` returns the current rules array. Rules are JSON in StateClient under key `schedule_rules`.
- **Validation errors:** `validate_rule()` raises `ValueError` with descriptive messages (e.g., "Rule must have a non-empty 'name' string", "Rule priority must be an integer").
- **Ontology:** New classes queryable via SPARQL once populated: `?plan a ms:DailyMediaPlan`, `?entry a ms:PlanEntry`.

## Deviations

- Fixed `_matches_condition` to fail-closed when `current_time` is missing from context but a `time_range` condition is specified. The initial implementation treated this as a pass-through (matching any context), but the test correctly identified this as unsafe — a time-scoped rule should not fire when the system can't determine the current time.
- Updated existing `test_manifest_has_one_task` → `test_manifest_has_tasks` to assert 2 tasks after adding generate-plan.

## Known Issues

None.

## Files Created/Modified

- `apps/media-scheduler/services/rules_service.py` — NEW: Rules CRUD + evaluation service (pure functions + async StateClient I/O)
- `models/media-scheduler/ontology/media-scheduler.jsonld` — MODIFIED: Added DailyMediaPlan, PlanEntry classes + 8 properties
- `models/media-scheduler/shapes/media-scheduler.jsonld` — MODIFIED: Added DailyMediaPlanShape, PlanEntryShape + PropertyGroups
- `apps/media-scheduler/manifest.yaml` — MODIFIED: Added generate-plan task with 6h interval
- `backend/tests/test_media_scheduler.py` — MODIFIED: Added 48 rule tests (TestRuleValidation, TestRuleCRUD, TestRuleEvaluation), updated manifest test
- `.gsd/milestones/M038/slices/S02/tasks/T01-PLAN.md` — MODIFIED: Added Observability Impact section
- `.gsd/milestones/M038/slices/S02/S02-PLAN.md` — MODIFIED: Added diagnostic verification step
