---
estimated_steps: 12
estimated_files: 3
skills_used: []
---

# T03: Migrate seed.py workflows + add tests for resolution and content validation

Three pieces: (1) Remove the 4 PPV-specific workflows from `SEED_WORKFLOWS` in seed.py, keeping only "Create & Review". (2) Add test coverage for dashboard_name→UUID resolution in ModelService. (3) Update existing tbox_loader tests and add real PPV workflows content validation.

**seed.py changes:** Remove "Weekly Review", "Monthly Review", "Quarterly Review", "Yearly Review" entries from `SEED_WORKFLOWS` list. Keep "Create & Review" (generic, no PPV references). Remove the `_PPV` namespace constant since it's no longer used.

**Tests to add/update in `test_tbox_lifecycle.py`:**
- `test_install_v2_resolves_dashboard_names` — create a v2 manifest with workflow steps containing `dashboard_name` references → verify after install, workflow steps have `dashboard_id` (not `dashboard_name`)
- `test_install_v2_unresolved_dashboard_name_logs_warning` — workflow references a dashboard name that doesn't exist in the model → verify install succeeds (degraded mode) and step retains `dashboard_name`

**Tests to add/update in `test_tbox_loader.py`:**
- `test_real_ppv_workflows` — load real PPV workflows file, verify 5 workflows with expected names and step counts
- Update `test_real_ppv_dashboards` assertion: `len(result) >= 5` (previously >= 1)

**Tests to add in `test_data_widgets.py` or standalone:**
- `test_seed_workflows_count` — verify SEED_WORKFLOWS has exactly 1 entry ("Create & Review")

**Verification of seed.py:**
`python3 -c "from app.dashboard.seed import SEED_WORKFLOWS; assert len(SEED_WORKFLOWS)==1, f'Expected 1, got {len(SEED_WORKFLOWS)}'; print('OK: 1 seed workflow')"` (run from backend/)

## Inputs

- ``backend/app/dashboard/seed.py` — existing seed with 5 workflows to trim to 1`
- ``backend/tests/test_tbox_lifecycle.py` — existing 13 tests to extend with dashboard_name resolution tests`
- ``backend/tests/test_tbox_loader.py` — existing 14 tests to extend with real PPV workflows validation`
- ``models/ppv/workflows/ppv.json` — T02 output: real workflows file to validate in tests`
- ``models/ppv/dashboards/ppv.json` — T01 output: real dashboards file (test_real_ppv_dashboards assertion update)`
- ``backend/app/services/models.py` — T02 output: dashboard_name resolution code to test`

## Expected Output

- ``backend/app/dashboard/seed.py` — SEED_WORKFLOWS trimmed to 1 entry`
- ``backend/tests/test_tbox_lifecycle.py` — 2+ new tests for dashboard_name resolution`
- ``backend/tests/test_tbox_loader.py` — updated test_real_ppv_dashboards + new test_real_ppv_workflows`

## Verification

cd backend && .venv/bin/python -m pytest tests/test_tbox_loader.py tests/test_tbox_lifecycle.py -v && .venv/bin/python -c "from app.dashboard.seed import SEED_WORKFLOWS; assert len(SEED_WORKFLOWS)==1; print('OK: 1 seed workflow')"
