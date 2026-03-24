---
id: T02
parent: S02
milestone: M038
provides:
  - plan_service.py with generate_plan(), build_item_query(), allocate_slots(), fetch_context()
  - generate-plan task handler in app.py
  - 39 new plan-related unit tests (IRI minting, query building, slot allocation, context fetch, plan generation, task handler)
key_files:
  - apps/media-scheduler/services/plan_service.py
  - apps/media-scheduler/app.py
  - backend/tests/test_media_scheduler.py
key_decisions:
  - Context fetch failure produces empty plan with warning, not crash — fail-safe for missing context API
  - Old plan entries patched to "replaced" status via object.patch, not deleted — avoids needing object.delete permission
  - Items deduped by IRI across multiple matched rules — prevents duplicate entries when rules overlap
  - Unknown source types default to 1800s duration — safe fallback
patterns_established:
  - plan_service uses same importlib fallback pattern as app.py for test-context compatibility
  - generate_plan returns structured summary dict for scheduler logging
  - build_item_query generates SPARQL with 3 action types (source_type, source_iri, category)
  - allocate_slots is pure function (no I/O) — takes items list + start_hour, returns slot dicts
observability_surfaces:
  - logger.info on plan generation with rules matched count, items selected, entries created
  - logger.warning on context fetch failure, empty context, item query failure, entry patch failure
  - logger.error on plan creation failure
  - generate_plan returns {plan_iri, date, rules_matched, entries_created, optional error}
duration: 15m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T02: Plan generation service + task handler

**Created plan_service.py with full plan generation orchestration (rules→items→slots→RDF), wired generate-plan task handler in app.py, and added 39 plan-related tests bringing total to 164.**

## What Happened

Created `plan_service.py` with the complete plan generation pipeline: `mint_plan_iri`/`mint_entry_iri` for deterministic IRI minting, `build_item_query` generating SPARQL SELECT for three action types (source_type, source_iri, category), `allocate_slots` for sequential time-slot assignment with default durations (1800s podcast, 900s youtube, 240s spotify), `fetch_context` for resilient context API calls, `get_existing_plan_entries` for finding old entries, and `generate_plan` orchestrating the full flow: context→rules→items→dedup→slots→patch-old→bulk-create.

Added the `generate-plan` task handler to `app.py` using the same importlib fallback pattern for plan_service import. The handler simply delegates to `generate_plan(ctx)`.

Added 39 new tests across 6 test classes: `TestPlanIriMinting` (8), `TestBuildItemQuery` (9), `TestAllocateSlots` (14), `TestFetchContext` (4), `TestGetExistingPlanEntries` (3), `TestGeneratePlan` (12 including dedup, patching, context override, error handling), and `TestGeneratePlanTask` (1). Total test count: 164.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v -k "plan or Plan or slot or Slot"` — 39 passed
- `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py --tb=short -q` — 164 passed
- `grep -c "generate_plan\|generate-plan" apps/media-scheduler/app.py` → 6 (≥2 threshold)
- `grep -c "async def test_\|def test_" backend/tests/test_media_scheduler.py` → 164 (≥100 threshold)
- `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v -k "invalid or error or empty"` — 31 passed

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v -k "plan or Plan or slot or Slot"` | 0 | ✅ pass | 0.36s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py --tb=short -q` — 164 passed | 0 | ✅ pass | 0.39s |
| 3 | `grep -c "generate_plan\|generate-plan" apps/media-scheduler/app.py` → 6 | 0 | ✅ pass | <1s |
| 4 | `grep -c "async def test_\|def test_" backend/tests/test_media_scheduler.py` → 164 | 0 | ✅ pass | <1s |
| 5 | `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v -k "invalid or error or empty"` — 31 passed | 0 | ✅ pass | 0.27s |

## Diagnostics

- **Plan generation:** Call `generate_plan(ctx, date_str="YYYY-MM-DD", context_override={...})` with mock or real context. Returns `{plan_iri, date, rules_matched, entries_created}`. Empty dict context triggers early exit with warning.
- **Query inspection:** `build_item_query({"type": "source_type", "value": "podcast"})` returns the SPARQL SELECT string for inspection.
- **Slot math:** `allocate_slots(items, start_hour=8)` is pure — call with any items list to verify slot chaining.
- **Context fetch:** `await fetch_context(http_client)` returns dict on success, empty dict on any failure (logged warning).
- **Existing entries:** `await get_existing_plan_entries(graph_client, plan_iri)` returns list of entry IRIs.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `apps/media-scheduler/services/plan_service.py` — NEW: Plan generation service with orchestration, SPARQL building, slot allocation, context fetch
- `apps/media-scheduler/app.py` — MODIFIED: Added plan_service import (with importlib fallback) and generate-plan task handler
- `backend/tests/test_media_scheduler.py` — MODIFIED: Added 39 plan tests across 6 new test classes, plus generate_plan_task import
- `.gsd/milestones/M038/slices/S02/tasks/T02-PLAN.md` — MODIFIED: Added Observability Impact section
