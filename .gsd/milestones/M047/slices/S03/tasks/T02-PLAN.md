---
estimated_steps: 15
estimated_files: 3
skills_used: []
---

# T02: Create PPV workflows JSON, update manifest, add dashboard_name→UUID resolution

Three pieces: (1) Create `models/ppv/workflows/ppv.json` with 5 workflow definitions. (2) Add `workflows: "workflows/ppv.json"` to `models/ppv/manifest.yaml`. (3) Add ~15 lines of dashboard_name→UUID post-processing in `ModelService.install()` so workflow steps with `dashboard_name` configs get resolved to real `dashboard_id` values at install time.

**Workflows to create:**
1. **Daily Check-in** — form step (create ActionItem), view step (action-kanban)
2. **Weekly Review** — dashboard step (Action Items dashboard), view step (weekly-table), form step (create WeeklyReview), dashboard step (Review Hub dashboard)
3. **Monthly Review** — view step (monthly-table), dashboard step (Review Hub), view step (weekly-table), form step (create MonthlyReview), view step (goaloutcome-table)
4. **Quarterly Review** — view step (quarterly-table), form step (create QuarterlyReview), dashboard step (Goals Overview), view step (valuegoal-table)
5. **Yearly Review** — view step (yearly-table), form step (create YearlyReview), dashboard step (Life Dashboard), view step (hierarchy-graph)

**Workflow step types:**
- `{"type": "view", "label": "...", "config": {"spec_iri": "urn:sempkm:model:ppv:view-XXX", "renderer_type": "table|graph|kanban"}}` — for ViewSpec steps
- `{"type": "dashboard", "label": "...", "config": {"dashboard_name": "Action Items"}}` — for dashboard steps (resolved to dashboard_id at install time)
- `{"type": "form", "label": "...", "config": {"target_class": "urn:sempkm:model:ppv:WeeklyReview"}}` — for form steps

**dashboard_name resolution in ModelService.install():**
The install sequence already creates dashboards before workflows (lines ~490-510 in models.py). After the dashboard creation loop, collect `{name: dashboard_data.id}` into a dict. Before creating each workflow, iterate its steps and replace any `config.dashboard_name` with `config.dashboard_id` using the mapping. If a referenced name isn't found, log a warning and leave the step as-is (degraded mode consistent with D380).

Same resolution must be added to `refresh_artifacts()` which does delete+recreate of TBox surfaces.

**Manifest update:** Add `workflows: "workflows/ppv.json"` under the `entrypoints:` section in `models/ppv/manifest.yaml`.

## Inputs

- ``models/ppv/dashboards/ppv.json` — T01 output: 5 dashboard names needed for dashboard_name references in workflows`
- ``models/ppv/views/ppv.jsonld` — ViewSpec IRIs for view step configs`
- ``models/ppv/manifest.yaml` — existing manifest to add workflows entrypoint`
- ``backend/app/services/models.py` — ModelService.install() and refresh_artifacts() to add dashboard_name resolution`

## Expected Output

- ``models/ppv/workflows/ppv.json` — 5 PPV workflow definitions with view/dashboard/form steps`
- ``models/ppv/manifest.yaml` — updated with workflows entrypoint`
- ``backend/app/services/models.py` — dashboard_name→UUID resolution in install() and refresh_artifacts()`

## Verification

python3 -c "import json; w=json.load(open('models/ppv/workflows/ppv.json')); assert len(w['workflows'])==5, f'Expected 5, got {len(w["workflows"])}'; print('OK: 5 workflows')" && python3 -c "import yaml; m=yaml.safe_load(open('models/ppv/manifest.yaml')); assert m['entrypoints'].get('workflows')=='workflows/ppv.json', 'Missing workflows entrypoint'; print('OK: manifest has workflows entrypoint')" && cd backend && .venv/bin/python -m pytest tests/test_tbox_lifecycle.py -v
