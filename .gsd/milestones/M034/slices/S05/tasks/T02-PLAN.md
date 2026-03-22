---
estimated_steps: 3
estimated_files: 2
skills_used:
  - test
  - best-practices
---

# T02: Seed PPV review workflows and fix idempotency

**Slice:** S05 — Task Templates & Review Workflows
**Milestone:** M034

## Description

Extend `seed_sample_data()` to create 4 PPV review workflows (weekly, monthly, quarterly, yearly) using existing PPV view spec IRIs and type IRIs. Fix the current idempotency logic: it currently skips ALL workflow seeding if the user has any workflow. Change to per-name checks so review workflows are seeded even when user-created workflows exist, and repeat seeding doesn't duplicate.

## Steps

1. **Update `backend/app/dashboard/seed.py`** — Replace the monolithic workflow seed block with a list-based approach:
   - Define `SEED_WORKFLOWS` list containing 5 workflow definitions: the existing "Create & Review" + 4 new review workflows
   - Each definition: `{"name": str, "description": str, "steps": list[dict]}`
   - Weekly Review (4 steps): (1) view ppv:view-weekly-table "Past Reviews", (2) view ppv:view-action-table "Completed Work", (3) form ppv:WeeklyReview "Create Review", (4) view ppv:view-review-graph "Confirm"
   - Monthly Review (4 steps): (1) view ppv:view-monthly-table "Past Reviews", (2) view ppv:view-weekly-table "This Month's Weeks", (3) form ppv:MonthlyReview "Create Review", (4) view ppv:view-goaloutcome-table "Goal Progress"
   - Quarterly Review (3 steps): (1) view ppv:view-quarterly-table "Past Reviews", (2) form ppv:QuarterlyReview "Create Review", (3) view ppv:view-valuegoal-table "Goals Overview"
   - Yearly Review (3 steps): (1) view ppv:view-yearly-table "Past Reviews", (2) form ppv:YearlyReview "Create Review", (3) view ppv:view-hierarchy-graph "Full Hierarchy"
   - Change workflow seeding: fetch existing workflows, build set of existing names, iterate SEED_WORKFLOWS, skip if name already in set, create otherwise
   - Track created count in result dict: `"workflows_created": <int>` (replaces boolean `workflow_created`)
   - Update the function signature/return to be backward-compatible: keep `workflow_created` key as `True` if any workflow was created

2. **Update `backend/tests/test_seed_data.py`** — Adjust existing tests and add new ones:
   - Update `test_seed_creates_dashboard_and_workflow_when_empty`: verify `workflow_service.create` called 5 times (1 existing + 4 reviews), check that "Weekly Review", "Monthly Review", "Quarterly Review", "Yearly Review" names appear in create calls
   - Update `test_seed_skips_when_data_already_exists`: mock `list_for_user` returning workflows with all 5 expected names → verify `create` not called for workflows
   - Add `test_seed_review_workflows_idempotent`: call seed twice (second call has first call's names in the returned list) → verify only called once per name
   - Add `test_seed_preserves_user_workflows`: mock existing workflow list with user's custom workflow "My Flow" → seed should still create all 5 seed workflows → verify "My Flow" not affected (no delete calls)
   - Add `test_seed_partial_review_workflows`: mock existing with only "Create & Review" and "Weekly Review" → seed should create the other 3 reviews only

3. **Verify all tests pass** — Run `cd backend && .venv/bin/python -m pytest tests/test_seed_data.py -v`

## Must-Haves

- [ ] 4 PPV review workflows with correct step configurations referencing real PPV view spec IRIs and type IRIs
- [ ] Per-name idempotency: each seed workflow checked individually, not "skip all if any exist"
- [ ] Existing "Create & Review" workflow preserved in seed list
- [ ] User-created workflows never deleted or overwritten
- [ ] Updated + new tests covering idempotency and partial seed scenarios

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_seed_data.py -v` — all tests pass
- `rg "Weekly Review" backend/app/dashboard/seed.py` — confirms review workflow definition
- `rg "Quarterly Review" backend/app/dashboard/seed.py` — confirms all 4 review types present

## Inputs

- `backend/app/dashboard/seed.py` — current seed_sample_data function
- `backend/tests/test_seed_data.py` — current seed tests
- `backend/app/workflow/service.py` — WorkflowService.create() signature: (user_id, name, steps, description)
- `models/ppv/views/ppv.jsonld` — PPV view spec IRIs: ppv:view-weekly-table, ppv:view-monthly-table, ppv:view-quarterly-table, ppv:view-yearly-table, ppv:view-review-graph, ppv:view-hierarchy-graph, ppv:view-action-table, ppv:view-goaloutcome-table, ppv:view-valuegoal-table
- `models/ppv/ontology/ppv.jsonld` — PPV type IRIs: ppv:WeeklyReview, ppv:MonthlyReview, ppv:QuarterlyReview, ppv:YearlyReview

## Expected Output

- `backend/app/dashboard/seed.py` — updated with 4 review workflow definitions and per-name idempotency
- `backend/tests/test_seed_data.py` — updated and extended tests for review workflow seeding
