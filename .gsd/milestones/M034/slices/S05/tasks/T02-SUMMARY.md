---
id: T02
parent: S05
milestone: M034
provides:
  - 4 PPV review workflows (Weekly, Monthly, Quarterly, Yearly) seeded at app startup
  - Per-name idempotency for workflow seeding — never duplicates, never deletes user workflows
  - SEED_WORKFLOWS module-level constant for declarative seed workflow definitions
key_files:
  - backend/app/dashboard/seed.py
  - backend/tests/test_seed_data.py
key_decisions:
  - Per-name idempotency via set lookup on existing workflow names, replacing monolithic "skip all if any exist" check
  - SEED_WORKFLOWS as a module-level list constant so downstream code (e.g. command palette) can reference expected names
patterns_established:
  - Declarative seed data list with per-name idempotency (iterate definitions, skip if name in existing set)
observability_surfaces:
  - seed_sample_data() INFO log per workflow created with name + user_id
  - seed_sample_data() DEBUG log per skipped workflow
  - Return dict includes workflows_created int count for granular inspection
duration: 12m
verification_result: passed
completed_at: 2026-03-22T02:10:00-04:00
blocker_discovered: false
---

# T02: Seed PPV review workflows and fix idempotency

**Added 4 PPV review workflow seeds (Weekly/Monthly/Quarterly/Yearly) with per-name idempotency so user-created workflows are never affected and partial re-seeding works correctly**

## What Happened

Replaced the monolithic workflow seed block in `seed_sample_data()` with a declarative `SEED_WORKFLOWS` list containing 5 workflow definitions — the existing "Create & Review" plus 4 new PPV review workflows. Each review workflow has correct step configurations referencing real PPV view spec IRIs (`urn:sempkm:model:ppv:view-weekly-table`, etc.) and type IRIs (`urn:sempkm:model:ppv:WeeklyReview`, etc.).

Changed the seeding strategy from "skip all workflows if the user has any" to per-name checks: fetch existing workflows, build a set of existing names, iterate `SEED_WORKFLOWS`, skip if name already exists, create otherwise. This means:
- A fresh user gets all 5 seed workflows
- A user who already has some seed workflows gets only the missing ones
- User-created workflows are never deleted or overwritten
- Adding new seed workflows to the list in the future is automatically handled

Updated tests from 4 to 10, covering: fresh user gets all 5 workflows, step detail verification for each review type, full skip when all exist, idempotency across two seed calls, partial seeding with some existing, user workflow preservation, and mixed dashboard+workflow scenarios.

## Verification

All 10 seed data tests pass. All slice-level grep checks pass for this task's scope.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_seed_data.py -v` | 0 | ✅ pass (10/10) | 4.5s |
| 2 | `rg "Weekly Review" backend/app/dashboard/seed.py` | 0 | ✅ pass | <1s |
| 3 | `rg "Quarterly Review" backend/app/dashboard/seed.py` | 0 | ✅ pass | <1s |
| 4 | `python3 -c "import ast; ast.parse(open('backend/app/task_templates/service.py').read()); ast.parse(open('backend/app/task_templates/router.py').read()); print('OK')"` | 0 | ✅ pass | <1s |
| 5 | `rg "urn:sempkm:task-templates" backend/app/task_templates/service.py` | 0 | ✅ pass | <1s |
| 6 | `rg "logger\." backend/app/task_templates/service.py \| head -5` | 0 | ✅ pass | <1s |
| 7 | `rg "status_code=4" backend/app/task_templates/router.py` | 0 | ✅ pass | <1s |

## Diagnostics

- **Inspect seed definitions:** `python3 -c "from app.dashboard.seed import SEED_WORKFLOWS; print([w['name'] for w in SEED_WORKFLOWS])"` — shows all 5 expected names
- **Inspect seeded workflows at runtime:** `GET /api/workflow` returns all workflows for the user — review workflows appear with their step configurations
- **Structured logs:** At startup, each seeded workflow produces an INFO log line with name and user_id; skipped workflows produce DEBUG logs

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/dashboard/seed.py` — replaced monolithic workflow seed with declarative SEED_WORKFLOWS list and per-name idempotency
- `backend/tests/test_seed_data.py` — rewrote and expanded from 4 to 10 tests covering all idempotency scenarios
- `.gsd/milestones/M034/slices/S05/tasks/T02-PLAN.md` — added Observability Impact section (pre-flight fix)
